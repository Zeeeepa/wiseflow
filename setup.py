from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="wiseflow",
    version="1.0.0",
    author="Wiseflow Team",
    author_email="info@wiseflow.example.com",
    description="AI-powered information extraction system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Zeeeepa/wiseflow",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "aiohttp>=3.8.0",
        "fastapi>=0.95.0",
        "uvicorn>=0.21.0",
        "pydantic>=1.10.0",
        "networkx>=2.8.0",
        "matplotlib>=3.5.0",
        "psutil>=5.9.0",
        "scikit-learn>=1.0.0",
        "numpy>=1.20.0",
        "pandas>=1.3.0",
        "requests>=2.28.0",
        "beautifulsoup4>=4.11.0",
        "pocketbase>=0.8.0",
        "litellm>=0.1.0",
        "openai>=0.27.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.0.0",
            "flake8>=6.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "wiseflow=wiseflow.cli:main",
        ],
    },
)

