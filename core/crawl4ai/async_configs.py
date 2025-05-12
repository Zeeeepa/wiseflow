from .config import (
    MIN_WORD_THRESHOLD,
    IMAGE_DESCRIPTION_MIN_WORD_THRESHOLD,
    SCREENSHOT_HEIGHT_TRESHOLD,
    PAGE_TIMEOUT,
    IMAGE_SCORE_THRESHOLD,
    SOCIAL_MEDIA_DOMAINS,
)

from .user_agent_generator import UAGen, ValidUAGenerator
from .markdown_generation_strategy import MarkdownGenerationStrategy
from .content_scraping_strategy import ContentScrapingStrategy, WebScrapingStrategy
from .enhanced_content_scraping import EnhancedWebScrapingStrategy
from typing import Union, List, Optional, Dict, Any
from .cache_context import CacheMode

import inspect
from enum import Enum 
import os
import logging

logger = logging.getLogger(__name__)

def to_serializable_dict(obj: Any) -> Dict:
    """
    Recursively convert an object to a serializable dictionary using {type, params} structure
    for complex objects.
    """
    if obj is None:
        return None
        
    # Handle basic types
    if isinstance(obj, (str, int, float, bool)):
        return obj
        
    # Handle Enum
    if isinstance(obj, Enum):
        return {
            "type": obj.__class__.__name__,
            "params": obj.value
        }
        
    # Handle datetime objects
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
        
    # Handle lists, tuples, and sets
    if isinstance(obj, (list, tuple, set)):
        return [to_serializable_dict(item) for item in obj]
        
    # Handle dictionaries - preserve them as-is
    if isinstance(obj, dict):
        return {
            "type": "dict",  # Mark as plain dictionary
            "value": {str(k): to_serializable_dict(v) for k, v in obj.items()}
        }
    
    # Handle class instances
    if hasattr(obj, '__class__'):
        # Get constructor signature
        sig = inspect.signature(obj.__class__.__init__)
        params = sig.parameters
        
        # Get current values
        current_values = {}
        for name, param in params.items():
            if name == 'self':
                continue
                
            value = getattr(obj, name, param.default)
            
            # Only include if different from default, considering empty values
            if not (is_empty_value(value) and is_empty_value(param.default)):
                if value != param.default:
                    current_values[name] = to_serializable_dict(value)
        
        return {
            "type": obj.__class__.__name__,
            "params": current_values
        }
        
    return str(obj)

def from_serializable_dict(data: Any) -> Any:
    """
    Recursively convert a serializable dictionary back to an object instance.
    """
    if data is None:
        return None

    # Handle basic types
    if isinstance(data, (str, int, float, bool)):
        return data

    # Handle typed data
    if isinstance(data, dict) and "type" in data:
        # Handle plain dictionaries
        if data["type"] == "dict":
            return {k: from_serializable_dict(v) for k, v in data["value"].items()}

    # Handle lists
    if isinstance(data, list):
        return [from_serializable_dict(item) for item in data]

    # Handle raw dictionaries (legacy support)
    if isinstance(data, dict):
        return {k: from_serializable_dict(v) for k, v in data.items()}

    return data
    
def is_empty_value(value: Any) -> bool:
    """Check if a value is effectively empty/null."""
    if value is None:
        return True
    if isinstance(value, (list, tuple, set, dict, str)) and len(value) == 0:
        return True
    return False

