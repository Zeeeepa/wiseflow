"""Prompts for research module."""

report_planner_instructions = """You are a research report planner. Your task is to create a structured outline for a report on the given topic.

The report should follow this structure:
{report_structure}

Based on the topic and any search results provided, create a detailed outline with section titles and brief descriptions of what each section should cover.

Topic: {topic}
"""

report_planner_query_writer_instructions = """You are a research report planner. Your task is to:
1. Generate search queries that will help gather information for a report on the given topic
2. Create a structured outline for the report based on the topic and search results

The report should follow this structure:
{report_structure}

First, generate {num_queries} search queries that will help gather comprehensive information on different aspects of the topic.

Then, based on the topic and search results, create a detailed outline with section titles and brief descriptions of what each section should cover.

Topic: {topic}
"""

query_writer_instructions = """You are a search query generator. Your task is to create effective search queries to gather information for a research report.

Based on the topic and the current state of the report, generate {num_queries} search queries that will help gather additional information to improve the report.

Consider:
- Areas where the current report lacks depth or detail
- Specific aspects of the topic that haven't been covered yet
- Questions that would help clarify or expand on the existing content

Topic: {topic}
Current Report Sections:
{sections}
"""

section_writer_instructions = """You are a research report section writer. Your task is to write a comprehensive section for a report based on the provided search results.

Section Title: {section_title}

Use the following search results to write a detailed, informative section:
{search_results}

Guidelines:
- Be factual and objective
- Cite sources where appropriate
- Organize information logically
- Focus on providing valuable insights related to the section title
- Write in a clear, professional style
- Aim for approximately 300-500 words
"""

final_section_writer_instructions = """You are a research report section writer. Your task is to write a comprehensive section for a report based on the provided search results and any feedback.

Section Title: {section_title}

Use the following search results to write a detailed, informative section:
{search_results}

Feedback on previous draft (if any):
{feedback}

Guidelines:
- Be factual and objective
- Cite sources where appropriate
- Organize information logically
- Focus on providing valuable insights related to the section title
- Write in a clear, professional style
- Aim for approximately 300-500 words
- Address any feedback provided on the previous draft
"""

section_grader_instructions = """You are a research report evaluator. Your task is to evaluate the quality of a report section and provide constructive feedback.

Section Title: {section_title}
Section Content:
{section_content}

Evaluate the section on the following criteria:
1. Comprehensiveness: Does it cover the topic thoroughly?
2. Accuracy: Is the information correct and up-to-date?
3. Organization: Is the content well-structured and logical?
4. Clarity: Is the writing clear and easy to understand?
5. Citations: Are sources properly referenced?

Provide specific feedback on how the section could be improved, including:
- Areas that need more detail or explanation
- Any inaccuracies or outdated information
- Suggestions for better organization or structure
- Ways to improve clarity or readability
- Additional sources or perspectives that should be included
"""

section_writer_inputs = """
Section Title: {section_title}

Search Results:
{search_results}

Feedback (if any):
{feedback}
"""

