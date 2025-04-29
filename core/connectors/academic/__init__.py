"""
Academic connector for Wiseflow.

This module provides a connector for academic sources like arXiv, Google Scholar, etc.
"""

from typing import Dict, List, Any, Optional, Union
import logging
import uuid
import asyncio
from datetime import datetime
import os
import re
import json
import aiohttp
from urllib.parse import quote_plus

from core.connectors import ConnectorBase, DataItem
from core.utils.general_utils import extract_and_convert_dates

logger = logging.getLogger(__name__)

class AcademicConnector(ConnectorBase):
    """Connector for academic sources."""
    
    name: str = "academic_connector"
    description: str = "Connector for academic sources like arXiv, Google Scholar, etc."
    source_type: str = "academic"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the academic connector."""
        super().__init__(config)
        self.config = config or {}
        self.semaphore = asyncio.Semaphore(self.config.get("concurrency", 3))
        
    def initialize(self) -> bool:
        """Initialize the connector."""
        try:
            # Set up API keys if provided
            if self.config.get("arxiv_api_key"):
                logger.info("Using provided arXiv API key")
            if self.config.get("scholar_api_key"):
                logger.info("Using provided Google Scholar API key")
                
            logger.info(f"Initialized academic connector with config: {self.config}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize academic connector: {e}")
            return False
    
    async def collect(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """Collect data from academic sources."""
        params = params or {}
        
        # Get search parameters
        query = params.get("query", "")
        sources = params.get("sources", ["arxiv"])
        max_results = params.get("max_results", 10)
        
        if not query:
            logger.error("No query provided for academic connector")
            return []
        
        # Process sources concurrently
        tasks = []
        for source in sources:
            if source == "arxiv":
                tasks.append(self._search_arxiv(query, max_results))
            elif source == "scholar":
                tasks.append(self._search_scholar(query, max_results))
            else:
                logger.warning(f"Unknown academic source: {source}")
        
        results = []
        if tasks:
            # Gather all results
            source_results = await asyncio.gather(*tasks)
            for items in source_results:
                results.extend(items)
        
        logger.info(f"Collected {len(results)} items from academic sources")
        return results
    
    async def _search_arxiv(self, query: str, max_results: int = 10) -> List[DataItem]:
        """Search arXiv for academic papers."""
        async with self.semaphore:
            try:
                logger.info(f"Searching arXiv for: {query}")
                
                # Construct arXiv API URL
                encoded_query = quote_plus(query)
                url = f"http://export.arxiv.org/api/query?search_query=all:{encoded_query}&start=0&max_results={max_results}"
                
                # Fetch results
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status != 200:
                            logger.error(f"arXiv API error: {response.status}")
                            return []
                        
                        # Parse XML response
                        xml_content = await response.text()
                        
                        # Extract entries (simplified parsing for demonstration)
                        entries = []
                        entry_pattern = r"<entry>(.*?)</entry>"
                        for entry_match in re.finditer(entry_pattern, xml_content, re.DOTALL):
                            entry_text = entry_match.group(1)
                            
                            # Extract title
                            title_match = re.search(r"<title>(.*?)</title>", entry_text, re.DOTALL)
                            title = title_match.group(1).strip() if title_match else "Unknown Title"
                            
                            # Extract authors
                            authors = []
                            author_pattern = r"<author>(.*?)</author>"
                            for author_match in re.finditer(author_pattern, entry_text, re.DOTALL):
                                author_text = author_match.group(1)
                                name_match = re.search(r"<name>(.*?)</name>", author_text)
                                if name_match:
                                    authors.append(name_match.group(1).strip())
                            
                            # Extract summary
                            summary_match = re.search(r"<summary>(.*?)</summary>", entry_text, re.DOTALL)
                            summary = summary_match.group(1).strip() if summary_match else ""
                            
                            # Extract link
                            link_match = re.search(r'<link title="pdf" href="(.*?)"', entry_text)
                            link = link_match.group(1) if link_match else ""
                            
                            # Extract published date
                            published_match = re.search(r"<published>(.*?)</published>", entry_text)
                            published = published_match.group(1) if published_match else ""
                            
                            entries.append({
                                "title": title,
                                "authors": authors,
                                "summary": summary,
                                "link": link,
                                "published": published
                            })
                
                # Convert to DataItems
                results = []
                for entry in entries:
                    # Create content from paper details
                    content = f"# {entry['title']}\n\n"
                    content += f"**Authors**: {', '.join(entry['authors'])}\n\n"
                    content += f"**Published**: {entry['published']}\n\n"
                    content += f"**Summary**:\n{entry['summary']}\n\n"
                    content += f"**Link**: {entry['link']}\n"
                    
                    # Create metadata
                    metadata = {
                        "title": entry["title"],
                        "authors": entry["authors"],
                        "published_date": extract_and_convert_dates(entry["published"]),
                        "source": "arxiv",
                        "url": entry["link"]
                    }
                    
                    # Create DataItem
                    item = DataItem(
                        source_id=f"arxiv_{uuid.uuid4().hex[:8]}",
                        content=content,
                        metadata=metadata,
                        url=entry["link"],
                        content_type="text/markdown",
                        language="en"
                    )
                    
                    results.append(item)
                
                return results
            except Exception as e:
                logger.error(f"Error searching arXiv: {e}")
                return []
    
    async def _search_scholar(self, query: str, max_results: int = 10) -> List[DataItem]:
        """Search Google Scholar for academic papers."""
        async with self.semaphore:
            try:
                logger.info(f"Searching Google Scholar for: {query}")
                
                # Note: Google Scholar doesn't have an official API
                # This is a placeholder implementation
                # In a real implementation, you would use a third-party service or scraping
                
                # Simulate results for demonstration
                simulated_results = [
                    {
                        "title": f"Simulated Scholar Paper on {query} - 1",
                        "authors": ["Author One", "Author Two"],
                        "abstract": f"This is a simulated abstract for a paper about {query}. It contains important findings and methodologies.",
                        "url": f"https://example.com/scholar/paper1",
                        "published": "2023-01-15"
                    },
                    {
                        "title": f"Simulated Scholar Paper on {query} - 2",
                        "authors": ["Author Three", "Author Four"],
                        "abstract": f"Another simulated abstract discussing {query} from a different perspective.",
                        "url": f"https://example.com/scholar/paper2",
                        "published": "2022-11-30"
                    }
                ]
                
                # Convert to DataItems
                results = []
                for paper in simulated_results[:max_results]:
                    # Create content from paper details
                    content = f"# {paper['title']}\n\n"
                    content += f"**Authors**: {', '.join(paper['authors'])}\n\n"
                    content += f"**Published**: {paper['published']}\n\n"
                    content += f"**Abstract**:\n{paper['abstract']}\n\n"
                    content += f"**Link**: {paper['url']}\n"
                    
                    # Create metadata
                    metadata = {
                        "title": paper["title"],
                        "authors": paper["authors"],
                        "published_date": extract_and_convert_dates(paper["published"]),
                        "source": "google_scholar",
                        "url": paper["url"]
                    }
                    
                    # Create DataItem
                    item = DataItem(
                        source_id=f"scholar_{uuid.uuid4().hex[:8]}",
                        content=content,
                        metadata=metadata,
                        url=paper["url"],
                        content_type="text/markdown",
                        language="en"
                    )
                    
                    results.append(item)
                
                return results
            except Exception as e:
                logger.error(f"Error searching Google Scholar: {e}")
                return []
