"""
Global configuration for LLM models and providers used across the application.

All configuration must be provided via environment variables or request parameters.
No defaults are set in this module.
"""

class CEREBRAS_MODELS:
    GPT_OSS = "openai/gpt-oss-120b"
    QWEN3_235B = "qwen/qwen3-235b-a22b-thinking-2507"
    QWEN3_32B = "qwen/qwen3-32b"
    QWEN3_CODER = "qwen/qwen3-coder"
    QWEN3_2507 = "qwen/qwen3-235b-a22b-2507"

class GROQ_MODELS:
    GPT_OSS = "openai/gpt-oss-120b"
    QWEN3_235B = "openai/gpt-oss-20b"
    QWEN3_32B = "meta-llama/llama-guard-4-12b"




# =============================================================================
# GATHER ENDPOINT CONFIGURATION
# =============================================================================

# Model settings for the /gather endpoint (conversation segmentation)
# Must be configured via environment variables or request
GATHER_CONFIG = {}

# =============================================================================
# EVALUATION ENDPOINT CONFIGURATION
# =============================================================================

# Model settings for the /generate-report endpoint (evaluation and scoring)
# Must be configured via environment variables or request
EVALUATION_CONFIG = {}



# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_gather_config():
    """Get the current gather endpoint configuration."""
    return GATHER_CONFIG.copy()

def get_evaluation_config():
    """Get the current evaluation endpoint configuration."""
    return EVALUATION_CONFIG.copy()



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

    # Load gather provider and model from environment
    gather_provider = os.getenv('GATHER_PROVIDER', 'openrouter')  # Default to openrouter for backwards compatibility
    gather_model = os.getenv('GATHER_MODEL')
    if gather_model:
        update_gather_model(gather_provider, gather_model)

    # Load evaluation provider and model from environment
    eval_provider = os.getenv('EVALUATION_PROVIDER', 'openrouter')  # Default to openrouter for backwards compatibility
    eval_model = os.getenv('EVALUATION_MODEL')
    if eval_model:
        update_evaluation_model(eval_provider, eval_model)

# Load environment overrides on import
load_config_from_env()