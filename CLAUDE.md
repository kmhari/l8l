# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## System Overview

This is an **Interview Report Generator API** built with FastAPI that processes interview transcripts and generates structured evaluation reports using various LLM providers.

### Core Architecture

The application follows a two-phase pipeline:
1. **Gather Phase** (`/gather`): Segments conversation transcripts into question groups using prompt-based LLM processing
2. **Evaluate Phase** (`/generate-report`): Generates comprehensive evaluation reports by analyzing question groups in parallel

### Key Components

- **main.py**: Primary FastAPI application with endpoints, caching, and orchestration logic
- **llm_client.py**: Abstract LLM provider interface supporting OpenAI, Anthropic, Groq, and OpenRouter
- **prompts/**: Contains system prompts and JSON schemas for LLM interactions
- **cache/**: File-based caching system for gather results to improve performance
- **output/**: Timestamped JSON outputs for both gather and evaluate operations

## Development Commands

### Environment Setup
```bash
# Create environment from requirements.txt
uv pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Running the Application
```bash
# Start the development server
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Alternative direct execution
uv run python main.py
```

### Testing
```bash
# Quick API test with sample data
uv run python test_simple.py

# Comprehensive API testing
uv run python test_api.py

# Performance testing
uv run python test_performance.py

# Model enforcement testing
uv run python test_model_enforcement.py

# Cache system testing
uv run python test_caching.py

# New endpoints testing
uv run python test_new_endpoints.py
```

### API Documentation
Access the interactive API documentation at:
- **Scalar UI**: http://localhost:8000/scalar
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Architecture Details

### LLM Provider System
The application uses a plugin-based LLM provider architecture:
- **OpenRouterProvider**: Primary provider with access to latest models
- **OpenAIProvider**: Direct OpenAI API integration
- **AnthropicProvider**: Claude models support
- **GroqProvider**: Fast inference for specific models

### Model Enforcement Strategy
- **Gather endpoint**: Forces `openrouter/openai/gpt-oss-120b:nitro` for consistency
- **Evaluate endpoint**: Allows flexible model selection, defaults to `qwen/qwen3-235b-a22b-thinking-2507`

### Caching System
- MD5-based cache keys generated from request content
- Cache hits return immediately with age metadata
- Failed LLM responses are not cached
- Cache management endpoints for monitoring and cleanup

### Error Handling & JSON Extraction
The system includes sophisticated JSON extraction for handling "thinking" models that may return additional reasoning text alongside structured JSON responses.

## Key Configuration

### Environment Variables
Required API keys in `.env`:
- `OPENROUTER_API_KEY`: Primary provider (recommended)
- `OPENAI_API_KEY`: Direct OpenAI access
- `ANTHROPIC_API_KEY`: Claude models
- `GROQ_API_KEY`: Fast inference models

### Default Models
- **Gather**: `openai/gpt-oss-120b:nitro` (enforced)
- **Evaluate**: `qwen/qwen3-235b-a22b-thinking-2507` (default)

See `models.md` for complete list of supported models and usage examples.

### Performance Considerations
- Question group evaluations run in parallel using `asyncio.gather()`
- Cache system prevents redundant LLM calls for identical inputs
- JSON schema validation ensures structured outputs
- Conversation building optimized using index references

## File Structure Notes

- `sample/`: Contains example request data for testing
- `prompts/*.md`: Human-readable system prompts
- `prompts/*.schema.json`: JSON schemas for LLM response validation
- `output/`: Timestamped results with comprehensive metadata
- `cache/gather/`: MD5-keyed cache files for gather operations