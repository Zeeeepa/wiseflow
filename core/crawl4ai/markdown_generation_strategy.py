from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple, List
import logging
import re
import traceback
from urllib.parse import urljoin

from .models import MarkdownGenerationResult
from .html2text import CustomHTML2Text
from .errors import ParsingError

# Pre-compile the regex pattern
LINK_PATTERN = re.compile(r'!?\[([^]]+)]\(([^)]+?)(?:\s+"([^"]*)")?\)')


def fast_urljoin(base: str, url: str) -> str:
    """Fast URL joining for common cases."""
    if not url:
        return base
        
    if url.startswith(("http://", "https://", "mailto:", "//")):
        return url
    if url.startswith("/"):
        # Handle absolute paths
        if base.endswith("/"):
            return base[:-1] + url
        return base + url
    return urljoin(base, url)


class MarkdownGenerationStrategy(ABC):
    """Abstract base class for markdown generation strategies."""

    def __init__(
        self,
        options: Optional[Dict[str, Any]] = None,
        verbose: bool = False,
        logger: Optional[logging.Logger] = None,
    ):
        self.options = options or {}
        self.verbose = verbose
        self.logger = logger or logging.getLogger(__name__)

    @abstractmethod
    def generate_markdown(
        self,
        cleaned_html: str,
        base_url: str = "",
        html2text_options: Optional[Dict[str, Any]] = None,
        citations: bool = False,
        **kwargs,
    ) -> MarkdownGenerationResult:
        """Generate markdown from cleaned HTML."""
        pass


