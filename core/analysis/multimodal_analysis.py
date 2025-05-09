"""
Multi-Modal Analysis Module for Wiseflow.

This module provides functionality for analyzing images and integrating visual information
with textual data to create a more comprehensive understanding of content.
"""

import os
import json
import asyncio
import base64
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Union
import re
import io
import uuid
import logging
import socket
from urllib.parse import urlparse
import requests
from PIL import Image
import ipaddress

from ..utils.general_utils import get_logger
from ..utils.pb_api import PbTalker
from ..llms.openai_wrapper import openai_llm as llm

# Set up logging
project_dir = os.environ.get("PROJECT_DIR", "")
if project_dir:
    os.makedirs(project_dir, exist_ok=True)
multimodal_logger = get_logger('multimodal_analysis', project_dir)
pb = PbTalker(multimodal_logger)

# Get the model from environment variables
vl_model = os.environ.get("VL_MODEL", "")
if not vl_model:
    multimodal_logger.warning("VL_MODEL not set, using PRIMARY_MODEL as fallback")
    vl_model = os.environ.get("PRIMARY_MODEL", "")
    if not vl_model:
        raise ValueError("Neither VL_MODEL nor PRIMARY_MODEL is set, please set one in environment variables or edit core/.env")

# Constants for image validation
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_IMAGE_FORMATS = ['JPEG', 'JPG', 'PNG', 'GIF', 'WEBP']
MAX_IMAGE_DIMENSION = 4096  # Maximum width or height in pixels
REQUEST_TIMEOUT = 10  # Timeout for HTTP requests in seconds
ALLOWED_URL_SCHEMES = ['http', 'https']
# Add trusted domains if needed
TRUSTED_DOMAINS = []  # e.g., ['example.com', 'trusted-cdn.net']
# Maximum number of redirects to follow
MAX_REDIRECTS = 5
# Cache for DNS resolution results to prevent DNS rebinding attacks
DNS_CACHE = {}
# Cache for validated images to improve performance
IMAGE_VALIDATION_CACHE = {}
# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

# Prompt for image analysis
IMAGE_ANALYSIS_PROMPT = """You are an expert in visual content analysis. Your task is to analyze the provided image and extract meaningful information from it.

Please provide the following:
1. A detailed description of the image content
2. Key entities visible in the image (people, objects, locations, etc.)
3. Any text visible in the image
4. The overall context or setting of the image
5. Any notable visual elements or patterns
6. Emotional tone or sentiment conveyed by the image

Focus on extracting factual information that would be valuable for knowledge extraction and integration with textual data.
"""

# Prompt for multimodal integration
MULTIMODAL_INTEGRATION_PROMPT = """You are an expert in multimodal information integration. Your task is to analyze both textual content and image analysis results to create a comprehensive understanding.

Text content:
{text_content}

Image analysis:
{image_analysis}

Please provide:
1. An integrated summary that combines insights from both text and images
2. Key entities identified across both modalities
3. Any additional context gained from the combination of text and images
4. Any discrepancies or contradictions between the text and image content
5. Overall confidence in the integrated information (high, medium, low)

Format your response as a JSON object with the following structure:
{
  "integrated_summary": "Comprehensive summary integrating text and image insights",
  "key_entities": [
    {"name": "Entity name", "type": "Entity type", "confidence": 0.95, "source": "text/image/both"},
    ...
  ],
  "additional_context": "Any additional context gained from multimodal analysis",
  "discrepancies": "Any contradictions between text and image content",
  "confidence": "high/medium/low",
  "reasoning": "Explanation of your confidence assessment"
}
"""

def is_private_ip(ip_str: str) -> bool:
    """
    Check if an IP address (IPv4 or IPv6) is private.
    
    Args:
        ip_str: IP address as string
        
    Returns:
        Boolean indicating if the IP is private
    """
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private or
            ip.is_loopback or
            ip.is_link_local or
            ip.is_multicast or
            ip.is_reserved or
            ip.is_unspecified
        )
    except ValueError:
        return False

