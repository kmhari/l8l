# Supported LLM Models

## OpenRouter Models (Only Supported Provider)

### High-Performance Models
- `openai/gpt-oss-120b:nitro` - OpenAI's latest large model with nitro acceleration
- `qwen/qwen3-235b-a22b-2507` - Qwen's advanced reasoning model
- `qwen/qwen3-32b:nitro` - Efficient mid-size model with nitro acceleration
- `openai/gpt-4o` - OpenAI's GPT-4 Optimized model
- `openai/gpt-4o-mini` - Smaller, faster version of GPT-4 Optimized

### Usage Example
```json
{
  "llm_settings": {
    "provider": "openrouter",
    "model": "qwen/qwen3-235b-a22b-2507",
    "api_key": "your_openrouter_api_key"
  }
}
```

## API Key Configuration

Set environment variable:
```bash
export OPENROUTER_API_KEY="your_key"
```

Or pass directly in the request body.

## Note
This application exclusively uses OpenRouter as the LLM provider. All other providers have been removed to simplify the codebase and focus on a single, reliable provider with access to multiple models.