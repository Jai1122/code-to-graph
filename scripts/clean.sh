#!/bin/bash
# Clean up files that should not be committed to Git

echo "🧹 Cleaning up files for Git commit..."

# Remove Python cache files
echo "Removing Python cache files..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true

# Remove macOS files
echo "Removing macOS system files..."
find . -name ".DS_Store" -delete 2>/dev/null || true
find . -name "._*" -delete 2>/dev/null || true

# Remove log files
echo "Removing log files..."
find . -name "*.log" -delete 2>/dev/null || true
rm -rf logs/ 2>/dev/null || true

# Remove temporary files
echo "Removing temporary files..."
find . -name "*.tmp" -delete 2>/dev/null || true
find . -name "*.temp" -delete 2>/dev/null || true
rm -rf tmp/ 2>/dev/null || true
rm -rf temp/ 2>/dev/null || true

# Remove cache directories
echo "Removing cache directories..."
rm -rf cache/ 2>/dev/null || true
rm -rf .cache/ 2>/dev/null || true

# Remove data directories (if they exist and contain test data)
echo "Checking for data directories..."
if [ -d "data" ]; then
    echo "⚠️  data/ directory exists. Please verify it doesn't contain important data before committing."
fi

# Remove any .env files with real secrets
echo "Checking for environment files..."
if [ -f ".env" ]; then
    echo "⚠️  .env file exists. Make sure it doesn't contain real secrets!"
    echo "   Use .env.template instead for the repository."
fi

# Check for any files that might contain secrets
echo "Checking for potential secret files..."
if find . -name "*.key" -o -name "*.pem" -o -name "*secret*" -o -name "*credential*" 2>/dev/null | grep -v .git | head -1; then
    echo "⚠️  Potential secret files found. Please review before committing."
fi

echo "✅ Cleanup completed!"
echo ""
echo "📝 Before committing:"
echo "   1. Review .env.template instead of .env"
echo "   2. Make sure no real API keys or passwords are in code"
echo "   3. Run: git add . && git commit -m 'your message'"
echo ""