"""
URL validation and processing utilities for crawl4ai.

This module provides utilities for validating and processing URLs,
including normalization, validation, and extraction of components.
"""

import re
import logging
from typing import Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urlparse, urljoin, urlunparse, parse_qs, urlencode

from .errors import ValidationError

logger = logging.getLogger(__name__)

# Regular expression for URL validation
# This regex is more comprehensive than simple checks and handles various URL formats
URL_REGEX = re.compile(
    r'^(?:(?:https?|ftp):\/\/)?'  # scheme
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain
    r'localhost|'  # localhost
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
    r'(?::\d+)?'  # port
    r'(?:\/\S*)?$',  # path
    re.IGNORECASE
)

# Common file extensions to skip
COMMON_FILE_EXTENSIONS = {
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.zip', '.rar', '.tar', '.gz', '.7z',
    '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.flv',
    '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp',
    '.exe', '.dll', '.bin', '.iso',
}

# Common social media domains
SOCIAL_MEDIA_DOMAINS = {
    'facebook.com', 'twitter.com', 'instagram.com', 'linkedin.com',
    'youtube.com', 'pinterest.com', 'reddit.com', 'tumblr.com',
    'tiktok.com', 'snapchat.com', 'whatsapp.com', 'telegram.org',
    'medium.com', 'quora.com', 'flickr.com', 'vimeo.com',
}

def is_valid_url(url: str) -> bool:
    """
    Check if a URL is valid.
    
    Args:
        url: The URL to check.
        
    Returns:
        True if the URL is valid, False otherwise.
    """
    if not url or not isinstance(url, str):
        return False
    
    # Check if the URL matches the regex pattern
    if not URL_REGEX.match(url):
        return False
    
    # Parse the URL to check its components
    try:
        parsed = urlparse(url)
        return bool(parsed.netloc) and bool(parsed.scheme)
    except Exception:
        return False

def normalize_url(url: str) -> str:
    """
    Normalize a URL by removing unnecessary components and standardizing format.
    
    Args:
        url: The URL to normalize.
        
    Returns:
        The normalized URL.
        
    Raises:
        ValidationError: If the URL is invalid.
    """
    if not url:
        raise ValidationError("URL cannot be empty")
    
    # Add scheme if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    try:
        # Parse the URL
        parsed = urlparse(url)
        
        # Remove default ports
        netloc = parsed.netloc
        if ':' in netloc:
            host, port = netloc.split(':', 1)
            if (parsed.scheme == 'http' and port == '80') or (parsed.scheme == 'https' and port == '443'):
                netloc = host
        
        # Remove trailing slash from path if it's the only character
        path = parsed.path
        if path == '/':
            path = ''
        
        # Remove common tracking parameters
        query_params = parse_qs(parsed.query)
        for param in ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'fbclid', 'gclid']:
            if param in query_params:
                del query_params[param]
        
        # Reconstruct query string
        query = urlencode(query_params, doseq=True) if query_params else ''
        
        # Reconstruct the URL
        normalized = urlunparse((
            parsed.scheme,
            netloc,
            path,
            parsed.params,
            query,
            ''  # Remove fragment
        ))
        
        return normalized
    except Exception as e:
        raise ValidationError(f"Failed to normalize URL: {url}", original_error=e)

def get_domain(url: str) -> str:
    """
    Extract the domain from a URL.
    
    Args:
        url: The URL to extract the domain from.
        
    Returns:
        The domain of the URL.
        
    Raises:
        ValidationError: If the URL is invalid.
    """
    if not url:
        raise ValidationError("URL cannot be empty")
    
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except Exception as e:
        raise ValidationError(f"Failed to extract domain from URL: {url}", original_error=e)