def validate_image_url(url: str) -> bool:
    """
    Validate if a URL is safe to download images from.
    
    Args:
        url: URL to validate
        
    Returns:
        Boolean indicating if the URL is safe
    """
    try:
        parsed_url = urlparse(url)
        
        # Check URL scheme
        if parsed_url.scheme not in ALLOWED_URL_SCHEMES:
            multimodal_logger.warning(f"Invalid URL scheme: {parsed_url.scheme}")
            return False
        
        # Check if domain is trusted (if TRUSTED_DOMAINS is not empty)
        if TRUSTED_DOMAINS and parsed_url.netloc not in TRUSTED_DOMAINS:
            multimodal_logger.warning(f"Domain not in trusted list: {parsed_url.netloc}")
            return False
        
        # Get hostname
        hostname = parsed_url.hostname
        if not hostname:
            multimodal_logger.warning("URL has no hostname")
            return False
            
        # Check for localhost or private IPs (both IPv4 and IPv6)
        # First check if it's already an IP address
        if is_private_ip(hostname):
            multimodal_logger.warning(f"URL points to private IP address: {hostname}")
            return False
            
        # DNS rebinding protection: resolve hostname and check if it's private
        if hostname in DNS_CACHE:
            resolved_ips = DNS_CACHE[hostname]
        else:
            try:
                # Resolve both IPv4 and IPv6 addresses
                resolved_ips = []
                for res_type in (socket.AF_INET, socket.AF_INET6):
                    try:
                        addrinfo = socket.getaddrinfo(hostname, None, res_type)
                        for family, _, _, _, sockaddr in addrinfo:
                            ip = sockaddr[0]
                            resolved_ips.append(ip)
                    except socket.gaierror:
                        # No addresses of this type
                        pass
                
                # Cache the results
                DNS_CACHE[hostname] = resolved_ips
            except Exception as e:
                multimodal_logger.error(f"Error resolving hostname {hostname}: {e}")
                return False
        
        # Check if any resolved IP is private
        for ip in resolved_ips:
            if is_private_ip(ip):
                multimodal_logger.warning(f"URL {url} resolves to private IP {ip}")
                return False
        
        return True
    except Exception as e:
        multimodal_logger.error(f"Error validating URL: {e}")
        return False

def validate_image_data(image_data: bytes) -> Tuple[bool, str, Optional[Image.Image]]:
    """
    Validate image data for size, format, and dimensions.
    
    Args:
        image_data: Image data as bytes
        
    Returns:
        Tuple of (is_valid, error_message, PIL_image_if_valid)
    """
    try:
        # Check file size
        if len(image_data) > MAX_IMAGE_SIZE_BYTES:
            return False, f"Image exceeds maximum size of {MAX_IMAGE_SIZE_BYTES/1024/1024:.1f} MB", None
        
        # Check image format and dimensions
        img = Image.open(io.BytesIO(image_data))
        
        # Check format
        if img.format not in ALLOWED_IMAGE_FORMATS:
            return False, f"Image format {img.format} not allowed. Allowed formats: {', '.join(ALLOWED_IMAGE_FORMATS)}", None
        
        # Check dimensions
        width, height = img.size
        if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
            return False, f"Image dimensions ({width}x{height}) exceed maximum allowed ({MAX_IMAGE_DIMENSION}x{MAX_IMAGE_DIMENSION})", None
        
        return True, "", img
    except Exception as e:
        return False, f"Invalid image data: {str(e)}", None

