"""
Academic connector for Wiseflow.

This module provides a connector for academic sources like research papers and journals.
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

from core.plugins import PluginBase
from core.connectors import ConnectorBase, DataItem
from core.utils.general_utils import extract_and_convert_dates

logger = logging.getLogger(__name__)

class AcademicConnector(ConnectorBase):
    """Connector for academic sources."""
    
    name: str = "academic_connector"
    description: str = "Connector for academic sources like research papers and journals"
    source_type: str = "academic"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the academic connector."""
        super().__init__(config)
        self.api_key = self.config.get("api_key", os.environ.get("SEMANTIC_SCHOLAR_API_KEY", ""))
        self.api_base_url = "https://api.semanticscholar.org/graph/v1"
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
            headers = {"Accept": "application/json"}
            if self.api_key:
                headers["x-api-key"] = self.api_key
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session
    
    async def _close_session(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    async def collect(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """Collect data from academic sources."""
        params = params or {}
        
        try:
            # Create session
            await self._create_session()
            
            # Determine what to collect
            if "paper_id" in params:
                # Collect a specific paper
                paper_id = params["paper_id"]
                return await self._collect_paper(paper_id)
            elif "author_id" in params:
                # Collect papers by a specific author
                author_id = params["author_id"]
                return await self._collect_author_papers(author_id)
            elif "query" in params:
                # Search for papers
                query = params["query"]
                return await self._search_papers(query, params)
            else:
                logger.error("No paper_id, author_id, or query parameter provided for academic connector")
                return []
        finally:
            # Close session
            await self._close_session()
    
    async def _collect_paper(self, paper_id: str) -> List[DataItem]:
        """Collect information about a specific paper."""
        try:
            # Get paper information
            url = f"{self.api_base_url}/paper/{paper_id}?fields=paperId,externalIds,url,title,abstract,venue,year,referenceCount,citationCount,influentialCitationCount,isOpenAccess,fieldsOfStudy,authors,citations.limit(10),references.limit(10)"
            async with self.semaphore:
                async with self.session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to get paper info for {paper_id}: {response.status}")
                        return []
                    
                    paper_data = await response.json()
            
            # Create content
            title = paper_data.get("title", "")
            abstract = paper_data.get("abstract", "")
            
            content = f"# {title}\n\n"
            if abstract:
                content += f"## Abstract\n\n{abstract}\n\n"
            
            # Add authors
            authors = paper_data.get("authors", [])
            if authors:
                content += "## Authors\n\n"
                for author in authors:
                    content += f"- {author.get('name', '')}\n"
                content += "\n"
            
            # Add citations
            citations = paper_data.get("citations", [])
            if citations:
                content += "## Top Citations\n\n"
                for citation in citations:
                    citation_title = citation.get("title", "")
                    citation_year = citation.get("year", "")
                    content += f"- {citation_title} ({citation_year})\n"
                content += "\n"
            
            # Add references
            references = paper_data.get("references", [])
            if references:
                content += "## References\n\n"
                for reference in references:
                    reference_title = reference.get("title", "")
                    reference_year = reference.get("year", "")
                    content += f"- {reference_title} ({reference_year})\n"
                content += "\n"
            
            # Create metadata
            metadata = {
                "title": title,
                "abstract": abstract,
                "authors": [author.get("name", "") for author in authors],
                "venue": paper_data.get("venue", ""),
                "year": paper_data.get("year", ""),
                "reference_count": paper_data.get("referenceCount", 0),
                "citation_count": paper_data.get("citationCount", 0),
                "influential_citation_count": paper_data.get("influentialCitationCount", 0),
                "is_open_access": paper_data.get("isOpenAccess", False),
                "fields_of_study": paper_data.get("fieldsOfStudy", []),
                "external_ids": paper_data.get("externalIds", {})
            }
            
            # Create data item
            item = DataItem(
                source_id=f"academic_paper_{paper_id}",
                content=content,
                metadata=metadata,
                url=paper_data.get("url", ""),
                timestamp=datetime(int(paper_data.get("year", datetime.now().year)), 1, 1) if paper_data.get("year") else None,
                content_type="text/markdown",
                raw_data=paper_data
            )
            
            return [item]
        except Exception as e:
            logger.error(f"Error collecting paper {paper_id}: {e}")
            return []
    
    async def _collect_author_papers(self, author_id: str) -> List[DataItem]:
        """Collect papers by a specific author."""
        try:
            # Get author information
            url = f"{self.api_base_url}/author/{author_id}?fields=authorId,name,url,affiliations,paperCount,citationCount,hIndex"
            async with self.semaphore:
                async with self.session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to get author info for {author_id}: {response.status}")
                        return []
                    
                    author_data = await response.json()
            
            # Get author's papers
            papers_url = f"{self.api_base_url}/author/{author_id}/papers?fields=paperId,externalIds,url,title,abstract,venue,year,referenceCount,citationCount,influentialCitationCount,isOpenAccess,fieldsOfStudy&limit=100"
            async with self.semaphore:
                async with self.session.get(papers_url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to get papers for author {author_id}: {response.status}")
                        return []
                    
                    papers_data = await response.json()
                    papers = papers_data.get("data", [])
            
            # Create content
            author_name = author_data.get("name", "")
            affiliations = author_data.get("affiliations", [])
            
            content = f"# {author_name}\n\n"
            if affiliations:
                content += f"## Affiliations\n\n"
                for affiliation in affiliations:
                    content += f"- {affiliation}\n"
                content += "\n"
            
            content += f"## Papers ({len(papers)})\n\n"
            for paper in papers:
                title = paper.get("title", "")
                year = paper.get("year", "")
                venue = paper.get("venue", "")
                content += f"- {title} ({year}), {venue}\n"
            
            # Create metadata
            metadata = {
                "name": author_name,
                "affiliations": affiliations,
                "paper_count": author_data.get("paperCount", 0),
                "citation_count": author_data.get("citationCount", 0),
                "h_index": author_data.get("hIndex", 0),
                "papers": [{
                    "id": paper.get("paperId", ""),
                    "title": paper.get("title", ""),
                    "year": paper.get("year", ""),
                    "venue": paper.get("venue", ""),
                    "citation_count": paper.get("citationCount", 0)
                } for paper in papers]
            }
            
            # Create data item
            item = DataItem(
                source_id=f"academic_author_{author_id}",
                content=content,
                metadata=metadata,
                url=author_data.get("url", ""),
                content_type="text/markdown",
                raw_data={"author": author_data, "papers": papers}
            )
            
            return [item]
        except Exception as e:
            logger.error(f"Error collecting papers for author {author_id}: {e}")
            return []
    
    async def _search_papers(self, query: str, params: Dict[str, Any]) -> List[DataItem]:
        """Search for papers."""
        try:
            # Set up search parameters
            limit = params.get("limit", 10)
            offset = params.get("offset", 0)
            fields_of_study = params.get("fields_of_study", [])
            year_start = params.get("year_start")
            year_end = params.get("year_end")
            
            # Build query parameters
            query_params = f"query={quote_plus(query)}&limit={limit}&offset={offset}"
            if fields_of_study:
                query_params += f"&fieldsOfStudy={','.join(fields_of_study)}"
            if year_start:
                query_params += f"&year={year_start}-"
            if year_end:
                query_params += f"{year_end}" if year_start else f"&year=-{year_end}"
            
            # Search for papers
            url = f"{self.api_base_url}/paper/search?{query_params}&fields=paperId,externalIds,url,title,abstract,venue,year,referenceCount,citationCount,influentialCitationCount,isOpenAccess,fieldsOfStudy,authors"
            async with self.semaphore:
                async with self.session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to search papers with query {query}: {response.status}")
                        return []
                    
                    search_data = await response.json()
                    papers = search_data.get("data", [])
            
            # Process search results
            results = []
            for paper in papers:
                paper_id = paper.get("paperId", "")
                title = paper.get("title", "")
                abstract = paper.get("abstract", "")
                
                # Create content
                content = f"# {title}\n\n"
                if abstract:
                    content += f"## Abstract\n\n{abstract}\n\n"
                
                # Add authors
                authors = paper.get("authors", [])
                if authors:
                    content += "## Authors\n\n"
                    for author in authors:
                        content += f"- {author.get('name', '')}\n"
                    content += "\n"
                
                # Create metadata
                metadata = {
                    "title": title,
                    "abstract": abstract,
                    "authors": [author.get("name", "") for author in authors],
                    "venue": paper.get("venue", ""),
                    "year": paper.get("year", ""),
                    "reference_count": paper.get("referenceCount", 0),
                    "citation_count": paper.get("citationCount", 0),
                    "influential_citation_count": paper.get("influentialCitationCount", 0),
                    "is_open_access": paper.get("isOpenAccess", False),
                    "fields_of_study": paper.get("fieldsOfStudy", []),
                    "external_ids": paper.get("externalIds", {}),
                    "search_query": query
                }
                
                # Create data item
                item = DataItem(
                    source_id=f"academic_paper_{paper_id}",
                    content=content,
                    metadata=metadata,
                    url=paper.get("url", ""),
                    timestamp=datetime(int(paper.get("year", datetime.now().year)), 1, 1) if paper.get("year") else None,
                    content_type="text/markdown",
                    raw_data=paper
                )
                
                results.append(item)
            
            return results
        except Exception as e:
            logger.error(f"Error searching papers with query {query}: {e}")
            return []

