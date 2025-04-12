"""
Topic Modeling module for WiseFlow.

This module provides functionality for identifying topics across collected content
using both statistical (LDA) and LLM-based approaches.
"""

import os
import json
import re
import logging
from typing import List, Dict, Any, Optional, Tuple, Set, Union
from collections import Counter, defaultdict
import uuid
from datetime import datetime

# Import necessary libraries for statistical topic modeling
try:
    import numpy as np
    from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
    from sklearn.decomposition import LatentDirichletAllocation, NMF
    import matplotlib.pyplot as plt
    import networkx as nx
    STATISTICAL_AVAILABLE = True
except ImportError:
    STATISTICAL_AVAILABLE = False
    
# Import from other modules
from ..utils.general_utils import get_logger
from ..utils.pb_api import PbTalker
from ..llms.openai_wrapper import openai_llm as llm

# Set up logging
project_dir = os.environ.get("PROJECT_DIR", "")
if project_dir:
    os.makedirs(project_dir, exist_ok=True)
topic_modeling_logger = get_logger('topic_modeling', project_dir)
pb = PbTalker(topic_modeling_logger)

# Get the model from environment variables
model = os.environ.get("PRIMARY_MODEL", "")
if not model:
    raise ValueError("PRIMARY_MODEL not set, please set it in environment variables or edit core/.env")

# Prompts for LLM-based topic modeling
TOPIC_IDENTIFICATION_PROMPT = """You are an expert in topic modeling and content analysis. Your task is to identify the main topics in the provided collection of texts.

Please analyze the following content and identify 5-10 distinct topics that represent the main themes across these texts.

Content to analyze:
{text}

For each topic you identify, provide:
1. A concise topic label (2-5 words)
2. A brief description of the topic (1-2 sentences)
3. A confidence score (0-100) indicating how strongly this topic is represented in the content
4. 3-5 key terms or phrases that are most representative of this topic

Format your response as a JSON array of objects with the following structure:
[
  {
    "topic": "topic label",
    "description": "brief description",
    "confidence": confidence_score,
    "key_terms": ["term1", "term2", "term3"]
  },
  ...
]
"""

HIERARCHICAL_TOPIC_PROMPT = """You are an expert in hierarchical topic modeling. Your task is to organize the provided topics into a hierarchical structure.

Here are the topics that have been identified:
{topics}

Please organize these topics into a hierarchical structure with:
1. 2-4 high-level parent topics that represent broad themes
2. The existing topics organized as child topics under these parent topics
3. For each parent topic, provide a concise label and brief description

Format your response as a JSON object with the following structure:
{
  "hierarchy": [
    {
      "parent_topic": "parent topic label",
      "description": "brief description of parent topic",
      "child_topics": ["child topic 1", "child topic 2", ...]
    },
    ...
  ]
}
"""

