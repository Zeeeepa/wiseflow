# WiseFlow Getting Started Guide

## Overview

This guide will help you get started with WiseFlow, an AI-powered system that uses LLMs to extract and analyze information from various sources. WiseFlow helps you focus on what matters by filtering through massive amounts of information from different sources.

## Prerequisites

Before you begin, ensure you have the following:

- Python 3.8 or higher
- pip package manager
- Git (for cloning the repository)
- An OpenAI API key or other supported LLM provider key

## Installation

### Step 1: Clone the Repository

```bash
$ git clone https://github.com/Zeeeepa/wiseflow.git
$ cd wiseflow
```

### Step 2: Install Dependencies

```bash
$ pip install -r requirements.txt
```

### Step 3: Set Up PocketBase

PocketBase is used for data storage in WiseFlow.

```bash
$ cd pb
$ ./pocketbase migrate up  # For first run
$ ./pocketbase --dev superuser create "your-email@example.com" "your-password"
$ ./pocketbase serve
```

> **Note:** On macOS, you may need to run `xattr -d com.apple.quarantine pocketbase` before running PocketBase.

### Step 4: Configure Environment Variables

Create a `.env` file in the root directory with the following content:

```
OPENAI_API_KEY=your_openai_api_key
```

Replace `your_openai_api_key` with your actual OpenAI API key.

## Basic Usage

### Starting WiseFlow

To start WiseFlow, run:

```bash
$ python -m core.app
```

This will start the WiseFlow server, which you can access at `http://localhost:8000`.

### Creating a Focus Point

Focus points define what information you're interested in extracting from your sources.

1. Open the WiseFlow dashboard at `http://localhost:8000`
2. Click on "Focus Points" in the navigation menu
3. Click "Create New Focus Point"
4. Fill in the following information:
   - **Name**: A descriptive name for your focus point
   - **Description**: What kind of information you're looking for
   - **Keywords**: Relevant keywords for your topic
5. Click "Save" to create the focus point

### Adding Data Sources

After creating a focus point, you need to add data sources to extract information from.

1. Navigate to your focus point
2. Click "Add Data Source"
3. Select the type of data source:
   - Web Pages
   - RSS Feeds
   - GitHub Repositories
   - Academic Papers
   - YouTube Videos
4. Configure the data source with the required information
5. Click "Add" to add the data source

### Running Data Mining

Once you've set up your focus points and data sources, you can start the data mining process.

1. Navigate to your focus point
2. Click "Start Mining"
3. WiseFlow will begin extracting information from your data sources
4. You can monitor the progress on the dashboard

### Viewing Results

After the mining process completes, you can view the extracted information.

1. Navigate to your focus point
2. Click "View Results"
3. Browse through the extracted information, organized by source
4. Use the filters to narrow down the results

## Common Use Cases

### Web Research

WiseFlow can help you gather information from multiple websites on a specific topic:

1. Create a focus point describing your research topic
2. Add relevant websites as data sources
3. Start the mining process
4. Review the extracted information

### Academic Research

For academic research, WiseFlow can extract information from research papers:

1. Create a focus point with your research question
2. Add academic sources like arXiv or PubMed
3. Start the mining process
4. Review the extracted information, including key findings and methodologies

### Social Media Monitoring

WiseFlow can help you monitor social media for relevant information:

1. Create a focus point with the topics you want to monitor
2. Add social media sources
3. Configure the mining frequency
4. Review the extracted information regularly

## Troubleshooting

### Installation Issues

**Problem**: PocketBase fails to start

**Solution**: Ensure you have the correct permissions for the PocketBase executable:

```bash
$ chmod +x pb/pocketbase
```

**Problem**: Dependencies fail to install

**Solution**: Try installing dependencies one by one to identify the problematic package:

```bash
$ pip install -r requirements-base.txt
$ pip install -r requirements-optional.txt
```

### Runtime Issues

**Problem**: WiseFlow fails to connect to PocketBase

**Solution**: Ensure PocketBase is running and accessible at the expected URL (default: `http://localhost:8090`).

**Problem**: LLM API calls fail

**Solution**: Check that your API key is correctly set in the `.env` file and that you have sufficient credits with your LLM provider.

## Next Steps

Now that you've set up WiseFlow and created your first focus point, you might want to explore:

- [Advanced Configuration Options](../admin-guide/configuration.md)
- [Plugin Development](../dev-guide/plugins/README.md)
- [API Integration](../dev-guide/api/README.md)
- [Dashboard Customization](../user-guide/dashboard.md)

## Related Topics

- [Focus Points Configuration](../user-guide/focus-points.md)
- [Data Sources Configuration](../user-guide/data-sources.md)
- [Export Options](../user-guide/export.md)
- [Troubleshooting Guide](../user-guide/troubleshooting.md)

## Version Information

This guide applies to WiseFlow version 3.9 and later.

