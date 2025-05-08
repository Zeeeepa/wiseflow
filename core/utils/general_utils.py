from urllib.parse import urlparse, urljoin
import os
import re
import logging
from pathlib import Path
from typing import Optional

# Import our new logging configuration
from core.utils.logging_config import logger, get_logger

url_pattern = r'((?:https?://|www\.)[-A-Za-z0-9+&@#/%?=~_|!:,.;]*[-A-Za-z0-9+&@#/%=~_|])'

def normalize_url(url: str, base_url: str) -> str:
    """
    Normalize a URL, ensuring it has the correct format.
    
    Args:
        url: URL to normalize
        base_url: Base URL for relative URLs
        
    Returns:
        Normalized URL
    """
    url = url.strip()
    if url.startswith(('www.', 'WWW.')):
        _url = f"https://{url}"
    elif url.startswith('/www.'):
        _url = f"https:/{url}"
    elif url.startswith("//"):
        _url = f"https:{url}"
    elif url.startswith(('http://', 'https://')):
        _url = url
    elif url.startswith('http:/'):
        _url = f"http://{url[6:]}"
    elif url.startswith('https:/'):
        _url = f"https://{url[7:]}"
    else:
        _url = urljoin(base_url, url)
    
    _ss = _url.split('//')
    if len(_ss) == 2:
        return '//'.join(_ss)
    else:
        return _ss[0] + '//' + '/'.join(_ss[1:])


def isURL(string: str) -> bool:
    """
    Check if a string is a valid URL.
    
    Args:
        string: String to check
        
    Returns:
        True if the string is a valid URL, False otherwise
    """
    if string.startswith("www."):
        string = f"https://{string}"
    result = urlparse(string)
    return result.scheme != '' and result.netloc != ''


def extract_urls(text: str) -> set:
    """
    Extract all URLs from a text.
    
    Args:
        text: Text to extract URLs from
        
    Returns:
        Set of extracted URLs
    """
    # Regular expression to match http, https, and www URLs
    urls = re.findall(url_pattern, text)
    # urls = {quote(url.rstrip('/'), safe='/:?=&') for url in urls}
    cleaned_urls = set()
    for url in urls:
        if url.startswith("www."):
            url = f"https://{url}"
        parsed_url = urlparse(url)
        if not parsed_url.netloc:
            continue
        # remove hash fragment
        if not parsed_url.scheme:
            # just try https
            cleaned_urls.add(f"https://{parsed_url.netloc}{parsed_url.path}{parsed_url.params}{parsed_url.query}")
        else:
            cleaned_urls.add(
                f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}{parsed_url.params}{parsed_url.query}")
    return cleaned_urls


def isChinesePunctuation(char: str) -> bool:
    """
    Check if a character is Chinese punctuation.
    
    Args:
        char: Character to check
        
    Returns:
        True if the character is Chinese punctuation, False otherwise
    """
    # Define the Unicode encoding range for Chinese punctuation marks
    chinese_punctuations = set(range(0x3000, 0x303F)) | set(range(0xFF00, 0xFFEF))
    # Check if the character is within the above range
    return ord(char) in chinese_punctuations


def is_chinese(string: str) -> bool:
    """
    Check if a string is mostly Chinese.
    
    Args:
        string: String to check
        
    Returns:
        True if the string is mostly Chinese, False otherwise
    """
    pattern = re.compile(r'[^\u4e00-\u9fa5]')
    non_chinese_count = len(pattern.findall(string))
    # It is easy to misjudge strictly according to the number of bytes less than half.
    # English words account for a large number of bytes, and there are punctuation marks, etc
    return (non_chinese_count/len(string)) < 0.68


def extract_and_convert_dates(input_string: str) -> str:
    """
    Extract and convert dates from a string to a standardized format.
    
    Args:
        input_string: String to extract dates from
        
    Returns:
        Standardized date string or empty string if no date found
    """
    # Define patterns for different date formats
    if not isinstance(input_string, str) or len(input_string) < 8:
        return ''

    patterns = [
        r'(\d{4})-(\d{2})-(\d{2})',  # YYYY-MM-DD
        r'(\d{4})/(\d{2})/(\d{2})',  # YYYY/MM/DD
        r'(\d{4})\.(\d{2})\.(\d{2})',  # YYYY.MM.DD
        r'(\d{4})\\(\d{2})\\(\d{2})',  # YYYY\\MM\\DD
        r'(\d{4})(\d{2})(\d{2})',  # YYYYMMDD
        r'(\d{4})年(\d{2})月(\d{2})日'  # YYYY年MM月DD日
    ]

    matches = []
    for pattern in patterns:
        matches = re.findall(pattern, input_string)
        if matches:
            break
    if matches:
        return '-'.join(matches[0])
    return ''


def get_logger(logger_name: str, logger_file_path: str = None):
    """
    Get a logger instance with the given name.
    
    This function is maintained for backward compatibility.
    New code should use core.utils.logging_config.get_logger instead.
    
    Args:
        logger_name: Logger name
        logger_file_path: Path to log file directory (optional)
        
    Returns:
        Logger instance
    """
    # Use our new logging system
    return get_logger(logger_name)


"""
def compare_phrase_with_list(target_phrase, phrase_list, threshold):

    Compare the similarity of a target phrase to each phrase in the phrase list.

    : Param target_phrase: target phrase (str)
    : Param phrase_list: list of str
    : param threshold: similarity threshold (float)
    : Return: list of phrases that satisfy the similarity condition (list of str)

    if not target_phrase:
        return []  # The target phrase is empty, and the empty list is returned directly.

    # Preprocessing: Segmentation of the target phrase and each phrase in the phrase list
    target_tokens = set(jieba.lcut(target_phrase))
    tokenized_phrases = {phrase: set(jieba.lcut(phrase)) for phrase in phrase_list}

    similar_phrases = [phrase for phrase, tokens in tokenized_phrases.items()
                       if len(target_tokens & tokens) / min(len(target_tokens), len(tokens)) > threshold]

    return similar_phrases
"""
