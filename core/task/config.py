"""
Task configuration module for managing reference files and task settings.
"""

import os
import json
import logging
import hashlib
import shutil
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class TaskConfig:
    """Configuration manager for tasks with reference file support."""
    
    def __init__(
        self,
        task_id: Optional[str] = None,
        config_dir: str = 'configs',
        references_dir: str = 'references'
    ):
        """Initialize task configuration.
        
        Args:
            task_id: Unique identifier for the task (generated if not provided)
            config_dir: Directory for storing configuration files
            references_dir: Directory for storing reference files
        """
        self.task_id = task_id or str(uuid.uuid4())
        self.config_dir = config_dir
        self.references_dir = references_dir
        
        # Create directories if they don't exist
        os.makedirs(self.config_dir, exist_ok=True)
        os.makedirs(self.references_dir, exist_ok=True)
        
        # Task-specific directories
        self.task_config_dir = os.path.join(self.config_dir, self.task_id)
        self.task_references_dir = os.path.join(self.references_dir, self.task_id)
        
        os.makedirs(self.task_config_dir, exist_ok=True)
        os.makedirs(self.task_references_dir, exist_ok=True)
        
        # Configuration data
        self.config_data = {
            'task_id': self.task_id,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'references': [],
            'settings': {}
        }
        
        # Load existing configuration if available
        self._load_config()
        
    def _load_config(self):
        """Load configuration from file if it exists."""
        config_file = os.path.join(self.task_config_dir, 'config.json')
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    self.config_data = json.load(f)
                logger.debug(f"Loaded configuration for task {self.task_id}")
            except Exception as e:
                logger.error(f"Error loading configuration: {str(e)}")
                
    def _save_config(self):
        """Save configuration to file."""
        config_file = os.path.join(self.task_config_dir, 'config.json')
        
        try:
            # Update timestamp
            self.config_data['updated_at'] = datetime.now().isoformat()
            
            with open(config_file, 'w') as f:
                json.dump(self.config_data, f, indent=2)
            logger.debug(f"Saved configuration for task {self.task_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")
            return False
            
    def add_reference_file(
        self,
        file_path: str,
        reference_type: str = 'document',
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Add a reference file to the task.
        
        Args:
            file_path: Path to the reference file
            reference_type: Type of reference ('document', 'image', 'data', etc.)
            description: Description of the reference
            metadata: Additional metadata for the reference
            
        Returns:
            Optional[str]: Reference ID if successful, None otherwise
        """
        if not os.path.exists(file_path):
            logger.error(f"Reference file not found: {file_path}")
            return None
            
        try:
            # Generate reference ID
            file_hash = self._hash_file(file_path)
            reference_id = f"{reference_type}_{file_hash[:8]}_{os.path.basename(file_path)}"
            
            # Copy file to references directory
            reference_path = os.path.join(self.task_references_dir, reference_id)
            shutil.copy2(file_path, reference_path)
            
            # Add reference to configuration
            reference_info = {
                'id': reference_id,
                'type': reference_type,
                'filename': os.path.basename(file_path),
                'path': reference_path,
                'description': description or '',
                'metadata': metadata or {},
                'added_at': datetime.now().isoformat()
            }
            
            self.config_data['references'].append(reference_info)
            self._save_config()
            
            logger.info(f"Added reference file: {reference_id}")
            return reference_id
            
        except Exception as e:
            logger.error(f"Error adding reference file: {str(e)}")
            return None
            
    def add_reference_content(
        self,
        content: str,
        filename: str,
        reference_type: str = 'document',
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Add reference content as a file to the task.
        
        Args:
            content: Content to save as a reference
            filename: Name for the reference file
            reference_type: Type of reference ('document', 'image', 'data', etc.)
            description: Description of the reference
            metadata: Additional metadata for the reference
            
        Returns:
            Optional[str]: Reference ID if successful, None otherwise
        """
        try:
            # Generate reference ID
            content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
            reference_id = f"{reference_type}_{content_hash[:8]}_{filename}"
            
            # Save content to references directory
            reference_path = os.path.join(self.task_references_dir, reference_id)
            
            with open(reference_path, 'w') as f:
                f.write(content)
                
            # Add reference to configuration
            reference_info = {
                'id': reference_id,
                'type': reference_type,
                'filename': filename,
                'path': reference_path,
                'description': description or '',
                'metadata': metadata or {},
                'added_at': datetime.now().isoformat()
            }
            
            self.config_data['references'].append(reference_info)
            self._save_config()
            
            logger.info(f"Added reference content: {reference_id}")
            return reference_id
            
        except Exception as e:
            logger.error(f"Error adding reference content: {str(e)}")
            return None
            
    def get_reference(self, reference_id: str) -> Optional[Dict[str, Any]]:
        """Get reference information by ID.
        
        Args:
            reference_id: Reference ID
            
        Returns:
            Optional[Dict[str, Any]]: Reference information if found, None otherwise
        """
        for reference in self.config_data['references']:
            if reference['id'] == reference_id:
                return reference
        return None
        
    def get_reference_content(self, reference_id: str) -> Optional[str]:
        """Get reference file content by ID.
        
        Args:
            reference_id: Reference ID
            
        Returns:
            Optional[str]: Reference content if found, None otherwise
        """
        reference = self.get_reference(reference_id)
        
        if not reference:
            return None
            
        try:
            with open(reference['path'], 'r') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading reference content: {str(e)}")
            return None
            
    def get_references_by_type(self, reference_type: str) -> List[Dict[str, Any]]:
        """Get all references of a specific type.
        
        Args:
            reference_type: Type of references to get
            
        Returns:
            List[Dict[str, Any]]: List of reference information
        """
        return [ref for ref in self.config_data['references'] if ref['type'] == reference_type]
        
    def remove_reference(self, reference_id: str) -> bool:
        """Remove a reference from the task.
        
        Args:
            reference_id: Reference ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        reference = self.get_reference(reference_id)
        
        if not reference:
            logger.warning(f"Reference not found: {reference_id}")
            return False
            
        try:
            # Remove file
            if os.path.exists(reference['path']):
                os.remove(reference['path'])
                
            # Remove from configuration
            self.config_data['references'] = [ref for ref in self.config_data['references'] if ref['id'] != reference_id]
            self._save_config()
            
            logger.info(f"Removed reference: {reference_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing reference: {str(e)}")
            return False
            
    def set_setting(self, key: str, value: Any) -> bool:
        """Set a task setting.
        
        Args:
            key: Setting key
            value: Setting value
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.config_data['settings'][key] = value
            return self._save_config()
        except Exception as e:
            logger.error(f"Error setting task setting: {str(e)}")
            return False
            
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a task setting.
        
        Args:
            key: Setting key
            default: Default value if setting not found
            
        Returns:
            Any: Setting value or default
        """
        return self.config_data['settings'].get(key, default)
        
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all task settings.
        
        Returns:
            Dict[str, Any]: All settings
        """
        return self.config_data['settings']
        
    def remove_setting(self, key: str) -> bool:
        """Remove a task setting.
        
        Args:
            key: Setting key
            
        Returns:
            bool: True if successful, False otherwise
        """
        if key in self.config_data['settings']:
            del self.config_data['settings'][key]
            return self._save_config()
        return True
        
    def _hash_file(self, file_path: str) -> str:
        """Generate a hash for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            str: File hash
        """
        hasher = hashlib.md5()
        
        with open(file_path, 'rb') as f:
            buf = f.read(65536)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
                
        return hasher.hexdigest()
        
    def export_config(self, export_path: Optional[str] = None) -> Optional[str]:
        """Export task configuration to a file.
        
        Args:
            export_path: Path to export the configuration (default: task_id.json in config_dir)
            
        Returns:
            Optional[str]: Export file path if successful, None otherwise
        """
        if export_path is None:
            export_path = os.path.join(self.config_dir, f"{self.task_id}.json")
            
        try:
            with open(export_path, 'w') as f:
                json.dump(self.config_data, f, indent=2)
            logger.info(f"Exported configuration to {export_path}")
            return export_path
        except Exception as e:
            logger.error(f"Error exporting configuration: {str(e)}")
            return None
            
    def import_config(self, import_path: str) -> bool:
        """Import task configuration from a file.
        
        Args:
            import_path: Path to the configuration file
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not os.path.exists(import_path):
            logger.error(f"Import file not found: {import_path}")
            return False
            
        try:
            with open(import_path, 'r') as f:
                imported_config = json.load(f)
                
            # Validate imported configuration
            if 'task_id' not in imported_config:
                logger.error("Invalid configuration file: missing task_id")
                return False
                
            # Update configuration
            self.config_data = imported_config
            self._save_config()
            
            logger.info(f"Imported configuration from {import_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error importing configuration: {str(e)}")
            return False
            
    def cleanup(self) -> bool:
        """Clean up task configuration and references.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Remove reference files
            if os.path.exists(self.task_references_dir):
                shutil.rmtree(self.task_references_dir)
                
            # Remove configuration directory
            if os.path.exists(self.task_config_dir):
                shutil.rmtree(self.task_config_dir)
                
            logger.info(f"Cleaned up task {self.task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up task: {str(e)}")
            return False

