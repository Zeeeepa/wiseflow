"""
Enhanced content scraping implementation for crawl4ai.

This module provides an improved implementation of content scraping with
better error handling, performance optimizations, and resource management.
"""

import re
import logging
import traceback
from typing import Dict, List, Any, Optional, Tuple, Set
from urllib.parse import urljoin
import asyncio
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup, NavigableString, Tag
from lxml import etree, html as lhtml

from .content_scraping_strategy import ContentScrapingStrategy
from .content_scraping_utils import parse_srcset, parse_dimension, score_image, BASE64_PATTERN
from .models import ScrapingResult, MediaItem, Link, Media, Links
from .errors import ParsingError
from .url_utils import is_valid_url, normalize_url, get_domain, is_same_domain
from .config import (
    MIN_WORD_THRESHOLD,
    IMAGE_DESCRIPTION_MIN_WORD_THRESHOLD,
    IMAGE_SCORE_THRESHOLD,
    ONLY_TEXT_ELIGIBLE_TAGS,
    IMPORTANT_ATTRS,
    SOCIAL_MEDIA_DOMAINS,
)

logger = logging.getLogger(__name__)

class EnhancedWebScrapingStrategy(ContentScrapingStrategy):
    """
    Enhanced implementation of web content scraping.
    
    This class provides an improved implementation of web content scraping with
    better error handling, performance optimizations, and resource management.
    """
    
    def __init__(self, logger=None, max_workers: int = 5):
        """
        Initialize the enhanced web scraping strategy.
        
        Args:
            logger: Logger instance for logging.
            max_workers: Maximum number of worker threads for parallel processing.
        """
        self.logger = logger or logging.getLogger(__name__)
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Pre-compile regular expressions for better performance
        self.base64_pattern = BASE64_PATTERN
    
    def _log(self, level: str, message: str, tag: str = "SCRAPE", **kwargs):
        """Helper method to safely use logger."""
        if self.logger:
            log_method = getattr(self.logger, level)
            log_method(message=message, tag=tag, **kwargs)
    
    def scrap(self, url: str, html: str, **kwargs) -> ScrapingResult:
        """
        Main entry point for content scraping.
        
        Args:
            url: The URL of the page to scrape.
            html: The HTML content of the page.
            **kwargs: Additional keyword arguments.
            
        Returns:
            ScrapingResult: A structured result containing the scraped content.
            
        Raises:
            ParsingError: If there's an error parsing the HTML content.
        """
        try:
            raw_result = self._scrap(url, html, is_async=False, **kwargs)
            if raw_result is None:
                return ScrapingResult(
                    cleaned_html="",
                    success=False,
                    media=Media(),
                    links=Links(),
                    metadata={},
                )

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
        except Exception as e:
            self._log("error", f"Error in scrap: {e}")
            traceback.print_exc()
            raise ParsingError(f"Failed to scrape content from {url}", url=url, original_error=e)
    
    async def ascrap(self, url: str, html: str, **kwargs) -> ScrapingResult:
        """
        Main entry point for asynchronous content scraping.
        
        Args:
            url: The URL of the page to scrape.
            html: The HTML content of the page.
            **kwargs: Additional keyword arguments.
            
        Returns:
            ScrapingResult: A structured result containing the scraped content.
            
        Raises:
            ParsingError: If there's an error parsing the HTML content.
        """
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor, 
                lambda: self._scrap(url, html, is_async=True, **kwargs)
            )
            
            if result is None:
                return ScrapingResult(
                    cleaned_html="",
                    success=False,
                    media=Media(),
                    links=Links(),
                    metadata={},
                )
                
            # Convert media items
            media = Media(
                images=[
                    MediaItem(**img)
                    for img in result.get("media", {}).get("images", [])
                    if img
                ],
                videos=[
                    MediaItem(**vid)
                    for vid in result.get("media", {}).get("videos", [])
                    if vid
                ],
                audios=[
                    MediaItem(**aud)
                    for aud in result.get("media", {}).get("audios", [])
                    if aud
                ],
            )

            # Convert links
            links = Links(
                internal=[
                    Link(**link)
                    for link in result.get("links", {}).get("internal", [])
                    if link
                ],
                external=[
                    Link(**link)
                    for link in result.get("links", {}).get("external", [])
                    if link
                ],
            )

            return ScrapingResult(
                cleaned_html=result.get("cleaned_html", ""),
                success=result.get("success", False),
                media=media,
                links=links,
                metadata=result.get("metadata", {}),
            )
        except Exception as e:
            self._log("error", f"Error in ascrap: {e}")
            traceback.print_exc()
            raise ParsingError(f"Failed to asynchronously scrape content from {url}", url=url, original_error=e)
    
    def _process_element(
        self,
        url: str,
        element: lhtml.HtmlElement,
        media: Dict[str, List],
        internal_links: Dict[str, Dict],
        external_links: Dict[str, Dict],
        base_domain: str,
        **kwargs
    ):
        """
        Process an HTML element and its children.
        
        Args:
            url: The URL of the page.
            element: The HTML element to process.
            media: Dictionary to store media items.
            internal_links: Dictionary to store internal links.
            external_links: Dictionary to store external links.
            base_domain: The base domain of the URL.
            **kwargs: Additional keyword arguments.
        """
        # Process images
        for img in element.xpath(".//img"):
            self._process_image(img, url, media, **kwargs)
        
        # Process videos
        for video in element.xpath(".//video"):
            self._process_video(video, url, media, **kwargs)
        
        # Process audio
        for audio in element.xpath(".//audio"):
            self._process_audio(audio, url, media, **kwargs)
        
        # Process links
        for link in element.xpath(".//a"):
            self._process_link(link, url, base_domain, internal_links, external_links, **kwargs)
    
    def _process_image(
        self,
        img: lhtml.HtmlElement,
        url: str,
        media: Dict[str, List],
        **kwargs
    ):
        """
        Process an image element.
        
        Args:
            img: The image element to process.
            url: The URL of the page.
            media: Dictionary to store media items.
            **kwargs: Additional keyword arguments.
        """
        try:
            # Get image attributes
            src = img.get("src", "")
            alt = img.get("alt", "")
            title = img.get("title", "")
            width = img.get("width")
            height = img.get("height")
            
            # Skip if no source
            if not src:
                return
                
            # Skip base64 images if they're too large
            if self.base64_pattern.match(src) and len(src) > 1000:
                return
            
            # Score the image
            image_score = score_image(img, **kwargs)
            
            # Skip low-scoring images
            image_score_threshold = kwargs.get("image_score_threshold", IMAGE_SCORE_THRESHOLD)
            if image_score < image_score_threshold:
                return
            
            # Create image item
            image_item = {
                "src": src,
                "alt": alt,
                "title": title,
                "width": width,
                "height": height,
                "score": image_score,
            }
            
            # Add to media
            if "images" not in media:
                media["images"] = []
            media["images"].append(image_item)
        except Exception as e:
            self._log("warning", f"Error processing image: {e}")
    
    def _process_video(
        self,
        video: lhtml.HtmlElement,
        url: str,
        media: Dict[str, List],
        **kwargs
    ):
        """
        Process a video element.
        
        Args:
            video: The video element to process.
            url: The URL of the page.
            media: Dictionary to store media items.
            **kwargs: Additional keyword arguments.
        """
        try:
            # Get video attributes
            src = video.get("src", "")
            poster = video.get("poster", "")
            width = video.get("width")
            height = video.get("height")
            
            # Check for source elements
            sources = []
            for source in video.xpath(".//source"):
                source_src = source.get("src", "")
                source_type = source.get("type", "")
                if source_src:
                    sources.append({
                        "src": source_src,
                        "type": source_type,
                    })
            
            # Skip if no source
            if not src and not sources:
                return
            
            # Create video item
            video_item = {
                "src": src,
                "poster": poster,
                "width": width,
                "height": height,
                "sources": sources,
            }
            
            # Add to media
            if "videos" not in media:
                media["videos"] = []
            media["videos"].append(video_item)
        except Exception as e:
            self._log("warning", f"Error processing video: {e}")
    
    def _process_audio(
        self,
        audio: lhtml.HtmlElement,
        url: str,
        media: Dict[str, List],
        **kwargs
    ):
        """
        Process an audio element.
        
        Args:
            audio: The audio element to process.
            url: The URL of the page.
            media: Dictionary to store media items.
            **kwargs: Additional keyword arguments.
        """
        try:
            # Get audio attributes
            src = audio.get("src", "")
            
            # Check for source elements
            sources = []
            for source in audio.xpath(".//source"):
                source_src = source.get("src", "")
                source_type = source.get("type", "")
                if source_src:
                    sources.append({
                        "src": source_src,
                        "type": source_type,
                    })
            
            # Skip if no source
            if not src and not sources:
                return
            
            # Create audio item
            audio_item = {
                "src": src,
                "sources": sources,
            }
            
            # Add to media
            if "audios" not in media:
                media["audios"] = []
            media["audios"].append(audio_item)
        except Exception as e:
            self._log("warning", f"Error processing audio: {e}")
    
    def _process_link(
        self,
        link: lhtml.HtmlElement,
        url: str,
        base_domain: str,
        internal_links: Dict[str, Dict],
        external_links: Dict[str, Dict],
        **kwargs
    ):
        """
        Process a link element.
        
        Args:
            link: The link element to process.
            url: The URL of the page.
            base_domain: The base domain of the URL.
            internal_links: Dictionary to store internal links.
            external_links: Dictionary to store external links.
            **kwargs: Additional keyword arguments.
        """
        try:
            # Get link attributes
            href = link.get("href", "")
            text = link.text_content().strip()
            title = link.get("title", "")
            
            # Skip if no href
            if not href:
                return
                
            # Skip anchors
            if href.startswith("#"):
                return
            
            # Skip javascript: links
            if href.startswith("javascript:"):
                return
            
            # Skip mailto: links
            if href.startswith("mailto:"):
                return
            
            # Normalize URL
            try:
                full_url = urljoin(url, href)
            except Exception:
                return
            
            # Check if internal or external
            try:
                is_internal = is_same_domain(url, full_url)
            except Exception:
                is_internal = False
            
            # Skip based on configuration
            if is_internal and kwargs.get("exclude_internal_links", False):
                return
                
            if not is_internal and kwargs.get("exclude_external_links", False):
                return
            
            # Check for social media domains
            if kwargs.get("exclude_social_media_links", False):
                try:
                    link_domain = get_domain(full_url)
                    if link_domain in kwargs.get("exclude_social_media_domains", SOCIAL_MEDIA_DOMAINS):
                        return
                except Exception:
                    pass
            
            # Check for excluded domains
            if kwargs.get("exclude_domains"):
                try:
                    link_domain = get_domain(full_url)
                    if link_domain in kwargs.get("exclude_domains", []):
                        return
                except Exception:
                    pass
            
            # Create link item
            link_item = {
                "url": full_url,
                "text": text,
                "title": title,
            }
            
            # Add to appropriate dictionary
            if is_internal:
                if full_url not in internal_links:
                    internal_links[full_url] = link_item
            else:
                if full_url not in external_links:
                    external_links[full_url] = link_item
        except Exception as e:
            self._log("warning", f"Error processing link: {e}")
    
    def _scrap(
        self,
        url: str,
        html: str,
        word_count_threshold: int = MIN_WORD_THRESHOLD,
        css_selector: str = None,
        is_async: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Internal implementation of content scraping.
        
        Args:
            url: The URL of the page to scrape.
            html: The HTML content of the page.
            word_count_threshold: Minimum word count threshold for content.
            css_selector: CSS selector to target specific elements.
            is_async: Whether this is being called asynchronously.
            **kwargs: Additional keyword arguments.
            
        Returns:
            A dictionary containing the scraped content.
            
        Raises:
            ParsingError: If there's an error parsing the HTML content.
        """
        if not html:
            return None

        success = True
        try:
            # Parse HTML with lxml for better performance
            doc = lhtml.document_fromstring(html)
            
            # Get base domain
            try:
                base_domain = get_domain(url)
            except Exception:
                base_domain = ""
            
            # Remove comments if requested
            if kwargs.get("remove_comments", False):
                comments = doc.xpath("//comment()")
                for comment in comments:
                    comment.getparent().remove(comment)
            
            # Handle tag-based removal
            excluded_tags = set(kwargs.get("excluded_tags", []) or [])
            if excluded_tags:
                for tag in excluded_tags:
                    for element in doc.xpath(f".//{tag}"):
                        if element.getparent() is not None:
                            element.getparent().remove(element)
            
            # Handle CSS selector-based exclusion
            excluded_selector = kwargs.get("excluded_selector", "")
            if excluded_selector:
                try:
                    for element in doc.cssselect(excluded_selector):
                        if element.getparent() is not None:
                            element.getparent().remove(element)
                except Exception as e:
                    self._log("error", f"Error with excluded CSS selector: {str(e)}")
            
            # Extract metadata
            try:
                from .utils import extract_metadata_using_lxml
                meta = extract_metadata_using_lxml("", doc)
            except Exception as e:
                self._log("error", f"Error extracting metadata: {str(e)}")
                meta = {}
            
            # Handle CSS selector targeting
            if css_selector:
                try:
                    selected_elements = doc.cssselect(css_selector)
                    if not selected_elements:
                        return {
                            "markdown": "",
                            "cleaned_html": "",
                            "success": True,
                            "media": {"images": [], "videos": [], "audios": []},
                            "links": {"internal": [], "external": []},
                            "metadata": meta,
                            "message": f"No elements found for CSS selector: {css_selector}",
                        }
                    body = lhtml.Element("div")
                    body.extend(selected_elements)
                except Exception as e:
                    self._log("error", f"Error with CSS selector: {str(e)}")
                    return None
            else:
                body = doc
            
            # Remove script and style tags
            for tag in ["script", "style", "link", "meta", "noscript"]:
                for element in body.xpath(f".//{tag}"):
                    if element.getparent() is not None:
                        element.getparent().remove(element)
            
            # Handle social media and domain exclusions
            kwargs["exclude_domains"] = set(kwargs.get("exclude_domains", []))
            if kwargs.get("exclude_social_media_links", False):
                kwargs["exclude_social_media_domains"] = set(
                    kwargs.get("exclude_social_media_domains", [])
                    + SOCIAL_MEDIA_DOMAINS
                )
                kwargs["exclude_domains"].update(kwargs["exclude_social_media_domains"])
            
            # Process forms if needed
            if kwargs.get("remove_forms", False):
                for form in body.xpath(".//form"):
                    if form.getparent() is not None:
                        form.getparent().remove(form)
            
            # Process content
            media = {"images": [], "videos": [], "audios": []}
            internal_links = {}
            external_links = {}
            
            # Process elements
            self._process_element(
                url,
                body,
                media,
                internal_links,
                external_links,
                base_domain=base_domain,
                **kwargs
            )
            
            # Handle only_text option
            if kwargs.get("only_text", False):
                for tag in ONLY_TEXT_ELIGIBLE_TAGS:
                    for element in body.xpath(f".//{tag}"):
                        if element.text:
                            new_text = lhtml.Element("span")
                            new_text.text = element.text_content()
                            if element.getparent() is not None:
                                element.getparent().replace(element, new_text)
            
            # Clean base64 images
            for img in body.xpath(".//img[@src]"):
                src = img.get("src", "")
                if self.base64_pattern.match(src):
                    img.set("src", self.base64_pattern.sub("", src))
            
            # Remove empty elements
            self._remove_empty_elements(body, word_count_threshold)
            
            # Remove unneeded attributes
            self._remove_unwanted_attributes(
                body, 
                keep_data_attributes=kwargs.get("keep_data_attributes", False),
                keep_attrs=kwargs.get("keep_attrs", [])
            )
            
            # Generate output HTML
            cleaned_html = lhtml.tostring(
                body,
                encoding="unicode",
                pretty_print=True,
                method="html",
                with_tail=False,
            ).strip()
            
            return {
                "cleaned_html": cleaned_html,
                "success": success,
                "media": media,
                "links": {
                    "internal": list(internal_links.values()),
                    "external": list(external_links.values()),
                },
                "metadata": meta,
            }
        except Exception as e:
            self._log("error", f"Error processing HTML: {str(e)}")
            traceback.print_exc()
            
            # Create error message in case of failure
            error_body = lhtml.Element("div")
            error_div = etree.SubElement(error_body, "div", id="crawl4ai_error_message")
            error_div.text = f"""
            Crawl4AI Error: This page is not fully supported.
            
            Error Message: {str(e)}
            
            Possible reasons:
            1. The page may have restrictions that prevent crawling.
            2. The page might not be fully loaded.
            
            Suggestions:
            - Try calling the crawl function with these parameters:
            magic=True,
            - Set headless=False to visualize what's happening on the page.
            
            If the issue persists, please check the page's structure and any potential anti-crawling measures.
            """
            
            cleaned_html = lhtml.tostring(
                error_body, encoding="unicode", pretty_print=True
            )
            
            return {
                "cleaned_html": cleaned_html,
                "success": False,
                "media": {"images": [], "videos": [], "audios": []},
                "links": {"internal": [], "external": []},
                "metadata": {},
            }
    
    def _remove_empty_elements(self, root: lhtml.HtmlElement, word_count_threshold: int = 1) -> None:
        """
        Remove elements with insufficient content.
        
        Args:
            root: The root element to process.
            word_count_threshold: Minimum word count threshold for content.
        """
        # Define tags that are allowed to have no content
        bypass_tags = {
            "a", "img", "br", "hr", "input", "meta", "link", "source", "track", "wbr",
        }
        
        # Process elements in reverse order to avoid issues with changing tree structure
        for el in reversed(list(root.iterdescendants())):
            if not isinstance(el, lhtml.HtmlElement):
                continue
                
            if el.tag in bypass_tags:
                continue
                
            text_content = (el.text_content() or "").strip()
            if len(text_content.split()) < word_count_threshold and not el.getchildren():
                parent = el.getparent()
                if parent is not None:
                    parent.remove(el)
    
    def _remove_unwanted_attributes(
        self, 
        root: lhtml.HtmlElement, 
        keep_data_attributes: bool = False,
        keep_attrs: List[str] = None
    ) -> None:
        """
        Remove unwanted attributes from elements.
        
        Args:
            root: The root element to process.
            keep_data_attributes: Whether to keep data-* attributes.
            keep_attrs: Additional attributes to keep.
        """
        important_attrs = set(IMPORTANT_ATTRS)
        if keep_attrs:
            important_attrs.update(keep_attrs)
            
        # Process all elements including root
        for el in [root] + list(root.iterdescendants()):
            if not isinstance(el, lhtml.HtmlElement):
                continue
                
            # Get attributes to remove
            attrs_to_remove = []
            for attr in el.attrib:
                if attr not in important_attrs:
                    if keep_data_attributes and attr.startswith("data-"):
                        continue
                    attrs_to_remove.append(attr)
            
            # Remove attributes
            for attr in attrs_to_remove:
                del el.attrib[attr]

