"""
Utility functions for content scraping.

This module provides utility functions for content scraping, including
parsing srcset, dimensions, and fetching image file sizes.
"""

import re
import logging
import requests
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urljoin
from requests.exceptions import InvalidSchema, RequestException, Timeout

from .errors import NetworkError

logger = logging.getLogger(__name__)

# Pre-compile regular expressions for better performance
DIMENSION_REGEX = re.compile(r"(\d+)(\D*)")
BASE64_PATTERN = re.compile(r"^data:image/[^;]+;base64,")

def parse_srcset(s: str) -> List[Dict]:
    """
    Parse srcset attribute to extract image URLs and widths.
    
    Args:
        s: The srcset attribute value.
        
    Returns:
        A list of dictionaries with URL and width information.
    """
    if not s:
        return []
        
    variants = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
            
        parts = part.split()
        if len(parts) >= 1:
            url = parts[0]
            width = (
                parts[1].rstrip("w")
                if len(parts) > 1 and parts[1].endswith("w")
                else None
            )
            variants.append({"url": url, "width": width})
            
    return variants


def parse_dimension(dimension) -> Tuple[Optional[int], Optional[str]]:
    """
    Parse image height/width value and units.
    
    Args:
        dimension: The dimension value to parse.
        
    Returns:
        A tuple of (number, unit) or (None, None) if parsing fails.
    """
    if dimension:
        match = DIMENSION_REGEX.match(str(dimension))
        if match:
            number = int(match.group(1))
            unit = match.group(2) or "px"  # Default unit is 'px' if not specified
            return number, unit
            
    return None, None


def fetch_image_file_size(img_url: str, base_url: str, timeout: int = 5) -> Optional[int]:
    """
    Fetch image file metadata to extract size.
    
    Args:
        img_url: The image URL.
        base_url: The base URL for resolving relative URLs.
        timeout: Timeout for the request in seconds.
        
    Returns:
        The file size in bytes, or None if the request fails.
        
    Raises:
        NetworkError: If there's a network error fetching the image.
    """
    # If src is relative path construct full URL, if not it may be CDN URL
    try:
        full_url = urljoin(base_url, img_url)
        
        response = requests.head(full_url, timeout=timeout)
        if response.status_code == 200:
            return int(response.headers.get("Content-Length", 0) or 0)
        else:
            logger.warning(f"Failed to retrieve file size for {full_url}: HTTP {response.status_code}")
            return None
    except Timeout:
        logger.warning(f"Timeout retrieving file size for {img_url}")
        return None
    except (InvalidSchema, RequestException) as e:
        logger.warning(f"Error retrieving file size for {img_url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error retrieving file size for {img_url}: {e}")
        return None


def score_image(img: Any, **kwargs) -> float:
    """
    Score an image based on various attributes to determine its importance.
    
    Args:
        img: The image element to score.
        **kwargs: Additional parameters for scoring.
        
    Returns:
        A score between 0 and 1, where higher values indicate more important images.
    """
    score = 0.0
    
    # Get image attributes
    alt = img.get("alt", "")
    width = img.get("width")
    height = img.get("height")
    src = img.get("src", "")
    
    # Score based on alt text (most important)
    if alt:
        alt_words = len(alt.split())
        if alt_words > 5:
            score += 0.4
        elif alt_words > 2:
            score += 0.3
        elif alt_words > 0:
            score += 0.2
    
    # Score based on dimensions
    if width and height:
        try:
            w = int(width)
            h = int(height)
            area = w * h
            
            # Larger images are more likely to be content
            if area > 100000:  # e.g., 316x316 or larger
                score += 0.3
            elif area > 40000:  # e.g., 200x200 or larger
                score += 0.2
            elif area > 10000:  # e.g., 100x100 or larger
                score += 0.1
                
            # Penalize very small images (likely icons)
            if area < 1000:  # e.g., 32x32 or smaller
                score -= 0.2
        except (ValueError, TypeError):
            pass
    
    # Penalize common icon/button patterns
    if any(pattern in (src or "").lower() for pattern in ["icon", "logo", "button"]):
        score -= 0.2
        
    if any(pattern in (alt or "").lower() for pattern in ["icon", "logo", "button"]):
        score -= 0.1
    
    # Ensure score is between 0 and 1
    return max(0.0, min(1.0, score))

