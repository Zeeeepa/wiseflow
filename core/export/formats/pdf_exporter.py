"""
PDF Export Module for Wiseflow.

This module provides specialized functionality for exporting data to PDF format.
"""

import logging
import os
from typing import Dict, List, Any, Optional
import tempfile
import json
from datetime import datetime
import contextlib

logger = logging.getLogger(__name__)

try:
    import pdfkit
    from weasyprint import HTML
    PDF_SUPPORT = True
except ImportError:
    logger.warning("PDF export functionality is limited: pdfkit or weasyprint not installed")
    PDF_SUPPORT = False

def export_to_pdf(data: List[Dict[str, Any]], filepath: str) -> None:
    """
    Export data to PDF.
    
    Args:
        data: Data to export
        filepath: Path to save the PDF file
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        
        if not PDF_SUPPORT:
            logger.error("PDF export requires pdfkit and weasyprint. Please install with: pip install pdfkit weasyprint")
            raise ImportError("PDF export requires pdfkit and weasyprint")
        
        # Generate HTML content
        html_content = _generate_html_table(data)
        
        # Export to PDF using weasyprint
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as temp_html:
            temp_html.write(html_content.encode('utf-8'))
            temp_html_path = temp_html.name
        
        try:
            HTML(filename=temp_html_path).write_pdf(filepath)
            logger.info(f"Exported {len(data)} records to PDF: {filepath}")
        finally:
            # Clean up temporary file
            with contextlib.suppress(Exception):
                os.unlink(temp_html_path)
    except Exception as e:
        logger.error(f"PDF export failed: {str(e)}")
        raise

def export_to_pdf_with_config(data: List[Dict[str, Any]], 
                             filepath: str, 
                             config: Dict[str, Any]) -> None:
    """
    Export data to PDF with additional configuration options.
    
    Args:
        data: Data to export
        filepath: Path to save the PDF file
        config: Configuration options (title, fields, etc.)
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        
        if not PDF_SUPPORT:
            logger.error("PDF export requires pdfkit and weasyprint. Please install with: pip install pdfkit weasyprint")
            raise ImportError("PDF export requires pdfkit and weasyprint")
        
        # Get PDF options
        title = config.get('title', 'Data Export')
        fields_to_include = config.get('fields', None)
        css = config.get('css', None)
        
        # Filter data if fields are specified
        if fields_to_include:
            filtered_data = []
            for item in data:
                filtered_item = {k: item.get(k) for k in fields_to_include if k in item}
                filtered_data.append(filtered_item)
            export_data = filtered_data
        else:
            export_data = data
        
        # Generate HTML content
        html_content = _generate_html_table(export_data, title=title, css=css)
        
        # Export to PDF using weasyprint
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as temp_html:
            temp_html.write(html_content.encode('utf-8'))
            temp_html_path = temp_html.name
        
        try:
            HTML(filename=temp_html_path).write_pdf(filepath)
            logger.info(f"Exported {len(export_data)} records to PDF with custom config: {filepath}")
        finally:
            # Clean up temporary file
            with contextlib.suppress(Exception):
                os.unlink(temp_html_path)
    except Exception as e:
        logger.error(f"PDF export with config failed: {str(e)}")
        raise

def html_to_pdf(html_content: str, filepath: str) -> None:
    """
    Convert HTML content to PDF.
    
    Args:
        html_content: HTML content to convert
        filepath: Path to save the PDF file
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        
        if not PDF_SUPPORT:
            logger.error("PDF export requires pdfkit and weasyprint. Please install with: pip install pdfkit weasyprint")
            raise ImportError("PDF export requires pdfkit and weasyprint")
        
        # Export to PDF using weasyprint
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as temp_html:
            temp_html.write(html_content.encode('utf-8'))
            temp_html_path = temp_html.name
        
        try:
            HTML(filename=temp_html_path).write_pdf(filepath)
            logger.info(f"Converted HTML to PDF: {filepath}")
        finally:
            # Clean up temporary file
            with contextlib.suppress(Exception):
                os.unlink(temp_html_path)
    except Exception as e:
        logger.error(f"HTML to PDF conversion failed: {str(e)}")
        raise

def _generate_html_table(data: List[Dict[str, Any]], title: str = 'Data Export', css: Optional[str] = None) -> str:
    """
    Generate HTML table from data.
    
    Args:
        data: Data to convert to HTML table
        title: Title for the HTML document
        css: Optional CSS styles
        
    Returns:
        HTML content as string
    """
    if not data:
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                .empty-message {{ color: #666; font-style: italic; }}
            </style>
            {css or ''}
        </head>
        <body>
            <h1>{title}</h1>
            <p class="empty-message">No data available</p>
        </body>
        </html>
        """
    
    # Get all fields from data
    fields = set()
    for item in data:
        fields.update(item.keys())
    fields = sorted(fields)
    
    # Generate HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{title}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #333; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
        </style>
        {css or ''}
    </head>
    <body>
        <h1>{title}</h1>
        <table>
            <thead>
                <tr>
    """
    
    # Add table headers
    for field in fields:
        html += f"<th>{field}</th>"
    
    html += """
                </tr>
            </thead>
            <tbody>
    """
    
    # Add table rows
    for item in data:
        html += "<tr>"
        for field in fields:
            value = item.get(field, "")
            
            # Format value for display
            if value is None:
                display_value = ""
            elif isinstance(value, (dict, list)):
                display_value = json.dumps(value)
            elif isinstance(value, datetime):
                display_value = value.isoformat()
            elif isinstance(value, bool):
                display_value = "Yes" if value else "No"
            else:
                display_value = str(value)
            
            html += f"<td>{display_value}</td>"
        html += "</tr>"
    
    html += """
            </tbody>
        </table>
    </body>
    </html>
    """
    
    return html
