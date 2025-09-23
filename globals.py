"""
Global configuration for LLM models and providers used across the application.

This module centralizes all model settings for the gather and generate-report APIs,
making it easy to update models without changing code in multiple places.
"""

# =============================================================================
# GATHER ENDPOINT CONFIGURATION
# =============================================================================

# Model settings for the /gather endpoint (conversation segmentation)
GATHER_CONFIG = {
    "provider": "openrouter",
    "model": "openai/gpt-oss-120b:nitro",
    "description": "High-performance model for conversation analysis and question group segmentation"
}

# =============================================================================
# EVALUATION ENDPOINT CONFIGURATION
# =============================================================================

# Model settings for the /generate-report endpoint (evaluation and scoring)
EVALUATION_CONFIG = {
    "provider": "openrouter",
    # "model": "qwen/qwen3-235b-a22b-2507",
    "model": "qwen/qwen3-32b",
    "description": "Advanced reasoning model for comprehensive candidate evaluation"
}

# =============================================================================
# FALLBACK CONFIGURATIONS
# =============================================================================

# Fallback models in case primary models are unavailable
FALLBACK_MODELS = {
    "gather_fallback": {
        "provider": "openrouter",
        "model": "anthropic/claude-3.5-sonnet",
        "description": "Fallback model for gather operations"
    },
    "evaluation_fallback": {
        "provider": "openrouter",
        "model": "anthropic/claude-3.5-sonnet",
        "description": "Fallback model for evaluation operations"
    }
}

# =============================================================================
# MODEL CAPABILITIES AND FEATURES
# =============================================================================

MODEL_FEATURES = {
    "openai/gpt-oss-120b:nitro": {
        "structured_output": True,
        "context_window": 120000,
        "reasoning": "strong",
        "speed": "fast",
        "cost": "medium"
    },
    "qwen/qwen3-235b-a22b-2507": {
        "structured_output": True,
        "context_window": 32000,
        "reasoning": "excellent",
        "speed": "medium",
        "cost": "low",
        "thinking_model": True
    },
    "anthropic/claude-3.5-sonnet": {
        "structured_output": True,
        "context_window": 200000,
        "reasoning": "excellent",
        "speed": "medium",
        "cost": "high"
    }
}

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_gather_config():
    """Get the current gather endpoint configuration."""
    return GATHER_CONFIG.copy()

def get_evaluation_config():
    """Get the current evaluation endpoint configuration."""
    return EVALUATION_CONFIG.copy()

def get_model_info(model_name):
    """Get feature information for a specific model."""
    return MODEL_FEATURES.get(model_name, {})

def update_gather_model(provider, model):
    """Update the gather model configuration."""
    GATHER_CONFIG["provider"] = provider
    GATHER_CONFIG["model"] = model
    print(f"✅ Updated gather model: {provider}/{model}")

def update_evaluation_model(provider, model):
    """Update the evaluation model configuration."""
    EVALUATION_CONFIG["provider"] = provider
    EVALUATION_CONFIG["model"] = model
    print(f"✅ Updated evaluation model: {provider}/{model}")

# =============================================================================
# ENVIRONMENT-SPECIFIC OVERRIDES
# =============================================================================

def load_config_from_env():
    """Load model configurations from environment variables if available."""
    import os

    # Override gather config from environment
    gather_provider = os.getenv('GATHER_PROVIDER')
    gather_model = os.getenv('GATHER_MODEL')
    if gather_provider and gather_model:
        update_gather_model(gather_provider, gather_model)

    # Override evaluation config from environment
    eval_provider = os.getenv('EVALUATION_PROVIDER')
    eval_model = os.getenv('EVALUATION_MODEL')
    if eval_provider and eval_model:
        update_evaluation_model(eval_provider, eval_model)

# Load environment overrides on import
load_config_from_env()