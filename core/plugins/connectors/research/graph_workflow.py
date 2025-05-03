"""Graph-based research workflow implementation."""

from typing import Literal, Dict, List, Any, Optional
import json

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

# Graph-based research prompts

PLANNER_PROMPT = """You are a research planner. Your task is to plan a research approach for the given topic.

Topic: {topic}

Your task is to:
1. Analyze the topic and identify key aspects that need to be researched
2. Formulate an initial set of research questions
3. Create a plan for how to approach the research

Please provide:
1. A brief analysis of the topic (2-3 sentences)
2. 3-5 key research questions
3. A suggested approach for conducting the research
"""

QUERY_GENERATOR_PROMPT = """You are a search query generator. Your task is to generate effective search queries based on the research topic and current state of knowledge.

Topic: {topic}
Current Knowledge:
{current_knowledge}

Your task is to generate {num_queries} search queries that will help gather additional information on aspects of the topic that are not yet well covered.

For each query:
1. Focus on a specific aspect of the topic
2. Be precise and use terminology that will yield relevant results
3. Consider different perspectives or angles on the topic

Please provide {num_queries} search queries, each on a new line.
"""

KNOWLEDGE_SYNTHESIZER_PROMPT = """You are a knowledge synthesizer. Your task is to integrate new information with existing knowledge.

Topic: {topic}
Current Knowledge:
{current_knowledge}

New Information:
{new_information}

Your task is to:
1. Analyze the new information
2. Identify key insights and facts
3. Integrate these with the existing knowledge
4. Identify any contradictions or gaps that still need to be addressed

Please provide:
1. A synthesis of the combined knowledge (300-500 words)
2. 2-3 key insights from the new information
3. Any remaining questions or gaps in knowledge
"""

REPORT_WRITER_PROMPT = """You are a report writer. Your task is to create a comprehensive report based on the synthesized knowledge.

Topic: {topic}
Synthesized Knowledge:
{synthesized_knowledge}

The report should follow this structure:
{report_structure}

Your task is to:
1. Organize the knowledge into a logical structure
2. Write clear, concise sections that cover all aspects of the topic
3. Ensure the report is comprehensive, accurate, and well-structured
4. Include an introduction and conclusion

Please provide a complete report with appropriate section headings.
"""

REFLECTION_PROMPT = """You are a research reflector. Your task is to analyze the current state of research and identify areas for further investigation.

Topic: {topic}
Current Report:
{current_report}

Your task is to:
1. Analyze the current report for comprehensiveness and depth
2. Identify specific aspects of the topic that need further research
3. Suggest directions for the next iteration of research

Please provide:
1. An assessment of the current report (2-3 sentences)
2. 3-5 specific aspects that need further research
3. Suggested focus for the next research iteration
"""

# Node functions

async def initialize_research(state: ReportState, config: RunnableConfig):
    """Initialize the research process.
    
    This node:
    1. Sets up the initial state
    2. Creates a research plan
    """
    # Get configuration
    configuration = state.config or Configuration()
    
    # Initialize planner model
    planner_provider = configuration.planner_provider
    planner_model = configuration.planner_model
    planner_model_kwargs = configuration.planner_model_kwargs or {}
    
    planner = init_chat_model(
        provider=planner_provider,
        model=planner_model,
        **planner_model_kwargs
    )
    
    # Generate initial research plan
    prompt = PLANNER_PROMPT.format(
        topic=state.topic
    )
    
    response = await planner.ainvoke([HumanMessage(content=prompt)])
    plan_content = response.content
    
    # Initialize state with empty sections
    state.sections = Sections(sections=[
        Section(title="Research Plan", content=plan_content, subsections=[]),
        Section(title="Introduction", content="", subsections=[]),
        Section(title="Main Findings", content="", subsections=[]),
        Section(title="Conclusion", content="", subsections=[])
    ])
    
    return state

async def generate_queries(state: ReportState, config: RunnableConfig):
    """Generate search queries based on current knowledge.
    
    This node:
    1. Analyzes the current state of knowledge
    2. Generates targeted search queries
    """
    # Get configuration
    configuration = state.config or Configuration()
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
    
    # Format current knowledge
    current_knowledge = ""
    for section in state.sections.sections:
        if section.content:
            current_knowledge += f"## {section.title}\n{section.content}\n\n"
    
    # Generate search queries
    prompt = QUERY_GENERATOR_PROMPT.format(
        topic=state.topic,
        current_knowledge=current_knowledge,
        num_queries=num_queries
    )
    
    response = await planner.ainvoke([HumanMessage(content=prompt)])
    queries_content = response.content
    
    # Extract queries
    queries = []
    for line in queries_content.split("\n"):
        line = line.strip()
        if line and not line.startswith("#"):
            # Clean up the line
            clean_line = line
            if clean_line[0].isdigit() and clean_line[1:3] in [". ", ") "]:
                clean_line = clean_line[3:].strip()
            elif clean_line[0] in ["-", "*"]:
                clean_line = clean_line[1:].strip()
                
            queries.append({"text": clean_line, "metadata": {}})
    
    # Limit to the specified number of queries
    queries = queries[:num_queries]
    
    # If no queries were extracted, create default ones
    if not queries:
        queries = [
            {"text": f"latest research on {state.topic}", "metadata": {}},
            {"text": f"key aspects of {state.topic}", "metadata": {}}
        ]
    
    # Update state
    state.queries = queries
    
    return state

