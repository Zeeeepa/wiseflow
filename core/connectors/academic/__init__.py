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

from core.plugins import PluginBase
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
    
    async def collect(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """Collect data from academic sources."""
        params = params or {}
        
        # Create a session for API requests
        self.session = aiohttp.ClientSession()
        
        try:
            # Determine what to collect
            if "arxiv_id" in params:
                # Collect data from a specific arXiv paper
                arxiv_id = params["arxiv_id"]
                return await self._collect_arxiv_paper(arxiv_id, params)
            elif "arxiv_search" in params:
                # Search for arXiv papers
                query = params["arxiv_search"]
                return await self._search_arxiv(query, params)
            elif "pubmed_id" in params:
                # Collect data from a specific PubMed paper
                pubmed_id = params["pubmed_id"]
                return await self._collect_pubmed_paper(pubmed_id, params)
            elif "pubmed_search" in params:
                # Search for PubMed papers
                query = params["pubmed_search"]
                return await self._search_pubmed(query, params)
            elif "doi" in params:
                # Collect data from a specific DOI
                doi = params["doi"]
                return await self._collect_doi(doi, params)
            else:
                logger.error("No arxiv_id, arxiv_search, pubmed_id, pubmed_search, or doi provided for academic connector")
                return []
        finally:
            # Close the session
            await self.session.close()
            self.session = None
    
    async def _collect_arxiv_paper(self, arxiv_id: str, params: Dict[str, Any]) -> List[DataItem]:
        """Collect data from a specific arXiv paper."""
        async with self.semaphore:
            try:
                # Clean the arXiv ID
                arxiv_id = arxiv_id.strip()
                if arxiv_id.startswith("http"):
                    # Extract ID from URL
                    match = re.search(r'arxiv\.org/(?:abs|pdf)/(\d+\.\d+)', arxiv_id)
                    if match:
                        arxiv_id = match.group(1)
                    else:
                        logger.error(f"Invalid arXiv URL: {arxiv_id}")
                        return []
                
                # Get paper details
                client = arxiv.Client()
                search = arxiv.Search(id_list=[arxiv_id])
                results = list(client.results(search))
                
                if not results:
                    logger.warning(f"No paper found with arXiv ID: {arxiv_id}")
                    return []
                
                paper = results[0]
                
                # Download PDF if requested
                pdf_text = None
                if params.get("include_pdf", True):
                    pdf_text = await self._download_arxiv_pdf(paper)
                
                # Create a data item for the paper
                item = DataItem(
                    source_id=f"arxiv_{arxiv_id}",
                    content=pdf_text or paper.summary,
                    metadata={
                        "arxiv_id": arxiv_id,
                        "title": paper.title,
                        "authors": [author.name for author in paper.authors],
                        "categories": paper.categories,
                        "published": paper.published.isoformat() if paper.published else None,
                        "updated": paper.updated.isoformat() if paper.updated else None,
                        "doi": paper.doi,
                        "journal_ref": paper.journal_ref,
                        "comment": paper.comment,
                        "primary_category": paper.primary_category,
                        "has_pdf": pdf_text is not None,
                        "type": "paper",
                        "source": "arxiv"
                    },
                    url=paper.entry_id,
                    content_type="text/plain",
                    timestamp=paper.published if paper.published else datetime.now()
                )
                
                return [item]
            except Exception as e:
                logger.error(f"Error collecting data from arXiv paper {arxiv_id}: {e}")
                return []
    
    async def _search_arxiv(self, query: str, params: Dict[str, Any]) -> List[DataItem]:
        """Search for arXiv papers."""
        try:
            # Set up search parameters
            max_results = params.get("max_results", 5)
            sort_by = params.get("sort_by", arxiv.SortCriterion.Relevance)
            sort_order = params.get("sort_order", arxiv.SortOrder.Descending)
            
            # Perform search
            client = arxiv.Client()
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=sort_by,
                sort_order=sort_order
            )
            results = list(client.results(search))
            
            if not results:
                logger.warning(f"No papers found for arXiv search: {query}")
                return []
            
            # Process each paper
            tasks = []
            for paper in results:
                arxiv_id = paper.get_short_id()
                tasks.append(self._collect_arxiv_paper(arxiv_id, params))
            
            # Gather results
            paper_results = await asyncio.gather(*tasks)
            
            # Flatten results
            flattened_results = []
            for items in paper_results:
                flattened_results.extend(items)
            
            return flattened_results
        except Exception as e:
            logger.error(f"Error searching arXiv papers with query {query}: {e}")
            return []
    
    async def _download_arxiv_pdf(self, paper: arxiv.Result) -> Optional[str]:
        """Download and extract text from an arXiv PDF."""
        try:
            # Create a temporary file to store the PDF
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Download the PDF
            paper.download_pdf(filename=temp_path)
            
            # Extract text from the PDF
            text = extract_text_from_pdf(temp_path)
            
            # Clean up the temporary file
            os.unlink(temp_path)
            
            return text
        except Exception as e:
            logger.error(f"Error downloading arXiv PDF for {paper.entry_id}: {e}")
            return None
    
    async def _collect_pubmed_paper(self, pubmed_id: str, params: Dict[str, Any]) -> List[DataItem]:
        """Collect data from a specific PubMed paper."""
        async with self.semaphore:
            try:
                # Clean the PubMed ID
                pubmed_id = pubmed_id.strip()
                if pubmed_id.startswith("http"):
                    # Extract ID from URL
                    match = re.search(r'pubmed/(\d+)', pubmed_id)
                    if match:
                        pubmed_id = match.group(1)
                    else:
                        logger.error(f"Invalid PubMed URL: {pubmed_id}")
                        return []
                
                # Get paper details from PubMed API
                url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pubmed_id}&retmode=xml"
                
                async with self.session.get(url) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to get PubMed paper {pubmed_id}: {response.status}")
                        return []
                    
                    xml_content = await response.text()
                
                # Parse XML
                soup = BeautifulSoup(xml_content, "xml")
                
                # Extract basic metadata
                article = soup.find("Article")
                if not article:
                    logger.warning(f"No article found in PubMed response for {pubmed_id}")
                    return []
                
                title = article.find("ArticleTitle")
                title_text = title.text if title else ""
                
                abstract = article.find("Abstract")
                abstract_text = ""
                if abstract:
                    abstract_parts = abstract.find_all("AbstractText")
                    for part in abstract_parts:
                        label = part.get("Label")
                        if label:
                            abstract_text += f"{label}: {part.text}\n\n"
                        else:
                            abstract_text += f"{part.text}\n\n"
                
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
                journal = article.find("Journal")
                journal_title = ""
                journal_issue = ""
                journal_volume = ""
                pub_date = ""
                
                if journal:
                    journal_title_elem = journal.find("Title")
                    journal_title = journal_title_elem.text if journal_title_elem else ""
                    
                    issue = journal.find("Issue")
                    journal_issue = issue.text if issue else ""
                    
                    volume = journal.find("Volume")
                    journal_volume = volume.text if volume else ""
                    
                    pub_date_elem = journal.find("PubDate")
                    if pub_date_elem:
                        year = pub_date_elem.find("Year")
                        month = pub_date_elem.find("Month")
                        day = pub_date_elem.find("Day")
                        
                        pub_date = ""
                        if year:
                            pub_date += year.text
                        if month:
                            pub_date += f"-{month.text}"
                        if day:
                            pub_date += f"-{day.text}"
                
                # Extract DOI
                article_id_list = soup.find("ArticleIdList")
                doi = ""
                if article_id_list:
                    for article_id in article_id_list.find_all("ArticleId"):
                        if article_id.get("IdType") == "doi":
                            doi = article_id.text
                
                # Create a data item for the paper
                item = DataItem(
                    source_id=f"pubmed_{pubmed_id}",
                    content=abstract_text,
                    metadata={
                        "pubmed_id": pubmed_id,
                        "title": title_text,
                        "authors": authors,
                        "journal": journal_title,
                        "journal_issue": journal_issue,
                        "journal_volume": journal_volume,
                        "published": pub_date,
                        "doi": doi,
                        "type": "paper",
                        "source": "pubmed"
                    },
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}/",
                    content_type="text/plain",
                    timestamp=datetime.now()  # Use current time as fallback
                )
                
                return [item]
            except Exception as e:
                logger.error(f"Error collecting data from PubMed paper {pubmed_id}: {e}")
                return []
    
    async def _search_pubmed(self, query: str, params: Dict[str, Any]) -> List[DataItem]:
        """Search for PubMed papers."""
        async with self.semaphore:
            try:
                # Set up search parameters
                max_results = params.get("max_results", 5)
                
                # Perform search
                search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={quote_plus(query)}&retmax={max_results}&retmode=json"
                
                async with self.session.get(search_url) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to search PubMed: {response.status}")
                        return []
                    
                    search_data = await response.json()
                
                # Extract IDs
                id_list = search_data.get("esearchresult", {}).get("idlist", [])
                
                if not id_list:
                    logger.warning(f"No papers found for PubMed search: {query}")
                    return []
                
                # Process each paper
                tasks = []
                for pubmed_id in id_list:
                    tasks.append(self._collect_pubmed_paper(pubmed_id, params))
                
                # Gather results
                paper_results = await asyncio.gather(*tasks)
                
                # Flatten results
                flattened_results = []
                for items in paper_results:
                    flattened_results.extend(items)
                
                return flattened_results
            except Exception as e:
                logger.error(f"Error searching PubMed papers with query {query}: {e}")
                return []
    
    async def _collect_doi(self, doi: str, params: Dict[str, Any]) -> List[DataItem]:
        """Collect data from a specific DOI."""
        async with self.semaphore:
            try:
                # Clean the DOI
                doi = doi.strip()
                if doi.startswith("http"):
                    # Extract DOI from URL
                    match = re.search(r'doi\.org/(.+)$', doi)
                    if match:
                        doi = match.group(1)
                    else:
                        logger.error(f"Invalid DOI URL: {doi}")
                        return []
                
                # Get paper details from DOI API
                url = f"https://doi.org/{doi}"
                headers = {
                    "Accept": "application/json"
                }
                
                async with self.session.get(url, headers=headers) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to get DOI {doi}: {response.status}")
                        return []
                    
                    data = await response.json()
                
                # Extract metadata
                title = data.get("title", "")
                if isinstance(title, list):
                    title = title[0] if title else ""
                
                authors = []
                for author in data.get("author", []):
                    given = author.get("given", "")
                    family = author.get("family", "")
                    if given and family:
                        authors.append(f"{given} {family}")
                    elif family:
                        authors.append(family)
                
                abstract = data.get("abstract", "")
                if isinstance(abstract, dict):
                    abstract = abstract.get("value", "")
                
                journal = data.get("container-title", "")
                if isinstance(journal, list):
                    journal = journal[0] if journal else ""
                
                published = data.get("published", {}).get("date-parts", [[]])[0]
                published_date = "-".join(map(str, published)) if published else ""
                
                # Create a data item for the paper
                item = DataItem(
                    source_id=f"doi_{doi}",
                    content=abstract,
                    metadata={
                        "doi": doi,
                        "title": title,
                        "authors": authors,
                        "journal": journal,
                        "published": published_date,
                        "type": "paper",
                        "source": "doi"
                    },
                    url=f"https://doi.org/{doi}",
                    content_type="text/plain",
                    timestamp=datetime.now()  # Use current time as fallback
                )
                
                return [item]
            except Exception as e:
                logger.error(f"Error collecting data from DOI {doi}: {e}")
                return []
