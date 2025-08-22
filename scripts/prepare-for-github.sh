#!/bin/bash
# Prepare CodeToGraph repository for GitHub

set -e  # Exit on any error

echo "🚀 Preparing CodeToGraph for GitHub..."
echo "=================================="

# Run cleanup first
echo "1. Running cleanup script..."
./scripts/clean.sh

# Check for sensitive files
echo ""
echo "2. Security check..."
SECRETS_FOUND=false

# Check .env file
if [ -f ".env" ]; then
    if grep -q "password123\|your.*key\|sk-" .env 2>/dev/null; then
        echo "❌ .env contains example/placeholder values - this is OK"
    else
        echo "⚠️  .env exists. Please ensure it doesn't contain real secrets"
    fi
fi

# Check for API keys in source code
if grep -r "sk-[a-zA-Z0-9]" src/ 2>/dev/null | grep -v template | grep -v example; then
    echo "❌ Real API keys found in source code!"
    SECRETS_FOUND=true
fi

if grep -r "password.*=" src/ 2>/dev/null | grep -v Field | grep -v template; then
    echo "❌ Hardcoded passwords found in source code!"
    SECRETS_FOUND=true
fi

if [ "$SECRETS_FOUND" = true ]; then
    echo "❌ Security issues found! Please fix before committing."
    exit 1
fi

# Check required files exist
echo ""
echo "3. Checking required files..."
REQUIRED_FILES=(
    "README.md"
    "GETTING_STARTED.md"
    "SECURITY.md"
    "CONTRIBUTING.md"
    ".gitignore"
    ".env.template"
    "src/code_to_graph/__init__.py"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file exists"
    else
        echo "❌ $file missing!"
        exit 1
    fi
done

# Check GitHub templates
echo ""
echo "4. Checking GitHub templates..."
GITHUB_FILES=(
    ".github/workflows/ci.yml"
    ".github/workflows/security.yml"
    ".github/PULL_REQUEST_TEMPLATE.md"
    ".github/ISSUE_TEMPLATE/bug_report.md"
    ".github/ISSUE_TEMPLATE/feature_request.md"
)

for file in "${GITHUB_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file exists"
    else
        echo "⚠️  $file missing (optional)"
    fi
done

# Test basic imports
echo ""
echo "5. Testing basic functionality..."

if PYTHONPATH=src python -c "from code_to_graph.core.config import settings; print('✅ Config import works')" 2>/dev/null; then
    echo "✅ Core imports working"
else
    echo "⚠️  Core imports failed (may be due to missing dependencies)"
fi

if PYTHONPATH=src python -c "from code_to_graph.llm.llm_factory import LLMFactory; print('✅ LLM factory works')" 2>/dev/null; then
    echo "✅ LLM factory import working"
else
    echo "⚠️  LLM factory import failed (may be due to missing dependencies)"
fi

# Git status check
echo ""
echo "6. Git repository status..."
if git status >/dev/null 2>&1; then
    echo "✅ Git repository already initialized"
else
    echo "⚠️  Git repository not initialized. Run: git init"
fi

# Final recommendations
echo ""
echo "🎉 Repository is ready for GitHub!"
echo ""
echo "📋 Next steps:"
echo "   1. Initialize Git (if not done): git init"
echo "   2. Add files: git add ."
echo "   3. Commit: git commit -m 'Initial commit: Add VLLM support to CodeToGraph'"
echo "   4. Create GitHub repository"
echo "   5. Add remote: git remote add origin https://github.com/your-username/CodeToGraph.git"
echo "   6. Push: git push -u origin main"
echo ""
echo "🔐 Security reminders:"
echo "   - Never commit .env files with real secrets"
echo "   - Use .env.template for examples"
echo "   - Review the SECURITY.md file"
echo "   - Enable GitHub security features (Dependabot, secret scanning)"
echo ""
echo "📚 Documentation provided:"
echo "   - README.md: Project overview"
echo "   - GETTING_STARTED.md: Detailed setup instructions"
echo "   - CONTRIBUTING.md: Contribution guidelines"
echo "   - SECURITY.md: Security policy"
echo ""
echo "✨ Your CodeToGraph repository with VLLM support is ready to share!"