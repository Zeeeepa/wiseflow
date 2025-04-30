"""
Command-line interface for data mining operations.
"""

import argparse
import logging
import sys
import os
import json
from typing import Any, Dict, List, Optional, Union
import importlib

from core.plugins.base import registry
from core.thread_pool_manager import thread_pool_manager, TaskPriority
from core.resource_monitor import resource_monitor
from core.task.monitor import task_monitor
from core.task.config import TaskConfig

logger = logging.getLogger(__name__)


def setup_logging(level=logging.INFO):
    """Set up logging configuration."""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('data_mining.log')
        ]
    )


def load_plugins():
    """Load all available plugins."""
    # Import connector plugins
    try:
        from core.plugins.connectors import GitHubConnector, YouTubeConnector, CodeSearchConnector
        logger.info(f"Loaded connector plugins: {', '.join(registry.list_connectors())}")
    except ImportError as e:
        logger.warning(f"Error loading connector plugins: {str(e)}")
        
    # Import processor plugins
    try:
        from core.plugins.processors import TextProcessor
        logger.info(f"Loaded processor plugins: {', '.join(registry.list_processors())}")
    except ImportError as e:
        logger.warning(f"Error loading processor plugins: {str(e)}")
        
    # Import analyzer plugins
    try:
        from core.plugins.analyzers import EntityAnalyzer, TrendAnalyzer
        logger.info(f"Loaded analyzer plugins: {', '.join(registry.list_analyzers())}")
    except ImportError as e:
        logger.warning(f"Error loading analyzer plugins: {str(e)}")


def create_parser():
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(description='Wiseflow Data Mining CLI')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # List plugins command
    list_parser = subparsers.add_parser('list', help='List available plugins')
    list_parser.add_argument('--type', choices=['connectors', 'processors', 'analyzers', 'all'], 
                            default='all', help='Type of plugins to list')
    
    # Connect command
    connect_parser = subparsers.add_parser('connect', help='Connect to a data source')
    connect_parser.add_argument('connector', help='Connector plugin to use')
    connect_parser.add_argument('--config', help='Path to connector configuration file')
    connect_parser.add_argument('--output', help='Path to save connection information')
    
    # Fetch command
    fetch_parser = subparsers.add_parser('fetch', help='Fetch data from a source')
    fetch_parser.add_argument('connector', help='Connector plugin to use')
    fetch_parser.add_argument('query', help='Query string for the connector')
    fetch_parser.add_argument('--config', help='Path to connector configuration file')
    fetch_parser.add_argument('--output', help='Path to save fetched data')
    fetch_parser.add_argument('--params', help='Additional parameters as JSON string')
    
    # Process command
    process_parser = subparsers.add_parser('process', help='Process data')
    process_parser.add_argument('processor', help='Processor plugin to use')
    process_parser.add_argument('--input', required=True, help='Path to input data file')
    process_parser.add_argument('--config', help='Path to processor configuration file')
    process_parser.add_argument('--output', help='Path to save processed data')
    process_parser.add_argument('--params', help='Additional parameters as JSON string')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze data')
    analyze_parser.add_argument('analyzer', help='Analyzer plugin to use')
    analyze_parser.add_argument('--input', required=True, help='Path to input data file')
    analyze_parser.add_argument('--config', help='Path to analyzer configuration file')
    analyze_parser.add_argument('--output', help='Path to save analysis results')
    analyze_parser.add_argument('--params', help='Additional parameters as JSON string')
    
    # Pipeline command
    pipeline_parser = subparsers.add_parser('pipeline', help='Run a data mining pipeline')
    pipeline_parser.add_argument('--pipeline', required=True, help='Path to pipeline configuration file')
    pipeline_parser.add_argument('--output', help='Path to save pipeline results')
    pipeline_parser.add_argument('--task-id', help='Task ID for tracking')
    
    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Monitor system resources')
    monitor_parser.add_argument('--interval', type=float, default=60.0, help='Monitoring interval in seconds')
    monitor_parser.add_argument('--output', help='Path to save monitoring data')
    monitor_parser.add_argument('--duration', type=float, help='Monitoring duration in seconds')
    
    # Task command
    task_parser = subparsers.add_parser('task', help='Manage tasks')
    task_subparsers = task_parser.add_subparsers(dest='task_command', help='Task command')
    
    # Task list command
    task_list_parser = task_subparsers.add_parser('list', help='List tasks')
    task_list_parser.add_argument('--status', help='Filter by task status')
    task_list_parser.add_argument('--type', help='Filter by task type')
    
    # Task info command
    task_info_parser = task_subparsers.add_parser('info', help='Get task information')
    task_info_parser.add_argument('task_id', help='Task ID')
    
    # Task log command
    task_log_parser = task_subparsers.add_parser('log', help='Get task log')
    task_log_parser.add_argument('task_id', help='Task ID')
    
    # Task cancel command
    task_cancel_parser = task_subparsers.add_parser('cancel', help='Cancel a task')
    task_cancel_parser.add_argument('task_id', help='Task ID')
    
    # Task cleanup command
    task_cleanup_parser = task_subparsers.add_parser('cleanup', help='Clean up completed tasks')
    task_cleanup_parser.add_argument('--age', type=float, default=86400.0, help='Maximum age in seconds')
    
    return parser


