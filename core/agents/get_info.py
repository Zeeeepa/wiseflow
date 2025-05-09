# -*- coding: utf-8 -*-
import asyncio
from loguru import logger
import os, re
import random
from typing import List, Dict, Any, Optional, Union, Tuple
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Fix import paths
from core.llms.openai_wrapper import openai_llm as llm
# from core.llms.siliconflow_wrapper import sfa_llm # or other llm wrapper
from core.utils.general_utils import normalize_url, url_pattern
from .get_info_prompts import *

# Define retryable exceptions
RETRYABLE_EXCEPTIONS = (
    Exception,  # Temporarily catch all exceptions for retry
)

common_file_exts = [
    'jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx', 'svg', 'm3u8',
    'mp4', 'mp3', 'wav', 'avi', 'mov', 'wmv', 'flv', 'webp', 'webm',
    'zip', 'rar', '7z', 'tar', 'gz', 'bz2',
    'txt', 'csv', 'xls', 'xlsx', 'ppt', 'pptx',
    'json', 'xml', 'yaml', 'yml', 'css', 'js', 'php', 'asp', 'jsp'
]
common_tlds = [
    '.com', '.cn', '.net', '.org', '.edu', '.gov', '.io', '.co',
    '.info', '.biz', '.me', '.tv', '.cc', '.xyz', '.app', '.dev',
    '.cloud', '.ai', '.tech', '.online', '.store', '.shop', '.site',
    '.top', '.vip', '.pro', '.ltd', '.group', '.team', '.work'
]

