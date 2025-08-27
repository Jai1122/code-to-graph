#!/bin/bash

# CodeToGraph Setup Script
# This script sets up the development environment and dependencies

set -e

echo "🚀 Setting up CodeToGraph development environment..."

# Check if Python 3.10+ is available
echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then 
    echo "❌ Python 3.10+ is required (found $python_version)"
    exit 1
fi

echo "✅ Python $python_version is compatible"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment and install dependencies
echo "📦 Installing Python dependencies..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Install development dependencies if in development mode
if [ "$1" == "--dev" ] || [ "$1" == "-d" ]; then
    echo "📦 Installing development dependencies..."
    pip install -r dev-requirements.txt
fi

# Install the package in editable mode
echo "📦 Installing CodeToGraph in editable mode..."
pip install -e .

# Check if Docker is available
if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
    echo "✅ Docker and Docker Compose are available"
    
    echo "🐳 Would you like to start the services with Docker? (y/N)"
    read -r start_docker
    
    if [[ $start_docker =~ ^[Yy]$ ]]; then
        echo "🚀 Starting Docker services..."
        docker-compose up -d neo4j
        echo "⏳ Waiting for Neo4j to be ready..."
        sleep 30
        echo "✅ Docker services started"
    fi
else
    echo "⚠️  Docker not found - you'll need to set up Neo4j manually"
fi

# Check if Joern is available
if command -v joern &> /dev/null; then
    echo "✅ Joern is available in PATH"
elif [ -d "/opt/joern" ]; then
    echo "✅ Joern found at /opt/joern"
    echo "export PATH=\$PATH:/opt/joern/bin" >> ~/.bashrc
else
    echo "⚠️  Joern not found. To install:"
    echo "    1. Download from: https://github.com/joernio/joern/releases"
    echo "    2. Extract to /opt/joern or add to PATH"
    echo "    3. Or set PROCESSING_ENABLE_JOERN=false to disable"
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data cache logs tmp config

# Copy configuration templates
echo "⚙️  Setting up configuration..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✅ Created .env file - please customize it"
else
    echo "⚠️  .env file already exists"
fi

# Configuration is handled via .env file only
echo "✅ Configuration uses .env file (no YAML config needed)"

# Test the installation
echo "🧪 Testing installation..."
source .venv/bin/activate
code-to-graph --version

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Customize .env file with your settings"
echo "2. Start Neo4j: docker-compose up -d neo4j"
echo "3. Activate environment: source .venv/bin/activate"
echo "4. Test with: code-to-graph status"
echo "5. Analyze a repository: code-to-graph analyze --repo-path /path/to/repo"
echo ""
echo "For more information, see the README.md file."