def load_config(config_path):
    """Load configuration from a file."""
    if not config_path:
        return {}
        
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        return {}


def save_output(data, output_path):
    """Save data to an output file."""
    if not output_path:
        print(json.dumps(data, indent=2))
        return True
        
    try:
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Output saved to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving output: {str(e)}")
        return False


def handle_list_command(args):
    """Handle the list command."""
    if args.type == 'connectors' or args.type == 'all':
        print("Available connectors:")
        for connector in registry.list_connectors():
            print(f"  - {connector}")
            
    if args.type == 'processors' or args.type == 'all':
        print("Available processors:")
        for processor in registry.list_processors():
            print(f"  - {processor}")
            
    if args.type == 'analyzers' or args.type == 'all':
        print("Available analyzers:")
        for analyzer in registry.list_analyzers():
            print(f"  - {analyzer}")


def handle_connect_command(args):
    """Handle the connect command."""
    connector_class = registry.get_connector(args.connector)
    
    if not connector_class:
        logger.error(f"Connector not found: {args.connector}")
        return False
        
    config = load_config(args.config)
    connector = connector_class(config)
    
    if not connector.initialize():
        logger.error(f"Failed to initialize connector: {args.connector}")
        return False
        
    if not connector.connect():
        logger.error(f"Failed to connect using connector: {args.connector}")
        return False
        
    result = {
        'connector': args.connector,
        'status': 'connected',
        'config': config
    }
    
    save_output(result, args.output)
    return True


def handle_fetch_command(args):
    """Handle the fetch command."""
    connector_class = registry.get_connector(args.connector)
    
    if not connector_class:
        logger.error(f"Connector not found: {args.connector}")
        return False
        
    config = load_config(args.config)
    connector = connector_class(config)
    
    if not connector.initialize():
        logger.error(f"Failed to initialize connector: {args.connector}")
        return False
        
    if not connector.connect():
        logger.error(f"Failed to connect using connector: {args.connector}")
        return False
        
    params = {}
    if args.params:
        try:
            params = json.loads(args.params)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON parameters: {args.params}")
            return False
            
    try:
        data = connector.fetch_data(args.query, **params)
        
        result = {
            'connector': args.connector,
            'query': args.query,
            'params': params,
            'data': data
        }
        
        save_output(result, args.output)
        return True
        
    except Exception as e:
        logger.error(f"Error fetching data: {str(e)}")
        return False
    finally:
        connector.disconnect()


def handle_process_command(args):
    """Handle the process command."""
    processor_class = registry.get_processor(args.processor)
    
    if not processor_class:
        logger.error(f"Processor not found: {args.processor}")
        return False
        
    config = load_config(args.config)
    processor = processor_class(config)
    
    if not processor.initialize():
        logger.error(f"Failed to initialize processor: {args.processor}")
        return False
        
    try:
        with open(args.input, 'r') as f:
            input_data = f.read()
            
        params = {}
        if args.params:
            try:
                params = json.loads(args.params)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON parameters: {args.params}")
                return False
                
        result = processor.process(input_data, **params)
        
        output_data = {
            'processor': args.processor,
            'input_file': args.input,
            'params': params,
            'result': result
        }
        
        save_output(output_data, args.output)
        return True
        
    except Exception as e:
        logger.error(f"Error processing data: {str(e)}")
        return False


