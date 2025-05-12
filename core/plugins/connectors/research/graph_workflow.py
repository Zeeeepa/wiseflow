"""Graph-based research workflow implementation with enhanced efficiency and error handling."""

import logging
import time
import json
from typing import Literal, Dict, List, Any, Optional, Set, Tuple
import asyncio
from concurrent.futures import ThreadPoolExecutor

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
    select_and_execute_search,
    ResearchError,
    SearchAPIError,
    ConfigurationError
)

logger = logging.getLogger(__name__)

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
4. Include an introduction that provides context and a conclusion that summarizes key findings
"""

# Enhanced prompts for better efficiency

PRIORITY_ANALYZER_PROMPT = """You are a research priority analyzer. Your task is to identify the most important aspects of a topic that need further research.

Topic: {topic}
Current Knowledge:
{current_knowledge}

Your task is to:
1. Analyze the current knowledge about the topic
2. Identify the 3 most important aspects that need further research
3. Rank these aspects in order of priority
4. Explain why each aspect is important

For each priority aspect, provide:
1. A clear description of the aspect
2. Why it's important to research this aspect
3. What specific information we need to gather
"""

KNOWLEDGE_EVALUATOR_PROMPT = """You are a knowledge evaluator. Your task is to assess the quality and completeness of the current knowledge on a topic.

Topic: {topic}
Current Knowledge:
{current_knowledge}

Your task is to:
1. Evaluate the comprehensiveness of the current knowledge
2. Identify any biases or limitations in the information
3. Assess the reliability of the sources
4. Determine if the knowledge is sufficient for a comprehensive report

