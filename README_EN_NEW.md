# AI Chief Intelligence Officer (Wiseflow)

**[中文](README.md) | [日本語](README_JP.md) | [한국어](README_KR.md)**

🚀 **Use LLMs to dig out what you care about from massive amounts of information and a variety of sources daily!**

We don't lack information, but rather the ability to filter out noise from massive amounts of information, allowing valuable information to surface.

🌱 See how the AI Intelligence Officer helps you save time, filter irrelevant information, and organize points of interest! 🌱

https://github.com/user-attachments/assets/fc328977-2366-4271-9909-a89d9e34a07b


## 🔥🔥🔥 AI Chief Intelligence Officer online service is now open for public beta testing, no deployment or setup required, no need to apply for various keys, just register and use!

Online experience address: https://www.aiqingbaoguan.com/

During the beta period, registration comes with 10 points of computing power (each focus point consumes 1 point per day, regardless of the number of sources).

*The online server is built on Alibaba Cloud, with limited access to websites outside mainland China, and the online service currently does not support WeChat official accounts. If your sources are mainly these two types, it is recommended to use the open-source version for self-deployment.*

## 🌟 V3.9-patch3 Version Released

For more information about this upgrade, please see [CHANGELOG.md](./CHANGELOG.md)

Starting from this version, we have updated the version naming convention: V0.3.9 -> V3.9, V0.3.8 -> V3.8, V0.3.7 -> V3.7, V0.3.6 -> V3.6, V0.3.5 -> V3.5 ...

The current online service core is based on V3.9-patch3 version.

**For users of V0.3.8 and earlier versions who are upgrading, it's best to remove Crawl4ai from the Python environment (`pip uninstall crawl4ai`)**

**For users of V0.3.7 and earlier versions who are upgrading, please first execute ./pocketbase migrate in the pb folder**

Thanks to the following community members for their PRs in versions V0.3.5~V0.3.9:

  - @ourines contributed the install_pocketbase.sh automated installation script
  - @ibaoger contributed the pocketbase automated installation script for Windows
  - @tusik contributed the asynchronous llm wrapper and discovered the AsyncWebCrawler lifecycle issue
  - @c469591 contributed the Windows version startup script
  - @braumye contributed the docker running solution
  - @YikaJ provided optimization for install_pocketbase.sh
  - @xxxiaogangg contributed export script references


## 🧐 'deep search' VS 'wide search'

I position wiseflow as a "wide search" product, which is relative to the currently popular "deep search".

Specifically, "deep search" is oriented towards a specific problem where the llm autonomously and dynamically plans the search path, continuously explores different pages, and provides answers or generates reports after collecting sufficient information. However, sometimes we don't have specific questions and don't need in-depth exploration, but rather need extensive information collection (such as industry intelligence gathering, background information collection on targets, customer information collection, etc.). In these cases, breadth is clearly more meaningful. Although "deep search" can also accomplish this task, it's like using a cannon to shoot a mosquito - inefficient and costly. Wiseflow is a tool specifically designed for this "wide search" scenario.


## ✋ What makes wiseflow different from other ai-powered crawlers?

The biggest difference is in the scraper stage, where we propose a pipeline that is different from all existing crawlers, namely the "integrated search" strategy. Specifically, we abandon the traditional filter-extractor process (of course, this process can also incorporate llm, as crawl4ai does), and we no longer treat a single page as the minimum processing unit. Instead, based on crawl4ai's html2markdown, we further divide the page into blocks, and according to a series of feature algorithms, divide the blocks into "content blocks" and "external link blocks", and adopt different llm extraction strategies based on different classifications (still using llm to analyze each block only once, just with different analysis strategies, avoiding token waste). This solution can simultaneously accommodate list pages, content pages, and mixed pages.

  - For "content blocks", directly summarize and extract according to focus points, avoiding information dispersion, and even directly completing translation and other tasks in this process;
  - For "external link blocks", comprehensively consider page layout and other information to determine which links are worth further exploration and which should be ignored, thus eliminating the need for users to manually configure depth, maximum crawl quantity, etc.

