"""
Academic connector for Wiseflow.

This module provides a connector for academic sources like arXiv, PubMed, etc.
"""

from typing import Dict, List, Any, Optional, Union
import logging
import uuid
import asyncio
from datetime import datetime
import os
import re
import json
import tempfile
from urllib.parse import urlparse, quote_plus

import aiohttp
import feedparser
import arxiv
import requests
from bs4 import BeautifulSoup

from core.plugins.base import BasePlugin
from core.connectors import ConnectorBase, DataItem
from core.crawl4ai.processors.pdf import extract_text_from_pdf

logger = logging.getLogger(__name__)

class AcademicConnector(ConnectorBase):
    """Connector for academic sources."""
    
    name: str = "academic_connector"
    description: str = "Connector for academic sources like arXiv, PubMed, etc."
    source_type: str = "academic"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the academic connector."""
        super().__init__(config)
        self.semaphore = asyncio.Semaphore(self.config.get("concurrency", 5))
        self.session = None
        
    def initialize(self) -> bool:
        """Initialize the connector."""
        try:
            logger.info("Initialized academic connector")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize academic connector: {e}")
            return False
    
    async def _create_session(self):
        """Create an aiohttp session if it doesn't exist."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def _close_session(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    def collect(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """Synchronous collect method - delegates to async version."""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.collect_async(params))
    
    async def collect_async(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """Collect data from academic sources."""
        params = params or {}
        source_type = params.get("source_type", "arxiv")
        
        try:
            # Create session
            await self._create_session()
            
            if source_type == "arxiv":
                return await self._collect_from_arxiv(params)
            elif source_type == "pubmed":
                return await self._collect_from_pubmed(params)
            elif source_type == "semantic_scholar":
                return await self._collect_from_semantic_scholar(params)
            else:
                logger.error(f"Unsupported academic source type: {source_type}")
                return []
        finally:
            # Close session
            await self._close_session()
    
    async def _collect_from_arxiv(self, params: Dict[str, Any]) -> List[DataItem]:
        """Collect data from arXiv."""
        query = params.get("query", "")
        max_results = params.get("max_results", 10)
        sort_by = params.get("sort_by", "relevance")
        sort_order = params.get("sort_order", "descending")
        download_pdf = params.get("download_pdf", False)
        
        if not query:
            logger.error("No query provided for arXiv search")
            return []
        
        try:
            # Configure arXiv client
            client = arxiv.Client()
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=getattr(arxiv.SortCriterion, sort_by.upper()),
                sort_order=getattr(arxiv.SortOrder, sort_order.upper())
            )
            
            # Execute search
            results = []
            async with self.semaphore:
                for result in client.results(search):
                    # Extract metadata
                    metadata = {
                        "title": result.title,
                        "authors": [author.name for author in result.authors],
                        "categories": result.categories,
                        "journal_ref": result.journal_ref,
                        "doi": result.doi,
                        "primary_category": result.primary_category,
                        "published": result.published.isoformat() if result.published else None,
                        "updated": result.updated.isoformat() if result.updated else None,
                        "comment": result.comment,
                        "pdf_url": result.pdf_url
                    }
                    
                    # Extract content
                    content = result.summary
                    
                    # Download and extract PDF content if requested
                    if download_pdf and result.pdf_url:
                        try:
                            # Download PDF
                            async with self.session.get(result.pdf_url) as response:
                                if response.status == 200:
                                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                                        temp_file_path = temp_file.name
                                        temp_file.write(await response.read())
                                    
                                    # Extract text from PDF
                                    pdf_text = extract_text_from_pdf(temp_file_path)
                                    if pdf_text:
                                        content = pdf_text
                                    
                                    # Clean up
                                    os.unlink(temp_file_path)
                        except Exception as e:
                            logger.error(f"Error downloading PDF from {result.pdf_url}: {e}")
                    
                    # Create data item
                    item = DataItem(
                        source_id=f"arxiv_{result.entry_id.split('/')[-1]}",
                        content=content,
                        metadata=metadata,
                        url=result.entry_id,
                        timestamp=result.published,
                        content_type="text/plain",
                        raw_data=result
                    )
                    
                    results.append(item)
            
            logger.info(f"Collected {len(results)} items from arXiv")
            return results
            
        except Exception as e:
            logger.error(f"Error collecting data from arXiv: {e}")
            # Re-raise the exception to prevent silent failure
            raise
    
    async def _collect_from_pubmed(self, params: Dict[str, Any]) -> List[DataItem]:
        """Collect data from PubMed."""
        query = params.get("query", "")
        max_results = params.get("max_results", 10)
        
        if not query:
            logger.error("No query provided for PubMed search")
            return []
        
        try:
            # Construct PubMed API URLs
            esearch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={quote_plus(query)}&retmode=json&retmax={max_results}"
            
            # Search for IDs
            async with self.session.get(esearch_url) as response:
                if response.status != 200:
                    logger.error(f"PubMed search failed with status {response.status}")
                    return []
                
                search_data = await response.json()
                pmids = search_data.get("esearchresult", {}).get("idlist", [])
                
                if not pmids:
                    logger.info("No PubMed results found")
                    return []
            
            # Fetch details for each ID
            results = []
            for pmid in pmids:
                efetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pmid}&retmode=xml"
                
                async with self.semaphore:
                    async with self.session.get(efetch_url) as response:
                        if response.status != 200:
                            logger.error(f"PubMed fetch failed for ID {pmid} with status {response.status}")
                            continue
                        
                        xml_content = await response.text()
                        soup = BeautifulSoup(xml_content, "xml")
                        
                        # Extract article data
                        article = soup.find("PubmedArticle")
                        if not article:
                            continue
                        
                        # Extract title
                        title_elem = article.find("ArticleTitle")
                        title = title_elem.text if title_elem else ""
                        
                        # Extract abstract
                        abstract_elem = article.find("AbstractText")
                        abstract = abstract_elem.text if abstract_elem else ""
                        
                        # Extract authors
                        authors = []
                        author_list = article.find("AuthorList")
                        if author_list:
                            for author in author_list.find_all("Author"):
                                last_name = author.find("LastName")
                                fore_name = author.find("ForeName")
                                if last_name and fore_name:
                                    authors.append(f"{fore_name.text} {last_name.text}")
                                elif last_name:
                                    authors.append(last_name.text)
                        
                        # Extract journal info
                        journal_elem = article.find("Journal")
                        journal = ""
                        if journal_elem:
                            journal_title = journal_elem.find("Title")
                            journal = journal_title.text if journal_title else ""
                        
                        # Extract publication date
                        pub_date = None
                        pub_date_elem = article.find("PubDate")
                        if pub_date_elem:
                            year = pub_date_elem.find("Year")
                            month = pub_date_elem.find("Month")
                            day = pub_date_elem.find("Day")
                            
                            if year:
                                year_text = year.text
                                month_text = month.text if month else "01"
                                day_text = day.text if day else "01"
                                
                                try:
                                    pub_date = datetime.strptime(f"{year_text}-{month_text}-{day_text}", "%Y-%m-%d")
                                except ValueError:
                                    try:
                                        pub_date = datetime.strptime(f"{year_text}-{month_text}-01", "%Y-%m-%d")
                                    except ValueError:
                                        try:
                                            pub_date = datetime.strptime(f"{year_text}-01-01", "%Y-%m-%d")
                                        except ValueError:
                                            pass
                        
                        # Create metadata
                        metadata = {
                            "title": title,
                            "authors": authors,
                            "journal": journal,
                            "pmid": pmid,
                            "publication_date": pub_date.isoformat() if pub_date else None
                        }
                        
                        # Create data item
                        item = DataItem(
                            source_id=f"pubmed_{pmid}",
                            content=abstract,
                            metadata=metadata,
                            url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                            timestamp=pub_date,
                            content_type="text/plain"
                        )
                        
                        results.append(item)
            
            logger.info(f"Collected {len(results)} items from PubMed")
            return results
            
        except Exception as e:
            logger.error(f"Error collecting data from PubMed: {e}")
            # Re-raise the exception to prevent silent failure
            raise
    
    async def _collect_from_semantic_scholar(self, params: Dict[str, Any]) -> List[DataItem]:
        """Collect data from Semantic Scholar."""
        query = params.get("query", "")
        max_results = params.get("max_results", 10)
        api_key = params.get("api_key", self.config.get("semantic_scholar_api_key", ""))
        
        if not query:
            logger.error("No query provided for Semantic Scholar search")
            return []
        
        try:
            # Construct Semantic Scholar API URL
            search_url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={quote_plus(query)}&limit={max_results}&fields=title,abstract,authors,year,journal,url,venue,publicationDate,externalIds"
            
            headers = {}
            if api_key:
                headers["x-api-key"] = api_key
            
            # Execute search
            async with self.session.get(search_url, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"Semantic Scholar search failed with status {response.status}")
                    return []
                
                search_data = await response.json()
                papers = search_data.get("data", [])
                
                if not papers:
                    logger.info("No Semantic Scholar results found")
                    return []
            
            # Process results
            results = []
            for paper in papers:
                # Extract metadata
                paper_id = paper.get("paperId", "")
                title = paper.get("title", "")
                abstract = paper.get("abstract", "")
                authors = [author.get("name", "") for author in paper.get("authors", [])]
                year = paper.get("year")
                journal = paper.get("journal", {}).get("name", "")
                venue = paper.get("venue", "")
                url = paper.get("url", "")
                publication_date = paper.get("publicationDate")
                external_ids = paper.get("externalIds", {})
                
                # Create timestamp
                timestamp = None
                if publication_date:
                    try:
                        timestamp = datetime.strptime(publication_date, "%Y-%m-%d")
                    except ValueError:
                        pass
                
                # Create metadata
                metadata = {
                    "title": title,
                    "authors": authors,
                    "year": year,
                    "journal": journal,
                    "venue": venue,
                    "publication_date": publication_date,
                    "external_ids": external_ids
                }
                
                # Create data item
                item = DataItem(
                    source_id=f"semantic_scholar_{paper_id}",
                    content=abstract,
                    metadata=metadata,
                    url=url or f"https://www.semanticscholar.org/paper/{paper_id}",
                    timestamp=timestamp,
                    content_type="text/plain",
                    raw_data=paper
                )
                
                results.append(item)
            
            logger.info(f"Collected {len(results)} items from Semantic Scholar")
            return results
            
        except Exception as e:
            logger.error(f"Error collecting data from Semantic Scholar: {e}")
            # Re-raise the exception to prevent silent failure
            raise
