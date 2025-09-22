# Supported LLM Models

## OpenRouter Models (Recommended)

### High-Performance Models
- `openai/gpt-oss-120b:nitro` - OpenAI's latest large model with nitro acceleration
- `qwen/qwen3-235b-a22b-thinking-2507:nitro` - Qwen's advanced reasoning model
- `qwen/qwen3-32b:nitro` - Efficient mid-size model with nitro acceleration

### Usage Example
```json
{
  "llm_settings": {
    "provider": "openrouter",
    "model": "qwen/qwen3-235b-a22b-thinking-2507:nitro",
    "api_key": "your_openrouter_api_key"
  }
}
```

## Other Providers

### OpenAI
- `gpt-4o-mini` (default)
- `gpt-4o`
- `gpt-4-turbo`

### Anthropic
- `claude-3-5-sonnet-20241022`
- `claude-3-5-haiku-20241022`

### Groq
- `llama-3.1-8b-instant`
- `llama-3.1-70b-versatile`
- `mixtral-8x7b-32768`

## API Key Configuration

Set environment variables:
```bash
export OPENROUTER_API_KEY="your_key"
export OPENAI_API_KEY="your_key"
export ANTHROPIC_API_KEY="your_key"
export GROQ_API_KEY="your_key"
```

Or pass directly in the request body.