This solution is actually very similar to AI Search.

In addition, we have also written dedicated parsing modules for specific types of pages, such as WeChat official account articles (which surprisingly have nine different formats...). For this type of content, wiseflow currently provides the best parsing results among similar products.

## ✋ What's Next (4.x plan)?

### Enhanced Crawler fetching stage
    
In the 3.x architecture, the crawler fetching part completely uses Crawl4ai. In 4.x, we will still use this solution for obtaining ordinary pages, but will gradually add fetching solutions for social platforms.


### Insight module
    
What's truly valuable may not be the "information that can be captured", but the "hidden information" beneath this information. Being able to intelligently associate captured information and analyze and extract the "hidden information" beneath it is the insight module that 4.x will focus on building.


# 📥 Installation and Usage Guide

## Quick Deployment (Windows Users)

Windows users can use our one-click deployment script, which will automatically complete all installation and configuration steps:

1. Download the `deploy_and_launch.bat` script to your computer
2. Double-click to run the script
3. Follow the prompts to complete the configuration

The script will automatically perform the following operations:
- Check necessary dependencies (Git, Python)
- Clone or update the WiseFlow repository
- Install PocketBase
- Create and configure environment variables
- Set up a Python virtual environment
- Install all dependencies
- Launch the WiseFlow application

## Manual Installation Steps

### 1. Clone the Code Repository

🌹 Liking and forking are good habits 🌹

