"""
State classes for the research connector.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class Section(BaseModel):
    """A section of a research report."""
    name: str = Field(
        description="Name for this section of the report.",
    )
    description: str = Field(
        description="Brief overview of the main topics and concepts to be covered in this section.",
    )
    research: bool = Field(
        description="Whether to perform web research for this section of the report."
    )
    content: str = Field(
        description="The content of the section."
    )   

class Sections(BaseModel):
    """Collection of report sections."""
    sections: List[Section] = Field(
        description="Sections of the report.",
    )

class SearchQuery(BaseModel):
    """A search query for web research."""
    search_query: str = Field(None, description="Query for web search.")

class Queries(BaseModel):
    """Collection of search queries."""
    queries: List[SearchQuery] = Field(
        description="List of search queries.",
    )

class Feedback(BaseModel):
    """Feedback on a research section."""
    grade: str = Field(
        description="Evaluation result indicating whether the response meets requirements ('pass') or needs revision ('fail')."
    )
    follow_up_queries: List[SearchQuery] = Field(
        description="List of follow-up search queries.",
    )

class ReportState(Dict[str, Any]):
    """State dictionary for the research report."""
    pass

class SectionState(Dict[str, Any]):
    """State dictionary for a section of the research report."""
    pass

