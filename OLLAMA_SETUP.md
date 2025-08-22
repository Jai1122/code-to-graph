# OLLAMA Integration Setup

## Prerequisites

1. Install OLLAMA from https://ollama.ai/
2. Start OLLAMA service: `ollama serve`

## Required Models

To use CodeToGraph with OLLAMA for code analysis, you need a chat/generation model. Install the recommended model:

```bash
# Install Qwen2.5:14B (recommended for code analysis)
ollama pull qwen2.5:14b

# Alternative models:
ollama pull llama3.1:8b
ollama pull codellama:13b
ollama pull deepseek-coder:6.7b
```

## Usage

### Check OLLAMA Status
```bash
code-to-graph ollama-status
```

### Analyze a Code File
```bash
code-to-graph analyze-code path/to/file.py
code-to-graph analyze-code --model qwen2.5:14b path/to/file.go
```

### Get Repository Insights
```bash
code-to-graph repo-insights --repo-path ./my-project
code-to-graph repo-insights --repo-path ./my-project --max-files 20
```

### Custom OLLAMA Server
```bash
code-to-graph analyze-code --ollama-url http://remote-server:11434 file.py
```

## Troubleshooting

### Connection Issues
- Ensure OLLAMA is running: `ollama serve`
- Check if models are installed: `ollama list`
- Verify server is accessible: `curl http://localhost:11434/api/tags`

### Model Issues
- 400 Bad Request: Usually means the model doesn't support chat/generation
- Use generation models like `qwen2.5:14b`, not embedding models like `nomic-embed-text`

### Performance
- Larger models (14B+) provide better analysis but require more memory
- Use smaller models (7B-8B) for faster responses on limited hardware