**Windows users should download the git bash tool in advance and execute the following command in bash [bash download link](https://git-scm.com/downloads/win)**

```bash
git clone https://github.com/TeamWiseFlow/wiseflow.git
```

### 2. Execute the install_pocketbase Script in the Root Directory

Linux/macOS users please execute:

```bash
chmod +x install_pocketbase
./install_pocketbase
```

**Windows users please execute the [install_pocketbase.ps1](./install_pocketbase.ps1) script**

Wiseflow 3.x version uses pocketbase as the database. You can also manually download the pocketbase client (remember to download version 0.23.4 and place it in the [pb](./pb) directory) and manually complete the creation of the superuser (remember to save it to the .env file)

For details, please refer to [pb/README.md](/pb/README.md)

### 3. Continue to Configure the core/.env File

🌟 **This is different from previous versions**. Starting from V0.3.5, the .env file needs to be placed in the [core](./core) folder.

#### 3.1 Large Model Related Configuration

Wiseflow is an LLM native application. Please ensure that you provide a stable LLM service for the program.

🌟 **Wiseflow does not limit the source of model services, as long as the service is compatible with the openAI SDK, including locally deployed services such as ollama, Xinference, etc.**

#### Recommendation 1: Use the MaaS service provided by siliconflow

Siliconflow provides online MaaS services for most mainstream open-source models. With its accumulated accelerated inference technology, its services have great advantages in terms of speed and price. When using siliconflow's services, the .env configuration can refer to the following:

```
LLM_API_KEY=Your_API_KEY
LLM_API_BASE="https://api.siliconflow.cn/v1"
PRIMARY_MODEL="deepseek-ai/DeepSeek-R1-Distill-Qwen-14B"
SECONDARY_MODEL="Qwen/Qwen2.5-14B-Instruct"
VL_MODEL="deepseek-ai/deepseek-vl2"
PROJECT_DIR="work_dir"
```
      
😄 If you're willing, you can use my [siliconflow invitation link](https://cloud.siliconflow.cn/i/WNLYbBpi), so I can also get more token rewards 🌹

#### Recommendation 2: Use AiHubMix proxy for openai, claude, gemini and other overseas closed-source commercial model services

If your sources are mostly non-Chinese pages, and you don't require the extracted info to be in Chinese, then it's more recommended to use overseas closed-source commercial models such as openai, claude, gemini. You can try the third-party proxy **AiHubMix**, which supports direct connection in domestic network environments, convenient Alipay payment, and avoids the risk of account bans.
When using AiHubMix models, the .env configuration can refer to the following:

```
LLM_API_KEY=Your_API_KEY
LLM_API_BASE="https://aihubmix.com/v1" # For details, refer to https://doc.aihubmix.com/
PRIMARY_MODEL="gpt-4o"
SECONDARY_MODEL="gpt-4o-mini"
VL_MODEL="gpt-4o"
PROJECT_DIR="work_dir"
```

😄 Welcome to use the [AiHubMix invitation link](https://aihubmix.com?aff=Gp54) to register 🌹

#### Locally Deployed Large Model Services

Taking Xinference as an example, the .env configuration can refer to the following:

```
# LLM_API_KEY='' Local service does not need this item, please comment it out or delete it
LLM_API_BASE='http://127.0.0.1:9997' # 'http://127.0.0.1:11434/v1' for ollama
PRIMARY_MODEL=Started model ID
VL_MODEL=Started model ID
PROJECT_DIR="work_dir"
```

#### 3.2 Pocketbase Account Password Configuration

```
PB_API_AUTH="test@example.com|1234567890" 
```

This is the superuser username and password for the pocketbase database, remember to separate them with | (if the install_pocketbase.sh script executed successfully, this item should already exist)


#### 3.3 Zhipu (bigmodel) Platform Key Setting (for Search Engine Service)

Reminder: **The Zhipu platform will officially charge for the web_search_pro interface starting from zero hour on March 14, 2025. If you need to use the search function, please pay attention to your account balance**
[Zhipu Platform Announcement](https://bigmodel.cn/dev/api/search-tool/web-search-pro)

```
ZHIPU_API_KEY=Your_API_KEY
```

(Application address: https://bigmodel.cn/ ~~Currently free~~ 0.03 yuan/time, please ensure account balance)

#### 3.4 Other Optional Configurations

The following are all optional configurations:
- #VERBOSE="true" 

  Whether to enable observation mode. If enabled, debug information will be recorded in the logger file (by default, it is only output on the console);

- #PB_API_BASE="" 

  Only needs to be configured if your pocketbase is not running on the default IP or port. In the default case, it can be ignored.

- #LLM_CONCURRENT_NUMBER=8 

  Used to control the number of concurrent requests for llm. If not set, the default is 1 (before enabling, please ensure that the llm provider supports the set concurrency. Use with caution for local large models, unless you have confidence in your hardware foundation)


### 4. Run the Program

It is recommended to use conda to build a virtual environment (of course, you can also skip this step, or use other python virtual environment solutions)

```bash
conda create -n wiseflow python=3.12
conda activate wiseflow
```

Then run

```bash
cd wiseflow
cd core
pip install -r requirements.txt
python -m playwright install --with-deps chromium
```

Then MacOS&Linux users execute

```bash
chmod +x run.sh
./run.sh
```

Windows users execute

```bash
python windows_run.py
```

The above script will automatically determine whether pocketbase is already running. If it is not running, it will automatically start it. But please note that when you terminate the process with ctrl+c or ctrl+z, the pocketbase process will not be terminated until you close the terminal.

run.sh will first execute a crawling task for all already activated (activated set to true) sources, and then execute periodically according to the set frequency in hours.

### 5. Adding Focus Points and Sources
    
After starting the program, open the pocketbase Admin dashboard UI (http://127.0.0.1:8090/_/)

#### 5.1 Open the sites Form

Through this form, you can configure sources. Note: Sources need to be selected in the focus_point form in the next step.

sites field description:
- url, the url of the source. The source does not need to be given a specific article page, just give the article list page.
- type, type, web or rss.
    
#### 5.2 Open the focus_point Form

Through this form, you can specify your focus points. The LLM will refine, filter, and categorize information according to this.
    
Field description:
- focuspoint, focus point description (required), such as "Shanghai primary to junior high school information", "tender notice"
- explanation, detailed explanation or specific agreement of the focus point, such as "Only limited to junior high school admission information officially released by Shanghai City", "Published after January 1, 2025, and with an amount of more than 1 million" etc.
- activated, whether it is activated. If closed, this focus point will be ignored. It can be reopened after closing
- per_hour, crawling frequency, in hours, type is integer (range 1~24, we recommend that the scanning frequency should not exceed once a day, i.e., set to 24)
- search_engine, whether to enable the search engine for each crawl
- sites, select the corresponding sources

**Note: After V0.3.8 version, configuration adjustments do not require restarting the program, they will automatically take effect the next time it is executed.**

## 🐳 Docker Deployment

If you wish to deploy Wiseflow using Docker, we also provide complete containerization support.

### 1. Preparation

Ensure that Docker is installed on your system.

### 2. Configure Environment Variables

Copy the `env_docker` file to the `.env` file in the root directory:

```bash
cp env_docker .env
```

### 3. Refer to [Installation and Usage](#-installation-and-usage) to Modify the `.env` File

The following environment variables must be modified as needed:

```bash
LLM_API_KEY=""
LLM_API_BASE="https://api.siliconflow.cn/v1"
PB_SUPERUSER_EMAIL="test@example.com"
PB_SUPERUSER_PASSWORD="1234567890" #no '&' in the password and at least 10 characters
```

### 4. Start the Service

Execute in the project root directory:

```bash
docker compose up -d
```

After the service starts:

- PocketBase management interface: http://localhost:8090/_/
- The Wiseflow service will automatically run and connect to PocketBase

### 5. Stop the Service

```bash
docker compose down
```

### 6. Notes

- The `./pb/pb_data` directory is used to store PocketBase related files
- The `./docker/pip_cache` directory is used to store Python dependency package cache, avoiding repeated downloading and installation of dependencies
- The `./core/work_dir` directory is used to store Wiseflow runtime logs, you can modify `PROJECT_DIR` in the `.env` file

## 📚 How to Use the Data Captured by Wiseflow in Your Own Program

1. Refer to the [dashboard](dashboard) part of the source code for secondary development.

Note that the core part of wiseflow does not need a dashboard, and the current product does not integrate a dashboard. If you have dashboard needs, please download [V0.2.1 version](https://github.com/TeamWiseFlow/wiseflow/releases/tag/V0.2.1)

2. Get data directly from Pocketbase

All data captured by wiseflow is immediately stored in pocketbase, so you can directly operate the pocketbase database to get data.

PocketBase, as a popular lightweight database, currently has SDKs for languages such as Go/Javascript/Python.
   - Go: https://pocketbase.io/docs/go-overview/
   - Javascript: https://pocketbase.io/docs/js-overview/
   - python: https://github.com/vaphes/pocketbase
  
3. The online service will also soon launch a sync api, supporting the synchronization of online capture results to local, for building "dynamic knowledge bases" and other purposes. Please stay tuned:

  - Online experience address: https://www.aiqingbaoguan.com/ 
  - Online service API usage cases: https://github.com/TeamWiseFlow/wiseflow_plus


## 🛡️ License

This project is open source under [Apache2.0](LICENSE).

For commercial cooperation, please contact **Email: zm.zhao@foxmail.com**

- Commercial customers please contact us to register, the product promises to be free forever.


## 📬 Contact

For any questions or suggestions, welcome to leave a message through [issue](https://github.com/TeamWiseFlow/wiseflow/issues).


## 🤝 This Project is Based on the Following Excellent Open Source Projects:

- crawl4ai (Open-source LLM Friendly Web Crawler & Scraper) https://github.com/unclecode/crawl4ai
- pocketbase (Open Source realtime backend in 1 file) https://github.com/pocketbase/pocketbase
- python-pocketbase (pocketBase client SDK for python) https://github.com/vaphes/pocketbase
- feedparser (Parse feeds in Python) https://github.com/kurtmckee/feedparser

The development of this project was inspired by [GNE](https://github.com/GeneralNewsExtractor/GeneralNewsExtractor), [AutoCrawler](https://github.com/kingname/AutoCrawler), and [SeeAct](https://github.com/OSU-NLP-Group/SeeAct).

## Citation

If you reference or cite part or all of this project in related work, please indicate the following information:

```
Author: Wiseflow Team
https://github.com/TeamWiseFlow/wiseflow
Licensed under Apache2.0
```