def handle_analyze_command(args):
    """Handle the analyze command."""
    analyzer_class = registry.get_analyzer(args.analyzer)
    
    if not analyzer_class:
        logger.error(f"Analyzer not found: {args.analyzer}")
        return False
        
    config = load_config(args.config)
    analyzer = analyzer_class(config)
    
    if not analyzer.initialize():
        logger.error(f"Failed to initialize analyzer: {args.analyzer}")
        return False
        
    try:
        with open(args.input, 'r') as f:
            input_data = f.read()
            
        params = {}
        if args.params:
            try:
                params = json.loads(args.params)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON parameters: {args.params}")
                return False
                
        result = analyzer.analyze(input_data, **params)
        
        output_data = {
            'analyzer': args.analyzer,
            'input_file': args.input,
            'params': params,
            'result': result
        }
        
        save_output(output_data, args.output)
        return True
        
    except Exception as e:
        logger.error(f"Error analyzing data: {str(e)}")
        return False


def handle_pipeline_command(args):
    """Handle the pipeline command."""
    try:
        pipeline_config = load_config(args.pipeline)
        
        if not pipeline_config:
            logger.error(f"Failed to load pipeline configuration: {args.pipeline}")
            return False
            
        # Register task if task ID provided
        task_id = args.task_id
        if task_id:
            task_monitor.register_task(
                task_id=task_id,
                task_type='pipeline',
                description=f"Pipeline: {args.pipeline}",
                metadata={'pipeline_config': args.pipeline}
            )
            task_monitor.start_task(task_id)
            
        # Execute pipeline steps
        results = []
        step_count = len(pipeline_config.get('steps', []))
        
        for i, step in enumerate(pipeline_config.get('steps', [])):
            step_type = step.get('type')
            step_name = step.get('name', f"Step {i+1}")
            
            logger.info(f"Executing pipeline step {i+1}/{step_count}: {step_name} ({step_type})")
            
            if task_id:
                task_monitor.update_task_progress(
                    task_id,
                    progress=i / step_count,
                    message=f"Executing step: {step_name}"
                )
                
            if step_type == 'connect':
                connector_name = step.get('connector')
                connector_class = registry.get_connector(connector_name)
                
                if not connector_class:
                    logger.error(f"Connector not found: {connector_name}")
                    continue
                    
                connector = connector_class(step.get('config', {}))
                connector.initialize()
                connector.connect()
                
                step_result = {
                    'step': i,
                    'name': step_name,
                    'type': step_type,
                    'connector': connector_name,
                    'status': 'connected'
                }
                
            elif step_type == 'fetch':
                connector_name = step.get('connector')
                connector_class = registry.get_connector(connector_name)
                
                if not connector_class:
                    logger.error(f"Connector not found: {connector_name}")
                    continue
                    
                connector = connector_class(step.get('config', {}))
                connector.initialize()
                connector.connect()
                
                data = connector.fetch_data(
                    step.get('query', ''),
                    **step.get('params', {})
                )
                
                connector.disconnect()
                
                step_result = {
                    'step': i,
                    'name': step_name,
                    'type': step_type,
                    'connector': connector_name,
                    'query': step.get('query', ''),
                    'data': data
                }
                
            elif step_type == 'process':
                processor_name = step.get('processor')
                processor_class = registry.get_processor(processor_name)
                
                if not processor_class:
                    logger.error(f"Processor not found: {processor_name}")
                    continue
                    
                processor = processor_class(step.get('config', {}))
                processor.initialize()
                
                # Get input data from previous step or file
                input_data = None
                input_step = step.get('input_step')
                input_file = step.get('input_file')
                
                if input_step is not None and 0 <= input_step < len(results):
                    input_data = results[input_step].get('data')
                elif input_file:
                    with open(input_file, 'r') as f:
                        input_data = f.read()
                        
                if input_data is None:
                    logger.error(f"No input data for processing step: {step_name}")
                    continue
                    
                result = processor.process(
                    input_data,
                    **step.get('params', {})
                )
                
                step_result = {
                    'step': i,
                    'name': step_name,
                    'type': step_type,
                    'processor': processor_name,
                    'data': result
                }
                
            elif step_type == 'analyze':
                analyzer_name = step.get('analyzer')
                analyzer_class = registry.get_analyzer(analyzer_name)
                
                if not analyzer_class:
                    logger.error(f"Analyzer not found: {analyzer_name}")
                    continue
                    
                analyzer = analyzer_class(step.get('config', {}))
                analyzer.initialize()
                
                # Get input data from previous step or file
                input_data = None
                input_step = step.get('input_step')
                input_file = step.get('input_file')
                
                if input_step is not None and 0 <= input_step < len(results):
                    input_data = results[input_step].get('data')
                elif input_file:
                    with open(input_file, 'r') as f:
                        input_data = f.read()
                        
                if input_data is None:
                    logger.error(f"No input data for analysis step: {step_name}")
                    continue
                    
                result = analyzer.analyze(
                    input_data,
                    **step.get('params', {})
                )
                
                step_result = {
                    'step': i,
                    'name': step_name,
                    'type': step_type,
                    'analyzer': analyzer_name,
                    'data': result
                }
                
            else:
                logger.error(f"Unknown step type: {step_type}")
                continue
                
            results.append(step_result)
            
        # Complete task if task ID provided
        if task_id:
            task_monitor.update_task_progress(task_id, progress=1.0)
            task_monitor.complete_task(task_id, result=results)
            
        # Save pipeline results
        pipeline_result = {
            'pipeline': args.pipeline,
            'steps': len(results),
            'results': results
        }
        
        save_output(pipeline_result, args.output)
        return True
        
    except Exception as e:
        logger.error(f"Error executing pipeline: {str(e)}")
        
        if task_id:
            task_monitor.fail_task(task_id, str(e))
            
        return False


