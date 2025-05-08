#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for the knowledge graph module.

This module contains tests for the knowledge graph module to ensure it works correctly.
"""

import os
import json
import unittest
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from typing import Dict, List, Any, Optional

import pytest
import networkx as nx

from core.knowledge.graph import (
    KnowledgeGraph, Node, Edge, NodeType, EdgeType,
    create_node, create_edge, load_knowledge_graph, save_knowledge_graph
)


class TestKnowledgeGraph(unittest.TestCase):
    """Test cases for the KnowledgeGraph class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.graph = KnowledgeGraph(name="test_graph", storage_path=self.temp_dir)
    
    def tearDown(self):
        """Tear down test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test graph initialization."""
        self.assertEqual(self.graph.name, "test_graph")
        self.assertEqual(self.graph.storage_path, self.temp_dir)
        self.assertIsInstance(self.graph.graph, nx.MultiDiGraph)
        self.assertEqual(len(self.graph.graph.nodes), 0)
        self.assertEqual(len(self.graph.graph.edges), 0)
    
    def test_add_node(self):
        """Test adding a node to the graph."""
        # Create a node
        node = Node(
            node_id="node1",
            node_type=NodeType.ENTITY,
            name="Test Entity",
            properties={"key": "value"},
            sources=["source1"]
        )
        
        # Add the node
        self.graph.add_node(node)
        
        # Check the node was added
        self.assertEqual(len(self.graph.graph.nodes), 1)
        self.assertIn("node1", self.graph.graph.nodes)
        
        # Check node attributes
        node_attrs = self.graph.graph.nodes["node1"]
        self.assertEqual(node_attrs["node_type"], NodeType.ENTITY)
        self.assertEqual(node_attrs["name"], "Test Entity")
        self.assertEqual(node_attrs["properties"], {"key": "value"})
        self.assertEqual(node_attrs["sources"], ["source1"])
    
    def test_add_edge(self):
        """Test adding an edge to the graph."""
        # Create nodes
        node1 = Node(
            node_id="node1",
            node_type=NodeType.ENTITY,
            name="Entity 1"
        )
        
        node2 = Node(
            node_id="node2",
            node_type=NodeType.ENTITY,
            name="Entity 2"
        )
        
        # Add nodes
        self.graph.add_node(node1)
        self.graph.add_node(node2)
        
        # Create an edge
        edge = Edge(
            source_id="node1",
            target_id="node2",
            edge_type=EdgeType.RELATED_TO,
            properties={"weight": 0.8},
            sources=["source1"]
        )
        
        # Add the edge
        self.graph.add_edge(edge)
        
        # Check the edge was added
        self.assertEqual(len(self.graph.graph.edges), 1)
        
        # Get the edge data
        edge_data = self.graph.graph.get_edge_data("node1", "node2")
        self.assertIsNotNone(edge_data)
        
        # Check edge attributes (first edge with key 0)
        edge_attrs = edge_data[0]
        self.assertEqual(edge_attrs["edge_type"], EdgeType.RELATED_TO)
        self.assertEqual(edge_attrs["properties"], {"weight": 0.8})
        self.assertEqual(edge_attrs["sources"], ["source1"])
    
    def test_get_node(self):
        """Test getting a node from the graph."""
        # Create and add a node
        node = Node(
            node_id="node1",
            node_type=NodeType.ENTITY,
            name="Test Entity"
        )
        self.graph.add_node(node)
        
        # Get the node
        retrieved_node = self.graph.get_node("node1")
        
        # Check the node
        self.assertIsNotNone(retrieved_node)
        self.assertEqual(retrieved_node.node_id, "node1")
        self.assertEqual(retrieved_node.node_type, NodeType.ENTITY)
        self.assertEqual(retrieved_node.name, "Test Entity")
        
        # Try to get a non-existent node
        non_existent = self.graph.get_node("non_existent")
        self.assertIsNone(non_existent)
    
    def test_get_nodes_by_type(self):
        """Test getting nodes by type."""
        # Create and add nodes of different types
        entity_node = Node(
            node_id="entity1",
            node_type=NodeType.ENTITY,
            name="Entity"
        )
        
        concept_node = Node(
            node_id="concept1",
            node_type=NodeType.CONCEPT,
            name="Concept"
        )
        
        event_node = Node(
            node_id="event1",
            node_type=NodeType.EVENT,
            name="Event"
        )
        
        self.graph.add_node(entity_node)
        self.graph.add_node(concept_node)
        self.graph.add_node(event_node)
        
        # Get nodes by type
        entity_nodes = self.graph.get_nodes_by_type(NodeType.ENTITY)
        concept_nodes = self.graph.get_nodes_by_type(NodeType.CONCEPT)
        event_nodes = self.graph.get_nodes_by_type(NodeType.EVENT)
        
        # Check results
        self.assertEqual(len(entity_nodes), 1)
        self.assertEqual(entity_nodes[0].node_id, "entity1")
        
        self.assertEqual(len(concept_nodes), 1)
        self.assertEqual(concept_nodes[0].node_id, "concept1")
        
        self.assertEqual(len(event_nodes), 1)
        self.assertEqual(event_nodes[0].node_id, "event1")
    
    def test_get_edges(self):
        """Test getting edges from the graph."""
        # Create and add nodes
        node1 = Node(node_id="node1", node_type=NodeType.ENTITY, name="Entity 1")
        node2 = Node(node_id="node2", node_type=NodeType.ENTITY, name="Entity 2")
        node3 = Node(node_id="node3", node_type=NodeType.ENTITY, name="Entity 3")
        
        self.graph.add_node(node1)
        self.graph.add_node(node2)
        self.graph.add_node(node3)
        
        # Create and add edges
        edge1 = Edge(
            source_id="node1",
            target_id="node2",
            edge_type=EdgeType.RELATED_TO
        )
        
        edge2 = Edge(
            source_id="node1",
            target_id="node3",
            edge_type=EdgeType.PART_OF
        )
        
        self.graph.add_edge(edge1)
        self.graph.add_edge(edge2)
        
        # Get all edges from node1
        edges_from_node1 = self.graph.get_edges(source_id="node1")
        self.assertEqual(len(edges_from_node1), 2)
        
        # Get edges of specific type
        related_edges = self.graph.get_edges(edge_type=EdgeType.RELATED_TO)
        self.assertEqual(len(related_edges), 1)
        self.assertEqual(related_edges[0].source_id, "node1")
        self.assertEqual(related_edges[0].target_id, "node2")
        
        # Get edges between specific nodes
        edges_node1_to_node2 = self.graph.get_edges(source_id="node1", target_id="node2")
        self.assertEqual(len(edges_node1_to_node2), 1)
        self.assertEqual(edges_node1_to_node2[0].edge_type, EdgeType.RELATED_TO)
    
    def test_remove_node(self):
        """Test removing a node from the graph."""
        # Create and add nodes
        node1 = Node(node_id="node1", node_type=NodeType.ENTITY, name="Entity 1")
        node2 = Node(node_id="node2", node_type=NodeType.ENTITY, name="Entity 2")
        
        self.graph.add_node(node1)
        self.graph.add_node(node2)
        
        # Create and add an edge
        edge = Edge(
            source_id="node1",
            target_id="node2",
            edge_type=EdgeType.RELATED_TO
        )
        
        self.graph.add_edge(edge)
        
        # Remove node1
        self.graph.remove_node("node1")
        
        # Check node1 was removed
        self.assertNotIn("node1", self.graph.graph.nodes)
        
        # Check the edge was also removed
        self.assertEqual(len(self.graph.graph.edges), 0)
    
    def test_remove_edge(self):
        """Test removing an edge from the graph."""
        # Create and add nodes
        node1 = Node(node_id="node1", node_type=NodeType.ENTITY, name="Entity 1")
        node2 = Node(node_id="node2", node_type=NodeType.ENTITY, name="Entity 2")
        
        self.graph.add_node(node1)
        self.graph.add_node(node2)
        
        # Create and add edges
        edge1 = Edge(
            source_id="node1",
            target_id="node2",
            edge_type=EdgeType.RELATED_TO
        )
        
        edge2 = Edge(
            source_id="node1",
            target_id="node2",
            edge_type=EdgeType.PART_OF
        )
        
        self.graph.add_edge(edge1)
        self.graph.add_edge(edge2)
        
        # Check both edges were added
        self.assertEqual(len(self.graph.get_edges(source_id="node1", target_id="node2")), 2)
        
        # Remove one edge
        self.graph.remove_edge("node1", "node2", EdgeType.RELATED_TO)
        
        # Check one edge remains
        remaining_edges = self.graph.get_edges(source_id="node1", target_id="node2")
        self.assertEqual(len(remaining_edges), 1)
        self.assertEqual(remaining_edges[0].edge_type, EdgeType.PART_OF)
    
    def test_merge_nodes(self):
        """Test merging nodes in the graph."""
        # Create and add nodes
        node1 = Node(
            node_id="node1",
            node_type=NodeType.ENTITY,
            name="Entity 1",
            properties={"prop1": "value1"},
            sources=["source1"]
        )
        
        node2 = Node(
            node_id="node2",
            node_type=NodeType.ENTITY,
            name="Entity 2",
            properties={"prop2": "value2"},
            sources=["source2"]
        )
        
        node3 = Node(
            node_id="node3",
            node_type=NodeType.ENTITY,
            name="Entity 3"
        )
        
        self.graph.add_node(node1)
        self.graph.add_node(node2)
        self.graph.add_node(node3)
        
        # Create and add edges
        edge1 = Edge(
            source_id="node1",
            target_id="node3",
            edge_type=EdgeType.RELATED_TO
        )
        
        edge2 = Edge(
            source_id="node2",
            target_id="node3",
            edge_type=EdgeType.PART_OF
        )
        
        self.graph.add_edge(edge1)
        self.graph.add_edge(edge2)
        
        # Merge node1 and node2
        merged_node = self.graph.merge_nodes(["node1", "node2"], "merged_node")
        
        # Check merged node
        self.assertEqual(merged_node.node_id, "merged_node")
        self.assertEqual(merged_node.node_type, NodeType.ENTITY)
        self.assertEqual(merged_node.properties, {"prop1": "value1", "prop2": "value2"})
        self.assertEqual(set(merged_node.sources), {"source1", "source2"})
        
        # Check original nodes were removed
        self.assertNotIn("node1", self.graph.graph.nodes)
        self.assertNotIn("node2", self.graph.graph.nodes)
        
        # Check edges were updated
        edges = self.graph.get_edges(source_id="merged_node")
        self.assertEqual(len(edges), 2)
        
        edge_types = [edge.edge_type for edge in edges]
        self.assertIn(EdgeType.RELATED_TO, edge_types)
        self.assertIn(EdgeType.PART_OF, edge_types)
    
    def test_save_and_load(self):
        """Test saving and loading the graph."""
        # Create and add nodes and edges
        node1 = Node(node_id="node1", node_type=NodeType.ENTITY, name="Entity 1")
        node2 = Node(node_id="node2", node_type=NodeType.ENTITY, name="Entity 2")
        
        self.graph.add_node(node1)
        self.graph.add_node(node2)
        
        edge = Edge(
            source_id="node1",
            target_id="node2",
            edge_type=EdgeType.RELATED_TO
        )
        
        self.graph.add_edge(edge)
        
        # Save the graph
        filepath = os.path.join(self.temp_dir, "test_graph.json")
        self.graph.save(filepath)
        
        # Check file exists
        self.assertTrue(os.path.exists(filepath))
        
        # Load the graph
        loaded_graph = KnowledgeGraph.load(filepath)
        
        # Check loaded graph
        self.assertEqual(loaded_graph.name, "test_graph")
        self.assertEqual(len(loaded_graph.graph.nodes), 2)
        self.assertEqual(len(loaded_graph.graph.edges), 1)
        
        # Check node attributes
        self.assertIn("node1", loaded_graph.graph.nodes)
        self.assertEqual(loaded_graph.graph.nodes["node1"]["name"], "Entity 1")
        
        # Check edge attributes
        edge_data = loaded_graph.graph.get_edge_data("node1", "node2")
        self.assertIsNotNone(edge_data)
        self.assertEqual(edge_data[0]["edge_type"], EdgeType.RELATED_TO)
    
    def test_to_dict(self):
        """Test converting the graph to a dictionary."""
        # Create and add nodes and edges
        node1 = Node(node_id="node1", node_type=NodeType.ENTITY, name="Entity 1")
        node2 = Node(node_id="node2", node_type=NodeType.ENTITY, name="Entity 2")
        
        self.graph.add_node(node1)
        self.graph.add_node(node2)
        
        edge = Edge(
            source_id="node1",
            target_id="node2",
            edge_type=EdgeType.RELATED_TO
        )
        
        self.graph.add_edge(edge)
        
        # Convert to dict
        graph_dict = self.graph.to_dict()
        
        # Check dict structure
        self.assertEqual(graph_dict["name"], "test_graph")
        self.assertEqual(len(graph_dict["nodes"]), 2)
        self.assertEqual(len(graph_dict["edges"]), 1)
        
        # Check node data
        node_ids = [node["node_id"] for node in graph_dict["nodes"]]
        self.assertIn("node1", node_ids)
        self.assertIn("node2", node_ids)
        
        # Check edge data
        edge_data = graph_dict["edges"][0]
        self.assertEqual(edge_data["source_id"], "node1")
        self.assertEqual(edge_data["target_id"], "node2")
        self.assertEqual(edge_data["edge_type"], "RELATED_TO")
    
    def test_from_dict(self):
        """Test creating a graph from a dictionary."""
        # Create a graph dict
        graph_dict = {
            "name": "test_graph",
            "nodes": [
                {
                    "node_id": "node1",
                    "node_type": "ENTITY",
                    "name": "Entity 1",
                    "properties": {"prop1": "value1"},
                    "sources": ["source1"]
                },
                {
                    "node_id": "node2",
                    "node_type": "ENTITY",
                    "name": "Entity 2",
                    "properties": {"prop2": "value2"},
                    "sources": ["source2"]
                }
            ],
            "edges": [
                {
                    "source_id": "node1",
                    "target_id": "node2",
                    "edge_type": "RELATED_TO",
                    "properties": {"weight": 0.8},
                    "sources": ["source1"]
                }
            ]
        }
        
        # Create graph from dict
        graph = KnowledgeGraph.from_dict(graph_dict)
        
        # Check graph
        self.assertEqual(graph.name, "test_graph")
        self.assertEqual(len(graph.graph.nodes), 2)
        self.assertEqual(len(graph.graph.edges), 1)
        
        # Check node attributes
        self.assertIn("node1", graph.graph.nodes)
        self.assertEqual(graph.graph.nodes["node1"]["name"], "Entity 1")
        self.assertEqual(graph.graph.nodes["node1"]["properties"], {"prop1": "value1"})
        
        # Check edge attributes
        edge_data = graph.graph.get_edge_data("node1", "node2")
        self.assertIsNotNone(edge_data)
        self.assertEqual(edge_data[0]["edge_type"], EdgeType.RELATED_TO)
        self.assertEqual(edge_data[0]["properties"], {"weight": 0.8})
    
    def test_validate_knowledge_graph(self):
        """Test validating the knowledge graph."""
        # Create a valid graph
        node1 = Node(node_id="node1", node_type=NodeType.ENTITY, name="Entity 1")
        node2 = Node(node_id="node2", node_type=NodeType.ENTITY, name="Entity 2")
        
        self.graph.add_node(node1)
        self.graph.add_node(node2)
        
        edge = Edge(
            source_id="node1",
            target_id="node2",
            edge_type=EdgeType.RELATED_TO
        )
        
        self.graph.add_edge(edge)
        
        # Validate the graph
        validation_result = self.graph.validate_knowledge_graph()
        
        # Check validation result
        self.assertTrue(validation_result["is_valid"])
        self.assertEqual(validation_result["node_count"], 2)
        self.assertEqual(validation_result["edge_count"], 1)
        self.assertEqual(len(validation_result["errors"]), 0)
    
    def test_validate_invalid_graph(self):
        """Test validating an invalid knowledge graph."""
        # Create an invalid graph (edge to non-existent node)
        node1 = Node(node_id="node1", node_type=NodeType.ENTITY, name="Entity 1")
        self.graph.add_node(node1)
        
        # Add edge to non-existent node
        edge = Edge(
            source_id="node1",
            target_id="non_existent",
            edge_type=EdgeType.RELATED_TO
        )
        
        # Bypass normal add_edge to create an invalid edge
        self.graph.graph.add_edge(
            "node1",
            "non_existent",
            edge_type=EdgeType.RELATED_TO
        )
        
        # Validate the graph
        validation_result = self.graph.validate_knowledge_graph()
        
        # Check validation result
        self.assertFalse(validation_result["is_valid"])
        self.assertEqual(validation_result["node_count"], 1)
        self.assertEqual(validation_result["edge_count"], 1)
        self.assertGreater(len(validation_result["errors"]), 0)
        self.assertIn("non_existent", validation_result["errors"][0])


