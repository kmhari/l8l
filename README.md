# Interview Report Generator API 🚀

AI-powered interview analysis and evaluation API with multi-provider LLM support.

## 🎯 Features

- **Multi-LLM Support**: OpenAI, Anthropic, Groq, OpenRouter
- **Two-stage Pipeline**: Conversation segregation + detailed evaluation
- **Performance Optimized**: Caching, parallel processing, index-based responses
- **Interactive Docs**: Scalar API documentation
- **Real Sample Data**: Based on actual interview transcripts

## 🏗️ Architecture

```
POST /gather → Conversation Segregation (GPT OSS 120B)
     ↓
POST /generate-report → Parallel Evaluation (Qwen Thinking Model)
     ↓
Comprehensive Report (Hire/No-hire + detailed analysis)
```

## 🚀 Quick Start

### Local Development

```bash
# Clone repository
git clone https://github.com/kmhari/l8l.git
cd l8l

# Setup environment
uv pip install -r requirements.txt
cp .env.example .env
# Add your API keys to .env

# Run development server
uv run uvicorn main:app --reload
```

### Docker

```bash
# Using Docker Compose
docker-compose up -d

# Or build manually
docker build -t l8l-api .
docker run -p 8000:8000 --env-file .env l8l-api
```

### Deploy with Nixpacks

```bash
# Railway, Render, or any Nixpacks-compatible platform
nixpacks build . --name l8l-api
```

## 🔧 Configuration

### Environment Variables

```bash
OPENROUTER_API_KEY=your_openrouter_key    # Required for gather
OPENAI_API_KEY=your_openai_key            # Optional
ANTHROPIC_API_KEY=your_anthropic_key      # Optional
GROQ_API_KEY=your_groq_key                # Optional
```

### LLM Models

**Gather Endpoint** (Fixed):
- Provider: OpenRouter
- Model: `openai/gpt-oss-120b:nitro`

**Evaluation Endpoint** (Configurable):
- Default: `qwen/qwen3-235b-a22b-thinking-2507:nitro`
- Supports: All OpenRouter, OpenAI, Anthropic, Groq models

## 📚 API Documentation

### Endpoints

- **GET** `/` - Health check
- **POST** `/gather` - Conversation segregation
- **POST** `/generate-report` - Full evaluation pipeline
- **GET** `/sample` - Sample gather data
- **GET** `/sample-evaluate` - Sample evaluation data
- **GET** `/scalar` - Interactive API documentation
- **GET** `/cache/stats` - Cache statistics
- **DELETE** `/cache/clear` - Clear cache

### Sample Usage

```bash
# Get sample data
curl http://localhost:8000/sample

# Run full evaluation
curl -X POST http://localhost:8000/generate-report \
  -H "Content-Type: application/json" \
  -d @sample/evaluate.json

# View interactive docs
open http://localhost:8000/scalar
```

## 📊 Sample Data

Based on real interview with Mohammed, Node.js developer:
- **Resume**: Experience, skills, salary expectations
- **Transcript**: 72 conversation turns, 10 technical questions
- **Analysis**: 12 conversation groups, detailed evaluations

## 🎯 Output Structure

```json
{
  "evaluation_report": {
    "overall_assessment": {
      "recommendation": "Hire|No Hire|Strong Hire|Strong No Hire",
      "confidence": "High|Medium|Low",
      "overall_score": 75,
      "summary": "Evaluation summary"
    },
    "competency_mapping": [...],
    "question_analysis": [...],
    "communication_assessment": {...},
    "critical_analysis": {...},
    "improvement_recommendations": [...]
  },
  "question_groups": {
    "groups": [...],
    "pre_inferred_facts_global": {...}
  }
}
```

## 🔄 Caching

- **Automatic caching** for gather operations
- **File-based cache** in `cache/gather/`
- **Cache management** endpoints
- **Output preservation** in `output/`

## 🧪 Testing

```bash
# Simple test
uv run python test_simple.py

# Comprehensive test suite
uv run python test_api.py

# Test specific features
uv run python test_caching.py
uv run python test_model_enforcement.py
```

## 📈 Performance

- **Parallel processing**: Multiple question groups evaluated simultaneously
- **Index-based responses**: ~70% reduction in LLM output tokens
- **Smart caching**: Avoid duplicate gather operations
- **Graceful degradation**: Individual failures don't crash pipeline

## 🛠️ Development

### Project Structure

```
l8l/
├── main.py                 # FastAPI application
├── llm_client.py          # Multi-provider LLM client
├── prompts/               # System prompts & schemas
├── sample/                # Sample data files
├── test_*.py             # Test scripts
├── cache/                # Cached results
├── output/               # Generated reports
└── requirements.txt      # Dependencies
```

### Adding New LLM Providers

1. Extend `llm_client.py` with new provider class
2. Add environment variable mapping
3. Update `LLMSettings` model defaults
4. Test with provider-specific models

## 🚀 Deployment

### Railway
```bash
railway login
railway new
railway add
railway deploy
```

### Render
- Connect GitHub repository
- Set environment variables
- Use Dockerfile or nixpacks.toml

### Heroku
```bash
heroku create l8l-api
heroku config:set OPENROUTER_API_KEY=your_key
git push heroku main
```

## 🤝 Contributing

1. Fork repository
2. Create feature branch
3. Add tests for new features
4. Submit pull request

## 📄 License

MIT License - see LICENSE file

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/kmhari/l8l/issues)
- **Docs**: `/scalar` endpoint for interactive documentation
- **Sample Data**: Use `/sample` and `/sample-evaluate` endpoints

---

Built with ❤️ using FastAPI, OpenRouter, and modern LLM APIs