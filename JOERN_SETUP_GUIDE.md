# Joern Setup Guide for Different Environments

## Enhanced Joern Detection

The CodeToGraph system now supports multiple Joern installation patterns commonly found in different environments:

### Supported Installation Patterns

1. **Standard Installation**: `./joern-cli/joern`
2. **Tools Directory**: `./tools/joern` (for enterprise/CI environments)
3. **System PATH**: Joern available in system PATH
4. **Environment Variable**: `JOERN_HOME` environment variable
5. **Alternative Patterns**: `./bin/joern`, `./external/joern/`, etc.

## Setup Options for Your Test Machine

### Option 1: Tools Directory Setup (Recommended for your environment)

Since your test machine uses `./tools/`, here's how to set it up:

```bash
# Create tools directory if it doesn't exist
mkdir -p tools

# Download and install Joern in tools directory
cd tools
wget https://github.com/joernio/joern/releases/latest/download/joern-cli.zip
unzip joern-cli.zip

# Move joern executable to tools root (if needed)
# This depends on your joern-cli.zip structure
# You want to end up with: ./tools/joern

# Make sure it's executable
chmod +x joern

# Test the installation
./joern --help
```

### Option 2: Environment Variable Setup

Set the `JOERN_HOME` environment variable:

```bash
# In your shell profile (.bashrc, .zshrc, etc.)
export JOERN_HOME=/path/to/your/joern/installation

# Or for just this session:
export JOERN_HOME=/path/to/your/tools/joern-parent-directory
```

### Option 3: Add to System PATH

```bash
# Add joern to PATH (in your shell profile)
export PATH="/path/to/your/tools:$PATH"

# Or create a symlink to a directory already in PATH
sudo ln -s /path/to/your/tools/joern /usr/local/bin/joern
```

## Directory Structure Examples

### Current Working Structure (this machine):
```
CodeToGraph/
├── joern-cli/
│   └── joern          # ✅ Detected
└── ...
```

### Your Test Machine Structure (Option A):
```
CodeToGraph/
├── tools/
│   └── joern          # ✅ Will be detected
└── ...
```

### Your Test Machine Structure (Option B):
```
CodeToGraph/
├── tools/
│   └── joern-cli/
│       └── joern      # ✅ Will be detected
└── ...
```

### Your Test Machine Structure (Option C):
```
CodeToGraph/
├── tools/
│   └── joern/
│       └── bin/
│           └── joern  # ✅ Will be detected
└── ...
```

## Testing Your Setup

### 1. Test with the Detection Script
```bash
source .venv/bin/activate
python test_joern_detection.py
```

### 2. Test with CodeToGraph Status
```bash
source .venv/bin/activate
code-to-graph status
```

Expected output for successful detection:
```
┃ Joern        │ ✓ Found   │ tools                          │
```

### 3. Test Joern Directly
```bash
# If in tools directory:
./tools/joern --help

# If in PATH:
joern --help

# If using JOERN_HOME:
$JOERN_HOME/joern --help
```

## Installation Instructions by Platform

### Linux/macOS (Direct Download)
```bash
# Create tools directory
mkdir -p tools
cd tools

# Download latest Joern
wget https://github.com/joernio/joern/releases/latest/download/joern-cli.zip
unzip joern-cli.zip

# The zip typically creates a directory structure like:
# joern-cli/
#   ├── joern           # Main executable
#   ├── bin/
#   └── ...

# For tools/joern pattern, you might need to:
cp joern-cli/joern ./joern
chmod +x joern
```

### Using Package Manager (if available)
```bash
# Some systems may have joern available via package manager
# This would make it available in PATH automatically
brew install joern    # macOS with Homebrew (if available)
```

### Docker-based Setup (Alternative)
```bash
# If you prefer Docker, you can create a wrapper script
cat > tools/joern << 'EOF'
#!/bin/bash
docker run --rm -v "$(pwd):/workspace" -w /workspace \
  joernio/joern:latest joern "$@"
EOF

chmod +x tools/joern
```

## Environment Variables (.env file)

You can also add Joern configuration to your `.env` file:

```bash
# Add to .env file
JOERN_HOME=/path/to/your/joern/installation

# Or disable Joern if you don't want to use it
PROCESSING_ENABLE_JOERN=false
```

## Troubleshooting

### Common Issues and Solutions

1. **"Not Found" Status**:
   - Check if joern executable exists and is executable
   - Verify directory structure matches one of the supported patterns
   - Test with `python test_joern_detection.py`

2. **"Permission Denied"**:
   - Make sure joern executable has execute permissions: `chmod +x path/to/joern`

3. **"Command Not Found" when running joern directly**:
   - Joern executable might not be in PATH
   - Try running with full path: `./tools/joern --help`

4. **Java/JVM Issues**:
   - Joern requires Java 11 or higher
   - Check with: `java -version`
   - Install Java if needed

### Debug Commands

```bash
# Check what the system finds
python test_joern_detection.py

# Check directory structure
ls -la tools/
ls -la tools/joern*

# Test joern directly
./tools/joern --help

# Check Java version (Joern requirement)
java -version

# Check system status
source .venv/bin/activate
code-to-graph status
```

## Disable Joern (Alternative)

If you don't want to use Joern parsing, you can disable it:

```bash
# In commands, add --disable-joern flag:
code-to-graph analyze --repo-path /path/to/repo --disable-joern

# Or set in environment:
export PROCESSING_ENABLE_JOERN=false
```

## Summary

The enhanced Joern detection now supports your `./tools/` directory structure. Choose the setup option that best fits your environment, and the system will automatically detect and use Joern for semantic analysis.