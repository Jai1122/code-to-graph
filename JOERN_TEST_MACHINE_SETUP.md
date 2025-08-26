# Joern Setup Guide for Test Machine

## Issue Diagnosis

The error `[Errno 2] No such file or directory: 'tools/bin/gosrc2cpg'` indicates that:

1. ✅ **Joern detection is working** - it found a Joern installation
2. ❌ **But it's looking in the wrong path** - `tools/bin/gosrc2cpg` instead of the correct location
3. 🔧 **Your test machine needs Joern in `./tools/` directory**

## Solution Options

### Option 1: Install Joern in tools/ Directory (Recommended)

This matches what your test machine expects:

```bash
# Create tools directory
mkdir -p tools

# Download Joern
cd tools
wget https://github.com/joernio/joern/releases/latest/download/joern-cli.zip
unzip joern-cli.zip

# Set up the structure that CodeToGraph expects
# Option A: Direct executables in tools/
cp joern-cli/gosrc2cpg ./gosrc2cpg
cp joern-cli/javasrc2cpg ./javasrc2cpg  
cp joern-cli/pysrc2cpg ./pysrc2cpg
cp joern-cli/jssrc2cpg ./jssrc2cpg  # This might need special handling
chmod +x gosrc2cpg javasrc2cpg pysrc2cpg jssrc2cpg

# Option B: Create bin subdirectory
mkdir -p bin
cp joern-cli/gosrc2cpg bin/
cp joern-cli/javasrc2cpg bin/
cp joern-cli/pysrc2cpg bin/
chmod +x bin/*

# Test the installation
./gosrc2cpg --help
# or
./bin/gosrc2cpg --help
```

### Option 2: Use Environment Variable Override

Set `JOERN_HOME` to point to your existing installation:

```bash
# If you have Joern elsewhere, set JOERN_HOME
export JOERN_HOME=/path/to/your/existing/joern

# Or add to .env file
echo "JOERN_HOME=/path/to/your/existing/joern" >> .env
```

### Option 3: Create Symbolic Links

If you already have Joern installed elsewhere:

```bash
# Create tools directory with links to existing Joern
mkdir -p tools
ln -s /path/to/existing/joern-cli/gosrc2cpg tools/gosrc2cpg
ln -s /path/to/existing/joern-cli/javasrc2cpg tools/javasrc2cpg  
ln -s /path/to/existing/joern-cli/pysrc2cpg tools/pysrc2cpg

# Or create bin subdirectory with links
mkdir -p tools/bin
ln -s /path/to/existing/joern-cli/gosrc2cpg tools/bin/gosrc2cpg
ln -s /path/to/existing/joern-cli/javasrc2cpg tools/bin/javasrc2cpg
ln -s /path/to/existing/joern-cli/pysrc2cpg tools/bin/pysrc2cpg
```

## Expected Directory Structure

After setup, your test machine should have one of these structures:

### Structure A: Direct in tools/
```
CodeToGraph/
├── tools/
│   ├── gosrc2cpg          # ✅ Go frontend
│   ├── javasrc2cpg        # ✅ Java frontend  
│   ├── pysrc2cpg          # ✅ Python frontend
│   └── jssrc2cpg          # ✅ JavaScript frontend
└── ...
```

### Structure B: In tools/bin/
```
CodeToGraph/
├── tools/
│   └── bin/
│       ├── gosrc2cpg      # ✅ Go frontend
│       ├── javasrc2cpg    # ✅ Java frontend
│       ├── pysrc2cpg      # ✅ Python frontend
│       └── jssrc2cpg      # ✅ JavaScript frontend
└── ...
```

### Structure C: Full Joern in tools/
```
CodeToGraph/
├── tools/
│   └── joern-cli/
│       ├── gosrc2cpg      # ✅ Go frontend
│       ├── javasrc2cpg    # ✅ Java frontend
│       ├── pysrc2cpg      # ✅ Python frontend
│       └── ...
└── ...
```

## Testing Your Setup

### 1. Test Frontend Detection
```bash
python test_frontend_detection.py
```

Expected output:
```
📊 SUMMARY:
  go: ✅ FOUND at tools/gosrc2cpg
  java: ✅ FOUND at tools/javasrc2cpg  
  python: ✅ FOUND at tools/pysrc2cpg
  javascript: ✅ FOUND at tools/jssrc2cpg
```

### 2. Test System Status
```bash
source .venv/bin/activate
code-to-graph status
```

Expected output:
```
┃ Joern        │ ✓ Found   │ tools                          │
```

### 3. Test Frontend Directly
```bash
# Test the Go frontend
./tools/gosrc2cpg --help

# Or if in bin subdirectory:
./tools/bin/gosrc2cpg --help
```

### 4. Test with a Small Repository
```bash
# Try analyzing a small Go repository
code-to-graph analyze --repo-path ./test_repo --language go
```

## Troubleshooting

### Error: "No such file or directory: 'tools/bin/gosrc2cpg'"
- **Cause**: System expects `tools/bin/gosrc2cpg` but you have different structure
- **Solution**: Follow Option 1 above to create the expected structure

### Error: "Permission denied"  
- **Cause**: Frontend executables don't have execute permissions
- **Solution**: `chmod +x tools/gosrc2cpg tools/javasrc2cpg tools/pysrc2cpg`

### Error: "Frontend 'gosrc2cpg' not found"
- **Cause**: Frontend executable doesn't exist or isn't executable
- **Solution**: Verify the file exists and run `ls -la tools/` to check permissions

### JavaScript Frontend Issues
The JavaScript frontend (`jssrc2cpg`) may be in a different location:
```bash
# If jssrc2cpg is missing, find it:
find . -name "*jssrc2cpg*" -type f

# It might be in:
# joern-cli/frontends/jssrc2cpg/bin/jssrc2cpg

# Copy or link it:
cp joern-cli/frontends/jssrc2cpg/bin/jssrc2cpg tools/jssrc2cpg
# or
ln -s ../joern-cli/frontends/jssrc2cpg/bin/jssrc2cpg tools/jssrc2cpg
```

## Alternative: Disable Joern

If you don't want to set up Joern, you can disable it:

```bash
# Add to .env file:
echo "PROCESSING_ENABLE_JOERN=false" >> .env

# Or use CLI flag:
code-to-graph analyze --repo-path ./test_repo --disable-joern
```

## Summary

The enhanced Joern detection now supports your `tools/` directory structure. Choose the setup option that works best for your environment:

- **Option 1**: Install Joern frontends directly in `tools/` (simplest)
- **Option 2**: Use environment variable to point to existing installation  
- **Option 3**: Create symbolic links to existing installation
- **Alternative**: Disable Joern parsing entirely

After setup, run the tests to verify everything works correctly.