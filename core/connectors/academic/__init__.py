"""
Academic connector for Wiseflow.

This module provides a connector for academic sources like arXiv, PubMed, and DOI.
"""

from typing import Dict, List, Any, Optional, Union
import logging
import uuid
import asyncio
from datetime import datetime
import os
import re
import json
import urllib.parse
import xml.etree.ElementTree as ET
from io import BytesIO

from core.connectors import ConnectorBase, DataItem
import httpx

logger = logging.getLogger(__name__)

class AcademicConnector(ConnectorBase):
    """Connector for academic sources like arXiv, PubMed, and DOI."""
    
    name: str = "academic_connector"
    description: str = "Connector for academic sources like arXiv, PubMed, and DOI"
    source_type: str = "academic"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the academic connector."""
        super().__init__(config)
        self.concurrency = self.config.get("concurrency", 3)
        self.semaphore = asyncio.Semaphore(self.concurrency)
        self.client = None
        
        self.pubmed_api_key = self.config.get("pubmed_api_key", os.environ.get("PUBMED_API_KEY"))
        self.crossref_email = self.config.get("crossref_email", os.environ.get("CROSSREF_EMAIL"))
        
        self.arxiv_api_url = "http://export.arxiv.org/api/query"
        self.pubmed_api_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.crossref_api_url = "https://api.crossref.org/works"
        
    def initialize(self) -> bool:
        """Initialize the connector."""
        try:
            self.client = httpx.AsyncClient(
                timeout=self.config.get("timeout", 30),
                headers={
                    "User-Agent": f"Wiseflow-Academic-Connector ({self.crossref_email or 'no-email-provided'})"
                }
            )
            
            logger.info(f"Initialized academic connector with concurrency: {self.concurrency}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize academic connector: {e}")
            return False
    
    async def collect(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """Collect data from academic sources."""
        params = params or {}
        
        if not self.client and not self.initialize():
            return []
        
        source_type = params.get("source", "arxiv")
        
        if source_type == "arxiv":
            return await self._collect_arxiv(params)
        elif source_type == "pubmed":
            return await self._collect_pubmed(params)
        elif source_type == "doi":
            return await self._collect_doi(params)
        else:
            logger.error(f"Unknown academic source type: {source_type}")
            return []
    
    async def _collect_arxiv(self, params: Dict[str, Any]) -> List[DataItem]:
        """Collect data from arXiv."""
        arxiv_id = params.get("id")
        query = params.get("query")
        
        if not arxiv_id and not query:
            logger.error("No arXiv ID or search query provided")
            return []
        
        max_results = params.get("max_results", 10)
        include_abstract = params.get("include_abstract", True)
        include_pdf = params.get("include_pdf", False)
        
        results = []
        
        try:
            async with self.semaphore:
                request_params = {
                    "max_results": max_results,
                    "sortBy": "relevance" if query else "submittedDate",
                    "sortOrder": "descending"
                }
                
                if arxiv_id:
                    request_params["id_list"] = arxiv_id
                elif query:
                    request_params["search_query"] = query
                
                response = await self.client.get(self.arxiv_api_url, params=request_params)
                
                if response.status_code != 200:
                    logger.error(f"arXiv API error: {response.status_code} - {response.text}")
                    return []
                
                root = ET.fromstring(response.text)
                
                ns = {"atom": "http://www.w3.org/2005/Atom",
                      "arxiv": "http://arxiv.org/schemas/atom"}
                
                for entry in root.findall(".//atom:entry", ns):
                    try:
                        title = entry.find("atom:title", ns).text.strip()
                        summary = entry.find("atom:summary", ns).text.strip() if include_abstract else ""
                        published = entry.find("atom:published", ns).text
                        updated = entry.find("atom:updated", ns).text
                        
                        authors = []
                        for author in entry.findall(".//atom:author/atom:name", ns):
                            authors.append(author.text)
                        
                        arxiv_id = entry.find(".//arxiv:id", ns).text.split("/")[-1]
                        primary_category = entry.find(".//arxiv:primary_category", ns).attrib["term"]
                        
                        categories = []
                        for category in entry.findall(".//atom:category", ns):
                            categories.append(category.attrib["term"])
                        
                        pdf_url = None
                        html_url = None
                        for link in entry.findall(".//atom:link", ns):
                            if link.attrib.get("title") == "pdf":
                                pdf_url = link.attrib["href"]
                            elif link.attrib.get("rel") == "alternate":
                                html_url = link.attrib["href"]
                        
                        item = DataItem(
                            source_id=f"arxiv_{arxiv_id}",
                            content=summary,
                            metadata={
                                "type": "arxiv",
                                "arxiv_id": arxiv_id,
                                "title": title,
                                "authors": authors,
                                "published": published,
                                "updated": updated,
                                "primary_category": primary_category,
                                "categories": categories,
                                "pdf_url": pdf_url,
                                "html_url": html_url
                            },
                            url=html_url or f"https://arxiv.org/abs/{arxiv_id}",
                            content_type="text/plain",
                            timestamp=datetime.fromisoformat(published.replace("Z", "+00:00"))
                        )
                        results.append(item)
                        
                        if include_pdf and pdf_url:
                            pdf_content = await self._get_pdf_content(pdf_url)
                            if pdf_content:
                                pdf_item = DataItem(
                                    source_id=f"arxiv_pdf_{arxiv_id}",
                                    content=pdf_content,
                                    metadata={
                                        "type": "arxiv_pdf",
                                        "arxiv_id": arxiv_id,
                                        "title": title,
                                        "authors": authors
                                    },
                                    url=pdf_url,
                                    content_type="text/plain",
                                    timestamp=datetime.fromisoformat(published.replace("Z", "+00:00"))
                                )
                                results.append(pdf_item)
                    except Exception as e:
                        logger.error(f"Error processing arXiv entry: {e}")
        
        except Exception as e:
            logger.error(f"Error collecting arXiv data: {e}")
        
        logger.info(f"Collected {len(results)} items from arXiv")
        return results
    
    async def _collect_pubmed(self, params: Dict[str, Any]) -> List[DataItem]:
        """Collect data from PubMed."""
        pubmed_id = params.get("id")
        query = params.get("query")
        
        if not pubmed_id and not query:
            logger.error("No PubMed ID or search query provided")
            return []
        
        max_results = params.get("max_results", 10)
        include_abstract = params.get("include_abstract", True)
        include_full_text = params.get("include_full_text", False)
        
        results = []
        
        try:
            async with self.semaphore:
                if pubmed_id:
                    pubmed_ids = [pubmed_id]
                else:
                    search_params = {
                        "db": "pubmed",
                        "term": query,
                        "retmax": max_results,
                        "sort": "relevance"
                    }
                    
                    if self.pubmed_api_key:
                        search_params["api_key"] = self.pubmed_api_key
                    
                    search_url = f"{self.pubmed_api_url}/esearch.fcgi"
                    search_response = await self.client.get(search_url, params=search_params)
                    
                    if search_response.status_code != 200:
                        logger.error(f"PubMed search API error: {search_response.status_code} - {search_response.text}")
                        return []
                    
                    search_root = ET.fromstring(search_response.text)
                    pubmed_ids = [id_elem.text for id_elem in search_root.findall(".//Id")]
                    
                    if not pubmed_ids:
                        logger.warning(f"No PubMed results found for query: {query}")
                        return []
                
                for pmid in pubmed_ids:
                    fetch_params = {
                        "db": "pubmed",
                        "id": pmid,
                        "retmode": "xml"
                    }
                    
                    if self.pubmed_api_key:
                        fetch_params["api_key"] = self.pubmed_api_key
                    
                    fetch_url = f"{self.pubmed_api_url}/efetch.fcgi"
                    fetch_response = await self.client.get(fetch_url, params=fetch_params)
                    
                    if fetch_response.status_code != 200:
                        logger.error(f"PubMed fetch API error: {fetch_response.status_code} - {fetch_response.text}")
                        continue
                    
                    try:
                        article_root = ET.fromstring(fetch_response.text)
                        article = article_root.find(".//PubmedArticle")
                        
                        if article is None:
                            logger.warning(f"No article data found for PubMed ID: {pmid}")
                            continue
                        
                        article_meta = article.find(".//Article")
                        
                        title_elem = article_meta.find(".//ArticleTitle")
                        title = title_elem.text if title_elem is not None else "No title"
                        
                        journal_elem = article_meta.find(".//Journal/Title")
                        journal = journal_elem.text if journal_elem is not None else "Unknown Journal"
                        
                        pub_date_elem = article_meta.find(".//PubDate")
                        pub_year = pub_date_elem.find(".//Year")
                        pub_month = pub_date_elem.find(".//Month")
                        pub_day = pub_date_elem.find(".//Day")
                        
                        pub_date = ""
                        if pub_year is not None:
                            pub_date = pub_year.text
                            if pub_month is not None:
                                pub_date += f"-{pub_month.text.zfill(2) if pub_month.text.isdigit() else pub_month.text}"
                                if pub_day is not None:
                                    pub_date += f"-{pub_day.text.zfill(2)}"
                        
                        authors = []
                        author_list = article_meta.find(".//AuthorList")
                        if author_list is not None:
                            for author in author_list.findall(".//Author"):
                                last_name = author.find(".//LastName")
                                fore_name = author.find(".//ForeName")
                                
                                if last_name is not None and fore_name is not None:
                                    authors.append(f"{fore_name.text} {last_name.text}")
                                elif last_name is not None:
                                    authors.append(last_name.text)
                        
                        abstract_text = ""
                        if include_abstract:
                            abstract_elem = article_meta.find(".//Abstract")
                            if abstract_elem is not None:
                                for abstract_part in abstract_elem.findall(".//AbstractText"):
                                    label = abstract_part.get("Label")
                                    if label:
                                        abstract_text += f"{label}: {abstract_part.text}\n\n"
                                    else:
                                        abstract_text += f"{abstract_part.text}\n\n"
                        
                        doi = None
                        article_ids = article.findall(".//ArticleId")
                        for article_id in article_ids:
                            if article_id.get("IdType") == "doi":
                                doi = article_id.text
                                break
                        
                        item = DataItem(
                            source_id=f"pubmed_{pmid}",
                            content=abstract_text,
                            metadata={
                                "type": "pubmed",
                                "pubmed_id": pmid,
                                "title": title,
                                "journal": journal,
                                "publication_date": pub_date,
                                "authors": authors,
                                "doi": doi
                            },
                            url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                            content_type="text/plain",
                            timestamp=datetime.now()
                        )
                        results.append(item)
                        
                        if include_full_text and doi:
                            full_text_items = await self._collect_doi({"id": doi, "include_pdf": True})
                            results.extend(full_text_items)
                    
                    except Exception as e:
                        logger.error(f"Error processing PubMed article {pmid}: {e}")
        
        except Exception as e:
            logger.error(f"Error collecting PubMed data: {e}")
        
        logger.info(f"Collected {len(results)} items from PubMed")
        return results
    
    async def _collect_doi(self, params: Dict[str, Any]) -> List[DataItem]:
        """Collect data from a DOI."""
        doi = params.get("id")
        if not doi:
            logger.error("No DOI provided")
            return []
        
        include_pdf = params.get("include_pdf", False)
        
        results = []
        
        try:
            async with self.semaphore:
                doi = doi.strip()
                if doi.lower().startswith("doi:"):
                    doi = doi[4:].strip()
                
                crossref_url = f"{self.crossref_api_url}/{urllib.parse.quote_plus(doi)}"
                headers = {}
                if self.crossref_email:
                    headers["mailto"] = self.crossref_email
                
                response = await self.client.get(crossref_url, headers=headers)
                
                if response.status_code != 200:
                    logger.error(f"CrossRef API error: {response.status_code} - {response.text}")
                    return []
                
                data = response.json()
                if "message" not in data:
                    logger.error(f"Invalid CrossRef response for DOI {doi}")
                    return []
                
                message = data["message"]
                
                title = message.get("title", ["Unknown Title"])[0] if isinstance(message.get("title", []), list) else message.get("title", "Unknown Title")
                
                authors = []
                for author in message.get("author", []):
                    given = author.get("given", "")
                    family = author.get("family", "")
                    if given or family:
                        authors.append(f"{given} {family}".strip())
                
                container_title = message.get("container-title", ["Unknown Journal"])[0] if isinstance(message.get("container-title", []), list) else message.get("container-title", "Unknown Journal")
                
                pub_date = ""
                if "published" in message and "date-parts" in message["published"]:
                    date_parts = message["published"]["date-parts"][0]
                    if len(date_parts) >= 1:
                        pub_date = str(date_parts[0])
                        if len(date_parts) >= 2:
                            pub_date += f"-{str(date_parts[1]).zfill(2)}"
                            if len(date_parts) >= 3:
                                pub_date += f"-{str(date_parts[2]).zfill(2)}"
                
                url = message.get("URL", f"https://doi.org/{doi}")
                
                abstract = message.get("abstract", "")
                
                item = DataItem(
                    source_id=f"doi_{doi.replace('/', '_')}",
                    content=abstract,
                    metadata={
                        "type": "doi",
                        "doi": doi,
                        "title": title,
                        "authors": authors,
                        "container_title": container_title,
                        "publication_date": pub_date,
                        "publisher": message.get("publisher", "Unknown Publisher"),
                        "type": message.get("type", "Unknown Type")
                    },
                    url=url,
                    content_type="text/plain",
                    timestamp=datetime.now()
                )
                results.append(item)
                
                if include_pdf:
                    pdf_url = None
                    for link in message.get("link", []):
                        if link.get("content-type") == "application/pdf":
                            pdf_url = link.get("URL")
                            break
                    
                    if not pdf_url:
                        pdf_url = await self._find_open_access_pdf(doi)
                    
                    if pdf_url:
                        pdf_content = await self._get_pdf_content(pdf_url)
                        if pdf_content:
                            pdf_item = DataItem(
                                source_id=f"doi_pdf_{doi.replace('/', '_')}",
                                content=pdf_content,
                                metadata={
                                    "type": "doi_pdf",
                                    "doi": doi,
                                    "title": title,
                                    "authors": authors
                                },
                                url=pdf_url,
                                content_type="text/plain",
                                timestamp=datetime.now()
                            )
                            results.append(pdf_item)
        
        except Exception as e:
            logger.error(f"Error collecting DOI data: {e}")
        
        logger.info(f"Collected {len(results)} items from DOI {doi}")
        return results
    
    async def _get_pdf_content(self, pdf_url: str) -> Optional[str]:
        """Get and extract text content from a PDF."""
        try:
            response = await self.client.get(pdf_url)
            
            if response.status_code != 200:
                logger.error(f"Error downloading PDF: {response.status_code}")
                return None
            
            return f"[PDF content would be extracted here from {pdf_url}]"
        except Exception as e:
            logger.error(f"Error extracting PDF content: {e}")
            return None
    
    async def _find_open_access_pdf(self, doi: str) -> Optional[str]:
        """Find an open access PDF for a DOI using services like Unpaywall."""
        try:
            unpaywall_url = f"https://api.unpaywall.org/v2/{doi}?email={self.crossref_email or 'no-email-provided'}"
            response = await self.client.get(unpaywall_url)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("is_oa", False):
                    best_oa_location = data.get("best_oa_location", {})
                    if best_oa_location and "url_for_pdf" in best_oa_location:
                        return best_oa_location["url_for_pdf"]
                    elif best_oa_location and "url" in best_oa_location:
                        return best_oa_location["url"]
            
            return None
        except Exception as e:
            logger.error(f"Error finding open access PDF: {e}")
            return None
    
    async def close(self):
        """Close the connector and release resources."""
        if self.client:
            await self.client.aclose()
            self.client = None

