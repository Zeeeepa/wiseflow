"""
PDF Export Module for Wiseflow.

This module provides specialized functionality for exporting data to PDF format.
"""

import logging
from typing import Dict, List, Any, Optional
import os
import tempfile
import json

logger = logging.getLogger(__name__)

def export_to_pdf(data: List[Dict[str, Any]], filepath: str) -> None:
    """
    Export data to PDF.
    
    Args:
        data: Data to export
        filepath: Path to save the PDF file
    """
    try:
        # Import here to avoid dependency issues
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib import colors
            from reportlab.lib.units import inch
        except ImportError:
            logger.error("PDF export requires reportlab. Install with: pip install reportlab")
            raise ImportError("PDF export requires reportlab")
        
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        elements = []
        
        # Add title
        styles = getSampleStyleSheet()
        title_style = styles['Title']
        normal_style = styles['Normal']
        heading_style = styles['Heading2']
        
        # Add document title
        elements.append(Paragraph("Data Export", title_style))
        elements.append(Spacer(1, 0.25 * inch))
        
        if not data:
            elements.append(Paragraph("No data to export", normal_style))
        else:
            # Get all possible fields from all records
            fieldnames = set()
            for item in data:
                fieldnames.update(item.keys())
            fieldnames = sorted(fieldnames)
            
            # Prepare table data
            table_data = [fieldnames]  # Header row
            
            for item in data:
                row = [str(item.get(field, "")) for field in fieldnames]
                table_data.append(row)
            
            # Create table
            table = Table(table_data)
            
            # Style the table
            style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ])
            
            table.setStyle(style)
            elements.append(table)
        
        # Build PDF
        doc.build(elements)
        
        logger.info(f"Exported {len(data)} records to PDF: {filepath}")
    except ImportError:
        # Already logged
        raise
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
        config: Configuration options (title, page_size, etc.)
    """
    try:
        # Import here to avoid dependency issues
        try:
            from reportlab.lib.pagesizes import letter, A4, legal
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors
            from reportlab.lib.units import inch
        except ImportError:
            logger.error("PDF export requires reportlab. Install with: pip install reportlab")
            raise ImportError("PDF export requires reportlab")
        
        # Get PDF options
        title = config.get('title', 'Data Export')
        subtitle = config.get('subtitle', '')
        page_size_name = config.get('page_size', 'letter')
        fields_to_include = config.get('fields', None)
        
        # Determine page size
        page_sizes = {
            'letter': letter,
            'a4': A4,
            'legal': legal
        }
        page_size = page_sizes.get(page_size_name.lower(), letter)
        
        # Create document
        doc = SimpleDocTemplate(
            filepath, 
            pagesize=page_size,
            title=title,
            author=config.get('author', 'Wiseflow Export Module')
        )
        elements = []
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = styles['Title']
        normal_style = styles['Normal']
        heading_style = styles['Heading2']
        
        # Add custom styles if specified
        if 'styles' in config:
            for style_name, style_props in config['styles'].items():
                if style_name in styles:
                    # Modify existing style
                    for prop, value in style_props.items():
                        setattr(styles[style_name], prop, value)
        
        # Add logo if specified
        if 'logo' in config and os.path.exists(config['logo']):
            logo = Image(config['logo'])
            logo.drawHeight = 0.5 * inch
            logo.drawWidth = 0.5 * inch
            elements.append(logo)
            elements.append(Spacer(1, 0.25 * inch))
        
        # Add title
        elements.append(Paragraph(title, title_style))
        
        # Add subtitle if specified
        if subtitle:
            elements.append(Spacer(1, 0.1 * inch))
            elements.append(Paragraph(subtitle, styles['Italic']))
        
        elements.append(Spacer(1, 0.25 * inch))
        
        if not data:
            elements.append(Paragraph("No data to export", normal_style))
        else:
            # Get fields to include
            if fields_to_include:
                fieldnames = fields_to_include
            else:
                # Get all possible fields from all records
                fieldnames = set()
                for item in data:
                    fieldnames.update(item.keys())
                fieldnames = sorted(fieldnames)
            
            # Add section headers if specified
            if 'sections' in config:
                for section in config['sections']:
                    section_title = section.get('title', '')
                    section_fields = section.get('fields', [])
                    
                    if section_title:
                        elements.append(Spacer(1, 0.2 * inch))
                        elements.append(Paragraph(section_title, heading_style))
                        elements.append(Spacer(1, 0.1 * inch))
                    
                    # Filter data for this section
                    section_data = []
                    for item in data:
                        section_item = {field: item.get(field, '') for field in section_fields if field in item}
                        if section_item:
                            section_data.append(section_item)
                    
                    if section_data:
                        # Prepare table data
                        table_data = [section_fields]  # Header row
                        
                        for item in section_data:
                            row = [str(item.get(field, '')) for field in section_fields]
                            table_data.append(row)
                        
                        # Create table
                        table = Table(table_data)
                        
                        # Style the table
                        style = TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black)
                        ])
                        
                        table.setStyle(style)
                        elements.append(table)
            else:
                # No sections, just create one table with all data
                # Prepare table data
                table_data = [fieldnames]  # Header row
                
                for item in data:
                    row = [str(item.get(field, '')) for field in fieldnames]
                    table_data.append(row)
                
                # Create table
                table = Table(table_data)
                
                # Style the table
                style = TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ])
                
                table.setStyle(style)
                elements.append(table)
        
        # Add footer if specified
        if 'footer' in config:
            elements.append(Spacer(1, 0.5 * inch))
            elements.append(Paragraph(config['footer'], styles['Italic']))
        
        # Build PDF
        doc.build(elements)
        
        logger.info(f"Exported {len(data)} records to PDF with custom config: {filepath}")
    except ImportError:
        # Already logged
        raise
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
        # Try to import weasyprint
        try:
            import weasyprint
        except ImportError:
            logger.error("HTML to PDF conversion requires weasyprint. Install with: pip install weasyprint")
            raise ImportError("HTML to PDF conversion requires weasyprint")
        
        # Create a temporary HTML file
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as temp:
            temp_path = temp.name
            temp.write(html_content.encode('utf-8'))
        
        try:
            # Convert HTML to PDF
            weasyprint.HTML(filename=temp_path).write_pdf(filepath)
            logger.info(f"Converted HTML to PDF: {filepath}")
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    except ImportError:
        # Already logged
        raise
    except Exception as e:
        logger.error(f"HTML to PDF conversion failed: {str(e)}")
        raise
