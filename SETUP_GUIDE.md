# CodeToGraph Setup and Configuration Guide

## Issues Fixed

This guide addresses the configuration loading and connection issues that were preventing CodeToGraph from working properly.

### ✅ Fixed Issues

1. **Environment Variables Not Loading** - Fixed Pydantic BaseSettings configuration
2. **Neo4j Connection Issues** - Enhanced error handling and provided clear guidance
3. **Joern Path Detection** - Improved auto-detection with better messaging
4. **LLM Configuration Loading** - Fixed VLLM client configuration loading
5. **Placeholder Detection** - Added intelligent detection of example/placeholder values

## Configuration Setup

### 1. Environment Variables (.env file)

The `.env` file should contain your actual configuration values (not placeholders):

```bash
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_actual_password_here
NEO4J_DATABASE=neo4j

# LLM Configuration - VLLM
LLM_PROVIDER=vllm
LLM_VLLM_BASE_URL=https://your-actual-vllm-endpoint.com
LLM_VLLM_API_KEY=your_actual_api_key_here
LLM_VLLM_MODEL=/app/models/qwen3:14b

# Processing Configuration
PROCESSING_MAX_CHUNK_SIZE=100
PROCESSING_MAX_MEMORY_GB=16
PROCESSING_JOERN_HEAP_SIZE=8G
PROCESSING_CHUNK_STRATEGY=hybrid

# Visualization Configuration
VIZ_HOST=localhost
VIZ_PORT=8080
VIZ_MAX_NODES_PER_VIEW=1000

# Debug Settings
DEBUG=false
LOG_LEVEL=INFO
```

### 2. Neo4j Setup

#### Option A: Docker (Recommended)
```bash
# Start Neo4j with Docker
docker run -d \
  --name neo4j-codetoraph \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your_actual_password_here \
  -v neo4j_data:/data \
  neo4j:5.12

# Check if running
docker ps
```

#### Option B: Local Installation
1. Download Neo4j from https://neo4j.com/download/
2. Install and start the service
3. Set password to match your `.env` file
4. Ensure it's listening on port 7687

### 3. VLLM Server Setup

For remote VLLM servers (enterprise environments):

1. **Update your .env file** with actual VLLM endpoint:
   ```bash
   LLM_VLLM_BASE_URL=https://vllm.yourcompany.com
   LLM_VLLM_API_KEY=your_actual_api_key
   ```

2. **VPN Connection** (if required):
   - Ensure you're connected to your company VPN
   - Test connectivity: `curl -H "Authorization: Bearer your_api_key" https://vllm.yourcompany.com/health`

### 4. Joern Setup

Joern is already included in the repository as `joern-cli/`. The system will auto-detect it.

If you need a fresh installation:
```bash
# Download Joern (if needed)
wget https://github.com/joernio/joern/releases/latest/download/joern-cli.zip
unzip joern-cli.zip
```

## Testing Your Setup

### 1. Run the Debug Script
```bash
source .venv/bin/activate
python debug_config.py
```

### 2. Check System Status
```bash
source .venv/bin/activate
code-to-graph status
```

### 3. Expected Status Output
```
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Component    ┃ Status    ┃ Details                                           ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Neo4j        │ ✓ Connected│ X nodes, Y relationships                         │
│ Tree-sitter  │ ✓ Enabled │ Languages: go, java, python, javascript, ts     │
│ Joern        │ ✓ Found   │ joern-cli                                        │
│ LLM (VLLM)   │ ✓ Connected│ Model: /app/models/qwen3:14b                    │
│ API Key      │ ℹ Info    │ ✓ Configured                                     │
│ Environment  │ ℹ Info    │ Production/VPN                                   │
└──────────────┴───────────┴───────────────────────────────────────────────────┘
```

## Troubleshooting

### Neo4j Issues

**"Connection refused":**
- Neo4j is not running
- Start with: `docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password123 neo4j:latest`

**"Authentication failure":**
- Wrong username/password in `.env` file
- Check `NEO4J_USERNAME` and `NEO4J_PASSWORD`
- Default is usually `neo4j/password123` for Docker

### LLM Issues

**"Server not responding":**
- VLLM endpoint is incorrect or down
- Check VPN connection if using enterprise endpoint
- Verify `LLM_VLLM_BASE_URL` and `LLM_VLLM_API_KEY`

**"Placeholder configuration detected":**
- Update `.env` file with actual values
- Remove example URLs like `https://vllm.example.com`
- Replace placeholder API keys

### Joern Issues

**"Not found":**
- Joern should be auto-detected in `joern-cli/` directory
- If missing, download from Joern releases
- Ensure executable permissions: `chmod +x joern-cli/joern`

## Usage Examples

### 1. Analyze a Repository
```bash
source .venv/bin/activate

# Analyze without importing to Neo4j
code-to-graph analyze --repo-path /path/to/your/repo --language go

# Analyze and import to Neo4j
code-to-graph import-graph --repo-path /path/to/your/repo --clear --create-indexes
```

### 2. Start Visualization
```bash
source .venv/bin/activate
code-to-graph visualize --port 8080
# Open http://localhost:8080 in browser
```

### 3. Code Analysis with LLM
```bash
source .venv/bin/activate

# Analyze single file
code-to-graph analyze-code /path/to/file.go

# Repository insights
code-to-graph repo-insights --repo-path /path/to/repo
```

## Technical Details of Fixes

### 1. Configuration Loading Fix
- **Issue**: Nested Pydantic BaseSettings classes weren't properly loading `.env` files
- **Fix**: Added `env_file = ".env"` and `extra = "ignore"` to each settings class Config
- **File**: `src/code_to_graph/core/config.py`

### 2. Neo4j Connection Enhancement
- **Issue**: Generic connection errors without helpful guidance
- **Fix**: Added specific error handling with solution suggestions
- **File**: `src/code_to_graph/storage/neo4j_client.py`

### 3. Joern Auto-Detection Improvement
- **Issue**: Poor path detection logic
- **Fix**: Enhanced detection with current directory priority and better messaging
- **File**: `src/code_to_graph/parsers/joern_parser.py`

### 4. Status Command Enhancement
- **Issue**: Generic "unknown" status for components
- **Fix**: Added proper status checking and detailed information
- **File**: `src/code_to_graph/cli/main.py`

## Configuration Files Structure

```
CodeToGraph/
├── .env                    # Your actual configuration
├── config/
│   └── settings.example.yaml  # YAML config template
├── joern-cli/              # Joern installation
│   └── joern               # Joern executable
├── debug_config.py         # Configuration testing script
└── SETUP_GUIDE.md         # This guide
```

All fixes are now in place and the configuration system should work correctly with your actual environment values.