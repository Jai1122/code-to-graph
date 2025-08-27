# CodeToGraph: Repository Analysis & Graph Visualization

A high-performance system for analyzing code repositories, extracting entities and relationships, and visualizing them as interactive graphs in Neo4j.

## 🚀 Features

- **Multi-language parsing**: Go, Java, Python, JavaScript, TypeScript
- **Tree-sitter powered**: Fast, accurate syntax analysis
- **Neo4j integration**: Scalable graph database storage
- **Interactive visualization**: Web-based graph exploration
- **Smart filtering**: Automatic exclusion of vendor/, build/, test files
- **Fresh imports**: Automatic database clearing and re-import

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Repository    │───▶│  Tree-sitter     │───▶│     Neo4j       │
│   (Go, Java,    │    │  Parser          │    │   Graph DB      │
│   Python, etc.) │    │  (Entities +     │    │                 │
└─────────────────┘    │  Relationships)  │    └─────────────────┘
                       └──────────────────┘             │
                                                        ▼
                                                ┌─────────────────┐
                                                │  Dash Web UI    │
                                                │  Visualization  │
                                                └─────────────────┘
```

## 🔧 Tech Stack

- **Backend**: Python 3.9+, Tree-sitter, Pydantic
- **Database**: Neo4j 5.x
- **Visualization**: Dash, Plotly
- **Parsing**: Tree-sitter parsers for multiple languages
- **Data Processing**: Pandas, NetworkX

## 📋 System Requirements

- **Python**: 3.9 or higher
- **Memory**: 8GB RAM minimum (16GB recommended)
- **Storage**: 2GB free space
- **Docker**: For Neo4j database
- **Network**: For downloading dependencies

## 🛠️ Installation

### 1. Clone Repository
```bash
git clone <repository-url>
cd CodeToGraph
```

### 2. Create Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
pip install -e .  # Install CodeToGraph in development mode
```

### 4. Setup Configuration
```bash
cp .env.template .env
# Edit .env with your specific settings
```

## 🔧 Configuration

Edit your `.env` file with the following key settings:

### Neo4j Database
```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password_here
NEO4J_DATABASE=neo4j
```

### VLLM Provider (Optional)
```bash
LLM_PROVIDER=vllm
LLM_VLLM_BASE_URL=https://your-vllm-endpoint.com
LLM_VLLM_API_KEY=your_api_key_here
LLM_VLLM_MODEL=/app/models/qwen3:14b
```

### Processing Settings
```bash
PROCESSING_CHUNK_STRATEGY=hybrid
PROCESSING_MAX_CHUNK_SIZE=100
PROCESSING_ENABLE_TREE_SITTER=true
```

## 🗄️ Database Setup

### Using Docker (Recommended)
```bash
# Start Neo4j container
docker run --name neo4j-codebase \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password123 \
  -d neo4j:5.12

# Verify it's running
docker logs neo4j-codebase
```

### Access Neo4j Browser
- Open http://localhost:7474
- Login: neo4j / password123

## 🏃‍♂️ Quick Start

### 1. Check System Status
```bash
NEO4J_PASSWORD=password123 code-to-graph status
```

### 2. Analyze a Repository (Preview)
```bash
code-to-graph analyze --repo-path /path/to/your/go/project
```

### 3. Import to Neo4j
```bash
NEO4J_PASSWORD=password123 code-to-graph import-graph \
  --repo-path /path/to/your/go/project \
  --clear-db \
  --create-indexes
```

### 4. Start Visualization
```bash
NEO4J_PASSWORD=password123 code-to-graph visualize
```

Then open: http://localhost:8080

## 🌐 Supported Languages

| Language   | Parser      | Entities Supported                          |
|------------|-------------|---------------------------------------------|
| Go         | Tree-sitter | Packages, Structs, Functions, Methods, Types |
| Java       | Tree-sitter | Classes, Methods, Fields, Interfaces       |
| Python     | Tree-sitter | Classes, Functions, Methods, Variables      |
| JavaScript | Tree-sitter | Functions, Classes, Variables               |
| TypeScript | Tree-sitter | Functions, Classes, Interfaces, Types      |

