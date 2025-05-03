"""Multi-agent research graph implementation."""

from typing import Literal, Dict, List, Any, Optional

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.runnables import RunnableConfig

from langgraph.constants import Send
from langgraph.graph import START, END, StateGraph
from langgraph.types import interrupt, Command

from core.plugins.connectors.research.state import (
    ReportStateInput,
    ReportStateOutput,
    Sections,
    ReportState,
    Section,
    SectionState,
    SectionOutputState,
    Queries,
    Feedback
)

from core.plugins.connectors.research.configuration import Configuration, SearchAPI
from core.plugins.connectors.research.utils import (
    format_sections, 
    get_config_value, 
    get_search_params, 
    select_and_execute_search
)

# Multi-agent specific prompts

SUPERVISOR_PROMPT = """You are the supervisor agent in a multi-agent research system. Your role is to:

1. Analyze the research topic and break it down into subtopics
2. Assign research tasks to specialized researcher agents
3. Integrate their findings into a cohesive report
4. Ensure the report is comprehensive, accurate, and well-structured

Research Topic: {topic}

Your task is to:
1. Break down this topic into {num_researchers} distinct subtopics or aspects
2. For each subtopic, formulate a specific research question
3. Integrate the findings from each researcher into a cohesive report
4. Ensure the final report has a logical structure with introduction, body sections, and conclusion

The report should follow this structure:
{report_structure}
"""

RESEARCHER_PROMPT = """You are a specialized researcher agent in a multi-agent research system. Your role is to:

1. Thoroughly investigate your assigned research question
2. Search for relevant information using the provided search API
3. Synthesize findings into a comprehensive report section
4. Provide accurate, well-sourced information

Your assigned research question: {research_question}
Related to the broader topic: {topic}

Your task is to:
1. Generate effective search queries to gather information on your question
2. Analyze the search results to extract relevant information
3. Synthesize this information into a comprehensive section
4. Ensure your section is factual, well-organized, and addresses the research question

Your section should be approximately 500-800 words and include:
- Key findings and insights
- Supporting evidence and examples
- Citations of sources where appropriate
- A logical structure with clear paragraphs
"""

INTEGRATION_PROMPT = """You are the integration agent in a multi-agent research system. Your role is to:

1. Review all the research sections provided by the researcher agents
2. Integrate these sections into a cohesive, well-structured report
3. Ensure consistency in style, terminology, and formatting
4. Add an introduction and conclusion to frame the research

Research Topic: {topic}

Research Sections:
{research_sections}

Your task is to:
1. Create a comprehensive report that integrates all the research sections
2. Ensure logical flow between sections
3. Add an introduction that provides context and outlines the scope of the report
4. Add a conclusion that summarizes key findings and their implications
5. Ensure consistent formatting and citation style throughout

The final report should follow this structure:
{report_structure}
"""

# Node functions

