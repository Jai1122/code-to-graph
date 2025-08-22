# Contributing to CodeToGraph

Thank you for your interest in contributing to CodeToGraph! This document provides guidelines for contributing to the project.

## Code of Conduct

By participating in this project, you agree to maintain a welcoming and inclusive environment for all contributors.

## Getting Started

### Development Setup

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/your-username/CodeToGraph.git
   cd CodeToGraph
   ```

2. **Set up development environment**:
   ```bash
   # Create virtual environment
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   
   # Install in development mode
   pip install -e .
   pip install -r requirements-dev.txt  # If available
   ```

3. **Set up pre-commit hooks** (optional but recommended):
   ```bash
   pip install pre-commit
   pre-commit install
   ```

4. **Configure environment**:
   ```bash
   cp .env.template .env
   # Edit .env with your local configuration
   ```

5. **Start dependencies**:
   ```bash
   # Start Neo4j
   docker run --name neo4j-dev -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password123 -d neo4j:5.12
   ```

6. **Verify setup**:
   ```bash
   code-to-graph status
   ```

## Development Guidelines

### Code Style

We use the following tools for code quality:

- **Black**: Code formatting
- **isort**: Import sorting  
- **flake8**: Linting
- **mypy**: Type checking

Run these before submitting:

```bash
# Format code
black src/
isort src/

# Check linting
flake8 src/

# Type checking
mypy src/
```

### Project Structure

```
CodeToGraph/
├── src/code_to_graph/           # Main package
│   ├── core/                    # Core configuration and utilities
│   ├── llm/                     # LLM providers and analysis
│   ├── storage/                 # Database clients and models
│   ├── parsers/                 # Code parsing logic
│   ├── processors/              # Data processing
│   ├── visualization/           # Web interface
│   └── cli/                     # Command-line interface
├── tests/                       # Test files
├── docs/                        # Documentation
├── .github/                     # GitHub templates and workflows
└── scripts/                     # Development and deployment scripts
```

### Architecture Principles

1. **Modularity**: Keep components loosely coupled
2. **Configurability**: Use environment variables for configuration
3. **Provider Agnostic**: Support multiple LLM providers
4. **Security First**: Never hardcode secrets
5. **Error Handling**: Provide clear error messages
6. **Logging**: Use structured logging with loguru
7. **Testing**: Write tests for new features

## Contributing Process

### 1. Choose an Issue

- Look at open issues labeled `good first issue` for beginners
- Check if the issue is already assigned
- Comment on the issue to express interest

### 2. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

### 3. Development

- Write code following the style guidelines
- Add tests for new functionality
- Update documentation as needed
- Ensure all tests pass locally

### 4. Testing

```bash
# Run basic functionality tests
python -c "from src.code_to_graph.core.config import settings; print('✅ Config loaded')"

# Test CLI commands
PYTHONPATH=src python -m code_to_graph.cli.main status

# Test LLM factory
python -c "
import sys; sys.path.append('src')
from code_to_graph.llm.llm_factory import LLMFactory
print('✅ Factory test passed')
"
```

### 5. Documentation

Update relevant documentation:

- Add docstrings to new functions/classes
- Update CLI help text
- Update GETTING_STARTED.md if needed
- Update .env.template for new configuration options

### 6. Commit Guidelines

Use conventional commit format:

```bash
feat: add VLLM provider support
fix: resolve Neo4j connection timeout
docs: update installation instructions
refactor: improve error handling in LLM clients
test: add integration tests for visualization
```

### 7. Submit Pull Request

- Fill out the pull request template completely
- Link to related issues
- Describe the changes and their impact
- Include screenshots for UI changes
- Ensure all CI checks pass

## Types of Contributions

### 🐛 Bug Fixes

- Follow the bug report template
- Include reproduction steps
- Add regression tests
- Ensure the fix doesn't break existing functionality

### ✨ New Features

- Discuss in an issue first for larger features
- Follow the feature request template
- Implement with backward compatibility in mind
- Add comprehensive tests and documentation

### 📚 Documentation

- Fix typos and improve clarity
- Add examples and use cases
- Update configuration documentation
- Improve error messages and help text

### 🔧 Infrastructure

- Improve CI/CD processes
- Add security scanning
- Enhance development tooling
- Optimize performance

## Specific Contribution Areas

### LLM Providers

When adding a new LLM provider:

1. Create a new client in `src/code_to_graph/llm/`
2. Follow the interface pattern of existing clients
3. Update the `LLMFactory` class
4. Add configuration options to `core/config.py`
5. Update CLI commands to support the provider
6. Add tests and documentation

### Visualization Features

When enhancing visualization:

1. Work in `src/code_to_graph/visualization/`
2. Test with different data sizes
3. Ensure mobile responsiveness
4. Add appropriate error handling
5. Update user documentation

### Code Analysis

When improving code analysis:

1. Work in `src/code_to_graph/parsers/` or `processors/`
2. Support multiple programming languages
3. Handle edge cases gracefully
4. Add comprehensive tests
5. Document new analysis capabilities

## Testing

### Running Tests

```bash
# Unit tests (when available)
pytest tests/

# Integration tests
python integration_test.py

# Manual testing checklist
code-to-graph status
code-to-graph llm-status
code-to-graph --help
```

### Test Coverage Areas

- Configuration loading
- LLM provider switching
- Neo4j connectivity
- CLI command execution
- Error handling
- Security (no hardcoded secrets)

## Security Considerations

- Never commit real API keys or passwords
- Use `.env.template` for configuration examples
- Follow the security policy in SECURITY.md
- Test with minimal required permissions
- Validate all user inputs

## Documentation Standards

- Use clear, concise language
- Include practical examples
- Explain the "why" not just the "how"
- Update configuration templates
- Add troubleshooting information

## Release Process

1. Update version numbers
2. Update CHANGELOG.md
3. Create release notes
4. Tag the release
5. Update documentation

## Getting Help

- Check existing documentation first
- Search existing issues
- Join discussions in issues
- Ask questions in pull requests
- Follow up on your contributions

## Recognition

Contributors will be recognized in:

- GitHub contributors list
- Release notes for significant contributions
- Documentation acknowledgments

Thank you for contributing to CodeToGraph! 🚀