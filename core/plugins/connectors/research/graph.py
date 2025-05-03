"""
Linear research graph implementation.
"""

import os
import asyncio
import json
from typing import Dict, Any, List, Optional

from langchain.chat_models import ChatAnthropic, ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser

from core.plugins.connectors.research.state import (
    Section, 
    Sections, 
    SearchQuery, 
    Queries, 
    Feedback,
    ReportState,
    SectionState
)
from core.plugins.connectors.research.prompts import (
    report_planner_query_writer_instructions,
    report_planner_instructions,
    query_writer_instructions, 
    section_writer_instructions,
    final_section_writer_instructions,
    section_grader_instructions,
    section_writer_inputs
)
from core.plugins.connectors.research.utils import (
    format_sections, 
    get_config_value, 
    get_search_params, 
    select_and_execute_search
)
from core.plugins.connectors.research.configuration import Configuration

def init_chat_model(model, model_provider="anthropic", model_kwargs=None, max_tokens=None, thinking=None):
    """Initialize a chat model based on provider and model name."""
    model_kwargs = model_kwargs or {}
    
    if max_tokens:
        model_kwargs["max_tokens"] = max_tokens
    
    if model_provider.lower() == "anthropic":
        if thinking:
            model_kwargs["thinking"] = thinking
        return ChatAnthropic(model=model, **model_kwargs)
    elif model_provider.lower() == "openai":
        return ChatOpenAI(model=model, **model_kwargs)
    else:
        raise ValueError(f"Unsupported model provider: {model_provider}")

async def generate_report_plan(state: Dict[str, Any], config: Configuration, api_keys: Dict[str, str]) -> Dict[str, Any]:
    """
    Generate the initial report plan with sections.
    
    Args:
        state: Current state containing the report topic
        config: Configuration for models, search APIs, etc.
        api_keys: Dictionary of API keys for different search services
        
    Returns:
        Dict containing the generated sections
    """
    # Inputs
    topic = state["topic"]
    feedback = state.get("feedback_on_report_plan", None)

    # Get configuration
    report_structure = config.report_structure
    number_of_queries = config.number_of_queries
    search_api = get_config_value(config.search_api)
    search_api_config = config.search_api_config or {}
    params_to_pass = get_search_params(search_api, search_api_config)

    # Convert JSON object to string if necessary
    if isinstance(report_structure, dict):
        report_structure = str(report_structure)

    # Set writer model (model used for query writing)
    writer_provider = get_config_value(config.writer_provider)
    writer_model_name = get_config_value(config.writer_model)
    writer_model_kwargs = get_config_value(config.writer_model_kwargs or {})
    writer_model = init_chat_model(model=writer_model_name, model_provider=writer_provider, model_kwargs=writer_model_kwargs) 
    
    # Format system instructions
    system_instructions_query = report_planner_query_writer_instructions.format(
        topic=topic, 
        report_organization=report_structure, 
        number_of_queries=number_of_queries
    )

    # Generate queries
    query_result = await writer_model.with_structured_output(Queries).ainvoke([
        SystemMessage(content=system_instructions_query),
        HumanMessage(content="Generate search queries that will help with planning the sections of the report.")
    ])
    
    # Web search
    query_list = [query.search_query for query in query_result.queries]

    # Search the web with parameters
    source_str = await select_and_execute_search(search_api, query_list, api_keys, params_to_pass)

    # Format system instructions
    system_instructions_sections = report_planner_instructions.format(
        topic=topic, 
        report_organization=report_structure, 
        context=source_str, 
        feedback=feedback
    )

    # Set the planner
    planner_provider = get_config_value(config.planner_provider)
    planner_model = get_config_value(config.planner_model)
    planner_model_kwargs = get_config_value(config.planner_model_kwargs or {})

    # Report planner instructions
    planner_message = """Generate the sections of the report. Your response must include a 'sections' field containing a list of sections. 
                        Each section must have: name, description, plan, research, and content fields."""

    # Run the planner
    if planner_model == "claude-3-7-sonnet-latest":
        # Allocate a thinking budget for claude-3-7-sonnet-latest as the planner model
        planner_llm = init_chat_model(
            model=planner_model, 
            model_provider=planner_provider, 
            max_tokens=20_000, 
            thinking={"type": "enabled", "budget_tokens": 16_000}
        )
    else:
        # With other models, thinking tokens are not specifically allocated
        planner_llm = init_chat_model(
            model=planner_model, 
            model_provider=planner_provider,
            model_kwargs=planner_model_kwargs
        )
    
    # Generate the report sections
    report_sections = await planner_llm.with_structured_output(Sections).ainvoke([
        SystemMessage(content=system_instructions_sections),
        HumanMessage(content=planner_message)
    ])

    # Get sections
    sections = report_sections.sections

    return {"sections": sections}