class Topic:
    """Represents a topic identified in the content."""
    
    def __init__(
        self,
        topic_id: str,
        label: str,
        description: str,
        confidence: float,
        key_terms: List[str],
        documents: List[str] = None,
        parent_topic: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ):
        """Initialize a topic."""
        self.topic_id = topic_id
        self.label = label
        self.description = description
        self.confidence = confidence
        self.key_terms = key_terms
        self.documents = documents or []
        self.parent_topic = parent_topic
        self.metadata = metadata or {}
        self.timestamp = timestamp or datetime.now()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the topic to a dictionary."""
        return {
            "topic_id": self.topic_id,
            "label": self.label,
            "description": self.description,
            "confidence": self.confidence,
            "key_terms": self.key_terms,
            "documents": self.documents,
            "parent_topic": self.parent_topic,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Topic':
        """Create a topic from a dictionary."""
        timestamp = None
        if data.get("timestamp"):
            try:
                timestamp = datetime.fromisoformat(data["timestamp"])
            except (ValueError, TypeError):
                pass
                
        return cls(
            topic_id=data.get("topic_id", str(uuid.uuid4())),
            label=data.get("label", ""),
            description=data.get("description", ""),
            confidence=data.get("confidence", 0.0),
            key_terms=data.get("key_terms", []),
            documents=data.get("documents", []),
            parent_topic=data.get("parent_topic"),
            metadata=data.get("metadata", {}),
            timestamp=timestamp
        )


class TopicModelingResult:
    """Represents the result of a topic modeling operation."""
    
    def __init__(
        self,
        result_id: str,
        topics: List[Topic],
        method: str,
        parameters: Dict[str, Any],
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize a topic modeling result."""
        self.result_id = result_id
        self.topics = topics
        self.method = method
        self.parameters = parameters
        self.timestamp = timestamp or datetime.now()
        self.metadata = metadata or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the result to a dictionary."""
        return {
            "result_id": self.result_id,
            "topics": [topic.to_dict() for topic in self.topics],
            "method": self.method,
            "parameters": self.parameters,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TopicModelingResult':
        """Create a result from a dictionary."""
        timestamp = None
        if data.get("timestamp"):
            try:
                timestamp = datetime.fromisoformat(data["timestamp"])
            except (ValueError, TypeError):
                pass
                
        topics = [Topic.from_dict(topic_data) for topic_data in data.get("topics", [])]
        
        return cls(
            result_id=data.get("result_id", str(uuid.uuid4())),
            topics=topics,
            method=data.get("method", ""),
            parameters=data.get("parameters", {}),
            timestamp=timestamp,
            metadata=data.get("metadata", {})
        )
    
    def get_topic_by_id(self, topic_id: str) -> Optional[Topic]:
        """Get a topic by its ID."""
        for topic in self.topics:
            if topic.topic_id == topic_id:
                return topic
        return None
    
    def get_topics_by_parent(self, parent_id: Optional[str]) -> List[Topic]:
        """Get all topics with the specified parent ID."""
        return [topic for topic in self.topics if topic.parent_topic == parent_id]
    
    def get_hierarchical_structure(self) -> Dict[str, Any]:
        """Get the hierarchical structure of topics."""
        result = {"hierarchy": []}
        
        # Get all parent topics (those without a parent)
        parent_topics = self.get_topics_by_parent(None)
        
        for parent in parent_topics:
            # Get all child topics for this parent
            children = self.get_topics_by_parent(parent.topic_id)
            
            parent_data = {
                "parent_topic": parent.label,
                "description": parent.description,
                "child_topics": [child.label for child in children]
            }
            
            result["hierarchy"].append(parent_data)
            
        return result
    
    def visualize(self, output_path: Optional[str] = None) -> None:
        """Visualize the topic model as a network graph."""
        if not STATISTICAL_AVAILABLE:
            topic_modeling_logger.warning("Visualization requires matplotlib and networkx. Please install them.")
            return
            
        # Create a graph
        G = nx.Graph()
        
        # Add topic nodes
        for topic in self.topics:
            # Size based on confidence
            size = 100 + (topic.confidence * 5)
            
            # Color based on whether it's a parent or child
            color = 'skyblue' if topic.parent_topic is None else 'lightgreen'
            
            G.add_node(topic.label, size=size, color=color, type='topic')
            
            # Add key terms as smaller nodes
            for term in topic.key_terms:
                G.add_node(term, size=50, color='lightgray', type='term')
                G.add_edge(topic.label, term, weight=1)
        
        # Add edges between parent and child topics
        for topic in self.topics:
            if topic.parent_topic:
                parent = self.get_topic_by_id(topic.parent_topic)
                if parent:
                    G.add_edge(parent.label, topic.label, weight=3)
        
        # Create the visualization
        plt.figure(figsize=(12, 10))
        
        # Get node positions
        pos = nx.spring_layout(G, k=0.3)
        
        # Draw nodes
        node_sizes = [G.nodes[node].get('size', 100) for node in G.nodes()]
        node_colors = [G.nodes[node].get('color', 'skyblue') for node in G.nodes()]
        
        nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color=node_colors, alpha=0.8)
        
        # Draw edges
        edge_weights = [G.edges[edge].get('weight', 1) for edge in G.edges()]
        nx.draw_networkx_edges(G, pos, width=edge_weights, alpha=0.5)
        
        # Draw labels
        topic_labels = {node: node for node in G.nodes() if G.nodes[node].get('type') == 'topic'}
        term_labels = {node: node for node in G.nodes() if G.nodes[node].get('type') == 'term'}
        
        nx.draw_networkx_labels(G, pos, labels=topic_labels, font_size=12, font_weight='bold')
        nx.draw_networkx_labels(G, pos, labels=term_labels, font_size=8)
        
        plt.title(f"Topic Model: {self.method}")
        plt.axis('off')
        
        # Save or show the visualization
        if output_path:
            plt.savefig(output_path, bbox_inches='tight', dpi=300)
            topic_modeling_logger.info(f"Visualization saved to {output_path}")
        else:
            plt.show()


class TopicModeler:
    """Class for performing topic modeling on collected content."""
    
    def __init__(self, logger=None):
        """Initialize the topic modeler."""
        self.logger = logger or topic_modeling_logger
        
    def _preprocess_text(self, documents: List[str]) -> List[str]:
        """Preprocess text for topic modeling."""
        processed_docs = []
        
        for doc in documents:
            if not doc:
                continue
                
            # Convert to lowercase
            text = doc.lower()
            
            # Remove URLs
            text = re.sub(r'https?://\S+|www\.\S+', '', text)
            
            # Remove special characters and digits
            text = re.sub(r'[^\w\s]', '', text)
            text = re.sub(r'\d+', '', text)
            
            # Remove extra whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            
            if text:
                processed_docs.append(text)
                
        return processed_docs
    
    def _extract_key_terms(self, vectorizer, lda_model, n_top_words=5) -> List[List[str]]:
        """Extract key terms for each topic."""
        feature_names = vectorizer.get_feature_names_out()
        key_terms = []
        
        for topic_idx, topic in enumerate(lda_model.components_):
            top_features_idx = topic.argsort()[:-n_top_words - 1:-1]
            top_features = [feature_names[i] for i in top_features_idx]
            key_terms.append(top_features)
            
        return key_terms
    
    def statistical_topic_modeling(
        self, 
        documents: List[str], 
        n_topics: int = 5,
        method: str = 'lda',
        min_df: int = 2,
        max_df: float = 0.95,
        n_top_words: int = 5
    ) -> TopicModelingResult:
        """
        Perform statistical topic modeling using LDA or NMF.
        
        Args:
            documents: List of text documents
            n_topics: Number of topics to extract
            method: Method to use ('lda' or 'nmf')
            min_df: Minimum document frequency for terms
            max_df: Maximum document frequency for terms
            n_top_words: Number of top words to extract per topic
            
        Returns:
            TopicModelingResult object
        """
        if not STATISTICAL_AVAILABLE:
            self.logger.error("Statistical topic modeling requires scikit-learn. Please install it.")
            raise ImportError("Statistical topic modeling requires scikit-learn. Please install it.")
            
        # Preprocess documents
        processed_docs = self._preprocess_text(documents)
        
        if len(processed_docs) < 2:
            self.logger.error("Not enough documents for statistical topic modeling.")
            raise ValueError("Not enough documents for statistical topic modeling.")
            
        # Create vectorizer
        if method.lower() == 'nmf':
            vectorizer = TfidfVectorizer(max_df=max_df, min_df=min_df, stop_words='english')
        else:  # LDA
            vectorizer = CountVectorizer(max_df=max_df, min_df=min_df, stop_words='english')
            
        # Transform documents to document-term matrix
        X = vectorizer.fit_transform(processed_docs)
        
        # Apply topic modeling
        if method.lower() == 'nmf':
            model = NMF(n_components=n_topics, random_state=42)
        else:  # LDA
            model = LatentDirichletAllocation(
                n_components=n_topics, 
                max_iter=10, 
                learning_method='online',
                random_state=42
            )
            
        model.fit(X)
        
        # Get document-topic distributions
        doc_topic_dists = model.transform(X)
        
        # Extract key terms for each topic
        key_terms_lists = self._extract_key_terms(vectorizer, model, n_top_words)
        
        # Create Topic objects
        topics = []
        for i in range(n_topics):
            # Get documents that are strongly associated with this topic
            topic_docs = []
            for doc_idx, doc_dist in enumerate(doc_topic_dists):
                if doc_dist[i] > 0.3:  # Document has significant association with topic
                    if doc_idx < len(documents):
                        topic_docs.append(documents[doc_idx])
            
            # Create a topic object
            topic = Topic(
                topic_id=str(uuid.uuid4()),
                label=f"Topic {i+1}",
                description=f"Automatically generated topic {i+1}",
                confidence=float(np.mean(doc_topic_dists[:, i]) * 100),
                key_terms=key_terms_lists[i],
                documents=topic_docs
            )
            topics.append(topic)
            
        # Create result object
        result = TopicModelingResult(
            result_id=str(uuid.uuid4()),
            topics=topics,
            method=f"statistical_{method.lower()}",
            parameters={
                "n_topics": n_topics,
                "min_df": min_df,
                "max_df": max_df,
                "n_top_words": n_top_words
            }
        )
        
        return result
    
    def llm_topic_modeling(
        self, 
        documents: List[str],
        n_topics: int = 5,
        hierarchical: bool = True
    ) -> TopicModelingResult:
        """
        Perform LLM-based topic modeling.
        
        Args:
            documents: List of text documents
            n_topics: Suggested number of topics (may be adjusted by LLM)
            hierarchical: Whether to create a hierarchical topic structure
            
        Returns:
            TopicModelingResult object
        """
        # Combine documents into a single text for analysis
        combined_text = "\n\n---\n\n".join(documents)
        
        # Prepare the prompt
        prompt = TOPIC_IDENTIFICATION_PROMPT.format(text=combined_text)
        
        # Get topics from LLM
        self.logger.info("Requesting topic identification from LLM")
        response = llm(prompt, model=model)
        
        # Parse the response
        try:
            # Extract JSON from the response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                topics_data = json.loads(json_str)
            else:
                self.logger.warning("Could not extract JSON from LLM response. Using full response.")
                topics_data = json.loads(response)
                
            # Create Topic objects
            topics = []
            for topic_data in topics_data:
                # Create a topic object
                topic = Topic(
                    topic_id=str(uuid.uuid4()),
                    label=topic_data.get("topic", f"Topic {len(topics)+1}"),
                    description=topic_data.get("description", ""),
                    confidence=float(topic_data.get("confidence", 50.0)),
                    key_terms=topic_data.get("key_terms", []),
                    documents=[]  # We'll assign documents later
                )
                topics.append(topic)
                
            # If hierarchical, create a hierarchical structure
            if hierarchical and len(topics) > 3:
                # Prepare the prompt for hierarchical organization
                topics_json = json.dumps([{
                    "topic": t.label,
                    "description": t.description,
                    "key_terms": t.key_terms
                } for t in topics], indent=2)
                
                hierarchy_prompt = HIERARCHICAL_TOPIC_PROMPT.format(topics=topics_json)
                
                # Get hierarchical structure from LLM
                self.logger.info("Requesting hierarchical topic organization from LLM")
                hierarchy_response = llm(hierarchy_prompt, model=model)
                
                try:
                    # Extract JSON from the response
                    json_match = re.search(r'\{.*\}', hierarchy_response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        hierarchy_data = json.loads(json_str)
                    else:
                        self.logger.warning("Could not extract JSON from LLM hierarchy response. Using full response.")
                        hierarchy_data = json.loads(hierarchy_response)
                    
                    # Create parent topics and update child topics
                    parent_topics = []
                    for parent_data in hierarchy_data.get("hierarchy", []):
                        # Create parent topic
                        parent_topic = Topic(
                            topic_id=str(uuid.uuid4()),
                            label=parent_data.get("parent_topic", f"Parent Topic {len(parent_topics)+1}"),
                            description=parent_data.get("description", ""),
                            confidence=90.0,  # High confidence for parent topics
                            key_terms=[],  # Parent topics don't have key terms
                            documents=[]
                        )
                        parent_topics.append(parent_topic)
                        
                        # Update child topics
                        child_labels = parent_data.get("child_topics", [])
                        for topic in topics:
                            if topic.label in child_labels:
                                topic.parent_topic = parent_topic.topic_id
                                
                    # Add parent topics to the list
                    topics.extend(parent_topics)
                    
                except (json.JSONDecodeError, ValueError) as e:
                    self.logger.error(f"Error parsing hierarchical structure: {e}")
                    # Continue without hierarchical structure
            
            # Assign documents to topics
            # This is a simple approach - in a real implementation, you might use
            # more sophisticated methods to determine which documents belong to which topics
            for doc in documents:
                best_topic = None
                best_score = -1
                
                for topic in topics:
                    # Skip parent topics
                    if not topic.key_terms:
                        continue
                        
                    # Calculate a simple relevance score
                    score = 0
                    for term in topic.key_terms:
                        if term.lower() in doc.lower():
                            score += 1
                            
                    if score > best_score:
                        best_score = score
                        best_topic = topic
                        
                if best_topic and best_score > 0:
                    best_topic.documents.append(doc)
            
            # Create result object
            result = TopicModelingResult(
                result_id=str(uuid.uuid4()),
                topics=topics,
                method="llm_based",
                parameters={
                    "n_topics": n_topics,
                    "hierarchical": hierarchical,
                    "model": model
                }
            )
            
            return result
            
        except (json.JSONDecodeError, ValueError) as e:
            self.logger.error(f"Error parsing LLM response: {e}")
            self.logger.error(f"Response: {response}")
            raise ValueError(f"Error parsing LLM response: {e}")
    
    def identify_topics(
        self, 
        documents: List[str],
        method: str = 'llm',
        n_topics: int = 5,
        hierarchical: bool = True,
        **kwargs
    ) -> TopicModelingResult:
        """
        Identify topics in the provided documents.
        
        Args:
            documents: List of text documents
            method: Method to use ('llm', 'lda', or 'nmf')
            n_topics: Number of topics to extract
            hierarchical: Whether to create a hierarchical topic structure (LLM only)
            **kwargs: Additional parameters for the specific method
            
        Returns:
            TopicModelingResult object
        """
        if not documents:
            self.logger.error("No documents provided for topic modeling.")
            raise ValueError("No documents provided for topic modeling.")
            
        # Choose the appropriate method
        if method.lower() == 'llm':
            return self.llm_topic_modeling(
                documents=documents,
                n_topics=n_topics,
                hierarchical=hierarchical
            )
        elif method.lower() in ['lda', 'nmf']:
            if not STATISTICAL_AVAILABLE:
                self.logger.warning("Statistical methods not available. Falling back to LLM.")
                return self.llm_topic_modeling(
                    documents=documents,
                    n_topics=n_topics,
                    hierarchical=hierarchical
                )
            else:
                return self.statistical_topic_modeling(
                    documents=documents,
                    n_topics=n_topics,
                    method=method,
                    **kwargs
                )
        else:
            self.logger.error(f"Unknown topic modeling method: {method}")
            raise ValueError(f"Unknown topic modeling method: {method}")
    
    def save_result(self, result: TopicModelingResult, output_path: str) -> None:
        """Save the topic modeling result to a file."""
        with open(output_path, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)
        self.logger.info(f"Topic modeling result saved to {output_path}")
    
    def load_result(self, input_path: str) -> TopicModelingResult:
        """Load a topic modeling result from a file."""
        with open(input_path, 'r') as f:
            data = json.load(f)
        return TopicModelingResult.from_dict(data)


# Function to identify topics in a collection of documents
def identify_topics(
    documents: List[str],
    method: str = 'llm',
    n_topics: int = 5,
    hierarchical: bool = True,
    output_path: Optional[str] = None,
    visualization_path: Optional[str] = None,
    **kwargs
) -> TopicModelingResult:
    """
    Identify topics in a collection of documents.
    
    Args:
        documents: List of text documents
        method: Method to use ('llm', 'lda', or 'nmf')
        n_topics: Number of topics to extract
        hierarchical: Whether to create a hierarchical topic structure (LLM only)
        output_path: Path to save the result (optional)
        visualization_path: Path to save the visualization (optional)
        **kwargs: Additional parameters for the specific method
        
    Returns:
        TopicModelingResult object
    """
    modeler = TopicModeler()
    
    result = modeler.identify_topics(
        documents=documents,
        method=method,
        n_topics=n_topics,
        hierarchical=hierarchical,
        **kwargs
    )
    
    # Save the result if requested
    if output_path:
        modeler.save_result(result, output_path)
    
    # Create visualization if requested
    if visualization_path:
        result.visualize(visualization_path)
    
    return result


# Function to load documents from PocketBase
def load_documents_from_pb(
    focus_point: Optional[str] = None,
    limit: int = 100,
    min_length: int = 50
) -> List[str]:
    """
    Load documents from PocketBase.
    
    Args:
        focus_point: Focus point to filter by (optional)
        limit: Maximum number of documents to load
        min_length: Minimum document length
        
    Returns:
        List of documents
    """
    # Query parameters
    params = {
        "sort": "-created",
        "expand": "tag",
        "perPage": limit
    }
    
    # Add focus point filter if provided
    if focus_point:
        # Get focus point ID
        focus_points = pb.get_all_records("focus_points", {"filter": f'focuspoint="{focus_point}"'})
        if focus_points and len(focus_points) > 0:
            focus_id = focus_points[0]["id"]
            params["filter"] = f'tag="{focus_id}"'
    
    # Get records
    records = pb.get_all_records("infos", params)
    
    # Extract content
    documents = []
    for record in records:
        content = record.get("content", "")
        if content and len(content) >= min_length:
            documents.append(content)
    
    return documents


# Main function for command-line usage
def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Topic modeling for WiseFlow")
    parser.add_argument("--focus", help="Focus point to analyze")
    parser.add_argument("--method", default="llm", choices=["llm", "lda", "nmf"], help="Topic modeling method")
    parser.add_argument("--topics", type=int, default=5, help="Number of topics")
    parser.add_argument("--hierarchical", action="store_true", help="Create hierarchical topic structure")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--viz", help="Visualization output path")
    parser.add_argument("--limit", type=int, default=100, help="Maximum number of documents")
    
    args = parser.parse_args()
    
    # Load documents
    documents = load_documents_from_pb(args.focus, args.limit)
    
    if not documents:
        print("No documents found.")
        return
    
    print(f"Loaded {len(documents)} documents.")
    
    # Identify topics
    result = identify_topics(
        documents=documents,
        method=args.method,
        n_topics=args.topics,
        hierarchical=args.hierarchical,
        output_path=args.output,
        visualization_path=args.viz
    )
    
    # Print results
    print(f"\nIdentified {len(result.topics)} topics using {result.method}:")
    for topic in result.topics:
        if not topic.parent_topic:  # Only print top-level topics
            print(f"\n{topic.label} (Confidence: {topic.confidence:.1f}%)")
            print(f"Description: {topic.description}")
            print(f"Key terms: {', '.join(topic.key_terms)}")
            print(f"Documents: {len(topic.documents)}")
            
            # Print child topics if any
            child_topics = result.get_topics_by_parent(topic.topic_id)
            if child_topics:
                print("Child topics:")
                for child in child_topics:
                    print(f"  - {child.label}")


if __name__ == "__main__":
    main()
        print("No documents found.")
        return
    
    print(f"Loaded {len(documents)} documents.")
    
    # Identify topics
    result = identify_topics(
        documents=documents,
        method=args.method,
        n_topics=args.topics,
        hierarchical=args.hierarchical,
        output_path=args.output,
        visualization_path=args.viz
    )
    
    # Print results
    print(f"\nIdentified {len(result.topics)} topics using {result.method}:")
    for topic in result.topics:
        if not topic.parent_topic:  # Only print top-level topics
            print(f"\n{topic.label} (Confidence: {topic.confidence:.1f}%)")
            print(f"Description: {topic.description}")
            print(f"Key terms: {', '.join(topic.key_terms)}")
            print(f"Documents: {len(topic.documents)}")
            
            # Print child topics if any
            child_topics = result.get_topics_by_parent(topic.topic_id)
            if child_topics:
                print("Child topics:")
                for child in child_topics:
                    print(f"  - {child.label}")


if __name__ == "__main__":
    main()
