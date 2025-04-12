"""
XML Export Module for Wiseflow.

This module provides specialized functionality for exporting data to XML format.
"""

import logging
import xml.dom.minidom
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional
import os

logger = logging.getLogger(__name__)

def export_to_xml(data: List[Dict[str, Any]], filepath: str) -> None:
    """
    Export data to XML.
    
    Args:
        data: Data to export
        filepath: Path to save the XML file
    """
    try:
        root = ET.Element("data")
        
        for item in data:
            record = ET.SubElement(root, "record")
            
            for key, value in item.items():
                # Skip None values
                if value is None:
                    continue
                
                field = ET.SubElement(record, key)
                field.text = str(value)
        
        # Pretty print XML
        xml_str = ET.tostring(root, encoding='utf-8')
        dom = xml.dom.minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent="  ")
        
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
        config: Configuration options (root_element, record_element, etc.)
    """
    try:
        # Get XML options
        root_element = config.get('root_element', 'data')
        record_element = config.get('record_element', 'record')
        indent = config.get('indent', '  ')
        
        # Get fields to include (if specified)
        fields_to_include = config.get('fields', None)
        
        # Create root element
        root = ET.Element(root_element)
        
        # Add attributes to root if specified
        root_attrs = config.get('root_attributes', {})
        for attr_name, attr_value in root_attrs.items():
            root.set(attr_name, str(attr_value))
        
        for item in data:
            record = ET.SubElement(root, record_element)
            
            # Add record attributes if specified
            record_attrs = config.get('record_attributes', {})
            for attr_name, attr_value in record_attrs.items():
                if attr_name in item:
                    record.set(attr_name, str(item[attr_name]))
            
            # Add fields
            for key, value in item.items():
                # Skip None values and attributes
                if value is None or key in record_attrs:
                    continue
                
                # Skip fields not in the include list if specified
                if fields_to_include and key not in fields_to_include:
                    continue
                
                # Handle nested dictionaries
                if isinstance(value, dict):
                    nested = ET.SubElement(record, key)
                    for nested_key, nested_value in value.items():
                        if nested_value is not None:
                            nested_field = ET.SubElement(nested, nested_key)
                            nested_field.text = str(nested_value)
                # Handle lists
                elif isinstance(value, list):
                    list_element = ET.SubElement(record, key)
                    for i, list_item in enumerate(value):
                        if isinstance(list_item, dict):
                            item_element = ET.SubElement(list_element, 'item')
                            for item_key, item_value in list_item.items():
                                if item_value is not None:
                                    item_field = ET.SubElement(item_element, item_key)
                                    item_field.text = str(item_value)
                        else:
                            item_element = ET.SubElement(list_element, 'item')
                            item_element.text = str(list_item)
                # Handle simple values
                else:
                    field = ET.SubElement(record, key)
                    field.text = str(value)
        
        # Pretty print XML
        xml_str = ET.tostring(root, encoding='utf-8')
        dom = xml.dom.minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent=indent)
        
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
        
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        result = []
        
        # Assume records are direct children of root
        for record in root:
            record_dict = {}
            
            # Add record attributes
            for attr_name, attr_value in record.attrib.items():
                record_dict[attr_name] = attr_value
            
            # Add record elements
            for element in record:
                # Check if element has children (nested structure)
                if len(element) > 0:
                    # Handle nested elements
                    nested_dict = {}
                    for nested_element in element:
                        nested_dict[nested_element.tag] = nested_element.text
                    record_dict[element.tag] = nested_dict
                else:
                    record_dict[element.tag] = element.text
            
            result.append(record_dict)
        
        return result
    except Exception as e:
        logger.error(f"XML to dict conversion failed: {str(e)}")
        return []