Please provide:
1. An overall assessment of the knowledge quality (1-10 scale)
2. Specific strengths of the current knowledge
3. Specific weaknesses or gaps that need to be addressed
4. Recommendations for improving the knowledge base
"""

# Node functions

async def plan_research(state: ReportState, config: RunnableConfig) -> Dict[str, Any]:
    """Plan the research approach for a topic with enhanced efficiency.
    
    Args:
        state (ReportState): The current state
        config (RunnableConfig): The configuration
        
    Returns:
        Dict[str, Any]: Updated state with research plan
    """
    start_time = time.time()
    logger.info(f"Planning research for topic: {state.topic}")
    
    try:
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
        
        # Generate research plan
        prompt = PLANNER_PROMPT.format(
            topic=state.topic
        )
        
        response = await planner.ainvoke([HumanMessage(content=prompt)])
        plan = response.content
        
        # Extract research questions
        research_questions = []
        in_questions_section = False
        
        for line in plan.split("\n"):
            line = line.strip()
            
            if "research question" in line.lower() or "key question" in line.lower():
                in_questions_section = True
                continue
                
            if in_questions_section and line and not line.startswith("#"):
                # Clean up the line
                if line[0].isdigit() and line[1:3] in [". ", ") "]:
                    line = line[3:].strip()
                elif line[0] in ["-", "*"]:
                    line = line[1:].strip()
                    
                if line and len(line) > 10:  # Arbitrary minimum length
                    research_questions.append(line)
        
        # Analyze research priorities
        priority_prompt = PRIORITY_ANALYZER_PROMPT.format(
            topic=state.topic,
            current_knowledge="No knowledge gathered yet."
        )
        
        priority_response = await planner.ainvoke([HumanMessage(content=priority_prompt)])
        priorities = priority_response.content
        
        # Extract priority aspects
        priority_aspects = []
        in_priority_section = False
        current_priority = None
        current_description = []
        
        for line in priorities.split("\n"):
            line = line.strip()
            
            if "priority" in line.lower() or "aspect" in line.lower() and line[0].isdigit():
                # Save previous priority if any
                if current_priority and current_description:
                    priority_aspects.append({
                        "aspect": current_priority,
                        "description": "\n".join(current_description)
                    })
                    current_description = []
                
                # Start new priority
                current_priority = line
                in_priority_section = True
            elif in_priority_section and line:
                current_description.append(line)
        
        # Save the last priority
        if current_priority and current_description:
            priority_aspects.append({
                "aspect": current_priority,
                "description": "\n".join(current_description)
            })
        
        logger.info(f"Generated research plan with {len(research_questions)} questions and {len(priority_aspects)} priority aspects in {time.time() - start_time:.2f}s")
        
        return {
            "plan": plan,
            "research_questions": research_questions,
            "priority_aspects": priority_aspects,
            "knowledge_base": "Initial planning phase completed. No research conducted yet.",
            "iteration": 0,
            "max_iterations": configuration.max_search_depth
        }
    except Exception as e:
        logger.error(f"Error planning research: {str(e)}", exc_info=True)
        raise ResearchError(f"Failed to plan research: {str(e)}") from e

async def generate_search_queries(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    """Generate search queries based on the current knowledge and research priorities.
    
    Args:
        state (Dict[str, Any]): The current state
        config (RunnableConfig): The configuration
        
    Returns:
        Dict[str, Any]: Updated state with search queries
    """
    start_time = time.time()
    logger.info("Generating search queries")
    
    try:
        # Get configuration
        configuration = state.config or Configuration()
        num_queries = configuration.number_of_queries
        
        # Initialize query generator model
        planner_provider = configuration.planner_provider
        planner_model = configuration.planner_model
        planner_model_kwargs = configuration.planner_model_kwargs or {}
        
        query_generator = init_chat_model(
            provider=planner_provider,
            model=planner_model,
            **planner_model_kwargs
        )
        
        # Prepare current knowledge
        current_knowledge = state.get("knowledge_base", "No knowledge gathered yet.")
        
        # Include priority aspects in the prompt
        priority_aspects = state.get("priority_aspects", [])
        priority_text = ""
        
        if priority_aspects:
            priority_text = "Priority Research Aspects:\n"
            for aspect in priority_aspects:
                priority_text += f"- {aspect['aspect']}\n"
        
        # Generate search queries
        prompt = QUERY_GENERATOR_PROMPT.format(
            topic=state.topic,
            current_knowledge=current_knowledge + "\n\n" + priority_text,
            num_queries=num_queries
        )
        
        response = await query_generator.ainvoke([HumanMessage(content=prompt)])
        response_content = response.content
        
        # Extract queries
        queries = []
        for line in response_content.split("\n"):
            line = line.strip()
            
            if line and not line.startswith("#") and len(line) > 10:
                # Clean up the line
                if line[0].isdigit() and line[1:3] in [". ", ") "]:
                    line = line[3:].strip()
                elif line[0] in ["-", "*"]:
                    line = line[1:].strip()
                
                if line:
                    queries.append(line)
                    
                # Limit to the configured number of queries
                if len(queries) >= num_queries:
                    break
        
        # If we didn't get enough queries, add some based on priority aspects
        while len(queries) < num_queries and priority_aspects:
            for aspect in priority_aspects:
                aspect_text = aspect["aspect"]
                if isinstance(aspect_text, str) and ":" in aspect_text:
                    aspect_text = aspect_text.split(":", 1)[1].strip()
                
                queries.append(f"Research on {aspect_text} related to {state.topic}")
                
                if len(queries) >= num_queries:
                    break
        
        # If we still don't have enough queries, add generic ones
        while len(queries) < num_queries:
            queries.append(f"Information about {state.topic} aspect {len(queries)+1}")
        
        logger.info(f"Generated {len(queries)} search queries in {time.time() - start_time:.2f}s")
        
        return {
            "queries": queries
        }
    except Exception as e:
        logger.error(f"Error generating search queries: {str(e)}", exc_info=True)
        raise ResearchError(f"Failed to generate search queries: {str(e)}") from e

async def execute_parallel_searches(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    """Execute search queries in parallel for better efficiency.
    
    Args:
        state (Dict[str, Any]): The current state
        config (RunnableConfig): The configuration
        
    Returns:
        Dict[str, Any]: Updated state with search results
    """
    start_time = time.time()
    logger.info("Executing parallel searches")
    
    try:
        # Get configuration
        configuration = state.config or Configuration()
        search_api = configuration.search_api
        search_params = get_search_params(configuration)
        
        # Get queries
        queries = state.get("queries", [])
        if not queries:
            logger.warning("No queries to search")
            return state
        
        # Execute searches in parallel
        search_results = []
        
        with ThreadPoolExecutor(max_workers=min(len(queries), 5)) as executor:
            # Submit all search tasks
            future_to_query = {
                executor.submit(
                    select_and_execute_search, 
                    query, 
                    search_api, 
                    search_params
                ): query for query in queries
            }
            
            # Process results as they complete
            for future in future_to_query:
                query = future_to_query[future]
                try:
                    results = future.result()
                    search_results.append({
                        "query": query,
                        "results": results
                    })
                except Exception as e:
                    logger.error(f"Error executing search for query '{query}': {str(e)}", exc_info=True)
                    search_results.append({
                        "query": query,
                        "results": [],
                        "error": str(e)
                    })
        
        logger.info(f"Completed {len(search_results)} searches in {time.time() - start_time:.2f}s")
        
        return {
            "search_results": search_results
        }
    except Exception as e:
        logger.error(f"Error executing parallel searches: {str(e)}", exc_info=True)
        raise ResearchError(f"Failed to execute parallel searches: {str(e)}") from e

async def synthesize_knowledge(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    """Synthesize new information with existing knowledge.
    
    Args:
        state (Dict[str, Any]): The current state
        config (RunnableConfig): The configuration
        
    Returns:
        Dict[str, Any]: Updated state with synthesized knowledge
    """
    start_time = time.time()
    logger.info("Synthesizing knowledge")
    
    try:
        # Get configuration
        configuration = state.config or Configuration()
        
        # Initialize synthesizer model
        planner_provider = configuration.planner_provider
        planner_model = configuration.planner_model
        planner_model_kwargs = configuration.planner_model_kwargs or {}
        
        synthesizer = init_chat_model(
            provider=planner_provider,
            model=planner_model,
            **planner_model_kwargs
        )
        
        # Prepare current knowledge
        current_knowledge = state.get("knowledge_base", "No knowledge gathered yet.")
        
        # Format search results
        search_results = state.get("search_results", [])
        new_information = []
        
        for search in search_results:
            new_information.append(f"Query: {search['query']}")
            
            if "error" in search:
                new_information.append(f"Error: {search['error']}")
                continue
                
            for i, result in enumerate(search["results"]):
                title = result.get("title", "No title")
                content = result.get("content", result.get("text", "No content"))
                url = result.get("url", "No URL")
                
                new_information.append(f"Result {i+1}: {title}")
                new_information.append(f"URL: {url}")
                new_information.append(f"Content: {content[:500]}..." if len(content) > 500 else f"Content: {content}")
                new_information.append("")
        
        # Synthesize knowledge
        prompt = KNOWLEDGE_SYNTHESIZER_PROMPT.format(
            topic=state.topic,
            current_knowledge=current_knowledge,
            new_information="\n".join(new_information)
        )
        
        response = await synthesizer.ainvoke([HumanMessage(content=prompt)])
        synthesis = response.content
        
        # Evaluate knowledge quality
        evaluation_prompt = KNOWLEDGE_EVALUATOR_PROMPT.format(
            topic=state.topic,
            current_knowledge=synthesis
        )
        
        evaluation_response = await synthesizer.ainvoke([HumanMessage(content=evaluation_prompt)])
        evaluation = evaluation_response.content
        
        # Extract knowledge quality score
        knowledge_score = 0
        for line in evaluation.split("\n"):
            if "assessment" in line.lower() and "scale" in line.lower():
                try:
                    # Try to extract a number from the line
                    for word in line.split():
                        if word.isdigit() and 1 <= int(word) <= 10:
                            knowledge_score = int(word)
                            break
                except ValueError:
                    pass
        
        logger.info(f"Synthesized knowledge with quality score {knowledge_score} in {time.time() - start_time:.2f}s")
        
        return {
            "knowledge_base": synthesis,
            "knowledge_evaluation": evaluation,
            "knowledge_score": knowledge_score,
            "iteration": state.get("iteration", 0) + 1
        }
    except Exception as e:
        logger.error(f"Error synthesizing knowledge: {str(e)}", exc_info=True)
        raise ResearchError(f"Failed to synthesize knowledge: {str(e)}") from e

def should_continue_research(state: Dict[str, Any]) -> Literal["generate_queries", "write_report"]:
    """Determine if more research is needed or if we should write the report.
    
    Args:
        state (Dict[str, Any]): The current state
        
    Returns:
        Literal["generate_queries", "write_report"]: The next node
    """
    # Check if we've reached the maximum number of iterations
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 1)
    
    if iteration >= max_iterations:
        logger.info(f"Reached maximum iterations ({max_iterations}), writing report")
        return "write_report"
    
    # Check if the knowledge quality is sufficient
    knowledge_score = state.get("knowledge_score", 0)
    if knowledge_score >= 8:  # Threshold for sufficient knowledge
        logger.info(f"Knowledge score ({knowledge_score}) is sufficient, writing report")
        return "write_report"
    
    # Continue research
    logger.info(f"Continuing research (iteration {iteration+1}/{max_iterations}, knowledge score: {knowledge_score})")
    return "generate_queries"

async def write_report(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    """Write the final report based on the synthesized knowledge.
    
    Args:
        state (Dict[str, Any]): The current state
        config (RunnableConfig): The configuration
        
    Returns:
        Dict[str, Any]: Updated state with report sections
    """
    start_time = time.time()
    logger.info("Writing final report")
    
    try:
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
        
        # Prepare synthesized knowledge
        synthesized_knowledge = state.get("knowledge_base", "No knowledge gathered.")
        
        # Write the report
        prompt = REPORT_WRITER_PROMPT.format(
            topic=state.topic,
            synthesized_knowledge=synthesized_knowledge,
            report_structure=report_structure
        )
        
        response = await writer.ainvoke([HumanMessage(content=prompt)])
        report_content = response.content
        
        # Parse the report into sections
        sections = []
        current_section = None
        current_content = []
        
        for line in report_content.split("\n"):
            # Check if this is a section header
            if line.startswith("# "):
                # Save the previous section if any
                if current_section is not None and current_content:
                    sections.append({
                        "title": current_section,
                        "content": "\n".join(current_content),
                        "subsections": []
                    })
                    current_content = []
                
                # Start a new section
                current_section = line[2:].strip()
            
            # Check if this is a subsection header
            elif line.startswith("## ") and current_section is not None:
                # Save the current content to the section
                if current_content:
                    if not sections:
                        sections.append({
                            "title": current_section,
                            "content": "\n".join(current_content),
                            "subsections": []
                        })
                    else:
                        sections[-1]["content"] = "\n".join(current_content)
                    current_content = []
                
                # Add the subsection
                subsection_title = line[3:].strip()
                if sections:
                    sections[-1]["subsections"].append({
                        "title": subsection_title,
                        "content": ""
                    })
            
            # Check if this is a subsection content
            elif line.startswith("### ") and current_section is not None:
                # Ignore these deeper headers for now
                continue
            
            # Add the line to the current content
            elif current_section is not None:
                current_content.append(line)
        
        # Save the last section
        if current_section is not None and current_content:
            if not sections:
                sections.append({
                    "title": current_section,
                    "content": "\n".join(current_content),
                    "subsections": []
                })
            else:
                # Check if this is content for the last section or a subsection
                if sections[-1]["subsections"]:
                    # Assume it's for the last subsection
                    sections[-1]["subsections"][-1]["content"] = "\n".join(current_content)
                else:
                    # It's for the section itself
                    sections[-1]["content"] = "\n".join(current_content)
        
        # Create the final report sections
        final_sections = Sections(sections=[
            Section(
                title=section["title"],
                content=section["content"],
                subsections=[
                    Section(title=subsection["title"], content=subsection["content"])
                    for subsection in section["subsections"]
                ]
            )
            for section in sections
        ])
        
        logger.info(f"Wrote report with {len(sections)} sections in {time.time() - start_time:.2f}s")
        
        return {
            "sections": final_sections
        }
    except Exception as e:
        logger.error(f"Error writing report: {str(e)}", exc_info=True)
        raise ResearchError(f"Failed to write report: {str(e)}") from e

def visualize_graph(state: Dict[str, Any]) -> None:
    """Visualize the research graph if enabled.
    
    Args:
        state (Dict[str, Any]): The current state
    """
    try:
        # Get configuration
        configuration = state.config or Configuration()
        
        if not configuration.visualization_enabled:
            return
            
        visualization_path = configuration.visualization_path
        
        # Create a simple HTML visualization
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Research Graph Visualization</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .node { margin: 10px; padding: 10px; border: 1px solid #ccc; border-radius: 5px; }
                .completed { background-color: #d4edda; }
                .in-progress { background-color: #fff3cd; }
                .pending { background-color: #f8f9fa; }
                .error { background-color: #f8d7da; }
                h1 { color: #333; }
                h2 { color: #666; }
                pre { background-color: #f8f9fa; padding: 10px; border-radius: 5px; overflow: auto; }
            </style>
        </head>
        <body>
            <h1>Research Graph: {topic}</h1>
            <div class="node completed">
                <h2>Research Plan</h2>
                <pre>{plan}</pre>
            </div>
            <div class="node {queries_status}">
                <h2>Search Queries</h2>
                <pre>{queries}</pre>
            </div>
            <div class="node {search_status}">
                <h2>Search Results</h2>
                <pre>{search_results}</pre>
            </div>
            <div class="node {knowledge_status}">
                <h2>Knowledge Base</h2>
                <pre>{knowledge_base}</pre>
            </div>
            <div class="node {report_status}">
                <h2>Final Report</h2>
                <pre>{report}</pre>
            </div>
        </body>
        </html>
        """
        
        # Determine node statuses
        queries_status = "completed" if "queries" in state else "pending"
        search_status = "completed" if "search_results" in state else "pending"
        knowledge_status = "completed" if "knowledge_base" in state else "pending"
        report_status = "completed" if "sections" in state else "pending"
        
        # Format state data for visualization
        plan = state.get("plan", "Not generated yet")
        queries = "\n".join(state.get("queries", ["Not generated yet"]))
        
        search_results = "Not executed yet"
        if "search_results" in state:
            search_results_lines = []
            for search in state["search_results"]:
                search_results_lines.append(f"Query: {search['query']}")
                if "error" in search:
                    search_results_lines.append(f"Error: {search['error']}")
                else:
                    search_results_lines.append(f"Results: {len(search['results'])} found")
            search_results = "\n".join(search_results_lines)
        
        knowledge_base = state.get("knowledge_base", "Not synthesized yet")
        
        report = "Not written yet"
        if "sections" in state:
            report_lines = []
            for section in state["sections"].sections:
                report_lines.append(f"# {section.title}")
                report_lines.append(section.content[:200] + "..." if len(section.content) > 200 else section.content)
                for subsection in section.subsections:
                    report_lines.append(f"## {subsection.title}")
                    report_lines.append(subsection.content[:100] + "..." if len(subsection.content) > 100 else subsection.content)
            report = "\n".join(report_lines)
        
        # Fill in the template
        html = html.format(
            topic=state.topic,
            plan=plan,
            queries=queries,
            queries_status=queries_status,
            search_results=search_results,
            search_status=search_status,
            knowledge_base=knowledge_base[:500] + "..." if len(knowledge_base) > 500 else knowledge_base,
            knowledge_status=knowledge_status,
            report=report,
            report_status=report_status
        )
        
        # Write the visualization to file
        with open(visualization_path, "w") as f:
            f.write(html)
            
        logger.info(f"Visualization saved to {visualization_path}")
    except Exception as e:
        logger.error(f"Error visualizing graph: {str(e)}", exc_info=True)
        # Don't raise an exception, just log the error

# Define the graph
def build_graph():
    """Build the graph-based research workflow.
    
    Returns:
        StateGraph: The compiled research graph
    """
    # Create a new graph
    builder = StateGraph(ReportState)
    
    # Add nodes
    builder.add_node("plan_research", plan_research)
    builder.add_node("generate_queries", generate_search_queries)
    builder.add_node("execute_searches", execute_parallel_searches)
    builder.add_node("synthesize_knowledge", synthesize_knowledge)
    builder.add_node("write_report", write_report)
    
    # Add edges
    builder.add_edge(START, "plan_research")
    builder.add_edge("plan_research", "generate_queries")
    builder.add_edge("generate_queries", "execute_searches")
    builder.add_edge("execute_searches", "synthesize_knowledge")
    
    # Add conditional edge for research iteration
    builder.add_conditional_edges(
        "synthesize_knowledge",
        should_continue_research,
        {
            "generate_queries": "generate_queries",
            "write_report": "write_report"
        }
    )
    
    builder.add_edge("write_report", END)
    
    # Compile the graph
    return builder.compile()

# Create the graph
graph = build_graph()
