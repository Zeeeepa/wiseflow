"""Multi-agent research graph implementation with enhanced coordination and error handling."""

import logging
import time
import asyncio
from typing import Literal, Dict, List, Any, Optional, Tuple, Set
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    select_and_execute_search,
    ResearchError,
    SearchAPIError,
    ConfigurationError
)

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

COORDINATION_PROMPT = """You are the coordination agent in a multi-agent research system. Your role is to:

1. Monitor the progress of all researcher agents
2. Identify overlaps or gaps in the research
3. Provide guidance to ensure comprehensive coverage of the topic
4. Facilitate communication between researcher agents when needed

Research Topic: {topic}
Current Research Questions and Progress:
{research_progress}

Your task is to:
1. Identify any overlaps where multiple agents are researching similar aspects
2. Identify any gaps in the research that aren't being addressed
3. Suggest adjustments to research questions to ensure comprehensive coverage
4. Facilitate knowledge sharing between agents when beneficial

Provide specific recommendations for each researcher agent to optimize the overall research effort.
"""

# Node functions

async def initialize_multi_agent_research(state: ReportState, config: RunnableConfig) -> Dict[str, Any]:
    """Initialize the multi-agent research process.
    
    Args:
        state (ReportState): The current state
        config (RunnableConfig): The configuration
        
    Returns:
        Dict[str, Any]: Updated state with research questions
    """
    start_time = time.time()
    logger.info(f"Initializing multi-agent research for topic: {state.topic}")
    
    try:
        # Get configuration
        configuration = state.config or Configuration()
        num_researchers = configuration.num_researcher_agents
        report_structure = configuration.report_structure
        
        # Initialize supervisor model
        supervisor_model_name = configuration.supervisor_model
        provider, model = supervisor_model_name.split(":", 1) if ":" in supervisor_model_name else ("openai", supervisor_model_name)
        
        supervisor = init_chat_model(
            provider=provider,
            model=model
        )
        
        # Generate research questions
        prompt = SUPERVISOR_PROMPT.format(
            topic=state.topic,
            num_researchers=num_researchers,
            report_structure=report_structure
        )
        
        response = await supervisor.ainvoke([HumanMessage(content=prompt)])
        response_content = response.content
        
        # Extract research questions
        research_questions = []
        in_questions_section = False
        
        for line in response_content.split("\n"):
            line = line.strip()
            
            # Look for sections that might contain research questions
            if any(marker in line.lower() for marker in ["research question", "subtopic", "aspect"]):
                in_questions_section = True
                continue
                
            if in_questions_section and line and not line.startswith("#"):
                # Clean up the line to extract just the question
                if line[0].isdigit() and line[1:3] in [". ", ") "]:
                    line = line[3:].strip()
                elif line[0] in ["-", "*"]:
                    line = line[1:].strip()
                    
                # If it looks like a question or topic, add it
                if line and len(line) > 10:  # Arbitrary minimum length to filter out headers
                    research_questions.append(line)
                    
                # Stop if we've found enough questions
                if len(research_questions) >= num_researchers:
                    break
        
        # If we didn't extract enough questions, generate some basic ones
        while len(research_questions) < num_researchers:
            research_questions.append(f"Research aspect {len(research_questions)+1} of {state.topic}")
        
        # Limit to the configured number of researchers
        research_questions = research_questions[:num_researchers]
        
        logger.info(f"Generated {len(research_questions)} research questions in {time.time() - start_time:.2f}s")
        
        return {
            "research_questions": research_questions,
            "research_results": [],
            "agent_status": {q: "pending" for q in research_questions},
            "coordination_feedback": {}
        }
    except Exception as e:
        logger.error(f"Error initializing multi-agent research: {str(e)}", exc_info=True)
        raise ResearchError(f"Failed to initialize multi-agent research: {str(e)}") from e