def get_base_domain(url: str) -> str:
    """
    Extract the base domain from a URL (without subdomains).
    
    Args:
        url: The URL to extract the base domain from.
        
    Returns:
        The base domain of the URL.
        
    Raises:
        ValidationError: If the URL is invalid.
    """
    if not url:
        raise ValidationError("URL cannot be empty")
    
    try:
        domain = get_domain(url)
        parts = domain.split('.')
        
        # Handle special cases like co.uk, com.au, etc.
        if len(parts) > 2 and parts[-2] in {'co', 'com', 'org', 'net', 'edu', 'gov', 'mil'}:
            if parts[-1] in {'uk', 'au', 'nz', 'jp', 'br', 'in', 'za', 'mx', 'ca'}:
                return '.'.join(parts[-3:])
        
        # Return the last two parts of the domain
        return '.'.join(parts[-2:]) if len(parts) > 1 else domain
    except Exception as e:
        raise ValidationError(f"Failed to extract base domain from URL: {url}", original_error=e)

def is_same_domain(url1: str, url2: str) -> bool:
    """
    Check if two URLs have the same domain.
    
    Args:
        url1: The first URL.
        url2: The second URL.
        
    Returns:
        True if the URLs have the same domain, False otherwise.
    """
    try:
        return get_domain(url1) == get_domain(url2)
    except ValidationError:
        return False

def is_same_base_domain(url1: str, url2: str) -> bool:
    """
    Check if two URLs have the same base domain.
    
    Args:
        url1: The first URL.
        url2: The second URL.
        
    Returns:
        True if the URLs have the same base domain, False otherwise.
    """
    try:
        return get_base_domain(url1) == get_base_domain(url2)
    except ValidationError:
        return False

def is_social_media_url(url: str) -> bool:
    """
    Check if a URL is from a social media domain.
    
    Args:
        url: The URL to check.
        
    Returns:
        True if the URL is from a social media domain, False otherwise.
    """
    try:
        domain = get_domain(url)
        base_domain = get_base_domain(url)
        
        return domain in SOCIAL_MEDIA_DOMAINS or base_domain in SOCIAL_MEDIA_DOMAINS
    except ValidationError:
        return False

def is_file_url(url: str) -> bool:
    """
    Check if a URL points to a file with a common extension.
    
    Args:
        url: The URL to check.
        
    Returns:
        True if the URL points to a file with a common extension, False otherwise.
    """
    if not url:
        return False
    
    # Check if the URL ends with a common file extension
    return any(url.lower().endswith(ext) for ext in COMMON_FILE_EXTENSIONS)

def get_absolute_url(base_url: str, relative_url: str) -> str:
    """
    Convert a relative URL to an absolute URL.
    
    Args:
        base_url: The base URL.
        relative_url: The relative URL.
        
    Returns:
        The absolute URL.
        
    Raises:
        ValidationError: If the base URL is invalid.
    """
    if not base_url:
        raise ValidationError("Base URL cannot be empty")
    
    try:
        return urljoin(base_url, relative_url)
    except Exception as e:
        raise ValidationError(
            f"Failed to convert relative URL to absolute: {relative_url} (base: {base_url})",
            original_error=e
        )

def filter_urls(urls: List[str], 
                exclude_social_media: bool = False,
                exclude_file_urls: bool = True,
                exclude_domains: Optional[Set[str]] = None) -> List[str]:
    """
    Filter a list of URLs based on various criteria.
    
    Args:
        urls: The list of URLs to filter.
        exclude_social_media: Whether to exclude social media URLs.
        exclude_file_urls: Whether to exclude file URLs.
        exclude_domains: Set of domains to exclude.
        
    Returns:
        The filtered list of URLs.
    """
    if not urls:
        return []
    
    exclude_domains = exclude_domains or set()
    filtered_urls = []
    
    for url in urls:
        try:
            # Skip invalid URLs
            if not is_valid_url(url):
                continue
            
            # Skip file URLs if requested
            if exclude_file_urls and is_file_url(url):
                continue
            
            # Skip social media URLs if requested
            if exclude_social_media and is_social_media_url(url):
                continue
            
            # Skip excluded domains
            if exclude_domains:
                domain = get_domain(url)
                base_domain = get_base_domain(url)
                if domain in exclude_domains or base_domain in exclude_domains:
                    continue
            
            # Add valid URL to filtered list
            filtered_urls.append(url)
        except ValidationError:
            # Skip URLs that cause validation errors
            continue
    
    return filtered_urls

