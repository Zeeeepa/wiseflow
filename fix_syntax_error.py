#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script to fix syntax errors in the wiseflow package.

This script fixes the syntax error in run_task.py by properly using the args parameter
for positional arguments in the register_task function call.
"""

import os
import sys
import re
import shutil
from pathlib import Path

def fix_run_task_file():
    """Fix the syntax error in run_task.py."""
    run_task_path = Path("wiseflow/task_management/run_task.py")
    
    if not run_task_path.exists():
        print(f"Error: {run_task_path} does not exist.")
        return False
    
    # Create a backup
    backup_path = run_task_path.with_suffix(".py.bak")
    shutil.copy2(run_task_path, backup_path)
    print(f"Created backup at {backup_path}")
    
    # Read the file
    with open(run_task_path, "r") as f:
        content = f.read()
    
    # Fix the syntax error
    pattern = r"func=process_focus_task_wrapper,\s+focus,\s+sites,"
    replacement = "func=process_focus_task_wrapper,\n                        args=(focus, sites),"
    
    new_content = re.sub(pattern, replacement, content)
    
    # Fix import paths
    import_pattern = r"from core\.general_process import main_process, wiseflow_logger, pb"
    import_replacement = "from wiseflow.utils.pb_api import PbTalker\nfrom wiseflow.task_management.task_manager import TaskManager\nfrom wiseflow.task_management.thread_pool_manager import ThreadPoolManager, TaskPriority, TaskStatus\nfrom wiseflow.resource_monitoring.resource_monitor import ResourceMonitor"
    
    new_content = re.sub(import_pattern, import_replacement, new_content)
    
    # Write the fixed content
    with open(run_task_path, "w") as f:
        f.write(new_content)
    
    print(f"Fixed syntax error in {run_task_path}")
    return True

def main():
    """Main entry point."""
    print("Starting syntax error fix...")
    
    if not fix_run_task_file():
        print("Failed to fix syntax error.")
        return 1
    
    print("Syntax error fix completed successfully.")
    return 0

if __name__ == "__main__":
    sys.exit(main())