## 🎯 Supported LLM Providers

- **VLLM**: Remote inference with API key authentication
  - Qwen models (qwen3:14b, qwen3:1.7b)
  - Custom model paths
  - VPN-secured endpoints

## 🔍 Usage Examples

### Basic Repository Analysis
```bash
# Analyze a Go REST API
code-to-graph analyze --repo-path ./my-go-api

# Exclude specific directories
code-to-graph analyze --repo-path ./my-project \
  --exclude-dirs vendor node_modules \
  --exclude-patterns "*.pb.go" "*_gen.go"

# Include test files
code-to-graph analyze --repo-path ./my-project --include-tests
```

### Advanced Import Options
```bash
# Import with custom exclusions
NEO4J_PASSWORD=password123 code-to-graph import-graph \
  --repo-path ./my-go-api \
  --exclude-dirs vendor build dist \
  --clear-db \
  --create-indexes

# Import without clearing existing data
NEO4J_PASSWORD=password123 code-to-graph import-graph \
  --repo-path ./my-project \
  --no-clear-db
```

### Code Analysis with LLM
```bash
# Analyze specific file with LLM
LLM_PROVIDER=vllm \
LLM_VLLM_BASE_URL=https://your-endpoint.com \
LLM_VLLM_API_KEY=your-key \
code-to-graph analyze-code --file-path ./main.go --model qwen3:14b
```

## 📊 Data Model

### Entities
- **ID**: Unique identifier
- **Name**: Entity name  
- **Type**: function, class, struct, method, variable, etc.
- **File Path**: Source file location
- **Line Numbers**: Start and end positions
- **Language**: Programming language
- **Metadata**: Additional properties

### Relationships
- **Source/Target**: Connected entity IDs
- **Type**: calls, contains, imports, extends, etc.
- **Context**: File path, line number
- **Metadata**: Additional relationship properties

## 🎨 Visualization Features

- **Interactive Graph**: Pan, zoom, filter nodes
- **Entity Filtering**: By type, language, file
- **Hierarchical Navigation**: Drill down from packages to functions
- **Relationship Exploration**: Trace calls, dependencies
- **Search**: Find entities by name or properties

## 📁 File Exclusions

CodeToGraph automatically excludes:
- `**/vendor/**` (Go dependencies)
- `**/node_modules/**` (Node.js dependencies)
- `**/build/**`, `**/dist/**` (Build outputs)
- `**/.git/**` (Git directories)
- `**/*_test.go`, `**/tests/**` (Test files, unless --include-tests)
- `**/*.pb.go`, `**/*_gen.go` (Generated files)

## 🐛 Troubleshooting

### Common Issues

**1. Neo4j Connection Failed**
```bash
# Check if Neo4j is running
docker ps | grep neo4j

# Check logs
docker logs neo4j-codebase

# Restart container
docker restart neo4j-codebase
```

**2. Parser Initialization Failed**
```bash
# Check Python dependencies
pip install -r requirements.txt

# Verify Tree-sitter parsers
python -c "import tree_sitter_go; print('Go parser OK')"
```

**3. Memory Issues**
```bash
# Reduce chunk size
export PROCESSING_MAX_CHUNK_SIZE=50
export PROCESSING_MAX_MEMORY_GB=8
```

**4. Import Failures**
```bash
# Clear database and retry
NEO4J_PASSWORD=password123 code-to-graph import-graph \
  --repo-path ./project --clear-db --create-indexes
```

### Debug Mode
```bash
# Enable debug logging
code-to-graph --debug --log-level DEBUG import-graph --repo-path ./project
```

## 🧪 Testing

```bash
# Create a test Go project
mkdir test_project && cd test_project
echo 'package main; func main() { println("Hello") }' > main.go

# Analyze it
cd .. && code-to-graph analyze --repo-path ./test_project
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if needed
5. Submit a pull request

## 📄 License

[Add your license information here]

## 🆘 Support

- Create issues for bugs or feature requests
- Check the troubleshooting section above
- Review logs in `./logs/code_to_graph.log`

---

**Built with ❤️ for code analysis and graph visualization**