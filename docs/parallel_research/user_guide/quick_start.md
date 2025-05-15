# Quick Start Guide

This guide will help you get started with parallel research in WiseFlow quickly. Follow these steps to configure and run your first parallel research task.

## Prerequisites

Before you begin, ensure you have:

- WiseFlow installed and configured
- Access to the WiseFlow dashboard
- API keys for any external search APIs you plan to use (e.g., Tavily, Perplexity, Exa)

## Step 1: Access the Research Dashboard

1. Open your web browser and navigate to the WiseFlow dashboard URL.
2. Log in with your credentials if required.
3. Click on the "Data Mining" tab in the navigation menu.

![Data Mining Tab](../images/data_mining_tab.png)

## Step 2: Choose a Research Source

WiseFlow supports multiple research sources. For this quick start, we'll use the Web Research source:

1. In the Data Mining dashboard, click on the "Web Research" card.

![Web Research Card](../images/web_research_card.png)

2. This will open the Web Research configuration dialog.

## Step 3: Configure Your Research

1. Enter a research topic in the "Focus" field (e.g., "Artificial Intelligence in Healthcare").
2. Provide a more detailed description in the "Description" field.
3. Set the number of parallel workers (recommended: 4 for most systems).
4. Choose a search API from the dropdown menu (e.g., Tavily).
5. Configure any additional options as needed.

![Web Research Configuration](../images/web_research_config.png)

## Step 4: Start the Research

1. Click the "Start" button to begin the research process.
2. You'll be redirected to the task monitoring view where you can see the progress of your research.

![Task Monitoring](../images/task_monitoring.png)

## Step 5: View Research Results

1. Once the research is complete, you'll see a notification.
2. Click on the completed task to view the research results.
3. The results will be displayed in a structured format with sections and subsections.

![Research Results](../images/research_results.png)

## Step 6: Explore and Export Results

1. Browse through the research results to explore the information gathered.
2. Use the visualization tools to view knowledge graphs or other visualizations.
3. Export the results to your preferred format (PDF, JSON, CSV, etc.) using the export options.

![Export Options](../images/export_options.png)

## Next Steps

Now that you've completed your first parallel research task, you can:

- Experiment with different research modes (Linear, Graph-based, Multi-agent)
- Adjust the number of parallel workers to optimize performance
- Try different search APIs to compare results
- Create templates for frequently used research configurations
- Explore advanced features like continuous research

## Example: Multi-agent Research

For a more advanced example, let's try a multi-agent research task:

1. In the Data Mining dashboard, click on the "Web Research" card.
2. Enter a complex topic that can be broken down into subtopics (e.g., "Climate Change Mitigation Strategies").
3. In the advanced settings, change the research mode to "Multi-agent".
4. Set the number of parallel workers to 6.
5. Click "Start" to begin the research.

The multi-agent mode will break down the topic into subtopics and assign specialized agents to research each subtopic in parallel, resulting in a more comprehensive report.

## Example: Graph-based Research

For an iterative research approach:

1. In the Data Mining dashboard, click on the "Web Research" card.
2. Enter a topic that requires deep exploration (e.g., "Quantum Computing Applications").
3. In the advanced settings, change the research mode to "Graph-based".
4. Set the max search depth to 3 (number of iterations).
5. Click "Start" to begin the research.

The graph-based mode will iteratively refine the research, identifying gaps and exploring them in subsequent iterations.

## Troubleshooting

If you encounter issues during the research process:

- Check the task logs for error messages
- Ensure your API keys are valid and have sufficient quota
- Adjust the number of parallel workers if you're experiencing performance issues
- See the [Troubleshooting](./troubleshooting.md) guide for more detailed help

## Further Reading

- [Research Modes](./research_modes.md)
- [Configuring Parallel Workers](./configuring_parallel_workers.md)
- [Search APIs](./search_apis.md)
- [Best Practices](./best_practices.md)

