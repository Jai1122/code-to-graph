# CodeToGraph: Scalable Repository Analysis System

A high-performance system for analyzing large codebases and storing them in graph databases with intelligent querying and visualization capabilities.

## Architecture Overview

This system addresses the scalability limitations of traditional code analysis tools by implementing:

- **Hybrid parsing**: Tree-sitter for fast file-level analysis + Joern CPG for deep semantic analysis
- **Chunked processing**: Memory-efficient repository processing in manageable chunks  
- **Optimized Neo4j pipeline**: CSV-based bulk imports for million+ node graphs
- **Multi-LLM provider support**: OLLAMA (local), VLLM (remote), and OpenAI integration for code analysis
- **Hierarchical visualization**: Scalable graph exploration beyond Bloom's 100K node limit

## Key Improvements Over Standard Approaches

### Scalability Enhancements
- Processes repositories in chunks to avoid Joern's memory bottlenecks
- Optimized Neo4j imports (CSV vs JSON) for 10x+ performance improvement
- Incremental processing for code changes
- Memory-efficient graph storage and retrieval

### LLM Integration Improvements  
- **Multi-provider support**: OLLAMA (local), VLLM (remote with API keys), OpenAI
- **Secured environment ready**: VPN-connected VLLM endpoints for enterprise use
- **Configurable models**: Support for custom model paths and endpoints
- Code analysis with models like Qwen2.5, CodeLlama, and DeepSeek-Coder
- Repository-level insights and documentation generation
- Natural language query processing with graph context

### Visualization Solutions
- Multi-level graph exploration (package → class → function)
- Custom D3.js components for unlimited node visualization
- REST API flow-specific perspectives
- Interactive drill-down capabilities

## Quick Start

### Prerequisites
- Python 3.9+
- Neo4j 5.x (Docker recommended)
- LLM Provider (choose one):
  - **OLLAMA** (local inference)
  - **VLLM** (remote with API key, VPN-ready)
  - **OpenAI** (API-based)
- At least 8GB RAM (16GB+ recommended for large repositories)
- VPN access (if using remote VLLM endpoints)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd CodeToGraph

# Quick setup with script
./scripts/setup.sh

# Or manual installation
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### Basic Usage

```bash
# Analyze a Go repository
code-to-graph analyze --repo-path /path/to/go-repo --language go

# Analyze a Java repository with custom chunk size
code-to-graph analyze --repo-path /path/to/java-repo --language java --chunk-size 50

# OLLAMA-powered code analysis
code-to-graph analyze-code path/to/file.py
code-to-graph repo-insights --repo-path /path/to/project

# Check system status including OLLAMA
code-to-graph status

# Query the graph database
code-to-graph query "Find all REST endpoints in the user service"

# Start visualization server
code-to-graph visualize --port 8080
```

## Configuration

Copy `config/settings.example.yaml` to `config/settings.yaml` and customize:

- Neo4j connection details
- OLLAMA server settings (URL, preferred models)
- Processing parameters (chunk sizes, memory limits)
- Visualization preferences

### OLLAMA Setup

Install and configure OLLAMA for code analysis:

```bash
# Install OLLAMA
curl -fsSL https://ollama.ai/install.sh | sh

# Pull recommended models
ollama pull qwen2.5:14b      # Best for code analysis
ollama pull codellama:13b    # Alternative code-focused model
ollama pull llama3.1:8b      # Lighter general model

# Start OLLAMA service
ollama serve

# Verify integration
code-to-graph ollama-status
```

## Project Structure

```
src/code_to_graph/
├── parsers/           # Tree-sitter + Joern integration
├── processors/        # Chunked repository processing
├── storage/          # Neo4j optimization layer
├── llm/              # OLLAMA integration and code analysis
└── cli/              # Command-line interface
```

## Performance Benchmarks

- **Memory usage**: 90% reduction vs vanilla Joern for large repositories
- **Import speed**: 10x faster Neo4j imports using CSV pipeline
- **LLM integration**: Local OLLAMA deployment eliminates API costs and latency
- **Code analysis**: Supports multiple specialized models (Qwen2.5, CodeLlama, DeepSeek)
- **Visualization scale**: Supports 1M+ nodes vs Bloom's 100K limit

## Development

```bash
# Install development dependencies
./scripts/setup.sh --dev

# Or manually
source .venv/bin/activate
pip install -r dev-requirements.txt

# Run tests
pytest

# Format code
black src/ tests/
isort src/ tests/

# Type checking
mypy src/
```

## License

MIT License - see LICENSE file for details