"""
Tests for the export_utils module.
"""

import os
import unittest
from unittest.mock import patch, MagicMock
import tempfile
from datetime import datetime

from core.utils.export_utils import (
    preprocess_data,
    test_connection,
    export_to_csv,
    export_to_excel,
    export_infos
)

class TestExportUtils(unittest.TestCase):
    """Test cases for export_utils module."""
    
    def test_preprocess_data(self):
        """Test preprocess_data function."""
        # Test data with datetime objects
        test_data = [
            {
                'id': '1',
                'created': datetime(2023, 1, 1, 12, 0, 0),
                'updated': datetime(2023, 1, 2, 12, 0, 0),
                'references': {'ref1': 'value1', 'ref2': 'value2'}
            },
            {
                'id': '2',
                'created': '2023-01-01',  # Already a string
                'references': None
            }
        ]
        
        # Process the data
        processed_data = preprocess_data(test_data)
        
        # Check that datetime objects were converted to strings
        self.assertEqual(processed_data[0]['created'], '2023-01-01 12:00:00')
        self.assertEqual(processed_data[0]['updated'], '2023-01-02 12:00:00')
        
        # Check that references were converted to string
        self.assertTrue(isinstance(processed_data[0]['references'], str))
        
        # Check that string dates were not modified
        self.assertEqual(processed_data[1]['created'], '2023-01-01')
        
        # Check that None references were not modified
        self.assertIsNone(processed_data[1]['references'])
    
    @patch('core.utils.export_utils.PbExporter')
    def test_test_connection(self, mock_exporter_class):
        """Test test_connection function."""
        # Create mock exporter
        mock_exporter = MagicMock()
        mock_exporter.client.base_url = 'http://test.com'
        mock_exporter.client.auth_store.token = 'test_token'
        
        # Mock read method to return test data
        mock_exporter.read.return_value = [
            {'id': '1', 'name': 'Test', '_created': '2023-01-01'}
        ]
        
        # Test successful connection
        result = test_connection(mock_exporter)
        self.assertTrue(result)
        mock_exporter.read.assert_called_once()
        
        # Test failed connection
        mock_exporter.read.side_effect = Exception('Connection error')
        result = test_connection(mock_exporter)
        self.assertFalse(result)
    
    @patch('core.utils.export_utils.PbExporter')
    def test_export_to_csv(self, mock_exporter_class):
        """Test export_to_csv function."""
        # Create mock exporter instance
        mock_exporter_instance = MagicMock()
        mock_exporter_class.return_value = mock_exporter_instance
        
        # Mock export_to_csv method to return True
        mock_exporter_instance.export_to_csv.return_value = True
        
        # Create temporary file for testing
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Create empty file to simulate successful export
            with open(temp_path, 'w') as f:
                f.write('test')
            
            # Test export
            result = export_to_csv(
                collection_name='test_collection',
                output_path=temp_path,
                fields=['id', 'name'],
                filter_str='id="1"'
            )
            
            # Check result
            self.assertTrue(result)
            mock_exporter_instance.export_to_csv.assert_called_once()
            
            # Test export failure
            mock_exporter_instance.export_to_csv.return_value = False
            result = export_to_csv(
                collection_name='test_collection',
                output_path=temp_path,
                fields=['id', 'name']
            )
            self.assertFalse(result)
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @patch('core.utils.export_utils.PbExporter')
    def test_export_to_excel(self, mock_exporter_class):
        """Test export_to_excel function."""
        # Create mock exporter instance
        mock_exporter_instance = MagicMock()
        mock_exporter_class.return_value = mock_exporter_instance
        
        # Mock export_to_excel method to return True
        mock_exporter_instance.export_to_excel.return_value = True
        
        # Create temporary file for testing
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Create empty file to simulate successful export
            with open(temp_path, 'w') as f:
                f.write('test')
            
            # Test export
            result = export_to_excel(
                collection_name='test_collection',
                output_path=temp_path,
                fields=['id', 'name'],
                sheet_name='Test Sheet'
            )
            
            # Check result
            self.assertTrue(result)
            mock_exporter_instance.export_to_excel.assert_called_once()
            
            # Test export failure
            mock_exporter_instance.export_to_excel.return_value = False
            result = export_to_excel(
                collection_name='test_collection',
                output_path=temp_path,
                fields=['id', 'name']
            )
            self.assertFalse(result)
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @patch('core.utils.export_utils.export_to_csv')
    def test_export_infos(self, mock_export_to_csv):
        """Test export_infos function."""
        # Mock export_to_csv to return True
        mock_export_to_csv.return_value = True
        
        # Test with default output path
        result = export_infos()
        self.assertTrue(result)
        mock_export_to_csv.assert_called_once()
        
        # Test with custom output path
        mock_export_to_csv.reset_mock()
        result = export_infos('custom_path.csv')
        self.assertTrue(result)
        mock_export_to_csv.assert_called_once_with(
            collection_name='pbc_629947526',
            output_path='custom_path.csv',
            fields=[
                'id', 'created', 'updated', 'content', 
                'references', 'report', 'screenshot', 
                'tag', 'url', 'url_title'
            ],
            filter_str='',
            preprocess_func=preprocess_data
        )

if __name__ == '__main__':
    unittest.main()