class TestNodeAndEdge(unittest.TestCase):
    """Test cases for the Node and Edge classes."""
    
    def test_create_node(self):
        """Test creating a node."""
        # Create a node
        node = create_node(
            node_id="test_node",
            node_type=NodeType.ENTITY,
            name="Test Node",
            properties={"key": "value"},
            sources=["source1"]
        )
        
        # Check node attributes
        self.assertEqual(node.node_id, "test_node")
        self.assertEqual(node.node_type, NodeType.ENTITY)
        self.assertEqual(node.name, "Test Node")
        self.assertEqual(node.properties, {"key": "value"})
        self.assertEqual(node.sources, ["source1"])
    
    def test_create_edge(self):
        """Test creating an edge."""
        # Create an edge
        edge = create_edge(
            source_id="node1",
            target_id="node2",
            edge_type=EdgeType.RELATED_TO,
            properties={"weight": 0.8},
            sources=["source1"]
        )
        
        # Check edge attributes
        self.assertEqual(edge.source_id, "node1")
        self.assertEqual(edge.target_id, "node2")
        self.assertEqual(edge.edge_type, EdgeType.RELATED_TO)
        self.assertEqual(edge.properties, {"weight": 0.8})
        self.assertEqual(edge.sources, ["source1"])
    
    def test_node_to_dict(self):
        """Test converting a node to a dictionary."""
        # Create a node
        node = Node(
            node_id="test_node",
            node_type=NodeType.ENTITY,
            name="Test Node",
            properties={"key": "value"},
            sources=["source1"]
        )
        
        # Convert to dict
        node_dict = node.to_dict()
        
        # Check dict structure
        self.assertEqual(node_dict["node_id"], "test_node")
        self.assertEqual(node_dict["node_type"], "ENTITY")
        self.assertEqual(node_dict["name"], "Test Node")
        self.assertEqual(node_dict["properties"], {"key": "value"})
        self.assertEqual(node_dict["sources"], ["source1"])
    
    def test_edge_to_dict(self):
        """Test converting an edge to a dictionary."""
        # Create an edge
        edge = Edge(
            source_id="node1",
            target_id="node2",
            edge_type=EdgeType.RELATED_TO,
            properties={"weight": 0.8},
            sources=["source1"]
        )
        
        # Convert to dict
        edge_dict = edge.to_dict()
        
        # Check dict structure
        self.assertEqual(edge_dict["source_id"], "node1")
        self.assertEqual(edge_dict["target_id"], "node2")
        self.assertEqual(edge_dict["edge_type"], "RELATED_TO")
        self.assertEqual(edge_dict["properties"], {"weight": 0.8})
        self.assertEqual(edge_dict["sources"], ["source1"])
    
    def test_node_from_dict(self):
        """Test creating a node from a dictionary."""
        # Create a node dict
        node_dict = {
            "node_id": "test_node",
            "node_type": "ENTITY",
            "name": "Test Node",
            "properties": {"key": "value"},
            "sources": ["source1"]
        }
        
        # Create node from dict
        node = Node.from_dict(node_dict)
        
        # Check node attributes
        self.assertEqual(node.node_id, "test_node")
        self.assertEqual(node.node_type, NodeType.ENTITY)
        self.assertEqual(node.name, "Test Node")
        self.assertEqual(node.properties, {"key": "value"})
        self.assertEqual(node.sources, ["source1"])
    
    def test_edge_from_dict(self):
        """Test creating an edge from a dictionary."""
        # Create an edge dict
        edge_dict = {
            "source_id": "node1",
            "target_id": "node2",
            "edge_type": "RELATED_TO",
            "properties": {"weight": 0.8},
            "sources": ["source1"]
        }
        
        # Create edge from dict
        edge = Edge.from_dict(edge_dict)
        
        # Check edge attributes
        self.assertEqual(edge.source_id, "node1")
        self.assertEqual(edge.target_id, "node2")
        self.assertEqual(edge.edge_type, EdgeType.RELATED_TO)
        self.assertEqual(edge.properties, {"weight": 0.8})
        self.assertEqual(edge.sources, ["source1"])


