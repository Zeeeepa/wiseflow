#!/usr/bin/env python3
"""
Script to migrate tests from the old structure to the new structure.

This script:
1. Identifies test files in the old structure (test/ directory and root test_*.py files)
2. Analyzes each file to determine the appropriate location in the new structure
3. Migrates the file to the new location, updating imports and structure as needed
4. Generates a report of the migration

Usage:
    python scripts/migrate_tests.py [--dry-run]

Options:
    --dry-run  Show what would be migrated without making changes
"""

import os
import sys
import re
import shutil
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Define the mapping of old test files to new locations
TEST_MAPPING = {
    "test/analysis/test_entity_linking.py": "tests/core/analysis/test_entity_linking.py",
    "test/craw4ai_fetching.py": "tests/core/crawl4ai/test_fetching.py",
    "test/crawlee_fetching.py": "tests/core/crawl4ai/test_crawlee_fetching.py",
    "test/get_info_test.py": "tests/core/agents/test_get_info.py",
    "test/pre_process_test.py": "tests/core/agents/test_pre_process.py",
    "test_specialized_prompting.py": "tests/core/llms/test_specialized_prompting.py",
    "test_auto_shutdown.py": "tests/core/utils/test_auto_shutdown.py",
}

def find_test_files() -> List[str]:
    """Find all test files in the old structure."""
    test_files = []
    
    # Find files in test/ directory
    if os.path.exists("test"):
        for root, _, files in os.walk("test"):
            for file in files:
                if file.endswith(".py"):
                    test_files.append(os.path.join(root, file))
    
    # Find test_*.py files in the root directory
    for file in os.listdir("."):
        if file.endswith(".py") and file.startswith("test_"):
            test_files.append(file)
    
    return test_files

def analyze_test_file(file_path: str) -> Tuple[str, Dict[str, str]]:
    """
    Analyze a test file to determine its appropriate location and needed changes.
    
    Returns:
        Tuple of (new_path, changes)
    """
    # Check if we have a predefined mapping
    if file_path in TEST_MAPPING:
        new_path = TEST_MAPPING[file_path]
    else:
        # Try to infer the new path
        if file_path.startswith("test/"):
            # Convert test/module/test_file.py to tests/core/module/test_file.py
            parts = file_path.split("/")
            if len(parts) >= 3:
                module = parts[1]
                filename = parts[-1]
                if not filename.startswith("test_"):
                    filename = f"test_{filename}"
                new_path = f"tests/core/{module}/{filename}"
            else:
                # Default location for tests without a clear module
                filename = os.path.basename(file_path)
                if not filename.startswith("test_"):
                    filename = f"test_{filename}"
                new_path = f"tests/core/{filename}"
        else:
            # Root test files go to tests/core/
            filename = os.path.basename(file_path)
            new_path = f"tests/core/{filename}"
    
    # Analyze file content to determine needed changes
    changes = {}
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Check for imports that need to be updated
    if "import sys" in content and "sys.path.append" in content:
        changes["update_imports"] = True
    
    # Check for unittest vs pytest
    if "import unittest" in content:
        changes["convert_unittest"] = True
    
    # Check for async tests
    if "async def" in content and "asyncio.run" in content:
        changes["update_async"] = True
    
    return new_path, changes

def migrate_test_file(file_path: str, new_path: str, changes: Dict[str, str], dry_run: bool = False) -> None:
    """Migrate a test file to the new structure."""
    print(f"Migrating {file_path} to {new_path}")
    
    # Create the directory if it doesn't exist
    new_dir = os.path.dirname(new_path)
    if not dry_run and not os.path.exists(new_dir):
        os.makedirs(new_dir, exist_ok=True)
    
    # Read the file content
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Apply changes
    if changes.get("update_imports"):
        # Replace sys.path manipulation with proper imports
        content = re.sub(
            r"import\s+sys.*?\n.*?sys\.path\.append.*?\n",
            "import pytest\n",
            content,
            flags=re.DOTALL
        )
    
    if changes.get("convert_unittest"):
        # Convert unittest to pytest (basic conversion)
        content = content.replace("import unittest", "import pytest")
        content = content.replace("unittest.TestCase", "object")
        content = content.replace("self.assertEqual(", "assert ")
        content = content.replace("self.assertTrue(", "assert ")
        content = content.replace("self.assertFalse(", "assert not ")
        content = content.replace("self.assertIsNotNone(", "assert ")
        content = content.replace("self.assertIsNone(", "assert ")
        content = content.replace("self.assertIn(", "assert ")
        content = content.replace("self.assertNotIn(", "assert ")
        content = content.replace("self.assertGreater(", "assert ")
        content = content.replace("self.assertLess(", "assert ")
        content = content.replace("self.assertRaises(", "with pytest.raises(")
    
    if changes.get("update_async"):
        # Update async tests to use the async_test decorator
        content = content.replace(
            "asyncio.run(",
            "from tests.utils import async_test\n\n@async_test\nasync def"
        )
    
    # Write the file to the new location
    if not dry_run:
        with open(new_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  ✓ Migrated to {new_path}")
    else:
        print(f"  Would migrate to {new_path}")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Migrate tests from old structure to new structure")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be migrated without making changes")
    args = parser.parse_args()
    
    # Find test files
    test_files = find_test_files()
    print(f"Found {len(test_files)} test files in the old structure")
    
    # Analyze and migrate each file
    for file_path in test_files:
        new_path, changes = analyze_test_file(file_path)
        migrate_test_file(file_path, new_path, changes, args.dry_run)
    
    print("\nMigration complete!")
    if args.dry_run:
        print("This was a dry run. No files were actually migrated.")

if __name__ == "__main__":
    main()

