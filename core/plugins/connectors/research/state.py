"""State classes for research module."""

from typing import Dict, List, Optional, Any, TypedDict, Union
from dataclasses import dataclass, field

from core.plugins.connectors.research.configuration import Configuration

@dataclass
class Section:
    """A section of the report."""
    title: str
    content: str = ""
    subsections: List["Section"] = field(default_factory=list)

@dataclass
class Sections:
    """Container for report sections."""
    sections: List[Section]

@dataclass
class Query:
    """A search query."""
    text: str
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class SearchResult:
    """A search result."""
    query: str
    results: List[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class Feedback:
    """Feedback on a section."""
    section_title: str
    feedback: str
    score: Optional[float] = None

@dataclass
class ReportState:
    """State for the report generation process."""
    topic: str
    sections: Sections
    queries: List[Query]
    search_results: List[SearchResult]
    feedback: Optional[Feedback] = None
    config: Optional[Configuration] = None
    previous_topic: Optional[str] = None

@dataclass
class SectionState:
    """State for a section generation process."""
    section_title: str
    section_content: str = ""
    queries: List[Query] = field(default_factory=list)
    search_results: List[SearchResult] = field(default_factory=list)
    feedback: Optional[Feedback] = None

@dataclass
class SectionOutputState:
    """Output state for a section generation process."""
    section_title: str
    section_content: str
    feedback: Optional[Feedback] = None

class ReportStateInput(TypedDict):
    """Input for the report generation process."""
    topic: str
    previous_topic: Optional[str]

class ReportStateOutput(TypedDict):
    """Output for the report generation process."""
    sections: Sections

class Queries(TypedDict):
    """Container for queries."""
    queries: List[Query]

