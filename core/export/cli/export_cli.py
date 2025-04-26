#!/usr/bin/env python3
"""
Command-line interface for Wiseflow Export Module.

This script provides a command-line interface for exporting data from Wiseflow.
"""

import argparse
import json
import logging
import os
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add parent directory to path to allow importing from core.export
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from core.export import get_export_manager
from core.export.webhook import get_webhook_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Wiseflow Export CLI')
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export data')
    export_parser.add_argument('--data', required=True, help='JSON file containing data to export')
    export_parser.add_argument('--format', required=True, choices=['csv', 'json', 'xml', 'pdf'], help='Export format')
    export_parser.add_argument('--output', help='Output file path (default: auto-generated)')
    export_parser.add_argument('--template', help='Template name to apply')
    
    # Template commands
    template_parser = subparsers.add_parser('template', help='Manage export templates')
    template_subparsers = template_parser.add_subparsers(dest='template_command', help='Template command')
    
    # List templates
    template_subparsers.add_parser('list', help='List available templates')
    
    # Create template
    create_template_parser = template_subparsers.add_parser('create', help='Create a new template')
    create_template_parser.add_argument('--name', required=True, help='Template name')
    create_template_parser.add_argument('--structure', required=True, help='Template structure JSON file path')
    
    # Delete template
    delete_template_parser = template_subparsers.add_parser('delete', help='Delete a template')
    delete_template_parser.add_argument('--name', required=True, help='Template name')
    
    # Webhook commands
    webhook_parser = subparsers.add_parser('webhook', help='Manage webhooks')
    webhook_subparsers = webhook_parser.add_subparsers(dest='webhook_command', help='Webhook command')
    
    # List webhooks
    webhook_subparsers.add_parser('list', help='List registered webhooks')
    
    # Register webhook
    register_webhook_parser = webhook_subparsers.add_parser('register', help='Register a new webhook')
    register_webhook_parser.add_argument('--endpoint', required=True, help='Webhook endpoint URL')
    register_webhook_parser.add_argument('--events', required=True, help='Comma-separated list of events')
    register_webhook_parser.add_argument('--headers', help='Headers JSON file path')
    register_webhook_parser.add_argument('--secret', help='Secret for signing webhook payloads')
    register_webhook_parser.add_argument('--description', help='Webhook description')
    
    # Delete webhook
    delete_webhook_parser = webhook_subparsers.add_parser('delete', help='Delete a webhook')
    delete_webhook_parser.add_argument('--id', required=True, help='Webhook ID')
    
    # Trigger webhook
    trigger_webhook_parser = webhook_subparsers.add_parser('trigger', help='Trigger a webhook')
    trigger_webhook_parser.add_argument('--event', required=True, help='Event name')
    trigger_webhook_parser.add_argument('--data', required=True, help='Data JSON file path')
    trigger_webhook_parser.add_argument('--async', dest='async_mode', action='store_true', help='Trigger asynchronously')
    
    # Schedule commands
    schedule_parser = subparsers.add_parser('schedule', help='Manage scheduled exports')
    schedule_subparsers = schedule_parser.add_subparsers(dest='schedule_command', help='Schedule command')
    
    # List schedules
    schedule_subparsers.add_parser('list', help='List scheduled exports')
    
    # Create schedule
    create_schedule_parser = schedule_subparsers.add_parser('create', help='Create a new scheduled export')
    create_schedule_parser.add_argument('--data', required=True, help='JSON file containing data query configuration')
    create_schedule_parser.add_argument('--format', required=True, choices=['csv', 'json', 'xml', 'pdf'], help='Export format')
    create_schedule_parser.add_argument('--interval', required=True, type=int, help='Interval value')
    create_schedule_parser.add_argument('--unit', choices=['minutes', 'hours', 'days'], default='hours', help='Interval unit')
    create_schedule_parser.add_argument('--template', help='Template name to apply')
    
    return parser.parse_args()

