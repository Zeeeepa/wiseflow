from urllib.parse import urlparse
import os
import re
from typing import Optional, Dict, Any, Union

# Import improved logging and error handling
from core.utils.logging_config import logger, get_logger, log_execution
from core.utils.error_handling import handle_exceptions, WiseflowError, ValidationError


@log_execution(level="DEBUG")
@handle_exceptions(error_types=[Exception], log_error=True, default=False)
def isURL(string: str) -> bool:
    """
    Check if a string is a valid URL.
    
    Args:
        string: String to check
        
    Returns:
        True if the string is a valid URL, False otherwise
    """
    if not string or not isinstance(string, str):
        return False
        
    if string.startswith("www."):
        string = f"https://{string}"
    result = urlparse(string)
    return result.scheme != '' and result.netloc != ''


@log_execution(level="DEBUG")
@handle_exceptions(error_types=[Exception], log_error=True, default=False)
def isChinesePunctuation(char: str) -> bool:
    """
    Check if a character is Chinese punctuation.
    
    Args:
        char: Character to check
        
    Returns:
        True if the character is Chinese punctuation, False otherwise
    """
    if not char or not isinstance(char, str) or len(char) != 1:
        return False
        
    # Define the Unicode encoding range for Chinese punctuation marks
    chinese_punctuations = set(range(0x3000, 0x303F)) | set(range(0xFF00, 0xFFEF))
    # Check if the character is within the above range
    return ord(char) in chinese_punctuations


@log_execution(level="DEBUG")
@handle_exceptions(error_types=[Exception], log_error=True, default=False)
def is_chinese(string: str) -> bool:
    """
    Check if a string is mostly Chinese.
    
    Args:
        string: String to check
        
    Returns:
        True if the string is mostly Chinese, False otherwise
    """
    if not string or not isinstance(string, str):
        return False
        
    pattern = re.compile(r'[^\u4e00-\u9fa5]')
    non_chinese_count = len(pattern.findall(string))
    # It is easy to misjudge strictly according to the number of bytes less than half.
    # English words account for a large number of bytes, and there are punctuation marks, etc
    return (non_chinese_count/len(string)) < 0.68


@log_execution(level="DEBUG")
@handle_exceptions(error_types=[Exception], log_error=True, default=None)
def extract_and_convert_dates(input_string: str) -> Optional[str]:
    """
    Extract and convert dates from a string to a standardized format.
    
    Args:
        input_string: String to extract dates from
        
    Returns:
        Standardized date string or None if no date found
    """
    if not isinstance(input_string, str) or len(input_string) < 8:
        return None
        
    # Define regular expressions that match different date formats
    patterns = [
        r'(\d{4})-(\d{2})-(\d{2})',  # YYYY-MM-DD
        r'(\d{4})/(\d{2})/(\d{2})',  # YYYY/MM/DD
        r'(\d{4})\.(\d{2})\.(\d{2})',  # YYYY.MM.DD
        r'(\d{4})\\(\d{2})\\(\d{2})',  # YYYY\\MM\\DD
        r'(\d{4})(\d{2})(\d{2})',  # YYYYMMDD
        r'(\d{4})\u5e74(\d{2})\u6708(\d{2})\u65e5'  # YYYY年MM月DD日
    ]

    matches = []
    for pattern in patterns:
        matches = re.findall(pattern, input_string)
        if matches:
            break
    if matches:
        return '-'.join(matches[0])
    return None


@log_execution(level="DEBUG")
@handle_exceptions(error_types=[Exception], log_error=True, default="INFO")
def get_logger_level() -> str:
    """
    Get the logger level from environment variables.
    
    Returns:
        Logger level string
    """
    level_map = {
        'silly': 'CRITICAL',
        'verbose': 'DEBUG',
        'info': 'INFO',
        'warn': 'WARNING',
        'error': 'ERROR',
    }
    level: str = os.environ.get('WS_LOG', 'info').lower()
    if level not in level_map:
        raise ValidationError(
            'WiseFlow LOG should support the values of `silly`, '
            '`verbose`, `info`, `warn`, `error`',
            {"provided_level": level}
        )
    return level_map.get(level, 'INFO')
