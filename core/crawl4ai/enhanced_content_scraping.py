"""
Enhanced content scraping strategy for web pages.

This module provides an improved implementation of content scraping with better
accuracy, performance, and error handling.
"""

import re
import time
import asyncio
import logging
from typing import Dict, Any, Optional, List, Set, Tuple, Union
from urllib.parse import urljoin, urlparse
import requests
from requests.exceptions import RequestException, Timeout

from bs4 import BeautifulSoup, NavigableString, Comment, Tag
from .content_scraping_strategy import ContentScrapingStrategy
from .models import ScrapingResult, MediaItem, Link, Media, Links
from .html2text import HTML2Text
from .config import (
    MIN_WORD_THRESHOLD,
    IMAGE_DESCRIPTION_MIN_WORD_THRESHOLD,
    IMAGE_SCORE_THRESHOLD,
    IMPORTANT_ATTRS,
)
from .utils import (
    extract_metadata,
    normalize_url,
    is_external_url,
    extract_metadata_using_lxml,
)

# Pre-compile regular expressions
URL_REGEX = re.compile(r'https?://[^\s<>"]+|www\.[^\s<>"]+')
DIMENSION_REGEX = re.compile(r"(\d+)(\D*)")

# Common content containers to prioritize
CONTENT_CONTAINERS = [
    "article", "main", "content", "post", "story", "body", "entry", 
    "text", "blog", "news", "page", "container", "wrapper"
]

# Tags that typically contain navigation, ads, or other non-content elements
NOISE_TAGS = [
    "nav", "header", "footer", "aside", "sidebar", "menu", "banner", 
    "advertisement", "ad", "promo", "related", "recommended", "share", 
    "comment", "social", "widget", "popup", "modal", "cookie", "newsletter"
]


