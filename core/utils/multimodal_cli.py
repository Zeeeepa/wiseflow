#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Command-line interface for running multimodal analysis on existing data.

This script provides a convenient way to process existing data with the new
multimodal analysis capabilities.
"""

import os
import sys
import json
import asyncio
import argparse
from datetime import datetime

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.general_utils import get_logger
from utils.pb_api import PbTalker
from analysis.multimodal_analysis import process_item_with_images, process_focus_for_multimodal_analysis
from analysis.multimodal_knowledge_integration import integrate_multimodal_analysis_with_knowledge_graph

# Set up logging
project_dir = os.environ.get("PROJECT_DIR", "")
if project_dir:
    os.makedirs(project_dir, exist_ok=True)
cli_logger = get_logger('multimodal_cli', project_dir)
pb = PbTalker(cli_logger)

async def process_focus(focus_id: str, analyze_only: bool = False, integrate_only: bool = False) -> None:
    """
    Process a focus point for multimodal analysis and knowledge graph integration.
    
    Args:
        focus_id: ID of the focus point to process
        analyze_only: Only perform multimodal analysis without knowledge graph integration
        integrate_only: Only perform knowledge graph integration without multimodal analysis
    """
    cli_logger.info(f"Processing focus point {focus_id}")
    
    # Get focus point details
    focus = pb.read_one(collection_name='focus_point', id=focus_id)
    if not focus:
        cli_logger.error(f"Focus point with ID {focus_id} not found")
        return
    
    focus_name = focus.get("focuspoint", "Unknown")
    cli_logger.info(f"Focus point: {focus_name}")
    
    # Perform multimodal analysis
    if not integrate_only:
        cli_logger.info("Performing multimodal analysis...")
        analysis_result = await process_focus_for_multimodal_analysis(focus_id)
        cli_logger.info(f"Multimodal analysis completed: {analysis_result}")
    
    # Perform knowledge graph integration
    if not analyze_only:
        cli_logger.info("Integrating multimodal analysis into knowledge graph...")
        integration_result = await integrate_multimodal_analysis_with_knowledge_graph(focus_id)
        cli_logger.info(f"Knowledge graph integration completed: {integration_result}")
    
    cli_logger.info(f"Processing completed for focus point {focus_id}")

async def process_all_focuses(analyze_only: bool = False, integrate_only: bool = False) -> None:
    """
    Process all active focus points for multimodal analysis and knowledge graph integration.
    
    Args:
        analyze_only: Only perform multimodal analysis without knowledge graph integration
        integrate_only: Only perform knowledge graph integration without multimodal analysis
    """
    cli_logger.info("Processing all active focus points")
    
    # Get all active focus points
    active_focuses = pb.read(collection_name='focus_point', filter="activated=true")
    
    if not active_focuses:
        cli_logger.warning("No active focus points found")
        return
    
    cli_logger.info(f"Found {len(active_focuses)} active focus points")
    
    # Process each focus point
    for focus in active_focuses:
        await process_focus(focus["id"], analyze_only, integrate_only)
    
    cli_logger.info("Processing completed for all focus points")

async def process_item(item_id: str) -> None:
    """
    Process a single item for multimodal analysis.
    
    Args:
        item_id: ID of the item to process
    """
    cli_logger.info(f"Processing item {item_id}")
    
    # Get the item
    item = pb.read_one(collection_name='infos', id=item_id)
    if not item:
        cli_logger.error(f"Item with ID {item_id} not found")
        return
    
    # Process the item
    updated_item = await process_item_with_images(item)
    
    cli_logger.info(f"Processing completed for item {item_id}")
    
    # Return the updated item
    return updated_item

def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="Multimodal Analysis CLI")
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Focus command
    focus_parser = subparsers.add_parser("focus", help="Process a focus point")
    focus_parser.add_argument("focus_id", help="ID of the focus point to process")
    focus_parser.add_argument("--analyze-only", action="store_true", help="Only perform multimodal analysis")
    focus_parser.add_argument("--integrate-only", action="store_true", help="Only perform knowledge graph integration")
    
    # All command
    all_parser = subparsers.add_parser("all", help="Process all active focus points")
    all_parser.add_argument("--analyze-only", action="store_true", help="Only perform multimodal analysis")
    all_parser.add_argument("--integrate-only", action="store_true", help="Only perform knowledge graph integration")
    
    # Item command
    item_parser = subparsers.add_parser("item", help="Process a single item")
    item_parser.add_argument("item_id", help="ID of the item to process")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Enable multimodal analysis
    os.environ["ENABLE_MULTIMODAL"] = "true"
    
    # Run the appropriate command
    if args.command == "focus":
        asyncio.run(process_focus(args.focus_id, args.analyze_only, args.integrate_only))
    elif args.command == "all":
        asyncio.run(process_all_focuses(args.analyze_only, args.integrate_only))
    elif args.command == "item":
        asyncio.run(process_item(args.item_id))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