async def supervisor_planning(state: ReportState, config: RunnableConfig):
    """Supervisor agent plans the research approach.
    
    This node:
    1. Analyzes the research topic
    2. Breaks it down into subtopics
    3. Formulates research questions for each subtopic
    """
    # Get configuration
    configuration = state.config or Configuration()
    report_structure = configuration.report_structure
    
    # Initialize supervisor model
    supervisor_model = configuration.supervisor_model
    provider, model = supervisor_model.split(":", 1) if ":" in supervisor_model else ("openai", supervisor_model)
    
    supervisor = init_chat_model(
        provider=provider,
        model=model
    )
    
    # Determine number of researchers (subtopics)
    num_researchers = 3  # Default to 3 researchers/subtopics
    
    # Generate research plan
    prompt = SUPERVISOR_PROMPT.format(
        topic=state.topic,
        num_researchers=num_researchers,
        report_structure=report_structure
    )
    
    response = await supervisor.ainvoke([HumanMessage(content=prompt)])
    plan_content = response.content
    
    # Extract research questions from the plan
    research_questions = []
    in_questions_section = False
    
    for line in plan_content.split("\n"):
        line = line.strip()
        
        if "research question" in line.lower() or "subtopic" in line.lower():
            in_questions_section = True
            continue
            
        if in_questions_section and line and not line.startswith("#") and not "conclusion" in line.lower():
            # Clean up the line
            clean_line = line
            if clean_line[0].isdigit() and clean_line[1:3] in [". ", ") "]:
                clean_line = clean_line[3:].strip()
            elif clean_line[0] in ["-", "*"]:
                clean_line = clean_line[1:].strip()
                
            if ":" in clean_line:
                clean_line = clean_line.split(":", 1)[1].strip()
                
            research_questions.append(clean_line)
            
        if in_questions_section and ("integration" in line.lower() or "conclusion" in line.lower()):
            in_questions_section = False
    
    # If no questions were extracted, create default ones
    if not research_questions:
        research_questions = [
            f"What is the background and context of {state.topic}?",
            f"What are the key aspects and components of {state.topic}?",
            f"What are the latest developments and future trends in {state.topic}?"
        ]
    
    # Limit to the specified number of researchers
    research_questions = research_questions[:num_researchers]
    
    # Create initial sections based on research questions
    sections = []
    for question in research_questions:
        # Convert question to a section title
        title = question.rstrip("?")
        if title.startswith("What"):
            title = title[4:].strip()
            if title.startswith("is") or title.startswith("are"):
                title = title[2:].strip()
                
        title = title.capitalize()
        
        sections.append(Section(
            title=title,
            content="",
            subsections=[]
        ))
    
    # Add introduction and conclusion sections
    sections.insert(0, Section(title="Introduction", content="", subsections=[]))
    sections.append(Section(title="Conclusion", content="", subsections=[]))
    
    # Update state
    state.sections = Sections(sections=sections)
    state.queries = [{"text": question, "metadata": {}} for question in research_questions]
    
    return state

async def researcher_investigation(state: ReportState, config: RunnableConfig):
    """Researcher agents investigate their assigned questions.
    
    This node:
    1. For each research question, performs searches
    2. Analyzes search results
    3. Writes a section addressing the question
    """
    # Get configuration
    configuration = state.config or Configuration()
    search_api = configuration.search_api
    search_params = get_search_params(configuration)
    
    # Initialize researcher model
    researcher_model = configuration.researcher_model
    provider, model = researcher_model.split(":", 1) if ":" in researcher_model else ("openai", researcher_model)
    
    researcher = init_chat_model(
        provider=provider,
        model=model
    )
    
    # Get research questions from state
    research_questions = [query["text"] for query in state.queries]
    
    # Skip introduction and conclusion for now
    content_sections = state.sections.sections[1:-1]
    
    # For each research question, perform research and write section
    updated_sections = [state.sections.sections[0]]  # Start with introduction
    
    for i, (question, section) in enumerate(zip(research_questions, content_sections)):
        # Generate search queries for this question
        search_query_1 = question
        search_query_2 = f"{state.topic} {section.title}"
        
        # Execute searches
        search_results_1 = select_and_execute_search(
            search_query_1, 
            search_api, 
            search_params
        )
        
        search_results_2 = select_and_execute_search(
            search_query_2, 
            search_api, 
            search_params
        )
        
        # Combine search results
        combined_results = search_results_1 + search_results_2
        
        # Format search results for the prompt
        search_results_text = ""
        for j, result in enumerate(combined_results):
            search_results_text += f"Result {j+1}: {result.get('title', 'No title')}\n"
            search_results_text += f"URL: {result.get('url', 'No URL')}\n"
            search_results_text += f"Content: {result.get('content', 'No content')}\n\n"
        
        # Write section content
        prompt = RESEARCHER_PROMPT.format(
            research_question=question,
            topic=state.topic
        )
        
        prompt += f"\nSearch Results:\n{search_results_text}"
        
        response = await researcher.ainvoke([HumanMessage(content=prompt)])
        section_content = response.content
        
        # Update section
        updated_section = Section(
            title=section.title,
            content=section_content,
            subsections=section.subsections
        )
        
        updated_sections.append(updated_section)
    
    # Add conclusion placeholder
    updated_sections.append(state.sections.sections[-1])
    
    # Update state
    state.sections = Sections(sections=updated_sections)
    state.search_results = [
        {
            "query": question,
            "results": select_and_execute_search(question, search_api, search_params),
            "metadata": {}
        }
        for question in research_questions
    ]
    
    return state

