from crawl4ai import BrowserConfig, AsyncWebCrawler, CrawlerRunConfig, CacheMode
from crawl4ai.hub import BaseCrawler
from crawl4ai.utils import optimize_html, get_home_folder
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
from pathlib import Path
import json
import os
from typing import Dict


class GoogleSearchCrawler(BaseCrawler):
    __meta__ = {
        "version": "1.0.0",
        "tested_on": ["google.com/search*"],
        "rate_limit": "10 RPM",
        "description": "Crawls Google Search results (text + images)",
    }

    def __init__(self):
        super().__init__()
        self.js_script = (Path(__file__).parent /
                          "script.js").read_text()