def export_data(args):
    """Export data based on command-line arguments."""
    # Load data from file
    try:
        with open(args.data, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load data: {str(e)}")
        return
    
    # Get export manager
    export_manager = get_export_manager()
    
    # Export data
    filepath = export_manager.export_to_format(
        data=data,
        format=args.format,
        filename=args.output,
        template_name=args.template
    )
    
    logger.info(f"Exported {len(data)} records to {filepath}")

def handle_template_command(args):
    """Handle template-related commands."""
    export_manager = get_export_manager()
    
    if args.template_command == 'list':
        templates = export_manager.list_templates()
        if templates:
            print("Available templates:")
            for template_name in templates:
                print(f"- {template_name}")
        else:
            print("No templates available")
    
    elif args.template_command == 'create':
        # Load template structure from file
        try:
            with open(args.structure, 'r', encoding='utf-8') as f:
                structure = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load template structure: {str(e)}")
            return
        
        # Create template
        template = export_manager.create_export_template(args.name, structure)
        logger.info(f"Created template: {args.name}")
    
    elif args.template_command == 'delete':
        # Delete template
        if export_manager.delete_template(args.name):
            logger.info(f"Deleted template: {args.name}")
        else:
            logger.error(f"Template not found: {args.name}")

def handle_webhook_command(args):
    """Handle webhook-related commands."""
    webhook_manager = get_webhook_manager()
    
    if args.webhook_command == 'list':
        webhooks = webhook_manager.list_webhooks()
        if webhooks:
            print("Registered webhooks:")
            for webhook in webhooks:
                print(f"- {webhook['id']}: {webhook['endpoint']} ({', '.join(webhook['events'])})")
                print(f"  Description: {webhook['description']}")
                print(f"  Created: {webhook['created_at']}")
                print(f"  Last triggered: {webhook['last_triggered'] or 'Never'}")
                print(f"  Success/Failure: {webhook['success_count']}/{webhook['failure_count']}")
                print()
        else:
            print("No webhooks registered")
    
    elif args.webhook_command == 'register':
        # Load headers from file if specified
        headers = None
        if args.headers:
            try:
                with open(args.headers, 'r', encoding='utf-8') as f:
                    headers = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load headers: {str(e)}")
                return
        
        # Register webhook
        events = args.events.split(',')
        webhook_id = webhook_manager.register_webhook(
            endpoint=args.endpoint,
            events=events,
            headers=headers,
            secret=args.secret,
            description=args.description
        )
        logger.info(f"Registered webhook: {webhook_id}")
    
    elif args.webhook_command == 'delete':
        # Delete webhook
        if webhook_manager.delete_webhook(args.id):
            logger.info(f"Deleted webhook: {args.id}")
        else:
            logger.error(f"Webhook not found: {args.id}")
    
    elif args.webhook_command == 'trigger':
        # Load data from file
        try:
            with open(args.data, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load data: {str(e)}")
            return
        
        # Trigger webhook
        responses = webhook_manager.trigger_webhook(
            event=args.event,
            data=data,
            async_mode=args.async_mode
        )
        
        if not args.async_mode and responses:
            logger.info(f"Triggered {len(responses)} webhooks")
            for response in responses:
                if response.get('success', False):
                    logger.info(f"Webhook {response['webhook_id']} succeeded with status code: {response.get('status_code')}")
                else:
                    logger.error(f"Webhook {response['webhook_id']} failed: {response.get('error', 'Unknown error')}")
        elif args.async_mode:
            logger.info(f"Triggered webhooks asynchronously")
        else:
            logger.info("No webhooks were triggered")

def handle_schedule_command(args):
    """Handle schedule-related commands."""
    export_manager = get_export_manager()
    
    if args.schedule_command == 'list':
        schedules = export_manager.scheduled_exports
        if schedules:
            print("Scheduled exports:")
            for schedule_id, schedule in schedules.items():
                print(f"- {schedule_id}: {schedule['data_query'].get('collection', 'data')} to {schedule['format']}")
                print(f"  Schedule: Every {schedule['schedule'].get('interval')} {schedule['schedule'].get('unit', 'hours')}")
                print(f"  Created: {schedule['created_at']}")
                print(f"  Last run: {schedule.get('last_run', 'Never')}")
                print(f"  Next run: {schedule.get('next_run', 'Unknown')}")
                print(f"  Enabled: {schedule.get('enabled', True)}")
                print()
        else:
            print("No scheduled exports")
    
    elif args.schedule_command == 'create':
        # Load data query from file
        try:
            with open(args.data, 'r', encoding='utf-8') as f:
                data_query = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load data query: {str(e)}")
            return
        
        # Prepare schedule
        schedule = {
            "interval": args.interval,
            "unit": args.unit
        }
        
        # Create schedule
        schedule_id = export_manager.schedule_export(
            data_query=data_query,
            format=args.format,
            schedule=schedule,
            template_name=args.template
        )
        
        logger.info(f"Created scheduled export: {schedule_id}")

def main():
    """Main entry point."""
    args = parse_args()
    
    if args.command == 'export':
        export_data(args)
    elif args.command == 'template':
        handle_template_command(args)
    elif args.command == 'webhook':
        handle_webhook_command(args)
    elif args.command == 'schedule':
        handle_schedule_command(args)
    else:
        logger.error("No command specified")

if __name__ == '__main__':
    main()
