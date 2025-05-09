"""
Reference content indexing for Wiseflow.

This module provides functionality for indexing reference content
to enable efficient search and retrieval.
"""

import os
import logging
import json
import uuid
import hashlib
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime
import re
import threading
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer

# Download required NLTK resources
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

logger = logging.getLogger(__name__)

class ReferenceIndexer:
    """Indexes reference content for efficient search and retrieval."""
    
    def __init__(self, index_path: str = "references/index"):
        """
        Initialize the reference indexer.
        
        Args:
            index_path: Path to store the index files
        """
        self.index_path = index_path
        os.makedirs(index_path, exist_ok=True)
        
        # Initialize index structures
        self.term_index: Dict[str, Dict[str, List[int]]] = {}  # term -> {doc_id -> [positions]}
        self.document_index: Dict[str, Dict[str, Any]] = {}  # doc_id -> document metadata
        self.stemmer = PorterStemmer()
        self.stop_words = set(stopwords.words('english'))
        self._lock = threading.RLock()  # Add a lock for thread safety
        
        # Load existing index if available
        self._load_index()
    
    def _load_index(self) -> None:
        """Load existing index from disk."""
        term_index_path = os.path.join(self.index_path, "term_index.json")
        doc_index_path = os.path.join(self.index_path, "document_index.json")
        
        if os.path.exists(term_index_path):
            try:
                with open(term_index_path, 'r', encoding='utf-8') as f:
                    self.term_index = json.load(f)
                logger.info(f"Loaded term index with {len(self.term_index)} terms")
            except Exception as e:
                logger.error(f"Error loading term index: {e}")
                self.term_index = {}
        
        if os.path.exists(doc_index_path):
            try:
                with open(doc_index_path, 'r', encoding='utf-8') as f:
                    self.document_index = json.load(f)
                logger.info(f"Loaded document index with {len(self.document_index)} documents")
            except Exception as e:
                logger.error(f"Error loading document index: {e}")
                self.document_index = {}
    
    def _save_index(self) -> None:
        """Save index to disk."""
        with self._lock:
            term_index_path = os.path.join(self.index_path, "term_index.json")
            doc_index_path = os.path.join(self.index_path, "document_index.json")
            
            try:
                # Create temporary files first to avoid corruption
                term_index_temp = term_index_path + ".tmp"
                doc_index_temp = doc_index_path + ".tmp"
                
                with open(term_index_temp, 'w', encoding='utf-8') as f:
                    json.dump(self.term_index, f)
                
                with open(doc_index_temp, 'w', encoding='utf-8') as f:
                    json.dump(self.document_index, f)
                
                # Rename temporary files to final files
                os.replace(term_index_temp, term_index_path)
                os.replace(doc_index_temp, doc_index_path)
                
                logger.info(f"Saved index with {len(self.term_index)} terms and {len(self.document_index)} documents")
            except Exception as e:
                logger.error(f"Error saving index: {e}")
    
    def _preprocess_text(self, text: str) -> List[str]:
        """
        Preprocess text for indexing.
        
        Args:
            text: Text to preprocess
            
        Returns:
            List of preprocessed tokens
        """
        try:
            # Convert to lowercase
            text = text.lower()
            
            # Remove special characters and digits
            text = re.sub(r'[^\w\s]', ' ', text)
            text = re.sub(r'\d+', ' ', text)
            
            # Tokenize
            tokens = word_tokenize(text)
            
            # Remove stop words and stem
            processed_tokens = []
            for token in tokens:
                if token not in self.stop_words and len(token) > 2:
                    processed_tokens.append(self.stemmer.stem(token))
            
            return processed_tokens
        except Exception as e:
            logger.error(f"Error preprocessing text: {e}")
            return []
    
    def _extract_sentences(self, text: str) -> List[str]:
        """
        Extract sentences from text.
        
        Args:
            text: Text to extract sentences from
            
        Returns:
            List of sentences
        """
        try:
            return sent_tokenize(text)
        except Exception as e:
            logger.error(f"Error extracting sentences: {e}")
            return [text]  # Return the whole text as a single sentence if extraction fails
    
    def _compute_document_hash(self, content: str) -> str:
        """
        Compute a hash for document content.
        
        Args:
            content: Document content
            
        Returns:
            Hash string
        """
        try:
            return hashlib.md5(content.encode('utf-8')).hexdigest()
        except Exception as e:
            logger.error(f"Error computing document hash: {e}")
            return str(uuid.uuid4())  # Generate a random hash if hashing fails
    
    def index_document(self, doc_id: str, content: str, metadata: Dict[str, Any]) -> bool:
        """
        Index a document.
        
        Args:
            doc_id: Document ID
            content: Document content
            metadata: Document metadata
            
        Returns:
            True if indexing was successful, False otherwise
        """
        try:
            with self._lock:
                # Check if document already exists and content is unchanged
                content_hash = self._compute_document_hash(content)
                if doc_id in self.document_index and self.document_index[doc_id].get("content_hash") == content_hash:
                    logger.debug(f"Document {doc_id} already indexed and unchanged")
                    return True
                
                # Extract sentences for context retrieval
                sentences = self._extract_sentences(content)
                
                # Process the document
                tokens = self._preprocess_text(content)
                
                # Update document index
                self.document_index[doc_id] = {
                    "content_hash": content_hash,
                    "metadata": metadata,
                    "token_count": len(tokens),
                    "sentence_count": len(sentences),
                    "sentences": sentences,
                    "indexed_at": datetime.now().isoformat()
                }
                
                # Remove existing entries for this document
                for term in list(self.term_index.keys()):
                    if doc_id in self.term_index[term]:
                        del self.term_index[term][doc_id]
                        # Remove term if no documents left
                        if not self.term_index[term]:
                            del self.term_index[term]
                
                # Index the document
                for position, token in enumerate(tokens):
                    if token not in self.term_index:
                        self.term_index[token] = {}
                    
                    if doc_id not in self.term_index[token]:
                        self.term_index[token][doc_id] = []
                    
                    self.term_index[token][doc_id].append(position)
                
                # Save the updated index
                self._save_index()
                
                logger.info(f"Successfully indexed document {doc_id} with {len(tokens)} tokens")
                return True
        except Exception as e:
            logger.error(f"Error indexing document {doc_id}: {e}")
            return False
    
    def remove_document(self, doc_id: str) -> bool:
        """
        Remove a document from the index.
        
        Args:
            doc_id: Document ID to remove
            
        Returns:
            True if removal was successful, False otherwise
        """
        try:
            with self._lock:
                # Remove from document index
                if doc_id in self.document_index:
                    del self.document_index[doc_id]
                
                # Remove from term index
                for term in list(self.term_index.keys()):
                    if doc_id in self.term_index[term]:
                        del self.term_index[term][doc_id]
                        # Remove term if no documents left
                        if not self.term_index[term]:
                            del self.term_index[term]
                
                # Save the updated index
                self._save_index()
                
                logger.info(f"Successfully removed document {doc_id} from index")
                return True
        except Exception as e:
            logger.error(f"Error removing document {doc_id} from index: {e}")
            return False
    
    def search(self, query: str, focus_id: Optional[str] = None, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search the index for documents matching the query.
        
        Args:
            query: Search query
            focus_id: Optional focus ID to filter results
            max_results: Maximum number of results to return
            
        Returns:
            List of search results with document IDs, scores, and snippets
        """
        try:
            # Preprocess the query
            query_tokens = self._preprocess_text(query)
            
            if not query_tokens:
                return []
            
            # Calculate document scores
            doc_scores: Dict[str, float] = {}
            
            for token in query_tokens:
                if token in self.term_index:
                    for doc_id, positions in self.term_index[token].items():
                        # Filter by focus_id if provided
                        if focus_id and self.document_index[doc_id]["metadata"].get("focus_id") != focus_id:
                            continue
                        
                        # Calculate term frequency
                        tf = len(positions) / self.document_index[doc_id]["token_count"]
                        
                        # Calculate inverse document frequency
                        idf = len(self.document_index) / len(self.term_index[token])
                        
                        # Calculate TF-IDF score
                        score = tf * idf
                        
                        # Add to document score
                        if doc_id not in doc_scores:
                            doc_scores[doc_id] = 0
                        doc_scores[doc_id] += score
            
            # Sort documents by score
            sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)[:max_results]
            
            # Generate results with snippets
            results = []
            for doc_id, score in sorted_docs:
                # Get document metadata
                doc_metadata = self.document_index[doc_id]["metadata"]
                
                # Generate snippet
                snippet = self._generate_snippet(doc_id, query_tokens)
                
                results.append({
                    "doc_id": doc_id,
                    "score": score,
                    "snippet": snippet,
                    "metadata": doc_metadata
                })
            
            return results
        except Exception as e:
            logger.error(f"Error searching index: {e}")
            return []
    
    def _generate_snippet(self, doc_id: str, query_tokens: List[str]) -> str:
        """
        Generate a snippet from a document highlighting query terms.
        
        Args:
            doc_id: Document ID
            query_tokens: Preprocessed query tokens
            
        Returns:
            Snippet text
        """
        try:
            # Get document sentences
            sentences = self.document_index[doc_id]["sentences"]
            
            if not sentences:
                return ""
            
            # Score sentences based on query token matches
            sentence_scores = []
            for i, sentence in enumerate(sentences):
                # Preprocess sentence
                sentence_tokens = self._preprocess_text(sentence)
                
                # Count matching tokens
                matches = sum(1 for token in sentence_tokens if token in query_tokens)
                
                # Score is the number of matches divided by sentence length
                score = matches / (len(sentence_tokens) + 1)  # Add 1 to avoid division by zero
                
                sentence_scores.append((i, score, sentence))
            
            # Sort sentences by score
            sorted_sentences = sorted(sentence_scores, key=lambda x: x[1], reverse=True)
            
            # Take top 3 sentences for snippet
            top_sentences = sorted_sentences[:3]
            
            # Sort by original order
            top_sentences.sort(key=lambda x: x[0])
            
            # Join sentences
            snippet = " ".join(s[2] for s in top_sentences)
            
            # Truncate if too long
            if len(snippet) > 300:
                snippet = snippet[:297] + "..."
            
            return snippet
        except Exception as e:
            logger.error(f"Error generating snippet for document {doc_id}: {e}")
            return ""
    
    def get_document_metadata(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a document.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document metadata or None if not found
        """
        return self.document_index.get(doc_id, {}).get("metadata")
    
    def get_related_documents(self, doc_id: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Find documents related to a given document.
        
        Args:
            doc_id: Document ID
            max_results: Maximum number of results to return
            
        Returns:
            List of related documents with scores
        """
        try:
            if doc_id not in self.document_index:
                return []
            
            # Get document terms
            doc_terms = set()
            for term, docs in self.term_index.items():
                if doc_id in docs:
                    doc_terms.add(term)
            
            # Calculate similarity scores for other documents
            doc_scores: Dict[str, float] = {}
            
            for other_doc_id in self.document_index:
                if other_doc_id == doc_id:
                    continue
                
                # Get other document terms
                other_doc_terms = set()
                for term, docs in self.term_index.items():
                    if other_doc_id in docs:
                        other_doc_terms.add(term)
                
                # Calculate Jaccard similarity
                intersection = len(doc_terms.intersection(other_doc_terms))
                union = len(doc_terms.union(other_doc_terms))
                
                if union > 0:
                    similarity = intersection / union
                    doc_scores[other_doc_id] = similarity
            
            # Sort documents by similarity score
            sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)[:max_results]
            
            # Generate results
            results = []
            for related_doc_id, score in sorted_docs:
                results.append({
                    "doc_id": related_doc_id,
                    "score": score,
                    "metadata": self.document_index[related_doc_id]["metadata"]
                })
            
            return results
        except Exception as e:
            logger.error(f"Error finding related documents for {doc_id}: {e}")
            return []
