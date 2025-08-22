#!/bin/bash

# Repository Analysis Script
# Example script showing how to analyze a repository with different configurations

set -e

# Default values
REPO_PATH=""
LANGUAGE=""
CHUNK_SIZE=50
STRATEGY="hybrid"
ENABLE_TREE_SITTER=true
ENABLE_JOERN=true
OUTPUT_DIR=""

# Usage function
usage() {
    echo "Usage: $0 -r <repo_path> [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -r, --repo-path PATH      Path to repository (required)"
    echo "  -l, --language LANG       Language (go, java, python, javascript, typescript)"
    echo "  -c, --chunk-size SIZE     Files per chunk (default: 50)"
    echo "  -s, --strategy STRATEGY   Chunking strategy: package, size, hybrid (default: hybrid)"
    echo "  --no-tree-sitter          Disable Tree-sitter parsing"
    echo "  --no-joern                Disable Joern CPG parsing"
    echo "  -o, --output-dir DIR      Output directory"
    echo "  -h, --help                Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 -r /path/to/go-repo -l go -c 100"
    echo "  $0 -r /path/to/java-repo --no-joern"
    echo "  $0 -r /path/to/mixed-repo -s package"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--repo-path)
            REPO_PATH="$2"
            shift 2
            ;;
        -l|--language)
            LANGUAGE="$2"
            shift 2
            ;;
        -c|--chunk-size)
            CHUNK_SIZE="$2"
            shift 2
            ;;
        -s|--strategy)
            STRATEGY="$2"
            shift 2
            ;;
        --no-tree-sitter)
            ENABLE_TREE_SITTER=false
            shift
            ;;
        --no-joern)
            ENABLE_JOERN=false
            shift
            ;;
        -o|--output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option $1"
            usage
            exit 1
            ;;
    esac
done

# Validate required arguments
if [ -z "$REPO_PATH" ]; then
    echo "Error: Repository path is required"
    usage
    exit 1
fi

if [ ! -d "$REPO_PATH" ]; then
    echo "Error: Repository path does not exist: $REPO_PATH"
    exit 1
fi

echo "🔍 Analyzing repository: $REPO_PATH"
echo "📋 Configuration:"
echo "   Language: ${LANGUAGE:-auto-detect}"
echo "   Chunk size: $CHUNK_SIZE"
echo "   Strategy: $STRATEGY"
echo "   Tree-sitter: $ENABLE_TREE_SITTER"
echo "   Joern: $ENABLE_JOERN"
echo ""

# Build command
CMD="code-to-graph analyze --repo-path '$REPO_PATH'"
CMD="$CMD --chunk-size $CHUNK_SIZE"
CMD="$CMD --chunk-strategy $STRATEGY"

if [ -n "$LANGUAGE" ]; then
    CMD="$CMD --language $LANGUAGE"
fi

if [ "$ENABLE_TREE_SITTER" = "true" ]; then
    CMD="$CMD --enable-tree-sitter"
else
    CMD="$CMD --disable-tree-sitter"
fi

if [ "$ENABLE_JOERN" = "true" ]; then
    CMD="$CMD --enable-joern"
else
    CMD="$CMD --disable-joern"
fi

if [ -n "$OUTPUT_DIR" ]; then
    CMD="$CMD --output-dir '$OUTPUT_DIR'"
fi

echo "🚀 Running analysis command:"
echo "   $CMD"
echo ""

# Activate virtual environment and execute command
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Execute the command  
eval $CMD

echo ""
echo "✅ Analysis completed!"
echo ""
echo "Next steps:"
echo "1. Import to Neo4j: code-to-graph import-graph --create-indexes"
echo "2. Start visualization: code-to-graph visualize"
echo "3. Query the graph: code-to-graph query 'find all functions'"