class BrowserConfig():
    """
    Configuration class for setting up a browser instance and its context in AsyncPlaywrightCrawlerStrategy.

    This class centralizes all parameters that affect browser and context creation. Instead of passing
    scattered keyword arguments, users can instantiate and modify this configuration object. The crawler
    code will then reference these settings to initialize the browser in a consistent, documented manner.
    """

    def __init__(
        self,
        browser_type: str = "chromium",
        headless: bool = True,
        use_managed_browser: bool = False,
        cdp_url: str = None,
        use_persistent_context: bool = False,
        user_data_dir: str = None,
        chrome_channel: str = "chromium",
        channel: str = "chromium",
        proxy: str = None,
        proxy_config: dict = None,
        viewport_width: int = 1080,
        viewport_height: int = 600,
        accept_downloads: bool = False,
        downloads_path: str = None,
        storage_state : Union[str, dict, None]=None,
        ignore_https_errors: bool = True,
        java_script_enabled: bool = True,
        sleep_on_close: bool = False,
        verbose: bool = True,
        cookies: list = None,
        headers: dict = None,
        user_agent: str = (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/116.0.0.0 Safari/537.36"
        ),
        user_agent_mode: str = "",
        user_agent_generator_config: dict = {},
        text_mode: bool = False,
        light_mode: bool = False,
        extra_args: list = None,
        debugging_port: int = 9222,
        host: str = "localhost",
    ):
        self.browser_type = browser_type
        self.headless = headless
        self.use_managed_browser = use_managed_browser
        self.cdp_url = cdp_url
        self.use_persistent_context = use_persistent_context
        self.user_data_dir = user_data_dir
        self.chrome_channel = chrome_channel or self.browser_type or "chromium"
        self.channel = channel or self.browser_type or "chromium"
        self.proxy = proxy
        self.proxy_config = proxy_config
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.accept_downloads = accept_downloads
        self.downloads_path = downloads_path
        self.storage_state = storage_state
        self.ignore_https_errors = ignore_https_errors
        self.java_script_enabled = java_script_enabled
        self.sleep_on_close = sleep_on_close
        self.verbose = verbose
        self.cookies = cookies or []
        self.headers = headers or {}
        self.user_agent = user_agent
        self.user_agent_mode = user_agent_mode
        self.user_agent_generator_config = user_agent_generator_config
        self.text_mode = text_mode
        self.light_mode = light_mode
        self.extra_args = extra_args or []
        self.debugging_port = debugging_port
        self.host = host

        # Validate and set user agent
        if self.user_agent_mode:
            try:
                ua_gen = ValidUAGenerator(**self.user_agent_generator_config)
                self.user_agent = ua_gen.get_ua()
            except Exception as e:
                logger.warning(f"Error generating user agent: {e}. Using default user agent.")

    def to_dict(self) -> Dict[str, Any]:
        """Convert the configuration to a dictionary."""
        return {
            "browser_type": self.browser_type,
            "headless": self.headless,
            "use_managed_browser": self.use_managed_browser,
            "cdp_url": self.cdp_url,
            "use_persistent_context": self.use_persistent_context,
            "user_data_dir": self.user_data_dir,
            "chrome_channel": self.chrome_channel,
            "channel": self.channel,
            "proxy": self.proxy,
            "proxy_config": self.proxy_config,
            "viewport_width": self.viewport_width,
            "viewport_height": self.viewport_height,
            "accept_downloads": self.accept_downloads,
            "downloads_path": self.downloads_path,
            "storage_state": self.storage_state,
            "ignore_https_errors": self.ignore_https_errors,
            "java_script_enabled": self.java_script_enabled,
            "sleep_on_close": self.sleep_on_close,
            "verbose": self.verbose,
            "cookies": self.cookies,
            "headers": self.headers,
            "user_agent": self.user_agent,
            "user_agent_mode": self.user_agent_mode,
            "user_agent_generator_config": self.user_agent_generator_config,
            "text_mode": self.text_mode,
            "light_mode": self.light_mode,
            "extra_args": self.extra_args,
            "debugging_port": self.debugging_port,
            "host": self.host,
        }

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'BrowserConfig':
        """Create a BrowserConfig from a dictionary."""
        return cls(**config_dict)

    @classmethod
    def from_env(cls) -> 'BrowserConfig':
        """Create a BrowserConfig from environment variables."""
        config = {}
        
        # Map environment variables to config parameters
        env_mapping = {
            "CRAWL4AI_BROWSER_TYPE": "browser_type",
            "CRAWL4AI_HEADLESS": "headless",
            "CRAWL4AI_VIEWPORT_WIDTH": "viewport_width",
            "CRAWL4AI_VIEWPORT_HEIGHT": "viewport_height",
            "CRAWL4AI_USER_AGENT": "user_agent",
            "CRAWL4AI_IGNORE_HTTPS_ERRORS": "ignore_https_errors",
            "CRAWL4AI_JAVASCRIPT_ENABLED": "java_script_enabled",
        }
        
        # Process environment variables
        for env_var, config_key in env_mapping.items():
            if env_var in os.environ:
                value = os.environ[env_var]
                
                # Convert value to appropriate type
                if value.lower() in ("true", "false"):
                    value = value.lower() == "true"
                elif value.isdigit():
                    value = int(value)
                
                config[config_key] = value
        
        return cls(**config)