async def generate_queries(state: Dict[str, Any], config: Configuration) -> Dict[str, Any]:
    """
    Generate search queries for researching a specific section.
    
    Args:
        state: Current state containing section details
        config: Configuration including number of queries to generate
        
    Returns:
        Dict containing the generated search queries
    """
    # Get state 
    topic = state["topic"]
    section = state["section"]

    # Get configuration
    number_of_queries = config.number_of_queries

    # Generate queries 
    writer_provider = get_config_value(config.writer_provider)
    writer_model_name = get_config_value(config.writer_model)
    writer_model_kwargs = get_config_value(config.writer_model_kwargs or {})
    writer_model = init_chat_model(model=writer_model_name, model_provider=writer_provider, model_kwargs=writer_model_kwargs) 
    
    # Format system instructions
    system_instructions = query_writer_instructions.format(
        topic=topic, 
        section_topic=section.description, 
        number_of_queries=number_of_queries
    )

    # Generate queries  
    queries = await writer_model.with_structured_output(Queries).ainvoke([
        SystemMessage(content=system_instructions),
        HumanMessage(content="Generate search queries on the provided topic.")
    ])

    return {"search_queries": queries.queries}

async def search_web(state: Dict[str, Any], config: Configuration, api_keys: Dict[str, str]) -> Dict[str, Any]:
    """
    Execute web searches for the section queries.
    
    Args:
        state: Current state with search queries
        config: Search API configuration
        api_keys: Dictionary of API keys for different search services
        
    Returns:
        Dict with search results and updated iteration count
    """
    # Get state
    search_queries = state["search_queries"]
    search_iterations = state.get("search_iterations", 0)

    # Get configuration
    search_api = get_config_value(config.search_api)
    search_api_config = config.search_api_config or {}
    params_to_pass = get_search_params(search_api, search_api_config)

    # Extract search queries
    query_list = [query.search_query for query in search_queries]

    # Search the web
    source_str = await select_and_execute_search(search_api, query_list, api_keys, params_to_pass)

    # Increment search iterations
    search_iterations += 1

    return {
        "source_str": source_str,
        "search_iterations": search_iterations
    }

async def write_section(state: Dict[str, Any], config: Configuration) -> Dict[str, Any]:
    """
    Write a section of the report and evaluate if more research is needed.
    
    Args:
        state: Current state with search results and section info
        config: Configuration for writing and evaluation
        
    Returns:
        Dict with section content and evaluation results
    """
    # Get state 
    topic = state["topic"]
    section = state["section"]
    source_str = state["source_str"]
    search_iterations = state["search_iterations"]

    # Format system instructions
    section_writer_inputs_formatted = section_writer_inputs.format(
        topic=topic, 
        section_name=section.name, 
        section_topic=section.description, 
        context=source_str, 
        section_content=section.content
    )

    # Generate section  
    writer_provider = get_config_value(config.writer_provider)
    writer_model_name = get_config_value(config.writer_model)
    writer_model_kwargs = get_config_value(config.writer_model_kwargs or {})
    writer_model = init_chat_model(model=writer_model_name, model_provider=writer_provider, model_kwargs=writer_model_kwargs) 

    section_content = await writer_model.ainvoke([
        SystemMessage(content=section_writer_instructions),
        HumanMessage(content=section_writer_inputs_formatted)
    ])
    
    # Write content to the section object  
    section.content = section_content.content

    # Grade prompt 
    section_grader_message = ("Grade the report and consider follow-up questions for missing information. "
                              "If the grade is 'pass', return empty strings for all follow-up queries. "
                              "If the grade is 'fail', provide specific search queries to gather missing information.")
    
    section_grader_instructions_formatted = section_grader_instructions.format(
        topic=topic, 
        section_topic=section.description,
        section=section.content, 
        number_of_follow_up_queries=config.number_of_queries
    )

    # Use planner model for reflection
    planner_provider = get_config_value(config.planner_provider)
    planner_model = get_config_value(config.planner_model)
    planner_model_kwargs = get_config_value(config.planner_model_kwargs or {})

    if planner_model == "claude-3-7-sonnet-latest":
        # Allocate a thinking budget for claude-3-7-sonnet-latest as the planner model
        reflection_model = init_chat_model(
            model=planner_model, 
            model_provider=planner_provider, 
            max_tokens=20_000, 
            thinking={"type": "enabled", "budget_tokens": 16_000}
        ).with_structured_output(Feedback)
    else:
        reflection_model = init_chat_model(
            model=planner_model, 
            model_provider=planner_provider, 
            model_kwargs=planner_model_kwargs
        ).with_structured_output(Feedback)
    
    # Generate feedback
    feedback = await reflection_model.ainvoke([
        SystemMessage(content=section_grader_instructions_formatted),
        HumanMessage(content=section_grader_message)
    ])

    # Return results
    result = {
        "section": section,
        "feedback": feedback,
        "search_iterations": search_iterations
    }
    
    # If the section is passing or the max search depth is reached, mark as completed
    if feedback.grade == "pass" or search_iterations >= config.max_search_depth:
        result["completed"] = True
    else:
        result["completed"] = False
        result["search_queries"] = feedback.follow_up_queries
    
    return result