async def execute_searches(state: ReportState, config: RunnableConfig):
    """Execute searches based on generated queries.
    
    This node:
    1. Performs searches using the specified search API
    2. Stores search results in the state
    """
    # Get configuration
    configuration = state.config or Configuration()
    search_api = configuration.search_api
    search_params = get_search_params(configuration)
    
    # Execute searches for each query
    search_results = []
    for query in state.queries:
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
    
    # Update state
    state.search_results = search_results
    
    return state

async def synthesize_knowledge(state: ReportState, config: RunnableConfig):
    """Synthesize new information with existing knowledge.
    
    This node:
    1. Analyzes search results
    2. Integrates new information with existing knowledge
    """
    # Get configuration
    configuration = state.config or Configuration()
    
    # Initialize writer model
    writer_provider = configuration.writer_provider
    writer_model = configuration.writer_model
    writer_model_kwargs = configuration.writer_model_kwargs or {}
    
    writer = init_chat_model(
        provider=writer_provider,
        model=writer_model,
        **writer_model_kwargs
    )
    
    # Format current knowledge
    current_knowledge = ""
    for section in state.sections.sections:
        if section.content:
            current_knowledge += f"## {section.title}\n{section.content}\n\n"
    
    # Format new information from search results
    new_information = ""
    for result in state.search_results:
        new_information += f"Search Query: {result['query']}\n\n"
        for item in result['results']:
            new_information += f"Title: {item.get('title', 'No title')}\n"
            new_information += f"URL: {item.get('url', 'No URL')}\n"
            new_information += f"Content: {item.get('content', 'No content')[:500]}...\n\n"
    
    # Synthesize knowledge
    prompt = KNOWLEDGE_SYNTHESIZER_PROMPT.format(
        topic=state.topic,
        current_knowledge=current_knowledge,
        new_information=new_information
    )
    
    response = await writer.ainvoke([HumanMessage(content=prompt)])
    synthesis = response.content
    
    # Update state - add or update Synthesis section
    synthesis_section = None
    for section in state.sections.sections:
        if section.title == "Knowledge Synthesis":
            synthesis_section = section
            break
    
    if synthesis_section:
        synthesis_section.content = synthesis
    else:
        state.sections.sections.append(Section(
            title="Knowledge Synthesis",
            content=synthesis,
            subsections=[]
        ))
    
    return state

async def update_report(state: ReportState, config: RunnableConfig):
    """Update the report based on synthesized knowledge.
    
    This node:
    1. Reorganizes and rewrites the report sections
    2. Ensures the report is comprehensive and well-structured
    """
    # Get configuration
    configuration = state.config or Configuration()
    report_structure = configuration.report_structure
    
    # Initialize writer model
    writer_provider = configuration.writer_provider
    writer_model = configuration.writer_model
    writer_model_kwargs = configuration.writer_model_kwargs or {}
    
    writer = init_chat_model(
        provider=writer_provider,
        model=writer_model,
        **writer_model_kwargs
    )
    
    # Find the synthesis section
    synthesized_knowledge = ""
    for section in state.sections.sections:
        if section.title == "Knowledge Synthesis":
            synthesized_knowledge = section.content
            break
    
    # If no synthesis found, use all sections
    if not synthesized_knowledge:
        for section in state.sections.sections:
            if section.content:
                synthesized_knowledge += f"## {section.title}\n{section.content}\n\n"
    
    # Generate updated report
    prompt = REPORT_WRITER_PROMPT.format(
        topic=state.topic,
        synthesized_knowledge=synthesized_knowledge,
        report_structure=report_structure
    )
    
    response = await writer.ainvoke([HumanMessage(content=prompt)])
    report_content = response.content
    
    # Extract sections from report content
    sections = []
    current_section = None
    current_content = []
    
    for line in report_content.split("\n"):
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
    
    # If no sections were extracted, create default ones
    if not sections:
        sections = [
            Section(title="Introduction", content="", subsections=[]),
            Section(title=f"Overview of {state.topic}", content=report_content, subsections=[]),
            Section(title="Conclusion", content="", subsections=[])
        ]
    
    # Preserve the Research Plan section
    research_plan = None
    for section in state.sections.sections:
        if section.title == "Research Plan":
            research_plan = section
            break
    
    if research_plan:
        sections.insert(0, research_plan)
    
    # Update state
    state.sections = Sections(sections=sections)
    
    return state