def parse_srcset(s: str) -> List[Dict]:
    """
    Parse the srcset attribute of an image.
    
    Args:
        s: The srcset attribute value
        
    Returns:
        List of dictionaries with url and width information
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


def parse_dimension(dimension):
    """
    Parse dimension values (width/height) from HTML attributes.
    
    Args:
        dimension: The dimension value to parse
        
    Returns:
        Tuple of (numeric value, unit)
    """
    if dimension:
        match = DIMENSION_REGEX.match(dimension)
        if match:
            number = int(match.group(1))
            unit = match.group(2) or "px"  # Default unit is 'px' if not specified
            return number, unit
    return None, None


class EnhancedWebScrapingStrategy(ContentScrapingStrategy):
    """
    Enhanced web content scraping strategy with improved accuracy and performance.
    
    Features:
    - Better content extraction with main content detection
    - Improved image processing and relevance scoring
    - Enhanced metadata extraction
    - Content caching for performance
    - Better error handling and recovery
    """

    def __init__(self, logger=None):
        """
        Initialize the enhanced web scraping strategy.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger
        
        # Initialize HTML2Text converter with optimized settings
        self.html2text = HTML2Text()
        self.html2text.ignore_links = False
        self.html2text.body_width = 0  # No wrapping
        self.html2text.ignore_images = False
        self.html2text.ignore_emphasis = False
        self.html2text.ignore_tables = False
        self.html2text.unicode_snob = True
        self.html2text.escape_snob = True
        self.html2text.single_line_break = True
        self.html2text.mark_code = True
        
        # Cache for parsed content to avoid redundant processing
        self.content_cache = {}
        self.cache_size_limit = 100
        self.cache_hits = 0
        self.cache_misses = 0

    def _log(self, level, message, tag="SCRAPE", **kwargs):
        """Helper method to safely use logger."""
        if self.logger:
            log_method = getattr(self.logger, level)
            log_method(message=message, tag=tag, **kwargs)
    
    def _get_cache_key(self, url: str, html: str) -> str:
        """Generate a cache key for the content."""
        # Use a combination of URL and HTML hash
        html_hash = hash(html[:1000] if html else "")  # Use first 1000 chars for efficiency
        return f"{url}:{html_hash}"
    
    def _cache_result(self, key: str, result: Dict[str, Any]):
        """Cache a scraping result."""
        # Implement LRU-like behavior by removing oldest entries when cache is full
        if len(self.content_cache) >= self.cache_size_limit:
            # Remove oldest entry (first key)
            if self.content_cache:
                oldest_key = next(iter(self.content_cache))
                del self.content_cache[oldest_key]
        
        self.content_cache[key] = {
            "result": result,
            "timestamp": time.time()
        }
    
    def _get_cached_result(self, key: str) -> Optional[Dict[str, Any]]:
        """Get a cached result if available and not expired."""
        cache_entry = self.content_cache.get(key)
        if not cache_entry:
            self.cache_misses += 1
            return None
        
        # Check if cache entry is expired (older than 1 hour)
        if time.time() - cache_entry["timestamp"] > 3600:
            del self.content_cache[key]
            self.cache_misses += 1
            return None
        
        self.cache_hits += 1
        return cache_entry["result"]

    def scrap(self, url: str, html: str, **kwargs) -> ScrapingResult:
        """
        Main entry point for content scraping.

        Args:
            url (str): The URL of the page to scrape.
            html (str): The HTML content of the page.
            **kwargs: Additional keyword arguments.

        Returns:
            ScrapingResult: A structured result containing the scraped content.
        """
        # Check cache first
        cache_key = self._get_cache_key(url, html)
        cached_result = self._get_cached_result(cache_key)
        if cached_result and not kwargs.get("bypass_cache", False):
            self._log("info", f"Using cached content for {url}")
            return self._convert_raw_result_to_scraping_result(cached_result)
        
        raw_result = self._scrap(url, html, is_async=False, **kwargs)
        if raw_result is None:
            return ScrapingResult(
                cleaned_html="",
                success=False,
                media=Media(),
                links=Links(),
                metadata={},
            )
        
        # Cache the result
        self._cache_result(cache_key, raw_result)
        
        return self._convert_raw_result_to_scraping_result(raw_result)
    
    def _convert_raw_result_to_scraping_result(self, raw_result: Dict[str, Any]) -> ScrapingResult:
        """Convert a raw result dictionary to a ScrapingResult object."""
        # Convert media items
        media = Media(
            images=[
                MediaItem(**img)
                for img in raw_result.get("media", {}).get("images", [])
                if img
            ],
            videos=[
                MediaItem(**vid)
                for vid in raw_result.get("media", {}).get("videos", [])
                if vid
            ],
            audios=[
                MediaItem(**aud)
                for aud in raw_result.get("media", {}).get("audios", [])
                if aud
            ],
        )

        # Convert links
        links = Links(
            internal=[
                Link(**link)
                for link in raw_result.get("links", {}).get("internal", [])
                if link
            ],
            external=[
                Link(**link)
                for link in raw_result.get("links", {}).get("external", [])
                if link
            ],
        )

        return ScrapingResult(
            cleaned_html=raw_result.get("cleaned_html", ""),
            success=raw_result.get("success", False),
            media=media,
            links=links,
            metadata=raw_result.get("metadata", {}),
        )

    async def ascrap(self, url: str, html: str, **kwargs) -> ScrapingResult:
        """
        Main entry point for asynchronous content scraping.

        Args:
            url (str): The URL of the page to scrape.
            html (str): The HTML content of the page.
            **kwargs: Additional keyword arguments.

        Returns:
            ScrapingResult: A structured result containing the scraped content.
        """
        # Check cache first
        cache_key = self._get_cache_key(url, html)
        cached_result = self._get_cached_result(cache_key)
        if cached_result and not kwargs.get("bypass_cache", False):
            self._log("info", f"Using cached content for {url}")
            return self._convert_raw_result_to_scraping_result(cached_result)
        
        # Use a thread pool for CPU-intensive parsing
        raw_result = await asyncio.to_thread(self._scrap, url, html, **kwargs)
        if raw_result is None:
            return ScrapingResult(
                cleaned_html="",
                success=False,
                media=Media(),
                links=Links(),
                metadata={},
            )
        
        # Cache the result
        self._cache_result(cache_key, raw_result)
        
        return self._convert_raw_result_to_scraping_result(raw_result)

    def _identify_main_content_container(self, soup: BeautifulSoup) -> Optional[Tag]:
        """
        Identify the main content container in the HTML.
        
        This uses heuristics to find the element most likely to contain the main content.
        
        Args:
            soup: BeautifulSoup object of the HTML
            
        Returns:
            Tag: The main content container, or None if not found
        """
        # Strategy 1: Look for elements with content-related IDs or classes
        for container_name in CONTENT_CONTAINERS:
            # Check for ID
            element = soup.find(id=re.compile(container_name, re.I))
            if element:
                return element
                
            # Check for class
            elements = soup.find_all(class_=re.compile(container_name, re.I))
            if elements:
                # Return the element with the most text content
                return max(elements, key=lambda e: len(e.get_text(strip=True)), default=None)
        
        # Strategy 2: Look for article or main tags
        for tag_name in ["article", "main"]:
            elements = soup.find_all(tag_name)
            if elements:
                return max(elements, key=lambda e: len(e.get_text(strip=True)), default=None)
        
        # Strategy 3: Find the div with the most text content
        divs = soup.find_all("div")
        if divs:
            # Filter out very small divs and those likely to be noise
            content_divs = [
                div for div in divs 
                if len(div.get_text(strip=True).split()) > MIN_WORD_THRESHOLD
                and not any(noise in str(div.get("class", [])).lower() for noise in NOISE_TAGS)
                and not any(noise in str(div.get("id", "")).lower() for noise in NOISE_TAGS)
            ]
            
            if content_divs:
                return max(content_divs, key=lambda e: len(e.get_text(strip=True)))
        
        # Fallback: Use body
        return soup.find("body")

    def remove_unwanted_attributes(
        self, element, important_attrs, keep_data_attributes=False
    ):
        """
        Remove unwanted attributes from an HTML element.

        Args:
            element (Tag): The HTML element to remove attributes from.
            important_attrs (list): List of important attributes to keep.
            keep_data_attributes (bool): Whether to keep data attributes.

        Returns:
            None
        """
        attrs_to_remove = []
        for attr in element.attrs:
            if attr not in important_attrs:
                if keep_data_attributes:
                    if not attr.startswith("data-"):
                        attrs_to_remove.append(attr)
                else:
                    attrs_to_remove.append(attr)

        for attr in attrs_to_remove:
            del element[attr]

    def process_image(self, img, url, index, total_images, **kwargs):
        """
        Process an image element.

        How it works:
        1. Check if the image has valid display and inside undesired html elements.
        2. Score an image for it's usefulness.
        3. Extract image file metadata to extract size and extension.
        4. Generate a dictionary with the processed image information.
        5. Return the processed image information.

        Args:
            img (Tag): The image element to process.
            url (str): The URL of the page containing the image.
            index (int): The index of the image in the list of images.
            total_images (int): The total number of images in the list.
            **kwargs: Additional keyword arguments.

        Returns:
            dict: A dictionary containing the processed image information.
        """
        # Constants for checks
        classes_to_check = frozenset(["button", "icon", "logo"])
        tags_to_check = frozenset(["button", "input"])
        image_formats = frozenset(["jpg", "jpeg", "png", "webp", "avif", "gif"])

        # Pre-fetch commonly used attributes
        style = img.get("style", "")
        src = img.get("src", "")
        alt = img.get("alt", "")
        title = img.get("title", "")
        width = img.get("width", "")
        height = img.get("height", "")
        
        # Skip data URLs and empty sources
        if not src or src.startswith("data:"):
            return None
        
        # Skip very small images
        try:
            width_val = int(width) if width and width.isdigit() else 0
            height_val = int(height) if height and height.isdigit() else 0
            if (width_val > 0 and width_val < 50) or (height_val > 0 and height_val < 50):
                return None
        except (ValueError, TypeError):
            pass

        # Check if image is hidden
        if "display: none" in style or "visibility: hidden" in style:
            return None

        # Check if image is inside a button or other interactive element
        parent = img.parent
        if parent and parent.name in tags_to_check:
            return None

        # Check if image has classes indicating it's not content
        img_classes = img.get("class", [])
        if isinstance(img_classes, str):
            img_classes = [img_classes]
        
        for cls in img_classes:
            if any(c in cls.lower() for c in classes_to_check):
                return None

        # Normalize image URL
        img_url = urljoin(url, src)

        # Extract image dimensions
        width_val, width_unit = parse_dimension(width)
        height_val, height_unit = parse_dimension(height)

        # Score the image for relevance
        score = 0
        
        # Score based on position
        if index < total_images * 0.2:  # First 20% of images
            score += 2
        elif index < total_images * 0.5:  # First 50% of images
            score += 1
            
        # Score based on alt text
        if alt:
            score += min(len(alt.split()), 5)  # Up to 5 points for alt text
            
        # Score based on dimensions
        if width_val and height_val:
            area = width_val * height_val
            if area > 40000:  # Larger than 200x200
                score += 3
            elif area > 10000:  # Larger than 100x100
                score += 1
                
        # Score based on file extension
        if any(src.lower().endswith(f".{ext}") for ext in image_formats):
            score += 1
            
        # Check if image is in a figure or has a caption
        in_figure = False
        caption = ""
        
        # Look for figure parent
        figure_parent = img.find_parent("figure")
        if figure_parent:
            in_figure = True
            figcaption = figure_parent.find("figcaption")
            if figcaption:
                caption = figcaption.get_text(strip=True)
                score += 3  # Images with captions are usually important
                
        # If no caption found, try to find nearby text that might describe the image
        if not caption:
            # Check for alt or title text
            if alt:
                caption = alt
            elif title:
                caption = title
            else:
                # Try to find nearby text
                next_sibling = img.next_sibling
                if next_sibling and isinstance(next_sibling, Tag):
                    if next_sibling.name in ["p", "div", "span"]:
                        caption = next_sibling.get_text(strip=True)
                        
        # If still no caption, look for parent text
        if not caption:
            parent_text = self.find_closest_parent_with_useful_text(img, **kwargs)
            if parent_text:
                caption = parent_text
            
        # If score is too low, skip this image
        image_score_threshold = kwargs.get("image_score_threshold", IMAGE_SCORE_THRESHOLD)
        if score < image_score_threshold:
            return None
            
        # Process srcset if available
        srcset = img.get("srcset", "")
        srcset_urls = parse_srcset(srcset)
        
        # Get the largest image from srcset if available
        largest_variant = None
        if srcset_urls:
            # Find the variant with the largest width
            largest_variant = max(
                srcset_urls, 
                key=lambda v: int(v["width"]) if v["width"] and v["width"].isdigit() else 0,
                default=None
            )
            
        # Use the largest variant or the original src
        final_src = largest_variant["url"] if largest_variant else src
        final_url = urljoin(url, final_src)
            
        # Create the image dictionary
        image_dict = {
            "src": final_url,
            "alt": alt,
            "title": title,
            "width": width_val,
            "height": height_val,
            "caption": caption,
            "in_figure": in_figure,
            "score": score,
        }
        
        return image_dict

    def find_closest_parent_with_useful_text(self, tag, **kwargs):
        """
        Find the closest parent with useful text.

        Args:
            tag (Tag): The starting tag to search from.
            **kwargs: Additional keyword arguments.

        Returns:
            str: The text content of the closest parent with useful text, or None if not found.
        """
        image_description_min_word_threshold = kwargs.get(
            "image_description_min_word_threshold", IMAGE_DESCRIPTION_MIN_WORD_THRESHOLD
        )
        current_tag = tag
        while current_tag:
            current_tag = current_tag.parent
            # Get the text content of the parent tag
            if current_tag:
                text_content = current_tag.get_text(separator=" ", strip=True)
                # Check if the text content has at least word_count_threshold
                if len(text_content.split()) >= image_description_min_word_threshold:
                    return text_content
        return None

    def _clean_markdown(self, markdown: str) -> str:
        """
        Clean up markdown content.
        
        Args:
            markdown: Raw markdown content
            
        Returns:
            Cleaned markdown content
        """
        if not markdown:
            return ""
            
        # Replace multiple newlines with at most two
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)
        
        # Remove empty list items
        markdown = re.sub(r'^\s*[\*\-\+]\s*$', '', markdown, flags=re.MULTILINE)
        
        # Remove empty headers
        markdown = re.sub(r'^#+\s*$', '', markdown, flags=re.MULTILINE)
        
        # Fix broken URLs
        def fix_url(match):
            url = match.group(0)
            if '(' in url and ')' not in url:
                url = url.split('(')[0]
            return url
            
        markdown = re.sub(URL_REGEX, fix_url, markdown)
        
        # Remove trailing whitespace
        markdown = '\n'.join(line.rstrip() for line in markdown.splitlines())
        
        return markdown.strip()

    def _scrap(self, url: str, html: str, is_async=False, **kwargs) -> Dict[str, Any]:
        """
        Scrape content from HTML.

        Args:
            url (str): The URL of the page to scrape.
            html (str): The HTML content of the page.
            is_async (bool): Whether the scraping is being done asynchronously.
            **kwargs: Additional keyword arguments.

        Returns:
            dict: A dictionary containing the scraped content.
        """
        if not html:
            self._log("warning", "Empty HTML content")
            return None

        try:
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            
            # Remove script and style elements
            for element in soup(["script", "style", "noscript", "iframe", "svg"]):
                element.decompose()
                
            # Remove comments
            for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
                comment.extract()
                
            # Extract metadata
            metadata = extract_metadata(soup, url)
            
            # Try to extract metadata using lxml as a fallback
            if not metadata.get("title"):
                try:
                    lxml_metadata = extract_metadata_using_lxml(html, url)
                    # Merge metadata, preferring existing values
                    for key, value in lxml_metadata.items():
                        if not metadata.get(key) and value:
                            metadata[key] = value
                except Exception as e:
                    self._log("warning", f"Error extracting metadata with lxml: {e}")
            
            # Identify the main content container
            main_content = self._identify_main_content_container(soup)
            
            # If main content is found, use it instead of the whole document
            if main_content:
                # Create a new soup with just the main content
                content_html = str(main_content)
                content_soup = BeautifulSoup(content_html, "html.parser")
            else:
                content_soup = soup
                
            # Process images
            images = []
            img_elements = content_soup.find_all("img")
            total_images = len(img_elements)
            
            for i, img in enumerate(img_elements):
                try:
                    img_data = self.process_image(img, url, i, total_images, **kwargs)
                    if img_data:
                        images.append(img_data)
                except Exception as e:
                    self._log("warning", f"Error processing image: {e}")
                    
            # Process links
            internal_links = []
            external_links = []
            
            for a in content_soup.find_all("a", href=True):
                try:
                    href = a["href"].strip()
                    if not href or href.startswith("#") or href.startswith("javascript:"):
                        continue
                        
                    # Normalize URL
                    full_url = urljoin(url, href)
                    
                    # Get link text
                    link_text = a.get_text(strip=True)
                    
                    # Create link dictionary
                    link_dict = {
                        "url": full_url,
                        "text": link_text,
                        "title": a.get("title", ""),
                    }
                    
                    # Determine if internal or external
                    if is_external_url(url, full_url):
                        external_links.append(link_dict)
                    else:
                        internal_links.append(link_dict)
                except Exception as e:
                    self._log("warning", f"Error processing link: {e}")
            
            # Clean the HTML for better markdown conversion
            for element in content_soup.find_all(recursive=True):
                # Remove empty elements
                if element.name not in ["br", "hr", "img"] and not element.get_text(strip=True):
                    if not element.find_all(["img", "video", "audio", "iframe"]):
                        element.decompose()
                        continue
                
                # Remove unwanted attributes
                self.remove_unwanted_attributes(
                    element, IMPORTANT_ATTRS, keep_data_attributes=False
                )
            
            # Convert to markdown
            markdown = self.html2text.handle(str(content_soup))
            
            # Clean up markdown
            markdown = self._clean_markdown(markdown)
            
            # Create the result dictionary
            result = {
                "cleaned_html": str(content_soup),
                "markdown": markdown,
                "success": True,
                "media": {
                    "images": images,
                    "videos": [],  # TODO: Implement video extraction
                    "audios": [],  # TODO: Implement audio extraction
                },
                "links": {
                    "internal": internal_links,
                    "external": external_links,
                },
                "metadata": metadata,
            }
            
            return result
            
        except Exception as e:
            self._log("error", f"Error scraping content: {e}")
            return None