async def coordinate_research(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    """Coordinate the research efforts of multiple agents.
    
    Args:
        state (Dict[str, Any]): The current state
        config (RunnableConfig): The configuration
        
    Returns:
        Dict[str, Any]: Updated state with coordination feedback
    """
    start_time = time.time()
    logger.info("Coordinating multi-agent research")
    
    try:
        # Get configuration
        configuration = state.config or Configuration()
        
        # Skip coordination if there are fewer than 2 research questions
        if len(state.get("research_questions", [])) < 2:
            logger.info("Skipping coordination with fewer than 2 research questions")
            return state
        
        # Initialize coordination model
        supervisor_model_name = configuration.supervisor_model
        provider, model = supervisor_model_name.split(":", 1) if ":" in supervisor_model_name else ("openai", supervisor_model_name)
        
        coordinator = init_chat_model(
            provider=provider,
            model=model
        )
        
        # Prepare research progress information
        research_progress = []
        for i, question in enumerate(state.get("research_questions", [])):
            status = state.get("agent_status", {}).get(question, "pending")
            result = ""
            
            if status == "completed" and i < len(state.get("research_results", [])):
                result = state["research_results"][i].get("summary", "No summary available")
                
            research_progress.append(f"Agent {i+1}:\nQuestion: {question}\nStatus: {status}\nFindings: {result}")
        
        # Generate coordination feedback
        prompt = COORDINATION_PROMPT.format(
            topic=state.topic,
            research_progress="\n\n".join(research_progress)
        )
        
        response = await coordinator.ainvoke([HumanMessage(content=prompt)])
        response_content = response.content
        
        # Extract coordination feedback for each agent
        coordination_feedback = {}
        current_agent = None
        current_feedback = []
        
        for line in response_content.split("\n"):
            line = line.strip()
            
            # Look for agent headers
            if line.lower().startswith(("agent ", "researcher ")):
                # Save previous agent's feedback if any
                if current_agent is not None and current_feedback:
                    coordination_feedback[current_agent] = "\n".join(current_feedback)
                    current_feedback = []
                
                # Extract agent number
                try:
                    agent_num = int(line.split()[1].rstrip(":")) - 1
                    if 0 <= agent_num < len(state.get("research_questions", [])):
                        current_agent = state["research_questions"][agent_num]
                    else:
                        current_agent = None
                except (IndexError, ValueError):
                    current_agent = None
            
            # Add line to current feedback if we have an agent
            elif current_agent is not None and line:
                current_feedback.append(line)
        
        # Save the last agent's feedback
        if current_agent is not None and current_feedback:
            coordination_feedback[current_agent] = "\n".join(current_feedback)
        
        logger.info(f"Generated coordination feedback for {len(coordination_feedback)} agents in {time.time() - start_time:.2f}s")
        
        # Update the state with coordination feedback
        state["coordination_feedback"] = coordination_feedback
        return state
    except Exception as e:
        logger.error(f"Error coordinating research: {str(e)}", exc_info=True)
        # Continue without coordination rather than failing the entire process
        return state

async def execute_parallel_research(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    """Execute research tasks in parallel using multiple agents.
    
    Args:
        state (Dict[str, Any]): The current state
        config (RunnableConfig): The configuration
        
    Returns:
        Dict[str, Any]: Updated state with research results
    """
    start_time = time.time()
    logger.info("Executing parallel research with multiple agents")
    
    try:
        # Get configuration
        configuration = state.config or Configuration()
        max_concurrent = configuration.max_concurrent_agents
        timeout = configuration.agent_timeout
        
        # Get research questions
        research_questions = state.get("research_questions", [])
        if not research_questions:
            logger.warning("No research questions to process")
            return state
        
        # Initialize researcher model
        researcher_model_name = configuration.researcher_model
        provider, model = researcher_model_name.split(":", 1) if ":" in researcher_model_name else ("openai", researcher_model_name)
        
        # Create a thread pool for parallel execution
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            # Submit all research tasks
            future_to_question = {}
            for i, question in enumerate(research_questions):
                # Skip already completed questions
                if state.get("agent_status", {}).get(question) == "completed":
                    continue
                    
                # Update status to in_progress
                if "agent_status" not in state:
                    state["agent_status"] = {}
                state["agent_status"][question] = "in_progress"
                
                # Get coordination feedback if available
                coordination = state.get("coordination_feedback", {}).get(question, "")
                
                # Submit the research task
                future = executor.submit(
                    research_question,
                    question=question,
                    topic=state.topic,
                    provider=provider,
                    model=model,
                    coordination_feedback=coordination,
                    search_api=configuration.search_api,
                    search_params=get_search_params(configuration)
                )
                future_to_question[future] = question
            
            # Process results as they complete
            research_results = state.get("research_results", [])
            for future in as_completed(future_to_question, timeout=timeout):
                question = future_to_question[future]
                try:
                    result = future.result()
                    # Update status to completed
                    state["agent_status"][question] = "completed"
                    # Add result to research_results
                    research_results.append({
                        "question": question,
                        "content": result["content"],
                        "summary": result["summary"],
                        "sources": result["sources"]
                    })
                except Exception as e:
                    logger.error(f"Error researching question '{question}': {str(e)}", exc_info=True)
                    # Update status to failed
                    state["agent_status"][question] = "failed"
                    # Add error result
                    research_results.append({
                        "question": question,
                        "content": f"Research failed: {str(e)}",
                        "summary": "Research could not be completed",
                        "sources": []
                    })
        
        # Update the state with research results
        state["research_results"] = research_results
        
        logger.info(f"Completed parallel research for {len(research_results)} questions in {time.time() - start_time:.2f}s")
        return state
    except Exception as e:
        logger.error(f"Error executing parallel research: {str(e)}", exc_info=True)
        raise ResearchError(f"Failed to execute parallel research: {str(e)}") from e

def research_question(
    question: str, 
    topic: str, 
    provider: str, 
    model: str,
    coordination_feedback: str = "",
    search_api: SearchAPI = SearchAPI.TAVILY,
    search_params: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Research a specific question using a researcher agent.
    
    Args:
        question (str): The research question
        topic (str): The overall research topic
        provider (str): The model provider
        model (str): The model name
        coordination_feedback (str): Feedback from the coordination agent
        search_api (SearchAPI): The search API to use
        search_params (Dict[str, Any]): The search parameters
        
    Returns:
        Dict[str, Any]: The research results
    """
    start_time = time.time()
    logger.info(f"Researching question: {question}")
    
    try:
        # Initialize researcher model
        researcher = init_chat_model(
            provider=provider,
            model=model
        )
        
        # Generate the prompt
        prompt_text = RESEARCHER_PROMPT.format(
            research_question=question,
            topic=topic
        )
        
        # Add coordination feedback if available
        if coordination_feedback:
            prompt_text += f"\n\nCoordination Feedback:\n{coordination_feedback}"
        
        # Generate search queries
        response = researcher.invoke([HumanMessage(content=prompt_text + "\n\nFirst, generate 3-5 search queries to gather information on this question.")])
        response_content = response.content
        
        # Extract search queries
        queries = []
        in_queries_section = False
        
        for line in response_content.split("\n"):
            line = line.strip()
            
            if any(marker in line.lower() for marker in ["search quer", "queries"]):
                in_queries_section = True
                continue
                
            if in_queries_section and line and not line.startswith("#"):
                # Clean up the line
                if line[0].isdigit() and line[1:3] in [". ", ") "]:
                    line = line[3:].strip()
                elif line[0] in ["-", "*"]:
                    line = line[1:].strip()
                    
                if line and len(line) > 5:  # Arbitrary minimum length
                    queries.append(line)
                    
                # Limit to 5 queries
                if len(queries) >= 5:
                    break
        
        # If no queries were extracted, create a default one
        if not queries:
            queries = [question]
        
        # Execute searches
        all_search_results = []
        for query in queries:
            try:
                results = select_and_execute_search(query, search_api, search_params or {})
                all_search_results.append({
                    "query": query,
                    "results": results
                })
            except Exception as e:
                logger.error(f"Error executing search for query '{query}': {str(e)}", exc_info=True)
                all_search_results.append({
                    "query": query,
                    "results": [],
                    "error": str(e)
                })
        
        # Format search results for the researcher
        formatted_results = []
        for search in all_search_results:
            formatted_results.append(f"Query: {search['query']}")
            
            if "error" in search:
                formatted_results.append(f"Error: {search['error']}")
                continue
                
            for i, result in enumerate(search["results"]):
                title = result.get("title", "No title")
                content = result.get("content", result.get("text", "No content"))
                url = result.get("url", "No URL")
                
                formatted_results.append(f"Result {i+1}: {title}")
                formatted_results.append(f"URL: {url}")
                formatted_results.append(f"Content: {content[:500]}..." if len(content) > 500 else f"Content: {content}")
                formatted_results.append("")
        
        # Generate the research section
        prompt_text = RESEARCHER_PROMPT.format(
            research_question=question,
            topic=topic
        )
        
        prompt_text += "\n\nSearch Results:\n" + "\n".join(formatted_results)
        
        if coordination_feedback:
            prompt_text += f"\n\nCoordination Feedback:\n{coordination_feedback}"
            
        prompt_text += "\n\nBased on these search results, write a comprehensive section addressing the research question."
        
        response = researcher.invoke([HumanMessage(content=prompt_text)])
        section_content = response.content
        
        # Generate a summary
        summary_prompt = f"Summarize the key findings from your research on: {question}\n\nProvide a concise summary (2-3 sentences) of the main insights."
        summary_response = researcher.invoke([HumanMessage(content=summary_prompt), AIMessage(content=section_content)])
        summary = summary_response.content
        
        # Extract sources
        sources = []
        for search in all_search_results:
            for result in search.get("results", []):
                if "url" in result and result["url"] not in [s.get("url") for s in sources]:
                    sources.append({
                        "title": result.get("title", "No title"),
                        "url": result["url"]
                    })
        
        logger.info(f"Completed research for question '{question}' in {time.time() - start_time:.2f}s")
        
        return {
            "content": section_content,
            "summary": summary,
            "sources": sources
        }
    except Exception as e:
        logger.error(f"Error researching question '{question}': {str(e)}", exc_info=True)
        raise ResearchError(f"Failed to research question '{question}': {str(e)}") from e

async def integrate_research_results(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    """Integrate research results into a cohesive report.
    
    Args:
        state (Dict[str, Any]): The current state
        config (RunnableConfig): The configuration
        
    Returns:
        Dict[str, Any]: Updated state with integrated report
    """
    start_time = time.time()
    logger.info("Integrating research results")
    
    try:
        # Get configuration
        configuration = state.config or Configuration()
        report_structure = configuration.report_structure
        
        # Initialize integration model
        supervisor_model_name = configuration.supervisor_model
        provider, model = supervisor_model_name.split(":", 1) if ":" in supervisor_model_name else ("openai", supervisor_model_name)
        
        integrator = init_chat_model(
            provider=provider,
            model=model
        )
        
        # Format research sections
        research_sections = []
        for result in state.get("research_results", []):
            research_sections.append(f"Question: {result['question']}\n\n{result['content']}")
        
        # Generate the integrated report
        prompt = INTEGRATION_PROMPT.format(
            topic=state.topic,
            research_sections="\n\n---\n\n".join(research_sections),
            report_structure=report_structure
        )
        
        response = await integrator.ainvoke([HumanMessage(content=prompt)])
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
        
        logger.info(f"Integrated research results into {len(sections)} sections in {time.time() - start_time:.2f}s")
        
        return {
            "sections": final_sections
        }
    except Exception as e:
        logger.error(f"Error integrating research results: {str(e)}", exc_info=True)
        raise ResearchError(f"Failed to integrate research results: {str(e)}") from e

# Define the graph
def build_graph():
    """Build the multi-agent research graph.
    
    Returns:
        StateGraph: The compiled research graph
    """
    # Create a new graph
    builder = StateGraph(ReportState)
    
    # Add nodes
    builder.add_node("initialize", initialize_multi_agent_research)
    builder.add_node("coordinate", coordinate_research)
    builder.add_node("research", execute_parallel_research)
    builder.add_node("integrate", integrate_research_results)
    
    # Add edges
    builder.add_edge(START, "initialize")
    builder.add_edge("initialize", "research")
    builder.add_edge("research", "coordinate")
    builder.add_edge("coordinate", "research")
    builder.add_edge("research", "integrate")
    builder.add_edge("integrate", END)
    
    # Add conditional edges
    def should_coordinate(state: Dict[str, Any]) -> Literal["coordinate", "integrate"]:
        """Determine if coordination is needed.
        
        Args:
            state (Dict[str, Any]): The current state
            
        Returns:
            Literal["coordinate", "integrate"]: The next node
        """
        # Check if all research is complete
        all_complete = True
        for status in state.get("agent_status", {}).values():
            if status != "completed":
                all_complete = False
                break
        
        # If all research is complete, move to integration
        if all_complete:
            return "integrate"
        
        # Otherwise, coordinate the research
        return "coordinate"
    
    # Replace the direct edge with a conditional one
    builder.remove_edge("research", "coordinate")
    builder.remove_edge("research", "integrate")
    builder.add_conditional_edges(
        "research",
        should_coordinate,
        {
            "coordinate": "coordinate",
            "integrate": "integrate"
        }
    )
    
    # Compile the graph
    return builder.compile()

# Create the graph
graph = build_graph()
