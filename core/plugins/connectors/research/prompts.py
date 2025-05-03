"""
Prompts for the research connector.
"""

# Prompt for generating search queries for report planning
report_planner_query_writer_instructions = """You are a research assistant tasked with generating search queries to help plan a report on the topic: {topic}.

The report will be organized as follows:
{report_organization}

Your task is to generate {number_of_queries} search queries that will help gather information to plan the sections of this report.

The queries should:
1. Cover different aspects of the topic
2. Be specific enough to return useful results
3. Help identify the key sections that should be included in the report
4. Be formulated to return factual, informative content rather than opinion pieces

Generate exactly {number_of_queries} search queries."""

# Prompt for planning report sections
report_planner_instructions = """You are a research assistant tasked with planning a report on the topic: {topic}.

The report should be organized as follows:
{report_organization}

Based on the following search results, plan the sections of the report:

{context}

{feedback}

For each section, determine:
1. A clear, descriptive name
2. A brief description of what the section should cover
3. Whether the section requires web research (true/false)
4. Initial content (leave empty for now)

Sections that typically require research:
- Factual information
- Current trends and statistics
- Technical details
- Case studies and examples

Sections that typically don't require research:
- Introduction (based on the topic)
- Conclusion (based on the researched sections)
- Methodology (if it's a standard approach)

Aim for 3-5 well-structured sections that together will create a comprehensive report on the topic."""

# Prompt for generating search queries for section research
query_writer_instructions = """You are a research assistant tasked with generating search queries for a section of a report.

The overall report topic is: {topic}
The specific section topic is: {section_topic}

Your task is to generate {number_of_queries} search queries that will help gather information for this specific section.

The queries should:
1. Be specific to the section topic
2. Cover different aspects of the section topic
3. Be formulated to return factual, informative content
4. Be diverse enough to gather comprehensive information

Generate exactly {number_of_queries} search queries."""

# Prompt for writing a section based on research
section_writer_instructions = """You are a research assistant tasked with writing a section of a report based on web search results.

Your task is to:
1. Analyze the search results provided
2. Extract relevant information for the section topic
3. Organize the information in a coherent, well-structured manner
4. Write a comprehensive section that covers the topic thoroughly
5. Use factual information from the search results
6. Cite sources where appropriate

The section should be well-written, informative, and based on the search results provided."""

# Input format for section writer
section_writer_inputs = """Overall report topic: {topic}
Section name: {section_name}
Section topic: {section_topic}

Current section content (may be empty):
{section_content}

Search results:
{context}

Write a comprehensive section on this topic based on the search results provided."""

# Prompt for writing final sections (like conclusion) based on researched sections
final_section_writer_instructions = """You are a research assistant tasked with writing a section of a report that doesn't require direct research.

The overall report topic is: {topic}
The section you need to write is: {section_name}
The section topic is: {section_topic}

This section should be based on the following completed sections of the report:

{context}

Your task is to:
1. Analyze the completed sections
2. Extract key points and insights
3. Synthesize the information into a coherent section
4. For conclusions, summarize the main findings and provide closing thoughts
5. For introductions, provide an overview of the topic and what will be covered

The section should be well-written, informative, and tie together the other sections of the report."""

# Prompt for evaluating section quality and identifying missing information
section_grader_instructions = """You are a research assistant tasked with evaluating the quality of a section of a report.

The overall report topic is: {topic}
The section topic is: {section_topic}

Here is the current section content:
{section}

Your task is to:
1. Evaluate whether the section adequately covers the topic
2. Identify any missing information or gaps in coverage
3. Determine if the section needs more research

Grade the section as either "pass" or "fail":
- "pass" if the section adequately covers the topic with sufficient detail and accuracy
- "fail" if the section has significant gaps, inaccuracies, or missing information

If the grade is "fail", provide {number_of_follow_up_queries} specific search queries that would help gather the missing information."""