async def analyze_image(image_data: Union[str, bytes], image_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Analyze an image using vision-language model.
    
    Args:
        image_data: Image data as base64 string or bytes
        image_url: Optional URL of the image for reference
        
    Returns:
        Dictionary containing image analysis results
    """
    multimodal_logger.info(f"Analyzing image{' from ' + image_url if image_url else ''}")
    
    try:
        # Prepare image data
        if isinstance(image_data, str):
            if image_data.startswith(('http://', 'https://')):
                # It's a URL, validate and download the image
                if not validate_image_url(image_data):
                    return {
                        "error": f"Invalid or unsafe image URL: {image_data}",
                        "timestamp": datetime.now().isoformat()
                    }
                
                response = requests.get(image_data, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                image_bytes = response.content
                
                # Validate the downloaded image
                is_valid, error_msg, _ = validate_image_data(image_bytes)
                if not is_valid:
                    return {
                        "error": f"Invalid image data: {error_msg}",
                        "timestamp": datetime.now().isoformat()
                    }
                
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            elif image_data.startswith('data:image'):
                # It's a data URL
                try:
                    image_base64 = image_data.split(',')[1]
                    # Decode and validate the image
                    image_bytes = base64.b64decode(image_base64)
                    is_valid, error_msg, _ = validate_image_data(image_bytes)
                    if not is_valid:
                        return {
                            "error": f"Invalid image data: {error_msg}",
                            "timestamp": datetime.now().isoformat()
                        }
                except Exception as e:
                    return {
                        "error": f"Invalid data URL: {str(e)}",
                        "timestamp": datetime.now().isoformat()
                    }
            else:
                # Assume it's already base64 encoded
                try:
                    image_base64 = image_data
                    # Decode and validate the image
                    image_bytes = base64.b64decode(image_base64)
                    is_valid, error_msg, _ = validate_image_data(image_bytes)
                    if not is_valid:
                        return {
                            "error": f"Invalid image data: {error_msg}",
                            "timestamp": datetime.now().isoformat()
                        }
                except Exception as e:
                    return {
                        "error": f"Invalid base64 data: {str(e)}",
                        "timestamp": datetime.now().isoformat()
                    }
        else:
            # It's bytes, validate the image
            is_valid, error_msg, _ = validate_image_data(image_data)
            if not is_valid:
                return {
                    "error": f"Invalid image data: {error_msg}",
                    "timestamp": datetime.now().isoformat()
                }
            # It's bytes
            image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Call the vision-language model
        messages = [
            {"role": "system", "content": "You are an expert in visual content analysis."},
            {"role": "user", "content": [
                {"type": "text", "text": IMAGE_ANALYSIS_PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
            ]}
        ]
        
        response = await llm(messages, model=vl_model, temperature=0.2)
        
        # Process the response
        analysis = {
            "description": response,
            "timestamp": datetime.now().isoformat(),
            "source_url": image_url,
            "analysis_model": vl_model
        }
        
        # Extract entities from the response
        entities = extract_entities_from_analysis(response)
        if entities:
            analysis["entities"] = entities
        
        # Extract text from the response
        text_content = extract_text_from_analysis(response)
        if text_content:
            analysis["extracted_text"] = text_content
        
        multimodal_logger.info("Image analysis completed successfully")
        return analysis
    
    except Exception as e:
        multimodal_logger.error(f"Error analyzing image: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

async def download_image(url: str) -> Optional[bytes]:
    """
    Download an image from a URL.
    
    Args:
        url: URL of the image
        
    Returns:
        Image data as bytes or None if download failed
    """
    # Check if URL is in validation cache
    cache_key = f"url_{url}"
    if cache_key in IMAGE_VALIDATION_CACHE:
        if not IMAGE_VALIDATION_CACHE[cache_key]:
            multimodal_logger.warning(f"Skipping previously invalid URL: {url}")
            return None
    
    # Validate URL before downloading
    if not validate_image_url(url):
        multimodal_logger.warning(f"Skipping download from invalid or unsafe URL: {url}")
        IMAGE_VALIDATION_CACHE[cache_key] = False
        return None
    
    # Cache the validation result
    IMAGE_VALIDATION_CACHE[cache_key] = True
    
    # Implement retry logic
    for attempt in range(MAX_RETRIES):
        try:
            # Use a session to handle redirects safely
            session = requests.Session()
            session.max_redirects = MAX_REDIRECTS
            
            response = session.get(
                url, 
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            )
            response.raise_for_status()
            
            # Verify content type is an image
            content_type = response.headers.get('Content-Type', '')
            if not content_type.startswith('image/'):
                multimodal_logger.warning(f"URL {url} returned non-image content type: {content_type}")
                return None
            
            image_data = response.content
            
            # Validate the downloaded image
            is_valid, error_msg, _ = validate_image_data(image_data)
            if not is_valid:
                multimodal_logger.warning(f"Invalid image data from {url}: {error_msg}")
                return None
                
            return image_data
            
        except requests.exceptions.Timeout:
            multimodal_logger.warning(f"Timeout downloading image from {url} (attempt {attempt+1}/{MAX_RETRIES})")
        except requests.exceptions.TooManyRedirects:
            multimodal_logger.warning(f"Too many redirects for {url}")
            return None  # Don't retry on redirect issues
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if hasattr(e, 'response') else 'unknown'
            multimodal_logger.warning(f"HTTP error {status_code} downloading from {url} (attempt {attempt+1}/{MAX_RETRIES})")
        except Exception as e:
            multimodal_logger.error(f"Error downloading image from {url} (attempt {attempt+1}/{MAX_RETRIES}): {e}")
        
        # Wait before retrying, with exponential backoff
        if attempt < MAX_RETRIES - 1:
            retry_time = RETRY_DELAY * (2 ** attempt)  # Exponential backoff
            await asyncio.sleep(retry_time)
    
    # All retries failed
    multimodal_logger.error(f"Failed to download image from {url} after {MAX_RETRIES} attempts")
    return None

def extract_entities_from_analysis(analysis_text: str) -> List[Dict[str, Any]]:
    """
    Extract entities from image analysis text.
    
    Args:
        analysis_text: Text from image analysis
        
    Returns:
        List of extracted entities
    """
    entities = []
    
    # Look for entity patterns in the text
    # People
    people_matches = re.findall(r'(?:person|man|woman|individual|people|group|crowd|audience|speaker|presenter|figure)(?:\s+named\s+|\s+identified as\s+|\s+)([A-Z][a-zA-Z\s\-\'\.]+)', analysis_text)
    for match in people_matches:
        entities.append({
            "name": match.strip(),
            "type": "person",
            "confidence": 0.8,
            "source": "image"
        })
    
    # Organizations
    org_matches = re.findall(r'(?:company|organization|corporation|institution|agency|brand|logo)(?:\s+of\s+|\s+from\s+|\s+named\s+|\s+)([A-Z][a-zA-Z0-9\s\-\'\.]+)', analysis_text)
    for match in org_matches:
        entities.append({
            "name": match.strip(),
            "type": "organization",
            "confidence": 0.7,
            "source": "image"
        })
    
    # Locations
    loc_matches = re.findall(r'(?:location|place|city|country|region|area|building|landmark)(?:\s+of\s+|\s+in\s+|\s+at\s+|\s+)([A-Z][a-zA-Z\s\-\'\.]+)', analysis_text)
    for match in loc_matches:
        entities.append({
            "name": match.strip(),
            "type": "location",
            "confidence": 0.7,
            "source": "image"
        })
    
    # Products
    product_matches = re.findall(r'(?:product|device|gadget|item|object)(?:\s+labeled\s+|\s+named\s+|\s+called\s+|\s+)([A-Z][a-zA-Z0-9\s\-\'\.]+)', analysis_text)
    for match in product_matches:
        entities.append({
            "name": match.strip(),
            "type": "product",
            "confidence": 0.6,
            "source": "image"
        })
    
    return entities

def extract_text_from_analysis(analysis_text: str) -> str:
    """
    Extract text content mentioned in the image analysis.
    
    Args:
        analysis_text: Text from image analysis
        
    Returns:
        Extracted text content
    """
    # Look for patterns indicating text in the image
    text_patterns = [
        r'text(?:\s+in the image|\s+visible|\s+shown|\s+displayed|\s+reads):?\s+"([^"]+)"',
        r'text(?:\s+in the image|\s+visible|\s+shown|\s+displayed|\s+reads):?\s+\'([^\']+)\'',
        r'text(?:\s+in the image|\s+visible|\s+shown|\s+displayed|\s+reads):?\s+([^\.]+)\.',
        r'(?:sign|banner|label|caption|heading|title)(?:\s+reads|\s+says|\s+displays|\s+shows):?\s+"([^"]+)"',
        r'(?:sign|banner|label|caption|heading|title)(?:\s+reads|\s+says|\s+displays|\s+shows):?\s+\'([^\']+)\'',
        r'(?:sign|banner|label|caption|heading|title)(?:\s+reads|\s+says|\s+displays|\s+shows):?\s+([^\.]+)\.'
    ]
    
    extracted_text = []
    for pattern in text_patterns:
        matches = re.findall(pattern, analysis_text, re.IGNORECASE)
        extracted_text.extend([match.strip() for match in matches if match.strip()])
    
    return "\n".join(extracted_text)

async def integrate_text_and_image(text_content: str, image_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Integrate text content with image analysis.
    
    Args:
        text_content: Text content
        image_analysis: Image analysis results
        
    Returns:
        Dictionary containing integrated analysis
    """
    multimodal_logger.info("Integrating text and image analysis")
    
    try:
        # Format the prompt with text content and image analysis
        image_analysis_text = image_analysis.get("description", "")
        prompt = MULTIMODAL_INTEGRATION_PROMPT.format(
            text_content=text_content,
            image_analysis=image_analysis_text
        )
        
        # Call the LLM for integration
        response = await llm([
            {'role': 'system', 'content': 'You are an expert in multimodal information integration.'},
            {'role': 'user', 'content': prompt}
        ], model=vl_model, temperature=0.3)
        
        # Parse the JSON response
        try:
            # Find JSON object in the response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                integrated_analysis = json.loads(json_str)
                multimodal_logger.debug("Multimodal integration completed successfully")
            else:
                multimodal_logger.warning("No valid JSON found in multimodal integration response")
                integrated_analysis = {
                    "integrated_summary": response,
                    "confidence": "medium",
                    "reasoning": "Response format was not as expected"
                }
        except Exception as e:
            multimodal_logger.error(f"Error parsing multimodal integration response: {e}")
            integrated_analysis = {
                "integrated_summary": response,
                "error": f"Error parsing response: {str(e)}",
                "confidence": "low",
                "reasoning": "Failed to parse structured response"
            }
        
        # Add metadata
        integrated_analysis["timestamp"] = datetime.now().isoformat()
        integrated_analysis["integration_model"] = vl_model
        
        return integrated_analysis
    
    except Exception as e:
        multimodal_logger.error(f"Error integrating text and image: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

async def process_item_with_images(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process an item that contains both text and images.
    
    Args:
        item: Dictionary containing item data with text and image URLs
        
    Returns:
        Dictionary containing processed item with multimodal analysis
    """
    item_id = item.get('id', 'unknown')
    multimodal_logger.info(f"Processing item with ID: {item_id}")
    
    # Create a copy of the item to avoid modifying the original
    updated_item = item.copy()
    
    # Extract text content
    text_content = item.get("content", "")
    if not text_content:
        multimodal_logger.warning(f"Item {item_id} has no text content")
        updated_item["multimodal_analysis"] = {
            "error": "No text content available for analysis",
            "timestamp": datetime.now().isoformat()
        }
        return updated_item
    
    # Extract image URLs
    image_urls = []
    
    # Check for image URLs in the item
    if "images" in item and isinstance(item["images"], list):
        image_urls.extend(item["images"])
    
    # Check for image URLs in the content
    if text_content:
        # Look for markdown image syntax
        md_images = re.findall(r'!\[.*?\]\((.*?)\)', text_content)
        image_urls.extend(md_images)
        
        # Look for HTML image tags
        html_images = re.findall(r'<img[^>]+src="([^"]+)"', text_content)
        image_urls.extend(html_images)
    
    if not image_urls:
        multimodal_logger.info(f"No images found in item {item_id}")
        updated_item["multimodal_analysis"] = {
            "status": "no_images",
            "message": "No images found in the item",
            "timestamp": datetime.now().isoformat()
        }
        return updated_item
    
    # Process each image with proper error handling
    image_analyses = []
    failed_urls = []
    
    for url in image_urls:
        try:
            # Download and analyze the image
            multimodal_logger.debug(f"Downloading image from URL: {url}")
            image_data = await download_image(url)
            
            if image_data:
                multimodal_logger.debug(f"Analyzing image from URL: {url}")
                analysis = await analyze_image(image_data, url)
                
                # Check if analysis contains an error
                if "error" in analysis:
                    multimodal_logger.warning(f"Error analyzing image from {url}: {analysis['error']}")
                    failed_urls.append({"url": url, "error": analysis["error"]})
                else:
                    image_analyses.append(analysis)
            else:
                multimodal_logger.warning(f"Failed to download image from {url}")
                failed_urls.append({"url": url, "error": "Failed to download image"})
        except Exception as e:
            multimodal_logger.error(f"Exception processing image from {url}: {e}")
            failed_urls.append({"url": url, "error": str(e)})
    
    if not image_analyses:
        multimodal_logger.warning(f"Failed to analyze any images for item {item_id}")
        updated_item["multimodal_analysis"] = {
            "status": "analysis_failed",
            "message": "Failed to analyze any images",
            "failed_urls": failed_urls,
            "timestamp": datetime.now().isoformat()
        }
        return updated_item
    
    # Integrate text and image analyses
    integrated_analyses = []
    for analysis in image_analyses:
        try:
            integrated = await integrate_text_and_image(text_content, analysis)
            integrated_analyses.append(integrated)
        except Exception as e:
            multimodal_logger.error(f"Error integrating text and image analysis: {e}")
            # Continue with other analyses
    
    if not integrated_analyses:
        multimodal_logger.warning(f"Failed to integrate any text and image analyses for item {item_id}")
        updated_item["multimodal_analysis"] = {
            "status": "integration_failed",
            "message": "Failed to integrate text and image analyses",
            "image_analyses": image_analyses,  # Include the successful image analyses
            "failed_urls": failed_urls,
            "timestamp": datetime.now().isoformat()
        }
        return updated_item
    
    # Combine all integrated analyses
    combined_analysis = combine_integrated_analyses(integrated_analyses)
    
    # Add metadata about processing
    combined_analysis["processed_images_count"] = len(image_analyses)
    combined_analysis["total_images_count"] = len(image_urls)
    if failed_urls:
        combined_analysis["failed_urls"] = failed_urls
    
    # Update the item with multimodal analysis
    updated_item["multimodal_analysis"] = combined_analysis
    
    # Extract additional entities from multimodal analysis
    if "key_entities" in combined_analysis:
        try:
            entity_links = updated_item.get("entity_links", [])
            if isinstance(entity_links, str):
                try:
                    entity_links = json.loads(entity_links)
                except json.JSONDecodeError:
                    multimodal_logger.warning(f"Invalid JSON in entity_links for item {item_id}")
                    entity_links = []
            
            # Add new entities from multimodal analysis
            for entity in combined_analysis["key_entities"]:
                if entity.get("source") in ["image", "both"]:
                    entity_links.append({
                        "entity_id": str(uuid.uuid4()),
                        "entity_name": entity["name"],
                        "entity_type": entity["type"],
                        "confidence": entity["confidence"],
                        "source": "multimodal_analysis"
                    })
            
            updated_item["entity_links"] = json.dumps(entity_links)
        except Exception as e:
            multimodal_logger.error(f"Error processing entities for item {item_id}: {e}")
    
    # Save the updated item to the database with retry logic
    try:
        for attempt in range(MAX_RETRIES):
            try:
                pb.update("infos", item["id"], {
                    "multimodal_analysis": json.dumps(combined_analysis),
                    "entity_links": updated_item["entity_links"] if "entity_links" in updated_item else None
                })
                multimodal_logger.info(f"Updated item {item_id} with multimodal analysis")
                break
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    retry_time = RETRY_DELAY * (2 ** attempt)
                    multimodal_logger.warning(f"Database update failed (attempt {attempt+1}/{MAX_RETRIES}), retrying in {retry_time}s: {e}")
                    await asyncio.sleep(retry_time)
                else:
                    raise
    except Exception as e:
        multimodal_logger.error(f"Error updating item {item_id} in database after {MAX_RETRIES} attempts: {e}")
        # Still return the updated item even if saving to DB failed
    
    return updated_item

def combine_integrated_analyses(analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Combine multiple integrated analyses into a single comprehensive analysis.
    
    Args:
        analyses: List of integrated analyses
        
    Returns:
        Combined analysis
    """
    if not analyses:
        return {}
    
    if len(analyses) == 1:
        return analyses[0]
    
    # Combine summaries
    summaries = [a.get("integrated_summary", "") for a in analyses if "integrated_summary" in a]
    combined_summary = "\n\n".join(summaries)
    
    # Combine entities
    all_entities = []
    for analysis in analyses:
        entities = analysis.get("key_entities", [])
        if entities:
            all_entities.extend(entities)
    
    # Deduplicate entities
    unique_entities = {}
    for entity in all_entities:
        key = f"{entity['name']}|{entity['type']}"
        if key not in unique_entities or entity.get("confidence", 0) > unique_entities[key].get("confidence", 0):
            unique_entities[key] = entity
    
    # Determine overall confidence
    confidence_levels = [a.get("confidence", "low") for a in analyses]
    if "low" in confidence_levels:
        overall_confidence = "low"
    elif "medium" in confidence_levels:
        overall_confidence = "medium"
    else:
        overall_confidence = "high"
    
    # Combine additional context
    context_parts = [a.get("additional_context", "") for a in analyses if "additional_context" in a]
    combined_context = "\n\n".join(context_parts)
    
    # Combine discrepancies
    discrepancy_parts = [a.get("discrepancies", "") for a in analyses if "discrepancies" in a]
    combined_discrepancies = "\n\n".join(discrepancy_parts)
    
    return {
        "integrated_summary": combined_summary,
        "key_entities": list(unique_entities.values()),
        "additional_context": combined_context,
        "discrepancies": combined_discrepancies,
        "confidence": overall_confidence,
        "reasoning": "Combined analysis from multiple images",
        "timestamp": datetime.now().isoformat(),
        "source_count": len(analyses)
    }

async def process_focus_for_multimodal_analysis(focus_id: str) -> Dict[str, Any]:
    """
    Process all items for a focus point to perform multimodal analysis.
    
    Args:
        focus_id: ID of the focus point
        
    Returns:
        Dictionary with processing results
    """
    multimodal_logger.info(f"Processing focus point {focus_id} for multimodal analysis")
    
    # Get all info items for this focus point
    info_items = pb.read(collection_name='infos', filter=f"tag='{focus_id}'")
    
    if not info_items:
        multimodal_logger.warning(f"No information items found for focus ID {focus_id}")
        return {"error": f"No information items found for focus ID {focus_id}"}
    
    # Process each item
    processed_count = 0
    image_count = 0
    
    for item in info_items:
        # Skip items that already have multimodal analysis
        if item.get("multimodal_analysis"):
            continue
        
        # Process the item
        updated_item = await process_item_with_images(item)
        
        if "multimodal_analysis" in updated_item:
            processed_count += 1
            image_count += len(updated_item.get("multimodal_analysis", {}).get("source_count", 0))
    
    # Generate a summary of the processing
    result = {
        "focus_id": focus_id,
        "processed_items": processed_count,
        "total_items": len(info_items),
        "image_count": image_count,
        "timestamp": datetime.now().isoformat()
    }
    
    multimodal_logger.info(f"Completed multimodal analysis for focus {focus_id}: {processed_count}/{len(info_items)} items processed")
    return result
