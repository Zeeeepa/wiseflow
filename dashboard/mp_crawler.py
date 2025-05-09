import httpx
from bs4 import BeautifulSoup
from datetime import datetime
import re
import asyncio
from typing import Tuple, Dict, Any, Optional


header = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/604.1 Edg/112.0.100.0'}


def mp_crawler(url: str, logger) -> Tuple[int, Dict[str, Any]]:
    """
    Crawl a WeChat MP article and extract its content.
    
    Args:
        url: The URL of the WeChat MP article
        logger: Logger instance for logging
        
    Returns:
        Tuple[int, Dict]: Status code and extracted content dictionary
            Status codes:
                11: Success
                0: No result
                -5: Not a WeChat MP URL
                -7: Error fetching or parsing content
    """
    if not url.startswith('https://mp.weixin.qq.com') and not url.startswith('http://mp.weixin.qq.com'):
        logger.warning(f'{url} is not a mp url, you should not use this function')
        return -5, {}

    url = url.replace("http://", "https://", 1)

    try:
        with httpx.Client(timeout=30) as client:
            response = client.get(url, headers=header, timeout=30)
            response.raise_for_status()  # Raise exception for 4XX/5XX responses
    except httpx.HTTPStatusError as e:
        logger.warning(f"HTTP error when fetching {url}: {e.response.status_code} {e.response.reason_phrase}")
        return -7, {}
    except httpx.RequestError as e:
        logger.warning(f"Request error when fetching {url}: {str(e)}")
        return -7, {}
    except Exception as e:
        logger.warning(f"Unexpected error when fetching {url}: {str(e)}")
        return -7, {}

    try:
        soup = BeautifulSoup(response.text, 'html.parser')

        # Get the original release date first
        pattern = r"var createTime = '(\d{4}-\d{2}-\d{2}) \d{2}:\d{2}'"
        match = re.search(pattern, response.text)

        if match:
            date_only = match.group(1)
            publish_time = date_only.replace('-', '')
        else:
            publish_time = datetime.strftime(datetime.today(), "%Y%m%d")

        # Get description content from <meta> tag
        meta_description = soup.find('meta', attrs={'name': 'description'})
        summary = meta_description['content'].strip() if meta_description else ''
        
        # Find the content container
        card_info = soup.find('div', id='img-content')
        
        # Try different selectors for title and author
        rich_media_title = None
        profile_nickname = None
        
        # Try to find title
        title_selectors = [
            ('h1', {'id': 'activity-name'}),
            ('h1', {'class_': 'rich_media_title'})
        ]
        
        for tag, attrs in title_selectors:
            element = soup.find(tag, attrs)
            if element:
                rich_media_title = element.text.strip()
                break
                
        # Try to find author/nickname
        author_selectors = [
            ('strong', {'class_': 'profile_nickname'}, card_info),
            ('div', {'class_': 'wx_follow_nickname'}, soup)
        ]
        
        for tag, attrs, parent in author_selectors:
            if parent:
                element = parent.find(tag, attrs)
                if element:
                    profile_nickname = element.text.strip()
                    break
    except Exception as e:
        logger.warning(f"Error parsing MP content: {url}\n{e}")
        return -7, {}

    if not rich_media_title or not profile_nickname:
        logger.warning(f"Failed to extract title or author from {url}")
        return -7, {}

    # Parse text and image links within the content interval
    try:
        texts = []
        images = set()
        content_area = soup.find('div', id='js_content')
        
        if content_area:
            # Extract text
            for section in content_area.find_all(['section', 'p'], recursive=False):
                text = section.get_text(separator=' ', strip=True)
                if text and text not in texts:
                    texts.append(text)

            # Extract images
            for img in content_area.find_all('img', class_='rich_pages wxw-img'):
                img_src = img.get('data-src') or img.get('src')
                if img_src:
                    images.add(img_src)
                    
            # Also try to find images without the specific classes
            if not images:
                for img in content_area.find_all('img'):
                    img_src = img.get('data-src') or img.get('src')
                    if img_src and not img_src.startswith('data:'):
                        images.add(img_src)
                        
            cleaned_texts = [t for t in texts if t.strip()]
            content = '\n'.join(cleaned_texts)
        else:
            logger.warning(f"Failed to find content area for {url}")
            return 0, {}
            
        if content:
            content = f"({profile_nickname} 文章){content}"
        else:
            # If the content does not have it, but the summary has it, it means that it is an mp of the picture sharing type.
            # At this time, you can use the summary as the content.
            content = f"({profile_nickname} 文章){summary}"

        # Get links to images in meta property="og:image" and meta property="twitter:image"
        og_image = soup.find('meta', property='og:image')
        twitter_image = soup.find('meta', property='twitter:image')
        if og_image and og_image.get('content'):
            images.add(og_image['content'])
        if twitter_image and twitter_image.get('content'):
            images.add(twitter_image['content'])

        if rich_media_title == summary or not summary:
            abstract = ''
        else:
            abstract = f"({profile_nickname} 文章){rich_media_title}——{summary}"

        return 11, {
            'title': rich_media_title,
            'author': profile_nickname,
            'publish_time': publish_time,
            'abstract': abstract,
            'content': content,
            'images': list(images),
            'url': url,
        }
    except Exception as e:
        logger.warning(f"Error extracting content from {url}: {str(e)}")
        return -7, {}