class AsyncConfigs:
    """
    Configuration class for AsyncWebCrawler.
    
    This class centralizes all parameters for the AsyncWebCrawler, including
    browser configuration, content processing, caching, and more.
    """

    def __init__(
        self,
        # Content Processing Parameters
        word_count_threshold: int = MIN_WORD_THRESHOLD,
        markdown_generator: Optional[MarkdownGenerationStrategy] = None,
        only_text: bool = False,
        css_selector: str = None,
        excluded_tags: List[str] = None,
        excluded_selector: str = "",
        keep_data_attributes: bool = False,
        keep_attrs: List[str] = None,
        remove_forms: bool = False,
        prettiify: bool = False,
        parser_type: str = "lxml",
        scraping_strategy: Optional[ContentScrapingStrategy] = None,
        proxy_config: dict = None,
        # SSL Parameters
        fetch_ssl_certificate: bool = False,
        # Caching Parameters
        cache_mode: CacheMode = CacheMode.ENABLED,
        session_id: str = None,
        shared_data: dict = None,
        # Page Navigation and Timing Parameters
        wait_until: str = "domcontentloaded",
        page_timeout: int = PAGE_TIMEOUT,
        wait_for: str = None,
        wait_for_images: bool = False,
        delay_before_return_html: float = 0.1,
        mean_delay: float = 0.1,
        max_range: float = 0.3,
        semaphore_count: int = 5,
        # Page Interaction Parameters
        js_code: str = None,
        js_only: bool = False,
        ignore_body_visibility: bool = True,
        scan_full_page: bool = False,
        scroll_delay: float = 0.2,
        process_iframes: bool = False,
        remove_overlay_elements: bool = False,
        simulate_user: bool = False,
        override_navigator: bool = False,
        magic: bool = False,
        adjust_viewport_to_content: bool = False,
        # Media Handling Parameters
        screenshot: bool = False,
        screenshot_wait_for: str = None,
        screenshot_height_threshold: int = SCREENSHOT_HEIGHT_TRESHOLD,
        pdf: bool = False,
        image_description_min_word_threshold: int = IMAGE_DESCRIPTION_MIN_WORD_THRESHOLD,
        image_score_threshold: float = IMAGE_SCORE_THRESHOLD,
        exclude_external_images: bool = False,
        # Link and Domain Handling Parameters
        exclude_social_media_domains: List[str] = None,
        exclude_external_links: bool = False,
        exclude_social_media_links: bool = False,
        exclude_domains: List[str] = None,
        exclude_internal_links: bool = False,
        # Debugging and Logging Parameters
        verbose: bool = True,
        log_console: bool = False,
        # Streaming Parameters
        stream: bool = False,
        # URL Parameter
        url: str = None,
        # Robots.txt Handling Parameters
        check_robots_txt: bool = False,
        # User Agent Parameters
        user_agent: str = None,
        user_agent_mode: str = None,
        user_agent_generator_config: dict = None,
        # Crawler Parameters
        max_depth: int = 1,
        max_pages: int = 10,
        timeout: int = 60000,  # 60 seconds in milliseconds
        # Additional Parameters
        **kwargs
    ):
        # Content Processing Parameters
        self.word_count_threshold = word_count_threshold
        self.markdown_generator = markdown_generator
        self.only_text = only_text
        self.css_selector = css_selector
        self.excluded_tags = excluded_tags or []
        self.excluded_selector = excluded_selector
        self.keep_data_attributes = keep_data_attributes
        self.keep_attrs = keep_attrs or []
        self.remove_forms = remove_forms
        self.prettiify = prettiify
        self.parser_type = parser_type
        self.scraping_strategy = scraping_strategy or EnhancedWebScrapingStrategy()
        self.proxy_config = proxy_config

        # SSL Parameters
        self.fetch_ssl_certificate = fetch_ssl_certificate

        # Caching Parameters
        self.cache_mode = cache_mode
        self.session_id = session_id
        self.shared_data = shared_data

        # Page Navigation and Timing Parameters
        self.wait_until = wait_until
        self.page_timeout = page_timeout
        self.wait_for = wait_for
        self.wait_for_images = wait_for_images
        self.delay_before_return_html = delay_before_return_html
        self.mean_delay = mean_delay
        self.max_range = max_range
        self.semaphore_count = semaphore_count

        # Page Interaction Parameters
        self.js_code = js_code
        self.js_only = js_only
        self.ignore_body_visibility = ignore_body_visibility
        self.scan_full_page = scan_full_page
        self.scroll_delay = scroll_delay
        self.process_iframes = process_iframes
        self.remove_overlay_elements = remove_overlay_elements
        self.simulate_user = simulate_user
        self.override_navigator = override_navigator
        self.magic = magic
        self.adjust_viewport_to_content = adjust_viewport_to_content

        # Media Handling Parameters
        self.screenshot = screenshot
        self.screenshot_wait_for = screenshot_wait_for
        self.screenshot_height_threshold = screenshot_height_threshold
        self.pdf = pdf
        self.image_description_min_word_threshold = image_description_min_word_threshold
        self.image_score_threshold = image_score_threshold
        self.exclude_external_images = exclude_external_images

        # Link and Domain Handling Parameters
        self.exclude_social_media_domains = (
            exclude_social_media_domains or SOCIAL_MEDIA_DOMAINS
        )
        self.exclude_external_links = exclude_external_links
        self.exclude_social_media_links = exclude_social_media_links
        self.exclude_domains = exclude_domains or []
        self.exclude_internal_links = exclude_internal_links

        # Debugging and Logging Parameters
        self.verbose = verbose
        self.log_console = log_console

        # Streaming Parameters
        self.stream = stream
        
        # URL Parameter
        self.url = url

        # Robots.txt Handling Parameters
        self.check_robots_txt = check_robots_txt

        # User Agent Parameters
        self.user_agent = user_agent
        self.user_agent_mode = user_agent_mode
        self.user_agent_generator_config = user_agent_generator_config or {}
        
        # Crawler Parameters
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.timeout = timeout
        
        # Process additional parameters
        for key, value in kwargs.items():
            setattr(self, key, value)


    @staticmethod
    def from_kwargs(kwargs: dict) -> "AsyncConfigs":
        """Create an AsyncConfigs instance from keyword arguments."""
        return AsyncConfigs(
            # Content Processing Parameters
            word_count_threshold=kwargs.get("word_count_threshold", MIN_WORD_THRESHOLD),
            markdown_generator=kwargs.get("markdown_generator"),
            only_text=kwargs.get("only_text", False),
            css_selector=kwargs.get("css_selector"),
            excluded_tags=kwargs.get("excluded_tags", []),
            excluded_selector=kwargs.get("excluded_selector", ""),
            keep_data_attributes=kwargs.get("keep_data_attributes", False),
            keep_attrs=kwargs.get("keep_attrs", []),
            remove_forms=kwargs.get("remove_forms", False),
            prettiify=kwargs.get("prettiify", False),
            parser_type=kwargs.get("parser_type", "lxml"),
            scraping_strategy=kwargs.get("scraping_strategy"),
            proxy_config=kwargs.get("proxy_config"),
            # SSL Parameters
            fetch_ssl_certificate=kwargs.get("fetch_ssl_certificate", False),
            # Caching Parameters
            cache_mode=kwargs.get("cache_mode"),
            session_id=kwargs.get("session_id"),
            shared_data=kwargs.get("shared_data", None),
            # Page Navigation and Timing Parameters
            wait_until=kwargs.get("wait_until", "domcontentloaded"),
            page_timeout=kwargs.get("page_timeout", PAGE_TIMEOUT),
            wait_for=kwargs.get("wait_for"),
            wait_for_images=kwargs.get("wait_for_images", False),
            delay_before_return_html=kwargs.get("delay_before_return_html", 0.1),
            mean_delay=kwargs.get("mean_delay", 0.1),
            max_range=kwargs.get("max_range", 0.3),
            semaphore_count=kwargs.get("semaphore_count", 5),
            # Page Interaction Parameters
            js_code=kwargs.get("js_code"),
            js_only=kwargs.get("js_only", False),
            ignore_body_visibility=kwargs.get("ignore_body_visibility", True),
            scan_full_page=kwargs.get("scan_full_page", False),
            scroll_delay=kwargs.get("scroll_delay", 0.2),
            process_iframes=kwargs.get("process_iframes", False),
            remove_overlay_elements=kwargs.get("remove_overlay_elements", False),
            simulate_user=kwargs.get("simulate_user", False),
            override_navigator=kwargs.get("override_navigator", False),
            magic=kwargs.get("magic", False),
            adjust_viewport_to_content=kwargs.get("adjust_viewport_to_content", False),
            # Media Handling Parameters
            screenshot=kwargs.get("screenshot", False),
            screenshot_wait_for=kwargs.get("screenshot_wait_for"),
            screenshot_height_threshold=kwargs.get(
                "screenshot_height_threshold", SCREENSHOT_HEIGHT_TRESHOLD
            ),
            pdf=kwargs.get("pdf", False),
            image_description_min_word_threshold=kwargs.get(
                "image_description_min_word_threshold",
                IMAGE_DESCRIPTION_MIN_WORD_THRESHOLD,
            ),
            image_score_threshold=kwargs.get(
                "image_score_threshold", IMAGE_SCORE_THRESHOLD
            ),
            exclude_external_images=kwargs.get("exclude_external_images", False),
            # Link and Domain Handling Parameters
            exclude_social_media_domains=kwargs.get(
                "exclude_social_media_domains", SOCIAL_MEDIA_DOMAINS
            ),
            exclude_external_links=kwargs.get("exclude_external_links", False),
            exclude_social_media_links=kwargs.get("exclude_social_media_links", False),
            exclude_domains=kwargs.get("exclude_domains", []),
            exclude_internal_links=kwargs.get("exclude_internal_links", False),
            # Debugging and Logging Parameters
            verbose=kwargs.get("verbose", True),
            log_console=kwargs.get("log_console", False),
            # Streaming Parameters
            stream=kwargs.get("stream", False),
            url=kwargs.get("url"),
            check_robots_txt=kwargs.get("check_robots_txt", False),
            user_agent=kwargs.get("user_agent"),
            user_agent_mode=kwargs.get("user_agent_mode"),
            user_agent_generator_config=kwargs.get("user_agent_generator_config", {}),
            # Crawler Parameters
            max_depth=kwargs.get("max_depth", 1),
            max_pages=kwargs.get("max_pages", 10),
            timeout=kwargs.get("timeout", PAGE_TIMEOUT),
        )

    # Create a funciton returns dict of the object
    def dump(self) -> dict:
        # Serialize the object to a dictionary
        return to_serializable_dict(self)

    @staticmethod
    def load(data: dict) -> "AsyncConfigs":
        # Deserialize the object from a dictionary
        return from_serializable_dict(data) if data else AsyncConfigs()

    def to_dict(self):
        """Convert the configuration to a dictionary."""
        return {
            "word_count_threshold": self.word_count_threshold,
            "markdown_generator": self.markdown_generator,
            "only_text": self.only_text,
            "css_selector": self.css_selector,
            "excluded_tags": self.excluded_tags,
            "excluded_selector": self.excluded_selector,
            "keep_data_attributes": self.keep_data_attributes,
            "keep_attrs": self.keep_attrs,
            "remove_forms": self.remove_forms,
            "prettiify": self.prettiify,
            "parser_type": self.parser_type,
            "scraping_strategy": self.scraping_strategy,
            "proxy_config": self.proxy_config,
            "fetch_ssl_certificate": self.fetch_ssl_certificate,
            "cache_mode": self.cache_mode,
            "session_id": self.session_id,
            "shared_data": self.shared_data,
            "wait_until": self.wait_until,
            "page_timeout": self.page_timeout,
            "wait_for": self.wait_for,
            "wait_for_images": self.wait_for_images,
            "delay_before_return_html": self.delay_before_return_html,
            "mean_delay": self.mean_delay,
            "max_range": self.max_range,
            "semaphore_count": self.semaphore_count,
            "js_code": self.js_code,
            "js_only": self.js_only,
            "ignore_body_visibility": self.ignore_body_visibility,
            "scan_full_page": self.scan_full_page,
            "scroll_delay": self.scroll_delay,
            "process_iframes": self.process_iframes,
            "remove_overlay_elements": self.remove_overlay_elements,
            "simulate_user": self.simulate_user,
            "override_navigator": self.override_navigator,
            "magic": self.magic,
            "adjust_viewport_to_content": self.adjust_viewport_to_content,
            "screenshot": self.screenshot,
            "screenshot_wait_for": self.screenshot_wait_for,
            "screenshot_height_threshold": self.screenshot_height_threshold,
            "pdf": self.pdf,
            "image_description_min_word_threshold": self.image_description_min_word_threshold,
            "image_score_threshold": self.image_score_threshold,
            "exclude_external_images": self.exclude_external_images,
            "exclude_social_media_domains": self.exclude_social_media_domains,
            "exclude_external_links": self.exclude_external_links,
            "exclude_social_media_links": self.exclude_social_media_links,
            "exclude_domains": self.exclude_domains,
            "exclude_internal_links": self.exclude_internal_links,
            "verbose": self.verbose,
            "log_console": self.log_console,
            "stream": self.stream,
            "url": self.url,
            "check_robots_txt": self.check_robots_txt,
            "user_agent": self.user_agent,
            "user_agent_mode": self.user_agent_mode,
            "user_agent_generator_config": self.user_agent_generator_config,
            "max_depth": self.max_depth,
            "max_pages": self.max_pages,
            "timeout": self.timeout,
        }

    def clone(self, **kwargs):
        """Create a copy of this configuration with updated values.
        
        Args:
            **kwargs: Key-value pairs of configuration options to update
            
        Returns:
            AsyncConfigs: A new instance with the specified updates
            
        Example:
            ```python
            # Create a new config with streaming enabled
            stream_config = config.clone(stream=True)
            
            # Create a new config with multiple updates
            new_config = config.clone(
                stream=True,
                cache_mode=CacheMode.BYPASS,
                verbose=True
            )
            ```
        """
        config_dict = self.to_dict()
        config_dict.update(kwargs)
        return AsyncConfigs.from_kwargs(config_dict)
        
    @classmethod
    def from_env(cls) -> 'AsyncConfigs':
        """Create an AsyncConfigs from environment variables."""
        config = {}
        
        # Map environment variables to config parameters
        env_mapping = {
            "CRAWL4AI_WORD_COUNT_THRESHOLD": "word_count_threshold",
            "CRAWL4AI_PAGE_TIMEOUT": "page_timeout",
            "CRAWL4AI_MAX_DEPTH": "max_depth",
            "CRAWL4AI_MAX_PAGES": "max_pages",
            "CRAWL4AI_TIMEOUT": "timeout",
            "CRAWL4AI_SEMAPHORE_COUNT": "semaphore_count",
            "CRAWL4AI_CHECK_ROBOTS_TXT": "check_robots_txt",
        }
        
        # Process environment variables
        for env_var, config_key in env_mapping.items():
            if env_var in os.environ:
                value = os.environ[env_var]
                
                # Convert value to appropriate type
                if value.lower() in ("true", "false"):
                    value = value.lower() == "true"
                elif value.isdigit():
                    value = int(value)
                elif value.replace(".", "", 1).isdigit() and value.count(".") == 1:
                    value = float(value)
                
                config[config_key] = value
        
        return cls(**config)