async def reflect_on_research(state: ReportState, config: RunnableConfig):
    """Reflect on the current state of research.
    
    This node:
    1. Analyzes the current report
    2. Identifies areas for further research
    3. Decides whether to continue or finalize
    """
    # Get configuration
    configuration = state.config or Configuration()
    max_search_depth = configuration.max_search_depth
    
    # Initialize planner model
    planner_provider = configuration.planner_provider
    planner_model = configuration.planner_model
    planner_model_kwargs = configuration.planner_model_kwargs or {}
    
    planner = init_chat_model(
        provider=planner_provider,
        model=planner_model,
        **planner_model_kwargs
    )
    
    # Format current report
    current_report = ""
    for section in state.sections.sections:
        if section.title != "Research Plan" and section.title != "Knowledge Synthesis":
            current_report += f"## {section.title}\n{section.content}\n\n"
    
    # Generate reflection
    prompt = REFLECTION_PROMPT.format(
        topic=state.topic,
        current_report=current_report
    )
    
    response = await planner.ainvoke([HumanMessage(content=prompt)])
    reflection = response.content
    
    # Add reflection to state
    reflection_section = None
    for section in state.sections.sections:
        if section.title == "Research Reflection":
            reflection_section = section
            break
    
    if reflection_section:
        reflection_section.content = reflection
    else:
        state.sections.sections.append(Section(
            title="Research Reflection",
            content=reflection,
            subsections=[]
        ))
    
    # Check if we've reached the maximum search depth
    current_depth = len(state.search_results) // configuration.number_of_queries
    
    if current_depth >= max_search_depth:
        return {"next": "finalize_report"}
    else:
        return {"next": "continue_research"}

async def finalize_report(state: ReportState, config: RunnableConfig):
    """Finalize the report.
    
    This node:
    1. Cleans up the report
    2. Removes working sections
    3. Ensures the report is ready for presentation
    """
    # Get configuration
    configuration = state.config or Configuration()
    
    # Initialize writer model
    writer_provider = configuration.writer_provider
    writer_model = configuration.writer_model
    writer_model_kwargs = configuration.writer_model_kwargs or {}
    
    writer = init_chat_model(
        provider=writer_provider,
        model=writer_model,
        **writer_model_kwargs
    )
    
    # Filter out working sections
    final_sections = []
    for section in state.sections.sections:
        if section.title not in ["Research Plan", "Knowledge Synthesis", "Research Reflection"]:
            final_sections.append(section)
    
    # Ensure we have at least introduction, body, and conclusion
    if not final_sections:
        final_sections = [
            Section(title="Introduction", content="", subsections=[]),
            Section(title=f"Overview of {state.topic}", content="", subsections=[]),
            Section(title="Conclusion", content="", subsections=[])
        ]
    elif len(final_sections) < 3:
        # Check if we have introduction
        has_intro = any(s.title.lower() in ["introduction", "overview", "background"] for s in final_sections)
        if not has_intro:
            final_sections.insert(0, Section(title="Introduction", content="", subsections=[]))
        
        # Check if we have conclusion
        has_conclusion = any(s.title.lower() in ["conclusion", "summary", "final thoughts"] for s in final_sections)
        if not has_conclusion:
            final_sections.append(Section(title="Conclusion", content="", subsections=[]))
    
    # Update state
    state.sections = Sections(sections=final_sections)
    
    return state

# Graph definition

graph = StateGraph(ReportState)

# Add nodes
graph.add_node("initialize_research", initialize_research)
graph.add_node("generate_queries", generate_queries)
graph.add_node("execute_searches", execute_searches)
graph.add_node("synthesize_knowledge", synthesize_knowledge)
graph.add_node("update_report", update_report)
graph.add_node("reflect_on_research", reflect_on_research)
graph.add_node("finalize_report", finalize_report)

# Add edges
graph.add_edge(START, "initialize_research")
graph.add_edge("initialize_research", "generate_queries")
graph.add_edge("generate_queries", "execute_searches")
graph.add_edge("execute_searches", "synthesize_knowledge")
graph.add_edge("synthesize_knowledge", "update_report")
graph.add_edge("update_report", "reflect_on_research")

# Add conditional edges
graph.add_conditional_edges(
    "reflect_on_research",
    lambda x: x["next"],
    {
        "continue_research": "generate_queries",
        "finalize_report": "finalize_report"
    }
)

graph.add_edge("finalize_report", END)

# Compile the graph
graph = graph.compile()

