"""
XML Export Module for Wiseflow.

This module provides specialized functionality for exporting data to XML format.
"""

import logging
import xml.dom.minidom
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional
import os
from datetime import datetime

logger = logging.getLogger(__name__)

def export_to_xml(data: List[Dict[str, Any]], filepath: str) -> None:
    """
    Export data to XML.
    
    Args:
        data: Data to export
        filepath: Path to save the XML file
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        
        # Create root element
        root = ET.Element("data")
        
        # Add items
        for i, item in enumerate(data):
            item_elem = ET.SubElement(root, "item", id=str(i+1))
            
            # Add fields
            for key, value in item.items():
                # Skip None values
                if value is None:
                    continue
                
                # Convert complex types to string
                if isinstance(value, (dict, list)):
                    value = str(value)
                elif isinstance(value, datetime):
                    value = value.isoformat()
                elif not isinstance(value, (str, int, float, bool)):
                    value = str(value)
                
                # Create field element
                field_elem = ET.SubElement(item_elem, key)
                
                # Set value
                if isinstance(value, bool):
                    field_elem.text = "true" if value else "false"
                else:
                    field_elem.text = str(value)
        
        # Create XML tree
        tree = ET.ElementTree(root)
        
        # Pretty print XML
        xml_string = ET.tostring(root, encoding='utf-8')
        dom = xml.dom.minidom.parseString(xml_string)
        pretty_xml = dom.toprettyxml(indent="  ", encoding='utf-8').decode('utf-8')
        
        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(pretty_xml)
        
        logger.info(f"Exported {len(data)} records to XML: {filepath}")
    except Exception as e:
        logger.error(f"XML export failed: {str(e)}")
        raise

def export_to_xml_with_config(data: List[Dict[str, Any]], 
                             filepath: str, 
                             config: Dict[str, Any]) -> None:
    """
    Export data to XML with additional configuration options.
    
    Args:
        data: Data to export
        filepath: Path to save the XML file
        config: Configuration options (root_name, item_name, fields, etc.)
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        
        # Get XML options
        root_name = config.get('root_name', 'data')
        item_name = config.get('item_name', 'item')
        fields_to_include = config.get('fields', None)
        id_field = config.get('id_field', None)
        
        # Create root element
        root = ET.Element(root_name)
        
        # Add items
        for i, item in enumerate(data):
            # Create item element with ID attribute if specified
            item_attrs = {}
            if id_field and id_field in item:
                item_attrs['id'] = str(item[id_field])
            else:
                item_attrs['id'] = str(i+1)
            
            item_elem = ET.SubElement(root, item_name, **item_attrs)
            
            # Add fields
            for key, value in item.items():
                # Skip fields not in the include list if specified
                if fields_to_include and key not in fields_to_include:
                    continue
                
                # Skip None values
                if value is None:
                    continue
                
                # Convert complex types to string
                if isinstance(value, (dict, list)):
                    value = str(value)
                elif isinstance(value, datetime):
                    value = value.isoformat()
                elif not isinstance(value, (str, int, float, bool)):
                    value = str(value)
                
                # Create field element
                field_elem = ET.SubElement(item_elem, key)
                
                # Set value
                if isinstance(value, bool):
                    field_elem.text = "true" if value else "false"
                else:
                    field_elem.text = str(value)
        
        # Create XML tree
        tree = ET.ElementTree(root)
        
        # Pretty print XML
        xml_string = ET.tostring(root, encoding='utf-8')
        dom = xml.dom.minidom.parseString(xml_string)
        pretty_xml = dom.toprettyxml(indent="  ", encoding='utf-8').decode('utf-8')
        
        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(pretty_xml)
        
        logger.info(f"Exported {len(data)} records to XML with custom config: {filepath}")
    except Exception as e:
        logger.error(f"XML export with config failed: {str(e)}")
        raise

def xml_to_dict(xml_file: str) -> List[Dict[str, Any]]:
    """
    Convert an XML file to a list of dictionaries.
    
    Args:
        xml_file: Path to the XML file
        
    Returns:
        List of dictionaries representing the XML data
    """
    try:
        if not os.path.exists(xml_file):
            logger.error(f"XML file not found: {xml_file}")
            return []
        
        # Parse XML
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        result = []
        
        # Process each item
        for item_elem in root:
            item_dict = {}
            
            # Get attributes
            for attr_name, attr_value in item_elem.attrib.items():
                item_dict[attr_name] = attr_value
            
            # Get child elements
            for child_elem in item_elem:
                # Convert value to appropriate type if possible
                value = child_elem.text or ""
                
                # Try to convert to number
                if value.isdigit():
                    value = int(value)
                elif value.replace('.', '', 1).isdigit() and value.count('.') <= 1:
                    value = float(value)
                elif value.lower() == 'true':
                    value = True
                elif value.lower() == 'false':
                    value = False
                
                item_dict[child_elem.tag] = value
            
            result.append(item_dict)
        
        return result
    except Exception as e:
        logger.error(f"XML to dict conversion failed: {str(e)}")
        return []