async def integration_finalization(state: ReportState, config: RunnableConfig):
    """Integration agent finalizes the report.
    
    This node:
    1. Reviews all research sections
    2. Writes introduction and conclusion
    3. Ensures consistency across the report
    """
    # Get configuration
    configuration = state.config or Configuration()
    report_structure = configuration.report_structure
    
    # Initialize supervisor model (used for integration)
    supervisor_model = configuration.supervisor_model
    provider, model = supervisor_model.split(":", 1) if ":" in supervisor_model else ("openai", supervisor_model)
    
    integrator = init_chat_model(
        provider=provider,
        model=model
    )
    
    # Format research sections for the prompt
    research_sections_text = ""
    for i, section in enumerate(state.sections.sections[1:-1]):  # Skip intro and conclusion
        research_sections_text += f"Section {i+1}: {section.title}\n"
        research_sections_text += f"{section.content}\n\n"
    
    # Generate integrated report
    prompt = INTEGRATION_PROMPT.format(
        topic=state.topic,
        research_sections=research_sections_text,
        report_structure=report_structure
    )
    
    response = await integrator.ainvoke([HumanMessage(content=prompt)])
    integrated_content = response.content
    
    # Extract sections from integrated content
    sections = []
    current_section = None
    current_content = []
    
    for line in integrated_content.split("\n"):
        if line.startswith("# ") or line.startswith("## "):
            # Save previous section if it exists
            if current_section:
                sections.append(Section(
                    title=current_section,
                    content="\n".join(current_content),
                    subsections=[]
                ))
                current_content = []
            
            # Extract new section title
            current_section = line.split(" ", 1)[1] if " " in line else line
        elif current_section:
            current_content.append(line)
    
    # Add the last section
    if current_section and current_content:
        sections.append(Section(
            title=current_section,
            content="\n".join(current_content),
            subsections=[]
        ))
    
    # If no sections were extracted, use the original sections with the integrated content
    # as the introduction and conclusion
    if not sections:
        # Split the content roughly in half for intro and conclusion
        content_parts = integrated_content.split("\n\n")
        midpoint = len(content_parts) // 2
        
        intro_content = "\n\n".join(content_parts[:midpoint])
        conclusion_content = "\n\n".join(content_parts[midpoint:])
        
        # Update introduction and conclusion
        updated_sections = []
        for i, section in enumerate(state.sections.sections):
            if i == 0:  # Introduction
                updated_sections.append(Section(
                    title=section.title,
                    content=intro_content,
                    subsections=section.subsections
                ))
            elif i == len(state.sections.sections) - 1:  # Conclusion
                updated_sections.append(Section(
                    title=section.title,
                    content=conclusion_content,
                    subsections=section.subsections
                ))
            else:  # Keep other sections as is
                updated_sections.append(section)
        
        sections = updated_sections
    
    # Update state
    state.sections = Sections(sections=sections)
    
    return state

# Graph definition

graph = StateGraph(ReportState)

# Add nodes
graph.add_node("supervisor_planning", supervisor_planning)
graph.add_node("researcher_investigation", researcher_investigation)
graph.add_node("integration_finalization", integration_finalization)

# Add edges
graph.add_edge(START, "supervisor_planning")
graph.add_edge("supervisor_planning", "researcher_investigation")
graph.add_edge("researcher_investigation", "integration_finalization")
graph.add_edge("integration_finalization", END)

# Compile the graph
graph = graph.compile()

