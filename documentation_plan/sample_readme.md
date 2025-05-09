# WiseFlow: AI-Powered Information Mining

<div align="center">

![WiseFlow Logo](path/to/logo.png)

**Use LLMs to extract what matters from massive amounts of information across various sources.**

[![GitHub stars](https://img.shields.io/github/stars/Zeeeepa/wiseflow)](https://github.com/Zeeeepa/wiseflow/stargazers)
[![GitHub license](https://img.shields.io/github/license/Zeeeepa/wiseflow)](https://github.com/Zeeeepa/wiseflow/blob/main/LICENSE)
[![GitHub issues](https://img.shields.io/github/issues/Zeeeepa/wiseflow)](https://github.com/Zeeeepa/wiseflow/issues)
[![GitHub release](https://img.shields.io/github/release/Zeeeepa/wiseflow)](https://github.com/Zeeeepa/wiseflow/releases)

[English](README_EN.md) | [简体中文](README.md) | [日本語](README_JP.md) | [한국어](README_KR.md)

</div>

## 🚀 Overview

WiseFlow is an intelligent system that uses Large Language Models (LLMs) to extract and analyze information from various sources. It helps you focus on what matters by filtering through massive amounts of information from different sources daily.

What we lack is not information, but the ability to filter out noise from massive information, thereby revealing valuable information.

### 🌱 See WiseFlow in Action

Watch how WiseFlow helps you save time, filter irrelevant information, and organize key points of interest:

[View Demo Video](https://github.com/user-attachments/assets/fc328977-2366-4271-9909-a89d9e34a07b)

## ✨ Key Features

- **Multi-Source Information Mining**: Extract information from websites, academic papers, GitHub repositories, YouTube videos, and more
- **Focus Point System**: Define what information matters to you through customizable focus points
- **Plugin Architecture**: Extend functionality with custom connectors, processors, and analyzers
- **Intelligent Analysis**: Use LLMs to analyze and synthesize information from multiple sources
- **Interactive Dashboard**: Visualize and explore extracted information through an intuitive dashboard
- **Export Capabilities**: Export findings in various formats for further analysis or sharing
- **Automated Scheduling**: Schedule regular information mining tasks
- **Resource Monitoring**: Automatically manage system resources and shut down when tasks are complete

## 🔥 Online Service

The online trial service of WiseFlow is now open for public testing. No deployment or setup is required, and there is no need to apply for various keys. Just register to use it!

**Online trial address**: [https://www.aiqingbaoguan.com/](https://www.aiqingbaoguan.com/)

During the public testing period, registration will give you 10 free credits (each focus point consumes 1 point per day, regardless of the number of information sources).

> *Note: The online service is built on Alibaba Cloud, and access to websites outside mainland China is restricted. Additionally, the online service currently does not support WeChat official accounts. If your sources primarily consist of these two types, we recommend using the open-source version to deploy yourself.*

## 🛠️ Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Git (for cloning the repository)

### Quick Install

```bash
# Clone the repository
git clone https://github.com/Zeeeepa/wiseflow.git
cd wiseflow

# Install dependencies
pip install -r requirements.txt

# Set up PocketBase
cd pb
./pocketbase migrate up  # For first run
./pocketbase --dev superuser create "your-email@example.com" "your-password"
./pocketbase serve
```

For detailed installation instructions, see the [Installation Guide](docs/getting-started/installation.md).

## 📚 Documentation

- [Getting Started Guide](docs/getting-started/README.md)
- [User Guide](docs/user-guide/README.md)
- [Administrator Guide](docs/admin-guide/README.md)
- [Developer Guide](docs/dev-guide/README.md)
- [API Reference](docs/reference/api-endpoints.md)
- [Troubleshooting](docs/user-guide/troubleshooting.md)

## 🧠 'Deep Search' VS 'Wide Search'

WiseFlow is positioned as a "wide search" product, in contrast to the currently popular "deep search" approach.

Specifically, "deep search" is oriented towards a specific question, where the LLM autonomously and dynamically plans the search path, continuously explores different pages, and collects enough information to give an answer or produce a report. However, sometimes we don't have a specific question and don't need in-depth exploration. We only need broad information collection (such as industry intelligence collection, background information collection on a subject, customer information collection, etc.). In these cases, breadth is clearly more meaningful. Although "deep search" can also accomplish this task, it's like using a cannon to kill a mosquito – inefficient and costly. WiseFlow is a powerful tool specifically designed for this "wide search" scenario.

## 🤝 Contributing

We welcome contributions to WiseFlow! Here's how you can help:

- **Code Contributions**: Submit pull requests with bug fixes or new features
- **Documentation**: Help improve the documentation
- **Bug Reports**: Submit issues for any bugs you encounter
- **Feature Requests**: Suggest new features or improvements
- **Testing**: Test the application and report any issues

See the [Contributing Guide](docs/dev-guide/contributing.md) for more details.

## 📝 Changelog

For a detailed list of changes between versions, see the [Changelog](CHANGELOG.md).

## 🙏 Acknowledgements

Thanks to the following community members for their contributions:

- @ourines contributed the install_pocketbase.sh automated installation script
- @ibaoger contributed the PocketBase automated installation script for Windows
- @tusik contributed the asynchronous llm wrapper and discovered the AsyncWebCrawler lifecycle issue
- @c469591 contributed the Windows version startup script
- @braumye contributed the Docker deployment solution
- @YikaJ provided optimizations for install_pocketbase.sh
- @xxxiaogangg contributed the export script reference

## 📄 License

WiseFlow is licensed under the [MIT License](LICENSE).

## 📞 Contact

For questions, feedback, or support, please [open an issue](https://github.com/Zeeeepa/wiseflow/issues) on GitHub.

