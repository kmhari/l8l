import json
import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
import httpx


@dataclass
class LLMConfig:
    provider: str
    api_key: str
    model: str
    base_url: Optional[str] = None


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, messages: list, schema: Optional[Dict] = None) -> str:
        pass


class OpenRouterProvider(LLMProvider):
    def __init__(self, config: LLMConfig):
        self.api_key = config.api_key
        self.model = config.model
        self.base_url = "https://openrouter.ai/api/v1"

    async def generate(self, messages: list, schema: Optional[Dict] = None) -> str:
        print("🧠 Using OpenRouterProvider")
        print("key", self.api_key + "..." if self.api_key else "No Key")

        # Create fresh HTTP client for each API call
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 28000,  # Increase token limit for complex JSON responses
            "provider": {"only": ["cerebras"]},
        }

        if schema:
            # Try OpenRouter's structured outputs feature first
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "response", "strict": True, "schema": schema},
            }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=120,  # Increase timeout for thinking models
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]

                # Basic validation
                if not content or content.strip() == "":
                    raise ValueError("Empty response from API")

                return content
            except httpx.HTTPStatusError as e:
                # If structured outputs fail, try fallback approach
                print("HTTP error:", e.response.text)
                raise ValueError(
                    f"HTTP error from OpenRouter API: {e.response.status_code} - {e.response.text}"
                )
            except httpx.TimeoutException:
                raise TimeoutError("Request to OpenRouter API timed out")
            except KeyError as e:
                raise ValueError(
                    f"Unexpected response format from OpenRouter API: missing {e}"
                )
            except Exception as e:
                raise ValueError(f"Error calling OpenRouter API: {str(e)}")


class GroqProvider(LLMProvider):
    def __init__(self, config: LLMConfig):
        self.api_key = config.api_key
        self.model = config.model
        self.base_url = "https://api.groq.com/openai/v1"

    async def generate(self, messages: list, schema: Optional[Dict] = None) -> str:
        print("🧠 Using GroqProvider")
        print("key", self.api_key[:20] + "..." if self.api_key else "No Key")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 8000,  # Groq has different token limits
        }

        # Groq doesn't support structured outputs yet, so we rely on prompt engineering
        if schema:
            schema_prompt = f"\n\nPlease respond with valid JSON matching this schema: {json.dumps(schema)}"
            if messages and messages[-1]["role"] == "user":
                messages[-1]["content"] += schema_prompt

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60,  # Groq is generally faster
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]

                if not content or content.strip() == "":
                    raise ValueError("Empty response from API")

                return content
            except httpx.HTTPStatusError as e:
                print("HTTP error:", e.response.text)
                raise ValueError(
                    f"HTTP error from Groq API: {e.response.status_code} - {e.response.text}"
                )
            except httpx.TimeoutException:
                raise TimeoutError("Request to Groq API timed out")
            except KeyError as e:
                raise ValueError(
                    f"Unexpected response format from Groq API: missing {e}"
                )
            except Exception as e:
                raise ValueError(f"Error calling Groq API: {str(e)}")


class LLMClient:
    def __init__(self, config: LLMConfig):
        provider_name = config.provider.lower()
        if provider_name == "openrouter":
            self.provider = OpenRouterProvider(config)
        elif provider_name == "groq":
            self.provider = GroqProvider(config)
        else:
            raise ValueError(f"Unsupported provider: {config.provider}. Supported: openrouter, groq")

    async def generate(self, messages: list, schema: Optional[Dict] = None) -> str:
        return await self.provider.generate(messages, schema)


def create_llm_client(
    provider: str, model: str, api_key: Optional[str] = None
) -> LLMClient:
    provider_name = provider.lower()

    if provider_name not in ["openrouter", "groq"]:
        raise ValueError(f"Unsupported provider: {provider}. Supported: openrouter, groq")

    if not api_key:
        if provider_name == "openrouter":
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY not found in environment variables")
        elif provider_name == "groq":
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY not found in environment variables")

    config = LLMConfig(provider=provider, api_key=api_key, model=model)

    return LLMClient(config)
