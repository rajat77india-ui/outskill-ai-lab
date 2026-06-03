"""Configuration loader for the SCF Brain agent."""

import os

from dotenv import load_dotenv


def load_config() -> dict[str, str | None]:
    """Load configuration from environment variables.

    Returns:
        dict: Configuration with OpenRouter credentials and model settings.
    """
    load_dotenv()
    return {
        "openrouter_api_key": os.getenv("OPENROUTER_API_KEY"),
        "openrouter_base_url": os.getenv(
            "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
        ),
        "model_name": os.getenv("OPENROUTER_MODEL", "openai/gpt-4.1-mini"),
    }
