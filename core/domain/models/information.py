#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Information Domain Models.

This module defines the domain models for information extraction and processing.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional

class ContentType(Enum):
    """Content types for information sources."""
    TEXT = "text"
    HTML = "html"
    MARKDOWN = "markdown"
    PDF = "pdf"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    CODE = "code"
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    UNKNOWN = "unknown"

class SourceType(Enum):
    """Types of information sources."""
    WEB = "web"
    FILE = "file"
    DATABASE = "database"
    API = "api"
    SOCIAL = "social"
    NEWS = "news"
    ACADEMIC = "academic"
    CODE = "code"
    CUSTOM = "custom"
    UNKNOWN = "unknown"

@dataclass
class InformationSource:
    """
    Information source model.
    
    This class represents a source of information, such as a web page, file, or API.
    """
    
    url: str
    source_type: SourceType
    content_type: ContentType
    title: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    published_date: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate and initialize the source."""
        if not self.title and self.url:
            # Extract title from URL if not provided
            self.title = self.url.split("/")[-1]
            
        if not self.source_type:
            # Determine source type from URL if not provided
            if self.url.startswith("http"):
                self.source_type = SourceType.WEB
            elif self.url.startswith("file"):
                self.source_type = SourceType.FILE
            else:
                self.source_type = SourceType.UNKNOWN
                
        if not self.content_type:
            # Determine content type from URL if not provided
            if self.url.endswith(".html") or self.url.endswith(".htm"):
                self.content_type = ContentType.HTML
            elif self.url.endswith(".md"):
                self.content_type = ContentType.MARKDOWN
            elif self.url.endswith(".pdf"):
                self.content_type = ContentType.PDF
            elif self.url.endswith((".jpg", ".jpeg", ".png", ".gif")):
                self.content_type = ContentType.IMAGE
            elif self.url.endswith((".mp4", ".avi", ".mov")):
                self.content_type = ContentType.VIDEO
            elif self.url.endswith((".mp3", ".wav", ".ogg")):
                self.content_type = ContentType.AUDIO
            else:
                self.content_type = ContentType.UNKNOWN

@dataclass
class Information:
    """
    Information model.
    
    This class represents information extracted from a source, including
    the original content, processed content, and metadata.
    """
    
    source: InformationSource
    focus_point: str
    content: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    summary: Optional[str] = None
    processed_content: Optional[str] = None
    insights: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def update(self, **kwargs):
        """
        Update information attributes.
        
        Args:
            **kwargs: Attributes to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        self.updated_at = datetime.now()
    
    def add_insight(self, insight: Dict[str, Any]):
        """
        Add an insight to the information.
        
        Args:
            insight: Insight to add
        """
        self.insights.append(insight)
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the information to a dictionary.
        
        Returns:
            Dictionary representation of the information
        """
        return {
            "id": self.id,
            "source": {
                "url": self.source.url,
                "source_type": self.source.source_type.value,
                "content_type": self.source.content_type.value,
                "title": self.source.title,
                "description": self.source.description,
                "author": self.source.author,
                "published_date": self.source.published_date.isoformat() if self.source.published_date else None,
                "metadata": self.source.metadata
            },
            "focus_point": self.focus_point,
            "content": self.content,
            "summary": self.summary,
            "processed_content": self.processed_content,
            "insights": self.insights,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Information':
        """
        Create an information object from a dictionary.
        
        Args:
            data: Dictionary representation of the information
            
        Returns:
            Information object
        """
        source_data = data.get("source", {})
        source = InformationSource(
            url=source_data.get("url", ""),
            source_type=SourceType(source_data.get("source_type", "unknown")),
            content_type=ContentType(source_data.get("content_type", "unknown")),
            title=source_data.get("title"),
            description=source_data.get("description"),
            author=source_data.get("author"),
            published_date=datetime.fromisoformat(source_data.get("published_date")) if source_data.get("published_date") else None,
            metadata=source_data.get("metadata", {})
        )
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            source=source,
            focus_point=data.get("focus_point", ""),
            content=data.get("content", ""),
            summary=data.get("summary"),
            processed_content=data.get("processed_content"),
            insights=data.get("insights", []),
            created_at=datetime.fromisoformat(data.get("created_at")) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data.get("updated_at")) if data.get("updated_at") else datetime.now(),
            metadata=data.get("metadata", {})
        )

