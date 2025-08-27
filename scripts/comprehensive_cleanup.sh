#!/bin/bash

# Comprehensive Cleanup Script for CodeToGraph
# Removes Joern installation, test files, and unnecessary documentation

set -e

echo "🧹 Starting comprehensive cleanup of CodeToGraph..."

# Navigate to project root
cd "$(dirname "$0")/.."

echo "📁 Current directory: $(pwd)"

# 1. Remove Joern installation completely
echo "🗑️  Removing Joern installation..."
if [ -d "joern-cli" ]; then
    rm -rf joern-cli
    echo "✅ Removed joern-cli directory"
fi

# 2. Remove test files and directories
echo "🗑️  Removing test files..."
rm -f test_*.py
rm -f debug_*.py  
rm -f demo_go_analysis.go
rm -f simple_test.go
if [ -d "test_repo" ]; then
    rm -rf test_repo
    echo "✅ Removed test_repo directory"
fi
if [ -d "test_go_project" ]; then
    rm -rf test_go_project  
    echo "✅ Removed test_go_project directory"
fi

# 3. Remove cache and temporary files
echo "🗑️  Removing cache and temporary files..."
if [ -d "cache" ]; then
    rm -rf cache
    echo "✅ Removed cache directory"
fi
if [ -d "tmp" ]; then
    rm -rf tmp
    echo "✅ Removed tmp directory"
fi
rm -f *.log

# 4. Remove excessive documentation (keep only essential ones)
echo "🗑️  Removing unnecessary documentation..."
rm -f GO_ANALYSIS_OPTIONS.md
rm -f GO_DEEP_ANALYSIS_PLAN.md
rm -f GO_NATIVE_PARSER_SUCCESS.md
rm -f HOW_IT_WORKS_WITHOUT_JOERN.md
rm -f JOERN_SETUP_GUIDE.md
rm -f JOERN_TEST_MACHINE_SETUP.md
rm -f PHASE_1A_SUCCESS.md
rm -f RUNNING_WITHOUT_JOERN.md
rm -f SETUP_GUIDE.md
rm -f COMPREHENSIVE_CONTEXT.md
echo "✅ Removed unnecessary documentation files"

# 5. Remove development files
echo "🗑️  Removing development files..."
rm -f dev-requirements.txt
rm -f run_visualization.py

# 6. Clean up data directory exports (keep structure)
echo "🗑️  Cleaning up data exports..."
if [ -d "data/export" ]; then
    rm -f data/export/*
    echo "✅ Cleaned data/export directory"
fi

# 7. Clean Python cache files
echo "🗑️  Removing Python cache files..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true

# 8. Clean logs directory but keep structure
echo "🗑️  Cleaning logs..."
if [ -d "logs" ]; then
    rm -f logs/*.log
    echo "✅ Cleaned logs directory"
fi

# 9. Remove old CFG analyzer (keep only simple one)
echo "🗑️  Cleaning Go analyzer..."
if [ -f "cmd/go-analyzer/cfg_analyzer.go" ]; then
    rm -f cmd/go-analyzer/cfg_analyzer.go
    echo "✅ Removed problematic cfg_analyzer.go"
fi

echo ""
echo "✅ Comprehensive cleanup completed!"
echo ""
echo "📊 Remaining structure:"
echo "├── Essential documentation (README.md, SECURITY.md, etc.)"
echo "├── Core source code (src/code_to_graph/)"
echo "├── Go analyzer (cmd/go-analyzer/ - cleaned)"
echo "├── Configuration (.env)"
echo "├── Scripts (scripts/)"
echo "└── Requirements (requirements*.txt, setup.py)"
echo ""
echo "🚀 CodeToGraph is now clean and ready for production use!"