async def write_final_sections(state: Dict[str, Any], config: Configuration) -> Dict[str, Any]:
    """
    Write sections that don't require research using completed sections as context.
    
    Args:
        state: Current state with completed sections as context
        config: Configuration for the writing model
        
    Returns:
        Dict containing the newly written section
    """
    # Get state 
    topic = state["topic"]
    section = state["section"]
    completed_report_sections = state["report_sections_from_research"]
    
    # Format system instructions
    system_instructions = final_section_writer_instructions.format(
        topic=topic, 
        section_name=section.name, 
        section_topic=section.description, 
        context=completed_report_sections
    )

    # Generate section  
    writer_provider = get_config_value(config.writer_provider)
    writer_model_name = get_config_value(config.writer_model)
    writer_model_kwargs = get_config_value(config.writer_model_kwargs or {})
    writer_model = init_chat_model(model=writer_model_name, model_provider=writer_provider, model_kwargs=writer_model_kwargs) 
    
    section_content = await writer_model.ainvoke([
        SystemMessage(content=system_instructions),
        HumanMessage(content="Generate a report section based on the provided sources.")
    ])
    
    # Write content to section 
    section.content = section_content.content

    # Return the updated section
    return {"section": section}

def compile_final_report(sections: List[Section]) -> str:
    """
    Compile all sections into the final report.
    
    Args:
        sections: List of all completed sections
        
    Returns:
        String containing the complete report
    """
    # Compile final report
    all_sections = "\n\n".join([s.content for s in sections])
    return all_sections

async def run_linear_research(topic: str, config: Configuration, api_keys: Dict[str, str]) -> Dict[str, Any]:
    """
    Run the linear research process.
    
    Args:
        topic: Topic to research
        config: Research configuration
        api_keys: Dictionary of API keys for different search services
        
    Returns:
        Dict containing the research results
    """
    # Initialize state
    state = {"topic": topic}
    
    # Step 1: Generate report plan
    plan_result = await generate_report_plan(state, config, api_keys)
    sections = plan_result["sections"]
    
    # Step 2: Research and write sections that require research
    completed_sections = []
    for section in sections:
        if section.research:
            # Initialize section state
            section_state = {
                "topic": topic,
                "section": section,
                "search_iterations": 0
            }
            
            # Generate initial queries
            query_result = await generate_queries(section_state, config)
            section_state.update(query_result)
            
            # Iterative research until section is complete
            completed = False
            while not completed:
                # Search web
                search_result = await search_web(section_state, config, api_keys)
                section_state.update(search_result)
                
                # Write section
                write_result = await write_section(section_state, config)
                section_state.update(write_result)
                
                # Check if section is complete
                if write_result["completed"]:
                    completed = True
                    completed_sections.append(section_state["section"])
    
    # Step 3: Format completed sections as context for final sections
    report_sections_from_research = format_sections(completed_sections)
    
    # Step 4: Write sections that don't require research
    for section in sections:
        if not section.research:
            # Initialize section state
            section_state = {
                "topic": topic,
                "section": section,
                "report_sections_from_research": report_sections_from_research
            }
            
            # Write final section
            final_section_result = await write_final_sections(section_state, config)
            completed_sections.append(final_section_result["section"])
    
    # Step 5: Compile final report
    final_report = compile_final_report(sections)
    
    # Return results
    return {
        "topic": topic,
        "report": final_report,
        "sections": {s.name: {"title": s.name, "content": s.content, "sources": []} for s in sections}
    }

