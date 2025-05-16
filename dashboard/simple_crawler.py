from gne import GeneralNewsExtractor
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from utils.general_utils import extract_and_convert_dates
import chardet
import logging
from typing import Tuple, Dict, Any, Union


extractor = GeneralNewsExtractor()
header = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/604.1 Edg/112.0.100.0'}


def simple_crawler(url: Union[str, Path], logger) -> Tuple[int, Dict[str, Any]]:
    """
    Return article information dict and flag, negative number is error, 0 is no result, 11 is success
    
    Args:
        url: URL or Path to crawl
        logger: Logger instance
        
    Returns:
        Tuple[int, Dict]: Status code and extracted content dictionary
    """
    try:
        with httpx.Client(timeout=30) as client:
            try:
                response = client.get(url, headers=header, timeout=30)
                response.raise_for_status()  # Raise exception for 4XX/5XX responses
                rawdata = response.content
            except httpx.HTTPStatusError as e:
                logger.warning(f"HTTP error when fetching {url}: {e.response.status_code} {e.response.reason_phrase}")
                return -7, {}
            except httpx.RequestError as e:
                logger.warning(f"Request error when fetching {url}: {str(e)}")
                return -7, {}
            
            # Detect encoding and decode content
            try:
                encoding_info = chardet.detect(rawdata)
                encoding = encoding_info['encoding'] if encoding_info['confidence'] > 0.5 else 'utf-8'
                text = rawdata.decode(encoding)
            except UnicodeDecodeError:
                # Fallback to utf-8 with error handling
                logger.warning(f"Encoding detection failed for {url}, falling back to utf-8 with errors='replace'")
                text = rawdata.decode('utf-8', errors='replace')
                
        # Extract content using GNE
        try:
            result = extractor.extract(text)
        except Exception as e:
            logger.error(f"GNE extraction error for {url}: {str(e)}")
            return 0, {}
    except Exception as e:
        logger.warning(f"Unexpected error when processing {url}: {str(e)}")
        return -7, {}

    if not result:
        logger.error(f"GNE returned empty result for {url}")
        return 0, {}

    # Validate extraction results
    if len(result.get('title', '')) < 4 or len(result.get('content', '')) < 24:
        logger.info(f"Extracted content too short for {url}: {result}")
        return 0, {}

    # Check for error pages
    error_indicators = [
        '服务器错误', '您访问的页面', '403', 'This website uses cookies', '出错了'
    ]
    
    for indicator in error_indicators:
        if (result.get('title', '').startswith(indicator) or 
            result.get('content', '').startswith(indicator)):
            logger.warning(f"Error page detected for {url}: {indicator}")
            return -7, {}

    # Process date
    try:
        date_str = extract_and_convert_dates(result.get('publish_time', ''))
        if date_str:
            result['publish_time'] = date_str
        else:
            result['publish_time'] = datetime.strftime(datetime.today(), "%Y%m%d")
    except Exception as e:
        logger.warning(f"Date extraction failed for {url}: {str(e)}")
        result['publish_time'] = datetime.strftime(datetime.today(), "%Y%m%d")

    # Extract meta description
    try:
        soup = BeautifulSoup(text, "html.parser")
        meta_description = soup.find("meta", {"name": "description"})
        if meta_description and meta_description.get("content"):
            result['abstract'] = meta_description["content"].strip()
        else:
            result['abstract'] = ''
    except Exception as e:
        logger.warning(f"Meta description extraction failed for {url}: {str(e)}")
        result['abstract'] = ''

    result['url'] = str(url)
    return 11, result
