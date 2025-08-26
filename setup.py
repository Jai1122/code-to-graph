"""Setup configuration for CodeToGraph."""

from setuptools import setup, find_packages
from pathlib import Path

# Read the contents of README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Read requirements
requirements = []
with open('requirements-core.txt', 'r', encoding='utf-8') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

# Read dev requirements
dev_requirements = []
try:
    with open('dev-requirements.txt', 'r', encoding='utf-8') as f:
        dev_requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
except FileNotFoundError:
    dev_requirements = []

setup(
    name="code-to-graph",
    version="0.1.0",
    author="CodeToGraph Team",
    author_email="team@codetograph.dev",
    description="Scalable repository analysis and graph database system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/codetograph/codetograph",
    project_urls={
        "Bug Reports": "https://github.com/codetograph/codetograph/issues",
        "Source": "https://github.com/codetograph/codetograph",
        "Documentation": "https://docs.codetograph.dev",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=requirements,
    extras_require={
        "dev": dev_requirements,
        "full": [
            # VLLM-only dependencies
            "transformers>=4.36.2",
            "igraph>=0.11.3",
            "scipy>=1.11.4",
            "fastapi>=0.104.1",
            "uvicorn>=0.24.0",
            "httpx>=0.25.2",
            "plotly>=5.17.0",
            "dash>=2.15.0",
            "requests>=2.31.0",
        ],
        "test": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "pytest-cov>=4.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "code-to-graph=code_to_graph.cli.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "code_to_graph": [
            "config/*.yaml",
            "config/*.example",
        ],
    },
    zip_safe=False,
    keywords="code analysis, graph database, static analysis, neo4j, ast, code visualization",
)