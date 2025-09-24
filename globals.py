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

    # Load gather model from environment (provider is always openrouter)
    gather_model = os.getenv('GATHER_MODEL')
    if gather_model:
        update_gather_model('openrouter', gather_model)

    # Load evaluation model from environment (provider is always openrouter)
    eval_model = os.getenv('EVALUATION_MODEL')
    if eval_model:
        update_evaluation_model('openrouter', eval_model)

# Load environment overrides on import
load_config_from_env()