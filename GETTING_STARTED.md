# Getting Started with CodeToGraph

CodeToGraph is a powerful tool for analyzing codebases and storing relationships in a graph database. This guide will walk you through setting up and running the application on different systems, including secured environments with remote VLLM endpoints.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [LLM Provider Setup](#llm-provider-setup)
   - [OLLAMA (Local)](#ollama-local)
   - [VLLM (Remote)](#vllm-remote)
   - [OpenAI](#openai)
5. [Database Setup](#database-setup)
6. [Running the Application](#running-the-application)
7. [Common Use Cases](#common-use-cases)
8. [Troubleshooting](#troubleshooting)

## System Requirements

- **Python**: 3.9 or higher
- **Memory**: At least 8GB RAM (16GB recommended)
- **Storage**: 2GB free space for data and dependencies
- **Network**: Internet access for remote LLM providers
- **Docker**: Required for Neo4j database

### For Secured/VPN Systems

- **VPN Connection**: Required for accessing remote VLLM endpoints
- **API Key**: Valid API key for VLLM service
- **Firewall**: Ports 7687 (Neo4j) and 8080 (visualization) should be accessible

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/CodeToGraph.git
cd CodeToGraph
```

### 2. Create Virtual Environment

```bash
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install in development mode
pip install -e .

# Or install from requirements
pip install -r requirements.txt
```

### 4. Install Additional Dependencies

```bash
# For visualization features
pip install dash plotly networkx pandas

# For parsing capabilities
pip install tree-sitter tree-sitter-languages
```

## Configuration

### 1. Environment Configuration

Copy the example configuration file:

```bash
cp .env.example .env
```

### 2. Edit Configuration

Open `.env` and configure your settings:

```bash
# ===== LLM Provider Configuration =====
# Choose your provider: ollama, vllm, openai
LLM_PROVIDER=vllm

# VLLM Configuration (for remote inference)
LLM_VLLM_BASE_URL=https://your-vllm-endpoint.com
LLM_VLLM_API_KEY=your_actual_api_key_here
LLM_VLLM_MODEL=/app/models/qwen3:14b

# ===== Neo4j Database Configuration =====
NEO4J_PASSWORD=your_secure_password

# ===== Processing Configuration =====
PROCESSING_MAX_CHUNK_SIZE=100
PROCESSING_MAX_MEMORY_GB=16
```

## LLM Provider Setup

CodeToGraph supports multiple LLM providers. Choose the one that best fits your environment:

### OLLAMA (Local)

**Best for**: Local development, offline environments, full control over models

#### Setup:

1. **Install OLLAMA**:
   ```bash
   # Linux/macOS
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # Or download from https://ollama.ai
   ```

2. **Start OLLAMA service**:
   ```bash
   ollama serve
   ```

3. **Pull a model**:
   ```bash
   # Lightweight model
   ollama pull qwen3:1.7b
   
   # More capable model
   ollama pull qwen3:14b
   ```

4. **Configure CodeToGraph**:
   ```bash
   # In .env file:
   LLM_PROVIDER=ollama
   LLM_OLLAMA_BASE_URL=http://localhost:11434
   LLM_OLLAMA_MODEL=qwen3:1.7b
   ```

### VLLM (Remote)

**Best for**: Secured environments, VPN-connected systems, production deployments

#### Setup:

1. **Obtain Access**:
   - Get your VLLM endpoint URL
   - Obtain your API key
   - Confirm VPN access if required

2. **Configure CodeToGraph**:
   ```bash
   # In .env file:
   LLM_PROVIDER=vllm
   LLM_VLLM_BASE_URL=https://vllm.com
   LLM_VLLM_API_KEY=sk-your-actual-key-here
   LLM_VLLM_MODEL=/app/models/qwen3:14b
   ```

3. **Test Connection**:
   ```bash
   # Activate virtual environment
   source .venv/bin/activate
   
   # Test VLLM connection
   code-to-graph llm-status
   ```

### OpenAI

**Best for**: Quick testing, maximum compatibility

#### Setup:

1. **Get API Key** from [OpenAI Platform](https://platform.openai.com/)

2. **Configure CodeToGraph**:
   ```bash
   # In .env file:
   LLM_PROVIDER=openai
   LLM_OPENAI_API_KEY=sk-your-openai-key-here
   LLM_OPENAI_MODEL=gpt-4o
   ```

## Database Setup

CodeToGraph uses Neo4j as its graph database.

### 1. Start Neo4j with Docker

```bash
# Start Neo4j container
docker run \
    --name neo4j-codetoggraph \
    -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/password123 \
    -e NEO4J_PLUGINS='["apoc"]' \
    -d neo4j:5.12
```

### 2. Verify Neo4j is Running

```bash
# Check container status
docker ps

# Test connection
code-to-graph status
```

### 3. Access Neo4j Browser (Optional)

Open http://localhost:7474 in your browser:
- Username: `neo4j`  
- Password: `password123` (or your configured password)

## Running the Application

### 1. Check System Status

```bash
# Verify all components are working
code-to-graph status
```

Expected output:
```
┌─────────────┬─────────────┬─────────────────────────────────┐
│ Component   │ Status      │ Details                         │
├─────────────┼─────────────┼─────────────────────────────────┤
│ Neo4j       │ ✓ Connected │ 0 nodes, 0 rels                │
│ LLM (VLLM)  │ ✓ Connected │ Model: /app/models/qwen3:14b    │
│ LLM URL     │ ℹ Info      │ https://vllm.com                │
│ API Key     │ ℹ Info      │ Configured                      │
└─────────────┴─────────────┴─────────────────────────────────┘
```

### 2. Analyze a Repository

```bash
# Analyze and import repository data
code-to-graph import-graph \
    --repo-path /path/to/your/repository \
    --clear \
    --create-indexes
```

Example with a Go repository:
```bash
# Clone a sample repository
git clone https://github.com/gin-gonic/gin.git /tmp/gin-example

# Analyze it
code-to-graph import-graph \
    --repo-path /tmp/gin-example \
    --language go \
    --chunk-size 50 \
    --clear \
    --create-indexes
```

### 3. Start Visualization Server

```bash
# Start the interactive web interface
code-to-graph visualize --host 0.0.0.0 --port 8080
```

Open http://localhost:8080 in your browser to explore the graph.

## Common Use Cases

### 1. Analyze Code Structure

```bash
# Analyze a specific file
code-to-graph analyze-code /path/to/file.go

# Get repository insights
code-to-graph repo-insights --repo-path /path/to/repo --max-files 20
```

### 2. Query the Graph

```bash
# Natural language queries (coming soon)
code-to-graph query "Show me all functions that handle HTTP requests"
```

### 3. Export Analysis Results

```bash
# Check database statistics
code-to-graph status

# Start visualization for detailed exploration
code-to-graph visualize
```

### 4. Batch Processing Multiple Repositories

```bash
#!/bin/bash
# Process multiple repositories

repos=(
    "/path/to/repo1"
    "/path/to/repo2" 
    "/path/to/repo3"
)

for repo in "${repos[@]}"; do
    echo "Processing $repo..."
    code-to-graph import-graph \
        --repo-path "$repo" \
        --chunk-size 50 \
        --create-indexes
done

echo "All repositories processed!"
```

## Configuration for Secured Systems

### Environment Variables for VPN/Secured Systems

```bash
# In .env or as environment variables:

# VLLM Configuration
export LLM_PROVIDER=vllm
export LLM_VLLM_BASE_URL=https://your-secure-vllm-endpoint.company.com
export LLM_VLLM_API_KEY=your-company-api-key
export LLM_VLLM_MODEL=/app/models/qwen3:14b

# Increase timeout for slower networks
export LLM_TIMEOUT=300

# Neo4j (use secured instance if available)
export NEO4J_URI=bolt://secure-neo4j.company.com:7687
export NEO4J_USERNAME=your-username
export NEO4J_PASSWORD=your-secure-password

# Adjust processing for secured environments
export PROCESSING_MAX_CHUNK_SIZE=20
export PROCESSING_MAX_MEMORY_GB=8
```

### Running in Docker (Recommended for Secured Systems)

1. **Create Dockerfile**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install -e .

CMD ["code-to-graph", "status"]
```

2. **Build and Run**:
```bash
# Build image
docker build -t codetoggraph .

# Run with environment file
docker run --env-file .env codetoggraph
```

## Troubleshooting

### Common Issues

#### 1. LLM Connection Failed

```bash
# Check LLM status
code-to-graph llm-status
```

**Solutions**:
- **VLLM**: Verify VPN connection, API key, and endpoint URL
- **OLLAMA**: Ensure `ollama serve` is running
- **Network**: Check firewall and proxy settings

#### 2. Neo4j Connection Failed

```bash
# Check Neo4j status
docker logs neo4j-codetoggraph
```

**Solutions**:
- Restart Neo4j container
- Check port 7687 is not blocked
- Verify password in configuration

#### 3. Memory Issues

```bash
# Reduce chunk size and memory usage
export PROCESSING_MAX_CHUNK_SIZE=20
export PROCESSING_MAX_MEMORY_GB=4

# Disable Joern if needed
export PROCESSING_ENABLE_JOERN=false
```

#### 4. Model Not Found

```bash
# For VLLM: Check available models
code-to-graph llm-status

# For OLLAMA: Pull the model
ollama pull qwen3:14b
```

### Debug Mode

Enable debug logging:

```bash
export DEBUG=true
export LOG_LEVEL=DEBUG

# Or run with debug flag
code-to-graph --debug status
```

### Performance Tuning

#### For Large Repositories

```bash
# Increase chunk size and memory
export PROCESSING_MAX_CHUNK_SIZE=200
export PROCESSING_MAX_MEMORY_GB=32

# Use package-based chunking
export PROCESSING_CHUNK_STRATEGY=package

# Enable incremental processing
export PROCESSING_ENABLE_INCREMENTAL=true
```

#### For Slow Networks

```bash
# Increase timeouts
export LLM_TIMEOUT=600
export NEO4J_MAX_CONNECTION_LIFETIME=7200

# Reduce concurrent processing
export PROCESSING_MAX_CHUNK_SIZE=10
```

## Support

### Getting Help

1. **Check Status**: `code-to-graph status`
2. **View Logs**: Check `logs/code_to_graph.log`
3. **Debug Mode**: Run with `--debug` flag
4. **Documentation**: See [README.md](README.md)

### Common Commands

```bash
# Quick start
code-to-graph status
code-to-graph llm-status
code-to-graph import-graph --repo-path . --clear
code-to-graph visualize

# Configuration
code-to-graph --help
cp .env.example .env

# Analysis
code-to-graph analyze-code file.py
code-to-graph repo-insights --repo-path .
```

## Next Steps

After successfully setting up CodeToGraph:

1. **Explore the Web Interface**: Use `code-to-graph visualize` to interactively explore your code graph
2. **Try Different Models**: Experiment with different VLLM models for various analysis tasks
3. **Automate Analysis**: Set up CI/CD pipelines to automatically analyze code changes
4. **Custom Queries**: Learn Cypher query language to create custom graph queries
5. **Integration**: Integrate CodeToGraph insights into your development workflow

Enjoy exploring your codebase with CodeToGraph! 🚀

### 2. Installation

```bash
# Clone the repository
git clone <repository-url>
cd CodeToGraph

# Run the setup script
./scripts/setup.sh

# For development (includes testing and linting tools)
./scripts/setup.sh --dev
```

The setup script will:
- Create a Python virtual environment
- Install all Python dependencies
- Set up Docker services (Neo4j)
- Create configuration files
- Test the installation

### 3. Configuration

Edit the configuration files:

```bash
# Environment variables
cp .env.example .env
# Edit .env with your settings

# Detailed configuration
cp config/settings.example.yaml config/settings.yaml
# Edit settings.yaml as needed
```

Key settings to configure:
- **Neo4j credentials**: Update password in `.env`
- **OLLAMA settings**: Configure server URL and preferred models
- **Memory limits**: Adjust based on your system resources
- **Languages**: Enable/disable specific programming languages

## Basic Usage

### 1. Start Services

Start the required services:

```bash
# Start Neo4j with Docker
docker-compose up -d neo4j
# Wait for Neo4j to be ready (check with docker-compose logs neo4j)

# Install and start OLLAMA
curl -fsSL https://ollama.ai/install.sh | sh
ollama serve &

# Pull recommended models
ollama pull qwen2.5:14b
ollama pull codellama:13b
```

### 2. Check System Status

```bash
# Activate virtual environment
source .venv/bin/activate

# Check system status
code-to-graph status
```

This will show:
- Neo4j connection status
- OLLAMA connection status
- Parser availability (Tree-sitter, Joern)
- Current configuration

### 3. Analyze a Repository

#### Simple Analysis

```bash
# Analyze a Go repository
code-to-graph analyze --repo-path /path/to/go-repo --language go

# Analyze a Java repository with custom chunk size
code-to-graph analyze --repo-path /path/to/java-repo --language java --chunk-size 100
```

#### Advanced Analysis

```bash
# Use the analysis script for more options
./scripts/analyze_repository.sh -r /path/to/repo -l go -c 50 -s hybrid
```

#### Large Repository Analysis

For large repositories (1000+ files), use these optimizations:

```bash
code-to-graph analyze \
  --repo-path /path/to/large-repo \
  --chunk-size 25 \
  --chunk-strategy package \
  --disable-joern  # Use only Tree-sitter for speed
```

### 4. Import to Neo4j

```bash
# Import analysis results and create indexes
code-to-graph import-graph --create-indexes
```

### 5. OLLAMA-Powered Code Analysis

```bash
# Analyze individual files
code-to-graph analyze-code path/to/file.py
code-to-graph analyze-code --model qwen2.5:14b path/to/file.go

# Get repository insights
code-to-graph repo-insights --repo-path /path/to/project
code-to-graph repo-insights --repo-path /path/to/project --max-files 20

# Check OLLAMA status
code-to-graph ollama-status

# Natural language queries (requires LLM setup)
code-to-graph query "Find all REST endpoints"
code-to-graph query "Show functions that call database methods"

# Check database statistics
code-to-graph status
```

### 6. Start Visualization

```bash
# Start the visualization server
code-to-graph visualize --port 8080

# Open in browser: http://localhost:8080
```

## Understanding the Architecture

### Parsing Strategy

CodeToGraph uses a hybrid parsing approach:

1. **Tree-sitter**: Fast syntactic analysis for basic structure
2. **Joern CPG**: Deep semantic analysis for complex relationships
3. **Chunked Processing**: Breaks large repos into manageable pieces

### Memory Optimization

The system is designed to handle large repositories efficiently:

- **Chunked processing**: Processes files in small batches
- **Incremental analysis**: Only re-processes changed files
- **Memory limits**: Configurable memory constraints
- **CSV imports**: Optimized Neo4j bulk loading

### Graph Structure

The resulting graph contains:

- **Entities**: Functions, classes, methods, variables
- **Relationships**: Calls, inheritance, dependencies
- **Metadata**: Source locations, signatures, confidence scores

## Configuration Examples

### For Go Repositories

```yaml
processing:
  supported_languages: ["go"]
  chunk_strategy: "package"  # Go packages work well
  max_chunk_size: 100
  enable_joern: true  # Good Go support in Joern
```

### For Java Repositories

```yaml
processing:
  supported_languages: ["java"]
  chunk_strategy: "package"
  max_chunk_size: 50  # Java files tend to be larger
  exclude_patterns:
    - "**/target/**"
    - "**/*.class"
```

### For Large Repositories (Memory Constrained)

```yaml
processing:
  chunk_strategy: "size"
  max_chunk_size: 25
  max_memory_gb: 8
  enable_joern: false  # Disable for speed
  enable_tree_sitter: true
```

### For Accuracy (Unlimited Resources)

```yaml
processing:
  chunk_strategy: "hybrid"
  max_chunk_size: 200
  max_memory_gb: 64
  enable_joern: true
  enable_tree_sitter: true
llm:
  provider: "ollama"
  ollama_base_url: "http://localhost:11434"
  ollama_model: "qwen2.5:14b"
```

## Troubleshooting

### Common Issues

1. **Out of Memory Errors**
   ```bash
   # Reduce chunk size and memory limits
   export PROCESSING_MAX_CHUNK_SIZE=25
   export PROCESSING_MAX_MEMORY_GB=8
   ```

2. **Joern Not Found**
   ```bash
   # Install Joern or disable it
   export PROCESSING_ENABLE_JOERN=false
   ```

3. **Neo4j Connection Failed**
   ```bash
   # Check Docker service
   docker-compose logs neo4j
   
   # Verify connection
   docker-compose exec neo4j cypher-shell -u neo4j -p password123
   ```

4. **Slow Analysis**
   ```bash
   # Use Tree-sitter only for large repos
   ./scripts/analyze_repository.sh -r /path/to/repo --no-joern
   ```

5. **OLLAMA Connection Issues**
   ```bash
   # Check OLLAMA status
   ollama list
   curl http://localhost:11434/api/tags
   
   # Restart OLLAMA service
   pkill ollama
   ollama serve &
   
   # Verify CodeToGraph integration
   code-to-graph ollama-status
   ```

6. **OLLAMA Model Issues**
   ```bash
   # Pull required models
   ollama pull qwen2.5:14b
   ollama pull codellama:13b
   
   # Check model availability
   ollama list
   
   # Test specific model
   code-to-graph analyze-code --model qwen2.5:14b test_file.py
   ```

### Performance Tuning

For optimal performance:

1. **Memory**: Allocate 2-4GB per 1000 files being analyzed
2. **Storage**: Use SSD storage for Neo4j data directory
3. **Chunking**: Smaller chunks for memory-constrained systems
4. **Parsing**: Disable Joern for initial exploration, enable for detailed analysis
5. **OLLAMA Models**: 
   - Use `qwen2.5:14b` for best code analysis quality
   - Use `llama3.1:8b` for faster analysis on limited hardware
   - Ensure adequate GPU memory for larger models (14B+ requires ~8GB VRAM)

### Monitoring

Monitor the analysis progress:

```bash
# Watch logs in real-time
tail -f logs/code_to_graph.log

# Check Neo4j performance
docker-compose exec neo4j neo4j-admin metrics
```

## Next Steps

1. **Explore the Graph**: Use Neo4j Browser at http://localhost:7474
2. **Custom Queries**: Write Cypher queries for specific analysis needs
3. **Visualization**: Customize the visualization dashboard
4. **Integration**: Connect to your CI/CD pipeline for continuous analysis

For advanced usage and customization, see the full documentation in the `docs/` directory.