class DefaultMarkdownGenerator(MarkdownGenerationStrategy):
    """
    Default implementation of markdown generation strategy.

    How it works:
    1. Generate raw markdown from cleaned HTML.
    2. Convert links to citations.
    3. Generate fit markdown if content filter is provided.
    4. Return MarkdownGenerationResult.

    Args:
        options (Optional[Dict[str, Any]]): Additional options for markdown generation. Defaults to None.
        verbose (bool): Whether to enable verbose logging. Defaults to False.
        logger (Optional[logging.Logger]): Logger instance. Defaults to None.

    Returns:
        MarkdownGenerationResult: Result containing raw markdown, fit markdown, fit HTML, and references markdown.
    """

    def __init__(
        self,
        options: Optional[Dict[str, Any]] = None,
        verbose: bool = False,
        logger: Optional[logging.Logger] = None,
    ):
        super().__init__(options, verbose, logger)

    def convert_links_to_citations(
        self, markdown: str, base_url: str = ""
    ) -> Tuple[str, str]:
        """
        Convert links in markdown to citations.

        How it works:
        1. Find all links in the markdown.
        2. Convert links to citations.
        3. Return converted markdown and references markdown.

        Note:
        This function uses a regex pattern to find links in markdown.

        Args:
            markdown (str): Markdown text.
            base_url (str): Base URL for URL joins.

        Returns:
            Tuple[str, str]: Converted markdown and references markdown.
            
        Raises:
            ParsingError: If there's an error converting links to citations.
        """
        if not markdown:
            return "", ""
            
        try:
            link_map = {}
            url_cache = {}  # Cache for URL joins
            parts = []
            last_end = 0
            counter = 1

            for match in LINK_PATTERN.finditer(markdown):
                parts.append(markdown[last_end : match.start()])
                text, url, title = match.groups()
                
                # Handle None values
                text = text or ""
                url = url or ""
                title = title or ""

                # Use cached URL if available, otherwise compute and cache
                if base_url and not url.startswith(("http://", "https://", "mailto:")):
                    if url not in url_cache:
                        url_cache[url] = fast_urljoin(base_url, url)
                    url = url_cache[url]

                if url not in link_map:
                    desc = []
                    if title:
                        desc.append(title)
                    if text and text != title:
                        desc.append(text)
                    link_map[url] = (counter, ": " + " - ".join(desc) if desc else "")
                    counter += 1

                num = link_map[url][0]
                parts.append(
                    f"{text}⟨{num}⟩"
                    if not match.group(0).startswith("!")
                    else f"![{text}⟨{num}⟩]"
                )
                last_end = match.end()

            parts.append(markdown[last_end:])
            converted_text = "".join(parts)

            # Pre-build reference strings
            references = ["## References\n\n"] if link_map else []
            references.extend(
                f"⟨{num}⟩ {url}{desc}\n"
                for url, (num, desc) in sorted(link_map.items(), key=lambda x: x[1][0])
            )

            return converted_text, "".join(references)
        except Exception as e:
            self.logger.error(f"Error converting links to citations: {e}")
            traceback.print_exc()
            raise ParsingError("Failed to convert links to citations", original_error=e)

    def generate_markdown(
        self,
        cleaned_html: str,
        base_url: str = "",
        html2text_options: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None,
        citations: bool = False,
        **kwargs,
    ) -> MarkdownGenerationResult:
        """
        Generate markdown with citations from cleaned HTML.

        How it works:
        1. Generate raw markdown from cleaned HTML.
        2. Convert links to citations.
        3. Generate fit markdown if content filter is provided.
        4. Return MarkdownGenerationResult.

        Args:
            cleaned_html (str): Cleaned HTML content.
            base_url (str): Base URL for URL joins.
            html2text_options (Optional[Dict[str, Any]]): HTML2Text options.
            options (Optional[Dict[str, Any]]): Additional options for markdown generation.
            citations (bool): Whether to generate citations.
            **kwargs: Additional keyword arguments.

        Returns:
            MarkdownGenerationResult: Result containing raw markdown, fit markdown, fit HTML, and references markdown.
            
        Raises:
            ParsingError: If there's an error generating markdown.
        """
        try:
            # Initialize HTML2Text with default options for better conversion
            h = CustomHTML2Text(baseurl=base_url)
            default_options = {
                "body_width": 0,  # Disable text wrapping
                "ignore_emphasis": False,
                "ignore_links": False,
                "ignore_images": False,
                "protect_links": False,
                "single_line_break": True,
                "mark_code": True,
                "escape_snob": False,
            }

            # Update with custom options if provided
            if html2text_options:
                default_options.update(html2text_options)
            elif options:
                default_options.update(options)
            elif self.options:
                default_options.update(self.options)

            h.update_params(**default_options)

            # Ensure we have valid input
            if not cleaned_html:
                cleaned_html = ""
            elif not isinstance(cleaned_html, str):
                cleaned_html = str(cleaned_html)

            # Generate raw markdown
            try:
                raw_markdown = h.handle(cleaned_html)
            except Exception as e:
                self.logger.error(f"Error converting HTML to markdown: {e}")
                traceback.print_exc()
                raise ParsingError("Failed to convert HTML to markdown", original_error=e)

            # Clean up code blocks
            raw_markdown = raw_markdown.replace("    ```", "```")

            # Convert links to citations
            markdown_with_citations: str = ""
            references_markdown: str = ""
            if citations:
                try:
                    (
                        markdown_with_citations,
                        references_markdown,
                    ) = self.convert_links_to_citations(raw_markdown, base_url)
                except ParsingError as e:
                    self.logger.error(f"Error generating citations: {e}")
                    markdown_with_citations = raw_markdown
                    references_markdown = f"Error generating citations: {str(e)}"
                except Exception as e:
                    self.logger.error(f"Unexpected error generating citations: {e}")
                    traceback.print_exc()
                    markdown_with_citations = raw_markdown
                    references_markdown = f"Error generating citations: {str(e)}"

            # Generate fit markdown if content filter is provided
            fit_markdown: Optional[str] = ""
            filtered_html: Optional[str] = ""

            return MarkdownGenerationResult(
                raw_markdown=raw_markdown or "",
                markdown_with_citations=markdown_with_citations or "",
                references_markdown=references_markdown or "",
                fit_markdown=fit_markdown or "",
                fit_html=filtered_html or "",
            )
        except ParsingError as e:
            # Re-raise parsing errors
            raise e
        except Exception as e:
            # If anything fails, return empty strings with error message
            error_msg = f"Error in markdown generation: {str(e)}"
            self.logger.error(error_msg)
            traceback.print_exc()
            raise ParsingError("Failed to generate markdown", original_error=e)