@retry(
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
async def pre_process(raw_markdown: str, base_url: str, used_img: list[str], 
                        recognized_img_cache: dict, existing_urls: set = set(), 
                        test_mode: bool = False) -> tuple[dict, list[str], list[str], dict]:

    link_dict = {}

    # for special url formate from craw4ai-de 0.4.247
    raw_markdown = re.sub(r'<javascript:.*?>', '<javascript:>', raw_markdown).strip()

    # 处理图片标记 ![alt](src)，使用非贪婪匹配并考虑嵌套括号的情况
    i_pattern = r'(!\[(.*?)\]\(((?:[^()]*|\([^()]*\))*)\))'
    matches = re.findall(i_pattern, raw_markdown, re.DOTALL)
    for _sec, alt, src in matches:
        # 替换为新格式 §alt||src§
        raw_markdown = raw_markdown.replace(_sec, f'§{alt}||{src}§', 1)

    async def check_url_text(text) -> tuple[int, str]:
        score = 0
        _valid_len = len(text.strip())

        # 找到所有[part0](part1)格式的片段，使用非贪婪匹配并考虑嵌套括号的情况
        link_pattern = r'(\[(.*?)\]\(((?:[^()]*|\([^()]*\))*)\))'
        matches = re.findall(link_pattern, text, re.DOTALL)
        for _sec, link_text, link_url in matches:
            # 存在“”嵌套情况，需要先提取出url
            _title = re.sub(url_pattern, '', link_url, re.DOTALL).strip()
            _title = _title.strip('"')
            link_text = link_text.strip()
            if _title and _title not in link_text:
                link_text = f"{_title} - {link_text}"
            """
            # for protecting_links model
            real_url_pattern = r'<(.*?)>'
            real_url = re.search(real_url_pattern, link_url, re.DOTALL)
            if real_url:
                _url = real_url.group(1).strip()
            else:
                _url = re.sub(quote_pattern, '', link_url, re.DOTALL).strip()
            """
            _url = re.findall(url_pattern, link_url)
            if not _url or _url[0].startswith(('#', 'javascript:')):
                text = text.replace(_sec, link_text, 1)
                continue
            score += 1
            _valid_len = _valid_len - len(_sec)
            url = normalize_url(_url[0], base_url)
            
            # 分离§§内的内容和后面的内容
            img_marker_pattern = r'§(.*?)\|\|(.*?)§'
            inner_matches = re.findall(img_marker_pattern, link_text, re.DOTALL)
            for alt, src in inner_matches:
                link_text = link_text.replace(f'§{alt}||{src}§', '')

            if not link_text and inner_matches:
                img_alt = inner_matches[0][0].strip()
                img_src = inner_matches[0][1].strip()
                if img_src and not img_src.startswith('#'):
                    img_src = normalize_url(img_src, base_url)
                    if not img_src:
                        link_text = img_alt
                    elif len(img_alt) > 2 or url in existing_urls:
                        _key = f"[img{len(link_dict)+1}]"
                        link_dict[_key] = img_src
                        link_text = img_alt
                    elif any(img_src.endswith(tld) or img_src.endswith(tld + '/') for tld in common_tlds):
                        _key = f"[img{len(link_dict)+1}]"
                        link_dict[_key] = img_src
                        link_text = img_alt
                    elif any(img_src.endswith(ext) for ext in common_file_exts if ext not in ['jpg', 'jpeg', 'png']):
                        _key = f"[img{len(link_dict)+1}]"
                        link_dict[_key] = img_src
                        link_text = img_alt
                    else:
                        if img_src not in recognized_img_cache:
                            recognized_img_cache[img_src] = await extract_info_from_img(img_src)
                        _key = f"[img{len(link_dict)+1}]"
                        link_dict[_key] = img_src
                        link_text = recognized_img_cache[img_src]
                else:
                    link_text = img_alt

            _key = f"[{len(link_dict)+1}]"
            link_dict[_key] = url
            text = text.replace(_sec, link_text + _key, 1)
 
        # 处理文本中的其他图片标记
        img_pattern = r'(§(.*?)\|\|(.*?)§)'
        matches = re.findall(img_pattern, text, re.DOTALL)
        remained_text = re.sub(img_pattern, '', text, re.DOTALL).strip()
        remained_text_len = len(remained_text)
        for _sec, alt, src in matches:
            if not src or src.startswith('#') or src not in used_img:
                text = text.replace(_sec, alt, 1)
                continue
            img_src = normalize_url(src, base_url)
            if not img_src:
                text = text.replace(_sec, alt, 1)
            elif remained_text_len > 5 or len(alt) > 2:
                _key = f"[{len(link_dict)+1}]"
                link_dict[_key] = img_src
                text = text.replace(_sec, alt + _key, 1)
            elif any(img_src.endswith(tld) or img_src.endswith(tld + '/') for tld in common_tlds):
                _key = f"[{len(link_dict)+1}]"
                link_dict[_key] = img_src
                text = text.replace(_sec, alt + _key, 1)
            elif any(img_src.endswith(ext) for ext in common_file_exts if ext not in ['jpg', 'jpeg', 'png']):
                _key = f"[{len(link_dict)+1}]"
                link_dict[_key] = img_src
                text = text.replace(_sec, alt + _key, 1)
            else:
                if img_src not in recognized_img_cache:
                    recognized_img_cache[img_src] = await extract_info_from_img(img_src)
                _key = f"[{len(link_dict)+1}]"
                link_dict[_key] = img_src
                text = text.replace(_sec, recognized_img_cache[img_src] + _key, 1)

        # 处理文本中的"野 url"，使用更精确的正则表达式
        matches = re.findall(url_pattern, text)
        for url in matches:
            url = normalize_url(url, base_url)
            _key = f"[{len(link_dict)+1}]"
            link_dict[_key] = url
            text = text.replace(url, _key, 1)
            score += 1
            _valid_len = _valid_len - len(url)
        
        if score == 0:
            # 如果没有任何链接，则认为这是一段纯文本
            return 999, text
        # 统计换行符数量
        newline_count = text.count(' * ')
        score += newline_count
        ratio = _valid_len/score if score != 0 else 999

        return ratio, text

    sections = raw_markdown.split('# ') # use '# ' to avoid # in url
    if len(sections) > 2:
        _sec = sections[0]
        # 更新正则表达式以处理嵌套括号
        section_remain = re.sub(r'\[(.*?)\]\(((?:[^()]*|\([^()]*\))*)\)', '', _sec, re.DOTALL).strip()
        section_remain_len = len(section_remain)
        # 更新正则表达式以处理嵌套括号
        total_links = len(re.findall(r'\[(.*?)\]\(((?:[^()]*|\([^()]*\))*)\)', _sec, re.DOTALL))
        ratio = total_links / section_remain_len if section_remain_len != 0 else 1
        if ratio > 0.05:
            if test_mode:
                print('\033[31mthis is a navigation section, will be removed\033[0m')
                print(ratio, '\n')
                print(section_remain)
                print('-' * 50)
            sections = sections[1:]
        _sec = sections[-1]
        # 更新正则表达式以处理嵌套括号
        section_remain = re.sub(r'\[(.*?)\]\(((?:[^()]*|\([^()]*\))*)\)', '', _sec, re.DOTALL).strip()
        section_remain_len = len(section_remain)
        if section_remain_len < 198:
            if test_mode:
                print('\033[31mthis is a footer section, will be removed\n\033[0m')
                print(section_remain_len)
                print(section_remain)
                print('-' * 50)
            sections = sections[:-1]

    links_parts = []
    contents = []
    for section in sections:
        ratio, text = await check_url_text(section)
        if ratio < 90:
            if test_mode:
                print('\033[32mthis is a links part\033[0m')
                print(ratio, '\n')
                print(text)
                print('-' * 50)
            if len(text) > 30000:
                lines = text.split('\n')
                _text = ''
                while lines:
                    l = lines.pop(0)
                    _text = f'{_text}{l}\n'
                    if len(_text) > 29000 or len(lines) == 0:
                        links_parts.append(_text)
                        _text = ''
            else:
                links_parts.append(text)
        else:
            if test_mode:
                print('\033[34mthis is a content part\033[0m')
                print(ratio, '\n')
                print(text)
                print('-' * 50)
            if len(text) > 30000:
                lines = text.split('\n')
                _text = ''
                while lines:
                    l = lines.pop(0)
                    _text = f'{_text}{l}\n'
                    if len(_text) > 29000 or len(lines) == 0:
                        contents.append(_text)
                        _text = ''
            else:
                contents.append(text)
    return link_dict, links_parts, contents, recognized_img_cache


vl_model = os.environ.get("VL_MODEL", "")
if not vl_model:
    print("VL_MODEL not set, will skip extracting info from img, some info may be lost!")


@retry(
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
async def extract_info_from_img(url: str) -> str:
    """
    Extract information from an image with retry logic.
    
    Args:
        url: URL of the image
        
    Returns:
        str: Extracted information
    """
    try:
        if not vl_model:
            return '\u00a7to_be_recognized_by_visual_llm\u00a7'

        llm_output = await llm([{"role": "user",
            "content": [{"type": "image_url", "image_url": {"url": url, "detail": "high"}},
            {"type": "text", "text": "\u63d0\u53d6\u56fe\u7247\u4e2d\u7684\u6240\u6709\u6587\u5b57\uff0c\u5982\u679c\u56fe\u7247\u4e0d\u5305\u542b\u6587\u5b57\u6216\u8005\u6587\u5b57\u5f88\u5c11\u6216\u8005\u4f60\u5224\u65ad\u56fe\u7247\u4ec5\u662f\u7f51\u7ad9logo\u3001\u5546\u6807\u3001\u56fe\u6807\u7b49\uff0c\u5219\u8f93\u51faNA\u3002\u6ce8\u610f\u8bf7\u4ec5\u8f93\u51fa\u63d0\u53d6\u51fa\u7684\u6587\u5b57\uff0c\u4e0d\u8981\u8f93\u51fa\u522b\u7684\u4efb\u4f55\u5185\u5bb9\u3002"}]}],
            model=vl_model)

        return llm_output
    except Exception as e:
        logger.error(f"Error extracting info from image: {e}")
        return '\u00a7error_extracting_image_info\u00a7'


@retry(
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
async def get_author_and_publish_date(text: str, model: str, test_mode: bool = False, _logger: logger = None) -> tuple[str, str]:
    """
    Get author and publish date from text with retry logic.
    
    Args:
        text: Text to extract from
        model: Model to use
        test_mode: Whether to run in test mode
        _logger: Optional logger
        
    Returns:
        Tuple containing author and publish date
    """
    try:
        if not text:
            return "", ""

        if len(text) > 2048:
            text = f'{text[:2048]}......'

        content = f'<text>\n{text}\n</text>\n\n{get_ap_suffix}'
        result = await llm([{'role': 'system', 'content': get_ap_system}, {'role': 'user', 'content': content}],
                                model=model, temperature=0.1)
                         
        if test_mode:
            print(f"llm output:\n {result}")
            
        author = re.findall(r'<source>(.*?)</source>', result, re.DOTALL)
        publish_date = re.findall(r'<publish_date>(.*?)</publish_date>', result, re.DOTALL)

        author = author[-1] if author else ''
        publish_date = publish_date[-1] if publish_date else ''

        if not author or not publish_date:
            if _logger:
                _logger.warning(f"failed to parse from llm output: {result}")

        return author if author.lower() != 'na' else '', publish_date
    except Exception as e:
        if _logger:
            _logger.error(f"Error getting author and publish date: {e}")
        return "", ""


@retry(
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
async def get_more_related_urls(texts: list[str], link_dict: dict, prompts: list[str], test_mode: bool = False,
                                _logger: logger = None) -> set:
    """
    Get more related URLs with retry logic.
    
    Args:
        texts: List of text strings
        link_dict: Dictionary of links
        prompts: List of prompts
        test_mode: Whether to run in test mode
        _logger: Optional logger
        
    Returns:
        Set of related URLs
    """
    try:
        sys_prompt, suffix, model = prompts
        text_batch = ''
        cache = set()
        while texts:
            t = texts.pop(0)
            text_batch = f'{text_batch}{t}\n\n'
            if len(text_batch) > 2048 or len(texts) == 0:
                content = f'<text>\n{text_batch}</text>\n\n{suffix}'
                result = await llm(
                        [{'role': 'system', 'content': sys_prompt}, {'role': 'user', 'content': content}],
                        model=model, temperature=0.1)

                if test_mode:
                    print(f"llm output:\n {result}")

                result = re.findall(r'<answer>(.*?)</answer>', result, re.DOTALL)
                if result:
                    links = re.findall(r'\[\d+]', result[-1])
                    for link in links:
                        if link not in link_dict or link not in text_batch:
                            if _logger:
                                _logger.warning(f"model generating hallucination:\n{link}\n{result[-1]}\n{text_batch}")
                            if test_mode:
                                print(f"model hallucination:\n{link}\n{result[-1]}\n{text_batch}")
                            continue
                        cache.add(link)
                text_batch = ''

        more_urls = set()
        for mark in cache:
            url = link_dict[mark]
            has_common_ext = any(url.endswith(ext) for ext in common_file_exts)
            has_common_tld = any(url.endswith(tld) or url.endswith(tld + '/') for tld in common_tlds)
            if has_common_ext or has_common_tld:
                continue
            more_urls.add(url)
        
        return more_urls
    except Exception as e:
        if _logger:
            _logger.error(f"Error getting more related URLs: {e}")
        return set()


@retry(
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
async def get_info(texts: list[str], link_dict: dict, prompts: list[str], author: str, publish_date: str,
                   test_mode: bool = False, _logger: logger = None) -> list[dict]:
    """
    Get information from texts with retry logic.
    
    Args:
        texts: List of text strings
        link_dict: Dictionary of links
        prompts: List of prompts
        author: Author name
        publish_date: Publish date
        test_mode: Whether to run in test mode
        _logger: Optional logger
        
    Returns:
        List of information dictionaries
    """
    try:
        sys_prompt, suffix, model = prompts

        if test_mode:
            info_pre_fix = ''
        else:
            info_pre_fix = f"//{author} {publish_date}//"
        
        texts = [t for t in texts if t.strip()]
        if not texts:
            return []

        batches = []
        text_batch = f'Author: {author}\nPublish Date: {publish_date}\n'
        while texts:
            t = texts.pop(0)
            text_batch = f'{text_batch}{t}# '
            if len(text_batch) > 9999 or len(texts) == 0:
                content = f'<text>\n{text_batch}</text>\n\n{suffix}'
                batches.append(content)
                text_batch = f'Author: {author}\nPublish Date: {publish_date}\n'

        # Process batches with error handling
        results = []
        for content in batches:
            try:
                res = await llm([{'role': 'system', 'content': sys_prompt}, {'role': 'user', 'content': content}], 
                               model=model, temperature=0.1)
                results.append(res)
            except Exception as e:
                if _logger:
                    _logger.error(f"Error processing batch: {e}")
                # Continue with other batches

        final = []
        for res in results:
            if test_mode:
                print(f"llm output:\n {res}")
            res = re.findall(r'<summary>(.*?)</summary>', res, re.DOTALL)
            if not res:
                if _logger:
                    _logger.warning("model lightly hallucination: contains no summary tag")
                if test_mode:
                    print("model lightly hallucination: contains no summary tag")
                continue
            res = res[-1].strip()
            if _logger:
                _logger.debug(res)
            if test_mode:
                print(res)
            if len(res) < 3:
                continue

            url_tags = re.findall(r'\[\d+]', res)
            refences = {}
            for _tag in url_tags:
                if _tag in link_dict:
                    refences[_tag] = link_dict[_tag]
                else:
                    if _logger and link_dict: # avoid warning when link_dict is empty(search engine)
                        _logger.warning(f"model hallucination: {res} \ncontains {_tag} which is not in link_dict")
                    if test_mode:
                        print(f"model hallucination: {res} \ncontains {_tag} which is not in link_dict")
                    res = res.replace(_tag, '')
            final.append({'content': f"{info_pre_fix}{res}", 'references': refences})
        
        return final
    except Exception as e:
        if _logger:
            _logger.error(f"Error getting info: {e}")
        return []
