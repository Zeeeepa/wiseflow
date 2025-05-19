import os
import json
import re
from collections import defaultdict

def find_python_files(root_dir='.'):
    """Find all Python files in the project."""
    python_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith('.py'):
                python_files.append(os.path.join(dirpath, filename))
    return python_files

def extract_imports(file_path):
    """Extract all imports from a Python file."""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Regular expressions to match different import patterns
    import_patterns = [
        r'^\s*import\s+([\w\.]+)',  # import module
        r'^\s*from\s+([\w\.]+)\s+import',  # from module import ...
        r'^\s*from\s+([\w\.]+)\s+import\s+\(',  # from module import (
    ]
    
    imports = []
    for pattern in import_patterns:
        matches = re.findall(pattern, content, re.MULTILINE)
        imports.extend(matches)
    
    return imports

def normalize_module_path(module_path, file_path):
    """Convert a module path to a file path."""
    if module_path.startswith('.'):
        # Relative import
        current_dir = os.path.dirname(file_path)
        parts = module_path.split('.')
        
        # Count leading dots for relative imports
        level = 0
        while parts and not parts[0]:
            level += 1
            parts.pop(0)
        
        # Go up directories based on level
        for _ in range(level - 1):
            current_dir = os.path.dirname(current_dir)
        
        # Construct the path
        if parts:
            rel_path = os.path.join(current_dir, *parts)
        else:
            rel_path = current_dir
        
        # Check if it's a directory or file
        if os.path.isdir(rel_path):
            return rel_path + '/__init__.py'
        else:
            return rel_path + '.py'
    else:
        # Absolute import within the project
        parts = module_path.split('.')
        
        # Try to find the module in the project
        for i in range(len(parts), 0, -1):
            prefix = '/'.join(parts[:i])
            suffix = '/'.join(parts[i:])
            
            # Check if it's a directory with __init__.py
            if os.path.isdir(prefix) and os.path.exists(f"{prefix}/__init__.py"):
                if suffix:
                    path = f"{prefix}/{suffix}.py"
                    if os.path.exists(path):
                        return path
                    
                    # Check if it's a directory with __init__.py
                    if os.path.isdir(f"{prefix}/{suffix}") and os.path.exists(f"{prefix}/{suffix}/__init__.py"):
                        return f"{prefix}/{suffix}/__init__.py"
                else:
                    return f"{prefix}/__init__.py"
    
    # If we can't resolve it, it's likely a standard library or external package
    return None

def build_usage_map():
    """Build a map of which files use which other files."""
    python_files = find_python_files()
    usage_map = defaultdict(list)
    
    for file_path in python_files:
        imports = extract_imports(file_path)
        for module_path in imports:
            imported_file = normalize_module_path(module_path, file_path)
            if imported_file and os.path.exists(imported_file):
                # Add to the usage map
                usage_map[imported_file].append(file_path)
    
    return usage_map

def find_redundant_files():
    """Find potentially redundant files."""
    python_files = find_python_files()
    usage_map = build_usage_map()
    
    # Files that aren't imported by any other file
    not_imported = [file for file in python_files if file not in usage_map]
    
    # Files with duplicate names
    file_names = {}
    for file in python_files:
        name = os.path.basename(file)
        if name in file_names:
            file_names[name].append(file)
        else:
            file_names[name] = [file]
    
    duplicate_names = {name: files for name, files in file_names.items() if len(files) > 1 and name != "__init__.py"}
    
    return {
        'not_imported': not_imported,
        'duplicate_names': duplicate_names,
        'usage_map': {k: v for k, v in usage_map.items()}
    }

def get_file_users(file_path, usage_map):
    """Get a list of files that use the given file."""
    return usage_map.get(file_path, [])

def generate_project_structure():
    """Generate a structured representation of the project with usage information."""
    python_files = find_python_files()
    usage_map = build_usage_map()
    
    # Group files by directory
    directory_structure = defaultdict(list)
    for file_path in python_files:
        directory = os.path.dirname(file_path)
        directory_structure[directory].append(file_path)
    
    # Sort directories by depth
    sorted_directories = sorted(directory_structure.keys(), key=lambda x: x.count('/'))
    
    # Generate the structure
    structure = []
    for directory in sorted_directories:
        files = directory_structure[directory]
        structure.append(f"Directory: {directory}")
        for file_path in sorted(files):
            users = get_file_users(file_path, usage_map)
            user_info = ""
            if users:
                user_files = [os.path.basename(user) for user in users]
                user_info = f" - used by: {', '.join(user_files)}"
            structure.append(f"  {os.path.basename(file_path)}{user_info}")
    
    return structure

def identify_redundant_files():
    """Identify redundant files based on various criteria."""
    results = find_redundant_files()
    
    # Files that are not imported and are not entry points or tests
    potential_redundant = []
    for file in results['not_imported']:
        # Skip main entry points
        if file in ['./wiseflow.py', './api_server.py', './deploy_wiseflow.py']:
            continue
        
        # Skip test files
        if '/test' in file or 'test_' in file or file.startswith('./test'):
            continue
        
        # Skip example files
        if '/examples/' in file or file.startswith('./examples/'):
            continue
        
        # Skip utility scripts
        if '/scripts/' in file or file.startswith('./scripts/'):
            continue
        
        # Skip the analysis scripts we just created
        if file in ['./analyze_imports.py', './generate_structure.py']:
            continue
        
        potential_redundant.append(file)
    
    # Files with duplicate names (potential redundancy)
    duplicate_files = results['duplicate_names']
    
    return {
        'potential_redundant': potential_redundant,
        'duplicate_files': duplicate_files
    }

def main():
    """Main function to generate the project structure and identify redundant files."""
    # Generate project structure with usage information
    structure = generate_project_structure()
    with open('project_structure.txt', 'w') as f:
        f.write('\n'.join(structure))
    
    # Identify redundant files
    redundant = identify_redundant_files()
    with open('redundant_files.json', 'w') as f:
        f.write(json.dumps(redundant, indent=2))
    
    print(f"Project structure written to project_structure.txt")
    print(f"Found {len(redundant['potential_redundant'])} potentially redundant files")
    print(f"Found {len(redundant['duplicate_files'])} duplicate file names")
    print("Redundant files information written to redundant_files.json")

if __name__ == "__main__":
    main()