class TestKnowledgeGraphUtils(unittest.TestCase):
    """Test cases for knowledge graph utility functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Tear down test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_save_and_load_knowledge_graph(self):
        """Test saving and loading a knowledge graph using utility functions."""
        # Create a graph
        graph = KnowledgeGraph(name="test_graph")
        
        # Add nodes and edges
        node1 = Node(node_id="node1", node_type=NodeType.ENTITY, name="Entity 1")
        node2 = Node(node_id="node2", node_type=NodeType.ENTITY, name="Entity 2")
        
        graph.add_node(node1)
        graph.add_node(node2)
        
        edge = Edge(
            source_id="node1",
            target_id="node2",
            edge_type=EdgeType.RELATED_TO
        )
        
        graph.add_edge(edge)
        
        # Save the graph
        filepath = os.path.join(self.temp_dir, "test_graph.json")
        save_knowledge_graph(graph, filepath)
        
        # Check file exists
        self.assertTrue(os.path.exists(filepath))
        
        # Load the graph
        loaded_graph = load_knowledge_graph(filepath)
        
        # Check loaded graph
        self.assertEqual(loaded_graph.name, "test_graph")
        self.assertEqual(len(loaded_graph.graph.nodes), 2)
        self.assertEqual(len(loaded_graph.graph.edges), 1)


if __name__ == "__main__":
    unittest.main()

