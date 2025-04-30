"""
Knowledge Graph visualization module for Wiseflow dashboard.
"""

from typing import Dict, List, Any, Optional
import logging
import json
import networkx as nx
import matplotlib.pyplot as plt
import io
import base64

from dashboard.visualization import KnowledgeGraphVisualization
from dashboard.plugins import dashboard_plugin_manager

logger = logging.getLogger(__name__)

def visualize_knowledge_graph(data: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Visualize a knowledge graph.
    
    Args:
        data: Knowledge graph data
        config: Visualization configuration
        
    Returns:
        Dict[str, Any]: Visualization data
    """
    config = config or {}
    
    # If data is a string, try to parse it as JSON
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception as e:
            logger.error(f"Error parsing knowledge graph data: {str(e)}")
            return {"error": str(e)}
    
    # If data is raw text, analyze it using the entity analyzer
    if isinstance(data, str) or (isinstance(data, dict) and "text" in data):
        text = data if isinstance(data, str) else data["text"]
        try:
            # Use the entity analyzer to extract entities and relationships
            analysis_result = dashboard_plugin_manager.analyze_entities(text, build_knowledge_graph=True)
            
            # Check if the analysis was successful
            if "error" in analysis_result:
                logger.error(f"Error analyzing text: {analysis_result['error']}")
                return {"error": analysis_result["error"]}
            
            # Use the knowledge graph from the analysis result
            if "knowledge_graph" in analysis_result:
                data = analysis_result["knowledge_graph"]
            else:
                # Create a simple knowledge graph from entities and relationships
                nodes = []
                edges = []
                
                for entity in analysis_result.get("entities", []):
                    nodes.append({
                        "id": entity["text"],
                        "label": entity["text"],
                        "type": entity["type"]
                    })
                
                for rel in analysis_result.get("relationships", []):
                    edges.append({
                        "source": rel["source"],
                        "target": rel["target"],
                        "label": rel["type"],
                        "weight": rel.get("confidence", 1.0)
                    })
                
                data = {"nodes": nodes, "edges": edges}
        except Exception as e:
            logger.error(f"Error creating knowledge graph from text: {str(e)}")
            return {"error": str(e)}
    
    # Apply filters if specified
    if config.get("filters"):
        data = filter_knowledge_graph(data, config["filters"])
    
    # Generate visualization
    try:
        # Create a graph
        G = nx.DiGraph()
        
        # Add nodes
        for node in data.get("nodes", []):
            G.add_node(
                node["id"],
                label=node.get("label", node["id"]),
                type=node.get("type", "unknown")
            )
        
        # Add edges
        for edge in data.get("edges", []):
            G.add_edge(
                edge["source"],
                edge["target"],
                label=edge.get("label", ""),
                weight=edge.get("weight", 1.0)
            )
        
        # Generate layout
        layout_type = config.get("layout", "spring")
        if layout_type == "spring":
            pos = nx.spring_layout(G)
        elif layout_type == "circular":
            pos = nx.circular_layout(G)
        elif layout_type == "kamada_kawai":
            pos = nx.kamada_kawai_layout(G)
        else:
            pos = nx.spring_layout(G)
        
        # Create figure
        plt.figure(figsize=(12, 8))
        
        # Draw nodes
        node_colors = []
        node_sizes = []
        node_labels = {}
        
        for node, attrs in G.nodes(data=True):
            # Set node color based on type
            node_type = attrs.get("type", "unknown")
            if node_type == "PERSON":
                node_colors.append("skyblue")
            elif node_type == "ORGANIZATION":
                node_colors.append("lightgreen")
            elif node_type == "LOCATION":
                node_colors.append("salmon")
            else:
                node_colors.append("lightgray")
            
            # Set node size based on degree
            node_sizes.append(100 + G.degree(node) * 50)
            
            # Set node label
            node_labels[node] = attrs.get("label", node)
        
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, alpha=0.8)
        
        # Draw edges
        edge_colors = []
        edge_widths = []
        edge_labels = {}
        
        for u, v, attrs in G.edges(data=True):
            # Set edge color and width based on weight
            weight = attrs.get("weight", 1.0)
            edge_colors.append("gray")
            edge_widths.append(1 + weight * 2)
            
            # Set edge label
            if attrs.get("label"):
                edge_labels[(u, v)] = attrs["label"]
        
        nx.draw_networkx_edges(G, pos, edge_color=edge_colors, width=edge_widths, alpha=0.6, arrows=True, arrowsize=15)
        
        # Draw labels
        nx.draw_networkx_labels(G, pos, labels=node_labels, font_size=10, font_weight="bold")
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8)
        
        # Set title
        plt.title(config.get("title", "Knowledge Graph"), fontsize=16)
        
        # Remove axis
        plt.axis("off")
        
        # Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=300, bbox_inches="tight")
        plt.close()
        
        # Convert to base64
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        
        # Return visualization data
        return {
            "type": "knowledge_graph",
            "image": f"data:image/png;base64,{img_base64}",
            "graph": {
                "nodes": len(G.nodes),
                "edges": len(G.edges),
                "density": nx.density(G)
            },
            "metrics": data.get("metrics", {})
        }
    except Exception as e:
        logger.error(f"Error generating knowledge graph visualization: {str(e)}")
        return {"error": str(e)}

def filter_knowledge_graph(data: Dict[str, Any], filters: Dict[str, Any]) -> Dict[str, Any]:
    """Filter a knowledge graph based on criteria.
    
    Args:
        data: Knowledge graph data
        filters: Filter criteria
        
    Returns:
        Dict[str, Any]: Filtered knowledge graph data
    """
    if not filters:
        return data
    
    filtered_nodes = []
    filtered_edges = []
    
    # Filter nodes
    for node in data.get("nodes", []):
        # Filter by node type
        if "node_types" in filters and node.get("type") not in filters["node_types"]:
            continue
        
        # Filter by node label
        if "node_label_contains" in filters and filters["node_label_contains"] not in node.get("label", node.get("id", "")):
            continue
        
        # Node passed all filters
        filtered_nodes.append(node)
    
    # Get filtered node IDs
    filtered_node_ids = [node["id"] for node in filtered_nodes]
    
    # Filter edges
    for edge in data.get("edges", []):
        # Only include edges between filtered nodes
        if edge["source"] not in filtered_node_ids or edge["target"] not in filtered_node_ids:
            continue
        
        # Filter by edge type
        if "edge_types" in filters and edge.get("label") not in filters["edge_types"]:
            continue
        
        # Filter by edge weight
        if "min_weight" in filters and edge.get("weight", 1.0) < filters["min_weight"]:
            continue
        
        # Edge passed all filters
        filtered_edges.append(edge)
    
    # Return filtered data
    return {
        "nodes": filtered_nodes,
        "edges": filtered_edges,
        "metrics": data.get("metrics", {})
    }
