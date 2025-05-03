"""Linear research graph implementation."""

from typing import Literal

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from langgraph.constants import Send
from langgraph.graph import START, END, StateGraph
from langgraph.types import interrupt, Command

from core.plugins.connectors.research.state import (
    ReportStateInput,
    ReportStateOutput,
    Sections,
    ReportState,
    SectionState,
    SectionOutputState,
    Queries,
    Feedback
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

from core.plugins.connectors.research.configuration import Configuration
from core.plugins.connectors.research.utils import (
    format_sections, 
    get_config_value, 
    get_search_params, 
    select_and_execute_search
)

## Nodes -- 

async def generate_report_plan(state: ReportState, config: RunnableConfig):
    """Generate the initial report plan with sections.
    
    This node:
    1. Gets configuration for the report structure and search parameters
    2. Generates search queries to gather context for planning
    3. Performs web searches using those queries
    4. Uses an LLM to generate a structured plan with sections
    """
    # Get configuration
    configuration = state.config or Configuration()
    report_structure = configuration.report_structure
    search_api = configuration.search_api
    search_params = get_search_params(configuration)
    num_queries = configuration.number_of_queries
    
    # Initialize planner model
    planner_provider = configuration.planner_provider
    planner_model = configuration.planner_model
    planner_model_kwargs = configuration.planner_model_kwargs or {}
    
    planner = init_chat_model(
        provider=planner_provider,
        model=planner_model,
        **planner_model_kwargs
    )
    
    # Generate search queries and plan
    prompt = report_planner_query_writer_instructions.format(
        report_structure=report_structure,
        topic=state.topic,
        num_queries=num_queries
    )
    
    response = await planner.ainvoke([HumanMessage(content=prompt)])
    response_content = response.content
    
    # Extract queries from response
    queries = []
    query_lines = []
    in_query_section = False
    
    for line in response_content.split("\n"):
        if "search queries" in line.lower() or "search query" in line.lower():
            in_query_section = True
            continue
        
        if in_query_section and line.strip() and not line.startswith("#") and not "outline" in line.lower():
            # Remove numbering and other formatting
            clean_line = line.strip()
            if clean_line[0].isdigit() and clean_line[1:3] in [". ", ") "]:
                clean_line = clean_line[3:].strip()
            elif clean_line[0] in ["-", "*"]:
                clean_line = clean_line[1:].strip()
                
            query_lines.append(clean_line)
        
        if in_query_section and ("outline" in line.lower() or "section" in line.lower() or "report structure" in line.lower()):
            in_query_section = False
    
    # Create query objects
    for query_text in query_lines[:num_queries]:
        queries.append({"text": query_text, "metadata": {}})
    
    # If no queries were extracted, generate generic ones
    if not queries:
        queries = [
            {"text": f"comprehensive information about {state.topic}", "metadata": {}},
            {"text": f"latest research on {state.topic}", "metadata": {}}
        ]
    
    # Execute searches for each query
    search_results = []
    for query in queries:
        results = select_and_execute_search(
            query["text"], 
            search_api, 
            search_params
        )
        search_results.append({
            "query": query["text"],
            "results": results,
            "metadata": {}
        })
    
    # Generate report plan with sections
    search_results_text = ""
    for i, result in enumerate(search_results):
        search_results_text += f"Search {i+1} for '{result['query']}':\n"
        for j, item in enumerate(result["results"][:3]):  # Limit to first 3 results per query
            search_results_text += f"Result {j+1}: {item.get('title', 'No title')}\n"
            search_results_text += f"URL: {item.get('url', 'No URL')}\n"
            search_results_text += f"Content: {item.get('content', 'No content')[:300]}...\n\n"
    
    plan_prompt = report_planner_instructions.format(
        report_structure=report_structure,
        topic=state.topic
    )
    
    if search_results_text:
        plan_prompt += f"\nSearch Results:\n{search_results_text}"
    
    plan_response = await planner.ainvoke([HumanMessage(content=plan_prompt)])
    plan_content = plan_response.content
    
    # Extract sections from plan
    sections = []
    current_section = None
    
    for line in plan_content.split("\n"):
        line = line.strip()
        if not line:
            continue
            
        # Check if line is a main section header
        if line.startswith("# ") or line.startswith("1. ") or line.startswith("I. "):
            if current_section:
                sections.append(current_section)
            
            title = line.split(" ", 1)[1] if " " in line else line
            current_section = {"title": title, "content": "", "subsections": []}
            
        # Check if line is a subsection header
        elif line.startswith("## ") or line.startswith("   a. ") or line.startswith("   - "):
            if current_section:
                title = line.split(" ", 1)[1] if " " in line else line
                current_section["subsections"].append({"title": title, "content": ""})
    
    # Add the last section if it exists
    if current_section:
        sections.append(current_section)
    
    # If no sections were extracted, create default ones
    if not sections:
        sections = [
            {"title": "Introduction", "content": "", "subsections": []},
            {"title": f"Overview of {state.topic}", "content": "", "subsections": []},
            {"title": "Key Aspects", "content": "", "subsections": []},
            {"title": "Conclusion", "content": "", "subsections": []}
        ]
    
    # Update state
    state.queries = queries
    state.search_results = search_results
    state.sections = Sections(sections=[])
    
    # Convert sections to the proper format
    for section in sections:
        section_obj = {"title": section["title"], "content": "", "subsections": []}
        for subsection in section.get("subsections", []):
            section_obj["subsections"].append({
                "title": subsection["title"],
                "content": ""
            })
        state.sections.sections.append(section_obj)
    
    return state

async def write_sections(state: ReportState, config: RunnableConfig):
    """Write content for each section based on search results.
    
    This node:
    1. For each section in the plan, generates specific search queries
    2. Performs web searches for each query
    3. Uses an LLM to write content for the section based on search results
    """
    # Get configuration
    configuration = state.config or Configuration()
    search_api = configuration.search_api
    search_params = get_search_params(configuration)
    
    # Initialize writer model
    writer_provider = configuration.writer_provider
    writer_model = configuration.writer_model
    writer_model_kwargs = configuration.writer_model_kwargs or {}
    
    writer = init_chat_model(
        provider=writer_provider,
        model=writer_model,
        **writer_model_kwargs
    )
    
    # For each section, generate queries, search, and write content
    updated_sections = []
    
    for section in state.sections.sections:
        # Generate search query for this section
        section_query = f"{state.topic} {section['title']}"
        
        # Execute search
        search_results = select_and_execute_search(
            section_query, 
            search_api, 
            search_params
        )
        
        # Format search results for the prompt
        search_results_text = ""
        for i, result in enumerate(search_results):
            search_results_text += f"Result {i+1}: {result.get('title', 'No title')}\n"
            search_results_text += f"URL: {result.get('url', 'No URL')}\n"
            search_results_text += f"Content: {result.get('content', 'No content')}\n\n"
        
        # Write section content
        section_prompt = section_writer_instructions.format(
            section_title=section["title"],
            search_results=search_results_text
        )
        
        section_response = await writer.ainvoke([HumanMessage(content=section_prompt)])
        section_content = section_response.content
        
        # Update section
        updated_section = {
            "title": section["title"],
            "content": section_content,
            "subsections": section["subsections"]
        }
        
        # If there are subsections, write content for each
        if section["subsections"]:
            updated_subsections = []
            
            for subsection in section["subsections"]:
                # Generate search query for this subsection
                subsection_query = f"{state.topic} {section['title']} {subsection['title']}"
                
                # Execute search
                subsection_search_results = select_and_execute_search(
                    subsection_query, 
                    search_api, 
                    search_params
                )
                
                # Format search results for the prompt
                subsection_search_results_text = ""
                for i, result in enumerate(subsection_search_results):
                    subsection_search_results_text += f"Result {i+1}: {result.get('title', 'No title')}\n"
                    subsection_search_results_text += f"URL: {result.get('url', 'No URL')}\n"
                    subsection_search_results_text += f"Content: {result.get('content', 'No content')}\n\n"
                
                # Write subsection content
                subsection_prompt = section_writer_instructions.format(
                    section_title=subsection["title"],
                    search_results=subsection_search_results_text
                )
                
                subsection_response = await writer.ainvoke([HumanMessage(content=subsection_prompt)])
                subsection_content = subsection_response.content
                
                # Update subsection
                updated_subsection = {
                    "title": subsection["title"],
                    "content": subsection_content
                }
                
                updated_subsections.append(updated_subsection)
            
            updated_section["subsections"] = updated_subsections
        
        updated_sections.append(updated_section)
    
    # Update state
    state.sections = Sections(sections=updated_sections)
    
    return state

## Graph definition

graph = StateGraph(ReportState)

# Add nodes
graph.add_node("generate_report_plan", generate_report_plan)
graph.add_node("write_sections", write_sections)

# Add edges
graph.add_edge(START, "generate_report_plan")
graph.add_edge("generate_report_plan", "write_sections")
graph.add_edge("write_sections", END)

# Compile the graph
graph = graph.compile()

