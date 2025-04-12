"""
Test script for the topic modeling module.
"""

import os
import sys
import json
from pathlib import Path

# Add the parent directory to the path so we can import the core modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.analysis.topic_modeling import (
    Topic, 
    TopicModelingResult, 
    TopicModeler, 
    identify_topics
)

def test_llm_topic_modeling():
    """Test LLM-based topic modeling."""
    # Sample documents
    documents = [
        "Machine learning is a field of study that gives computers the ability to learn without being explicitly programmed.",
        "Deep learning is part of a broader family of machine learning methods based on artificial neural networks.",
        "Neural networks are computing systems inspired by the biological neural networks that constitute animal brains.",
        "Reinforcement learning is an area of machine learning concerned with how software agents ought to take actions in an environment.",
        "Natural language processing is a subfield of linguistics, computer science, and artificial intelligence concerned with the interactions between computers and human language.",
        "Computer vision is an interdisciplinary scientific field that deals with how computers can gain high-level understanding from digital images or videos.",
        "Artificial intelligence is intelligence demonstrated by machines, as opposed to the natural intelligence displayed by humans and animals.",
        "Data mining is the process of discovering patterns in large data sets involving methods at the intersection of machine learning, statistics, and database systems.",
        "Robotics is an interdisciplinary branch of engineering and science that includes mechanical engineering, electronic engineering, information engineering, computer science, and others.",
        "The Internet of Things is a system of interrelated computing devices, mechanical and digital machines provided with unique identifiers and the ability to transfer data over a network."
    ]
    
    # Test LLM-based topic modeling
    print("Testing LLM-based topic modeling...")
    result = identify_topics(
        documents=documents,
        method="llm",
        n_topics=3,
        hierarchical=True
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
    
    # Test saving and loading
    output_path = "test_topic_model.json"
    modeler = TopicModeler()
    modeler.save_result(result, output_path)
    print(f"\nSaved topic model to {output_path}")
    
    loaded_result = modeler.load_result(output_path)
    print(f"Loaded topic model from {output_path}")
    print(f"Loaded {len(loaded_result.topics)} topics")
    
    # Clean up
    os.remove(output_path)
    print(f"Removed {output_path}")
    
    return result

if __name__ == "__main__":
    test_llm_topic_modeling()
