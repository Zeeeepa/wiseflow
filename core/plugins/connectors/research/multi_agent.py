"""Multi-agent research graph implementation."""

import logging
import asyncio
import time
from typing import Literal, Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

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

# Setup logger
logger = logging.getLogger(__name__)

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
{report_structure}"""

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
- A logical structure with clear paragraphs"""

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
{report_structure}"""

# Node functions

async def supervisor_planning(state: ReportState, config: RunnableConfig):
    """Supervisor agent plans the research approach.
    
    This node:
    1. Analyzes the research topic
    2. Breaks it down into subtopics
    3. Formulates research questions for each subtopic
    """
    start_time = time.time()
    logger.info(f"Starting supervisor planning for topic: {state.topic}")
    
    # Get configuration
    configuration = state.config or Configuration()
    report_structure = configuration.report_structure
    
    # Initialize supervisor model
    supervisor_model = configuration.supervisor_model
    provider, model = supervisor_model.split(":", 1) if ":" in supervisor_model else ("openai", supervisor_model)
    
    try:
        supervisor = init_chat_model(
            provider=provider,
            model=model
        )
        
        # Determine number of researchers (subtopics)
        num_researchers = configuration.max_concurrent_researchers
        
        # Generate research plan
        prompt = SUPERVISOR_PROMPT.format(
            topic=state.topic,
            num_researchers=num_researchers,
            report_structure=report_structure
        )
        
        logger.debug(f"Sending prompt to supervisor model: {provider}:{model}")
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
            logger.warning("No research questions extracted from supervisor response, using defaults")
            research_questions = [
                f"What is the background and context of {state.topic}?",
                f"What are the key aspects and components of {state.topic}?",
                f"What are the latest developments and future trends in {state.topic}?"
            ]
        
        # Limit to the specified number of researchers
        research_questions = research_questions[:num_researchers]
        logger.info(f"Generated {len(research_questions)} research questions")
        
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
                subsections=[],
                metadata={"research_question": question}
            ))
        
        # Add introduction and conclusion sections
        sections.insert(0, Section(title="Introduction", content="", subsections=[]))
        sections.append(Section(title="Conclusion", content="", subsections=[]))
        
        # Update state
        state.sections = Sections(sections=sections)
        state.queries = [{"text": question, "metadata": {}} for question in research_questions]
        
        # Add execution time to metadata
        execution_time = time.time() - start_time
        state.metadata["supervisor_planning_time"] = execution_time
        logger.info(f"Supervisor planning completed in {execution_time:.2f} seconds")
        
        return state
    except Exception as e:
        logger.error(f"Error in supervisor planning: {str(e)}", exc_info=True)
        # Create default sections if planning fails
        sections = [
            Section(title="Introduction", content="", subsections=[]),
            Section(title=f"Overview of {state.topic}", content="", subsections=[]),
            Section(title="Key Aspects", content="", subsections=[]),
            Section(title="Conclusion", content="", subsections=[])
        ]
        
        state.sections = Sections(sections=sections)
        state.queries = [
            {"text": f"comprehensive information about {state.topic}", "metadata": {}},
            {"text": f"key aspects of {state.topic}", "metadata": {}}
        ]
        
        # Add error to metadata
        state.metadata["supervisor_planning_error"] = str(e)
        
        return state

async def _researcher_task(
    question: str, 
    section: Section, 
    topic: str, 
    search_api: SearchAPI, 
    search_params: Dict[str, Any],
    researcher_model: str
) -> Tuple[Section, List[Dict[str, Any]]]:
    """Execute a single researcher task.
    
    Args:
        question (str): The research question
        section (Section): The section to populate
        topic (str): The main research topic
        search_api (SearchAPI): The search API to use
        search_params (Dict[str, Any]): The search parameters
        researcher_model (str): The model to use for the researcher
        
    Returns:
        Tuple[Section, List[Dict[str, Any]]]: The updated section and search results
    """
    try:
        logger.info(f"Starting researcher task for question: {question}")
        task_start_time = time.time()
        
        # Initialize researcher model
        provider, model = researcher_model.split(":", 1) if ":" in researcher_model else ("openai", researcher_model)
        
        researcher = init_chat_model(
            provider=provider,
            model=model
        )
        
        # Generate search queries for this question
        search_query_1 = question
        search_query_2 = f"{topic} {section.title}"
        
        # Execute searches
        logger.debug(f"Executing search for query: {search_query_1}")
        search_results_1 = select_and_execute_search(
            search_query_1, 
            search_api, 
            search_params
        )
        
        logger.debug(f"Executing search for query: {search_query_2}")
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
            topic=topic
        )
        
        prompt += f"\nSearch Results:\n{search_results_text}"
        
        logger.debug(f"Sending prompt to researcher model: {provider}:{model}")
        response = await researcher.ainvoke([HumanMessage(content=prompt)])
        section_content = response.content
        
        # Update section
        updated_section = Section(
            title=section.title,
            content=section_content,
            subsections=section.subsections,
            metadata={
                **section.metadata,
                "execution_time": time.time() - task_start_time,
                "search_results_count": len(combined_results)
            }
        )
        
        logger.info(f"Researcher task completed for question: {question} in {time.time() - task_start_time:.2f} seconds")
        
        return updated_section, combined_results
    except Exception as e:
        logger.error(f"Error in researcher task for question {question}: {str(e)}", exc_info=True)
        # Return section with error information
        error_section = Section(
            title=section.title,
            content=f"Error researching this topic: {str(e)}",
            subsections=section.subsections,
            metadata={
                **section.metadata,
                "error": str(e)
            }
        )
        return error_section, []

async def researcher_investigation(state: ReportState, config: RunnableConfig):
    """Researcher agents investigate their assigned questions.
    
    This node:
    1. For each research question, performs searches
    2. Analyzes search results
    3. Writes a section addressing the question
    """
    start_time = time.time()
    logger.info(f"Starting researcher investigation for topic: {state.topic}")
    
    # Get configuration
    configuration = state.config or Configuration()
    search_api = configuration.search_api
    search_params = get_search_params(configuration)
    
    # Get research questions from state
    research_questions = [query["text"] for query in state.queries]
    
    # Skip introduction and conclusion for now
    content_sections = state.sections.sections[1:-1]
    
    # Check if we have enough questions for all sections
    if len(research_questions) < len(content_sections):
        logger.warning(f"Not enough research questions ({len(research_questions)}) for all sections ({len(content_sections)})")
        # Generate additional questions if needed
        for i in range(len(research_questions), len(content_sections)):
            research_questions.append(f"What are the important aspects of {content_sections[i].title} in relation to {state.topic}?")
    
    # Start with introduction
    updated_sections = [state.sections.sections[0]]
    all_search_results = []
    
    try:
        # Determine if we should run in parallel
        if configuration.enable_parallel_execution and len(content_sections) > 1:
            logger.info(f"Running {len(content_sections)} researcher tasks in parallel")
            
            # Create tasks for each section
            tasks = []
            for i, (question, section) in enumerate(zip(research_questions, content_sections)):
                tasks.append(_researcher_task(
                    question=question,
                    section=section,
                    topic=state.topic,
                    search_api=search_api,
                    search_params=search_params,
                    researcher_model=configuration.researcher_model
                ))
            
            # Run tasks in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error in parallel researcher task {i}: {str(result)}")
                    # Add error section
                    updated_sections.append(Section(
                        title=content_sections[i].title,
                        content=f"Error researching this topic: {str(result)}",
                        subsections=content_sections[i].subsections,
                        metadata={"error": str(result)}
                    ))
                else:
                    updated_section, search_results = result
                    updated_sections.append(updated_section)
                    all_search_results.append({
                        "query": research_questions[i],
                        "results": search_results,
                        "metadata": {}
                    })
        else:
            # Run sequentially
            logger.info(f"Running {len(content_sections)} researcher tasks sequentially")
            for i, (question, section) in enumerate(zip(research_questions, content_sections)):
                updated_section, search_results = await _researcher_task(
                    question=question,
                    section=section,
                    topic=state.topic,
                    search_api=search_api,
                    search_params=search_params,
                    researcher_model=configuration.researcher_model
                )
                
                updated_sections.append(updated_section)
                all_search_results.append({
                    "query": question,
                    "results": search_results,
                    "metadata": {}
                })
    except Exception as e:
        logger.error(f"Error in researcher investigation: {str(e)}", exc_info=True)
        # Add remaining sections with error information
        for i in range(len(updated_sections) - 1, len(content_sections)):
            updated_sections.append(Section(
                title=content_sections[i].title,
                content=f"Error researching this topic: {str(e)}",
                subsections=content_sections[i].subsections,
                metadata={"error": str(e)}
            ))
    
    # Add conclusion placeholder
    updated_sections.append(state.sections.sections[-1])
    
    # Update state
    state.sections = Sections(sections=updated_sections)
    state.search_results = all_search_results
    
    # Add execution time to metadata
    execution_time = time.time() - start_time
    state.metadata["researcher_investigation_time"] = execution_time
    logger.info(f"Researcher investigation completed in {execution_time:.2f} seconds")
    
    return state

async def integration_finalization(state: ReportState, config: RunnableConfig):
    """Integration agent finalizes the report.
    
    This node:
    1. Reviews all research sections
    2. Writes introduction and conclusion
    3. Ensures consistency across the report
    """
    start_time = time.time()
    logger.info(f"Starting integration finalization for topic: {state.topic}")
    
    # Get configuration
    configuration = state.config or Configuration()
    report_structure = configuration.report_structure
    
    # Initialize supervisor model (used for integration)
    supervisor_model = configuration.supervisor_model
    provider, model = supervisor_model.split(":", 1) if ":" in supervisor_model else ("openai", supervisor_model)
    
    try:
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
        
        logger.debug(f"Sending prompt to integrator model: {provider}:{model}")
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
            logger.warning("No sections extracted from integrator response, using original sections with integrated content")
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
                        subsections=section.subsections,
                        metadata={"source": "integrator"}
                    ))
                elif i == len(state.sections.sections) - 1:  # Conclusion
                    updated_sections.append(Section(
                        title=section.title,
                        content=conclusion_content,
                        subsections=section.subsections,
                        metadata={"source": "integrator"}
                    ))
                else:  # Keep other sections as is
                    updated_sections.append(section)
            
            sections = updated_sections
        
        # Update state
        state.sections = Sections(sections=sections)
        
        # Add execution time to metadata
        execution_time = time.time() - start_time
        state.metadata["integration_finalization_time"] = execution_time
        logger.info(f"Integration finalization completed in {execution_time:.2f} seconds")
        
        return state
    except Exception as e:
        logger.error(f"Error in integration finalization: {str(e)}", exc_info=True)
        
        # If integration fails, keep the original sections but add intro and conclusion
        try:
            # Generate simple introduction and conclusion
            intro_prompt = f"Write a brief introduction (2-3 paragraphs) for a report on the topic: {state.topic}"
            conclusion_prompt = f"Write a brief conclusion (2-3 paragraphs) summarizing the key points about: {state.topic}"
            
            # Try to get intro and conclusion
            intro_response = await integrator.ainvoke([HumanMessage(content=intro_prompt)])
            conclusion_response = await integrator.ainvoke([HumanMessage(content=conclusion_prompt)])
            
            # Update introduction and conclusion
            updated_sections = []
            for i, section in enumerate(state.sections.sections):
                if i == 0:  # Introduction
                    updated_sections.append(Section(
                        title=section.title,
                        content=intro_response.content,
                        subsections=section.subsections,
                        metadata={"source": "fallback_integrator"}
                    ))
                elif i == len(state.sections.sections) - 1:  # Conclusion
                    updated_sections.append(Section(
                        title=section.title,
                        content=conclusion_response.content,
                        subsections=section.subsections,
                        metadata={"source": "fallback_integrator"}
                    ))
                else:  # Keep other sections as is
                    updated_sections.append(section)
            
            state.sections = Sections(sections=updated_sections)
        except Exception as fallback_e:
            logger.error(f"Error in fallback integration: {str(fallback_e)}", exc_info=True)
            # Keep original sections if fallback fails
        
        # Add error to metadata
        state.metadata["integration_finalization_error"] = str(e)
        
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
