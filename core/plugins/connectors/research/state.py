"""State classes for research module."""

import json
import logging
from typing import Dict, List, Optional, Any, TypedDict, Union
from dataclasses import dataclass, field
from datetime import datetime

from core.plugins.connectors.research.configuration import Configuration

# Setup logger
logger = logging.getLogger(__name__)

@dataclass
class Section:
    """A section of the report."""
    title: str
    content: str = ""
    subsections: List["Section"] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert section to dictionary for serialization."""
        return {
            "title": self.title,
            "content": self.content,
            "subsections": [s.to_dict() for s in self.subsections],
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Section":
        """Create section from dictionary."""
        return cls(
            title=data["title"],
            content=data["content"],
            subsections=[cls.from_dict(s) for s in data.get("subsections", [])],
            metadata=data.get("metadata", {})
        )

@dataclass
class Sections:
    """Container for report sections."""
    sections: List[Section]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert sections to dictionary for serialization."""
        return {
            "sections": [s.to_dict() for s in self.sections]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Sections":
        """Create sections from dictionary."""
        return cls(
            sections=[Section.from_dict(s) for s in data.get("sections", [])]
        )

@dataclass
class Query:
    """A search query."""
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert query to dictionary for serialization."""
        return {
            "text": self.text,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Query":
        """Create query from dictionary."""
        timestamp = None
        if data.get("timestamp"):
            try:
                timestamp = datetime.fromisoformat(data["timestamp"])
            except ValueError:
                logger.warning(f"Invalid timestamp format: {data['timestamp']}")
        
        return cls(
            text=data["text"],
            metadata=data.get("metadata", {}),
            timestamp=timestamp
        )

@dataclass
class SearchResult:
    """A search result."""
    query: str
    results: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[datetime] = None
    search_api: Optional[str] = None
    
    def __post_init__(self):
        """Initialize timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert search result to dictionary for serialization."""
        return {
            "query": self.query,
            "results": self.results,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "search_api": self.search_api
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchResult":
        """Create search result from dictionary."""
        timestamp = None
        if data.get("timestamp"):
            try:
                timestamp = datetime.fromisoformat(data["timestamp"])
            except ValueError:
                logger.warning(f"Invalid timestamp format: {data['timestamp']}")
        
        return cls(
            query=data["query"],
            results=data["results"],
            metadata=data.get("metadata", {}),
            timestamp=timestamp,
            search_api=data.get("search_api")
        )

@dataclass
class Feedback:
    """Feedback on a section."""
    section_title: str
    feedback: str
    score: Optional[float] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert feedback to dictionary for serialization."""
        return {
            "section_title": self.section_title,
            "feedback": self.feedback,
            "score": self.score,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Feedback":
        """Create feedback from dictionary."""
        timestamp = None
        if data.get("timestamp"):
            try:
                timestamp = datetime.fromisoformat(data["timestamp"])
            except ValueError:
                logger.warning(f"Invalid timestamp format: {data['timestamp']}")
        
        return cls(
            section_title=data["section_title"],
            feedback=data["feedback"],
            score=data.get("score"),
            timestamp=timestamp
        )

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
    metadata: Dict[str, Any] = field(default_factory=dict)
    start_time: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize timestamps if not provided."""
        if self.start_time is None:
            self.start_time = datetime.now()
        if self.last_updated is None:
            self.last_updated = datetime.now()
    
    def update_timestamp(self):
        """Update the last_updated timestamp."""
        self.last_updated = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report state to dictionary for serialization."""
        return {
            "topic": self.topic,
            "sections": self.sections.to_dict(),
            "queries": [q.to_dict() for q in self.queries],
            "search_results": [sr.to_dict() for sr in self.search_results],
            "feedback": self.feedback.to_dict() if self.feedback else None,
            "previous_topic": self.previous_topic,
            "metadata": self.metadata,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], config: Optional[Configuration] = None) -> "ReportState":
        """Create report state from dictionary."""
        start_time = None
        if data.get("start_time"):
            try:
                start_time = datetime.fromisoformat(data["start_time"])
            except ValueError:
                logger.warning(f"Invalid start_time format: {data['start_time']}")
        
        last_updated = None
        if data.get("last_updated"):
            try:
                last_updated = datetime.fromisoformat(data["last_updated"])
            except ValueError:
                logger.warning(f"Invalid last_updated format: {data['last_updated']}")
        
        return cls(
            topic=data["topic"],
            sections=Sections.from_dict(data["sections"]),
            queries=[Query.from_dict(q) for q in data.get("queries", [])],
            search_results=[SearchResult.from_dict(sr) for sr in data.get("search_results", [])],
            feedback=Feedback.from_dict(data["feedback"]) if data.get("feedback") else None,
            config=config,
            previous_topic=data.get("previous_topic"),
            metadata=data.get("metadata", {}),
            start_time=start_time,
            last_updated=last_updated
        )
    
    def save_to_file(self, filepath: str) -> None:
        """Save report state to a file.
        
        Args:
            filepath (str): Path to save the state
        """
        try:
            with open(filepath, "w") as f:
                json.dump(self.to_dict(), f, indent=2)
            logger.info(f"Report state saved to {filepath}")
        except Exception as e:
            logger.error(f"Error saving report state to {filepath}: {str(e)}")
    
    @classmethod
    def load_from_file(cls, filepath: str, config: Optional[Configuration] = None) -> "ReportState":
        """Load report state from a file.
        
        Args:
            filepath (str): Path to load the state from
            config (Optional[Configuration], optional): Configuration to use. Defaults to None.
            
        Returns:
            ReportState: The loaded report state
        """
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            logger.info(f"Report state loaded from {filepath}")
            return cls.from_dict(data, config)
        except Exception as e:
            logger.error(f"Error loading report state from {filepath}: {str(e)}")
            raise

@dataclass
class SectionState:
    """State for a section generation process."""
    section_title: str
    section_content: str = ""
    queries: List[Query] = field(default_factory=list)
    search_results: List[SearchResult] = field(default_factory=list)
    feedback: Optional[Feedback] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert section state to dictionary for serialization."""
        return {
            "section_title": self.section_title,
            "section_content": self.section_content,
            "queries": [q.to_dict() for q in self.queries],
            "search_results": [sr.to_dict() for sr in self.search_results],
            "feedback": self.feedback.to_dict() if self.feedback else None,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SectionState":
        """Create section state from dictionary."""
        return cls(
            section_title=data["section_title"],
            section_content=data["section_content"],
            queries=[Query.from_dict(q) for q in data.get("queries", [])],
            search_results=[SearchResult.from_dict(sr) for sr in data.get("search_results", [])],
            feedback=Feedback.from_dict(data["feedback"]) if data.get("feedback") else None,
            metadata=data.get("metadata", {})
        )

@dataclass
class SectionOutputState:
    """Output state for a section generation process."""
    section_title: str
    section_content: str
    feedback: Optional[Feedback] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert section output state to dictionary for serialization."""
        return {
            "section_title": self.section_title,
            "section_content": self.section_content,
            "feedback": self.feedback.to_dict() if self.feedback else None,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SectionOutputState":
        """Create section output state from dictionary."""
        return cls(
            section_title=data["section_title"],
            section_content=data["section_content"],
            feedback=Feedback.from_dict(data["feedback"]) if data.get("feedback") else None,
            metadata=data.get("metadata", {})
        )

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