def handle_monitor_command(args):
    """Handle the monitor command."""
    try:
        interval = args.interval
        duration = args.duration
        
        # Start resource monitor if not already running
        if not resource_monitor.monitor_thread or not resource_monitor.monitor_thread.is_alive():
            resource_monitor.check_interval = interval
            resource_monitor.start()
            
        print(f"Monitoring system resources (interval: {interval}s)")
        
        if duration:
            print(f"Monitoring will stop after {duration}s")
            
        start_time = time.time()
        
        try:
            while True:
                if duration and time.time() - start_time >= duration:
                    break
                    
                # Get current resource usage
                usage = resource_monitor.get_resource_usage()
                
                print(f"CPU: {usage['cpu']:.1f}%, Memory: {usage['memory']:.1f}%, Disk: {usage['disk']:.1f}%")
                
                # Sleep for interval
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("Monitoring stopped by user")
            
        # Save monitoring data if output path provided
        if args.output:
            history = resource_monitor.get_resource_history()
            save_output(history, args.output)
            
        return True
        
    except Exception as e:
        logger.error(f"Error monitoring resources: {str(e)}")
        return False


def handle_task_command(args):
    """Handle the task command."""
    if not args.task_command:
        print("Task command required. Use --help for more information.")
        return False
        
    if args.task_command == 'list':
        tasks = task_monitor.get_all_tasks()
        
        if args.status:
            tasks = {k: v for k, v in tasks.items() if v['status'] == args.status}
            
        if args.type:
            tasks = {k: v for k, v in tasks.items() if v['task_type'] == args.type}
            
        print(f"Tasks ({len(tasks)}):")
        for task_id, task_info in tasks.items():
            print(f"  - {task_id}: {task_info['task_type']} ({task_info['status']})")
            
        return True
        
    elif args.task_command == 'info':
        task_info = task_monitor.get_task_info(args.task_id)
        
        if not task_info:
            logger.error(f"Task not found: {args.task_id}")
            return False
            
        print(json.dumps(task_info, indent=2))
        return True
        
    elif args.task_command == 'log':
        log = task_monitor.get_task_log(args.task_id)
        
        if log is None:
            logger.error(f"Task not found: {args.task_id}")
            return False
            
        print(log)
        return True
        
    elif args.task_command == 'cancel':
        result = task_monitor.cancel_task(args.task_id)
        
        if result:
            print(f"Task cancelled: {args.task_id}")
        else:
            logger.error(f"Failed to cancel task: {args.task_id}")
            
        return result
        
    elif args.task_command == 'cleanup':
        count = task_monitor.cleanup_completed_tasks(args.age)
        print(f"Cleaned up {count} completed tasks")
        return True
        
    return False


def main():
    """Main entry point for the CLI."""
    setup_logging()
    load_plugins()
    
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
        
    try:
        if args.command == 'list':
            handle_list_command(args)
        elif args.command == 'connect':
            handle_connect_command(args)
        elif args.command == 'fetch':
            handle_fetch_command(args)
        elif args.command == 'process':
            handle_process_command(args)
        elif args.command == 'analyze':
            handle_analyze_command(args)
        elif args.command == 'pipeline':
            handle_pipeline_command(args)
        elif args.command == 'monitor':
            handle_monitor_command(args)
        elif args.command == 'task':
            handle_task_command(args)
        else:
            logger.error(f"Unknown command: {args.command}")
            return 1
            
        return 0
        
    except Exception as e:
        logger.error(f"Error executing command: {str(e)}")
        return 1
    finally:
        # Clean up resources
        resource_monitor.stop()


if __name__ == '__main__':
    sys.exit(main())

