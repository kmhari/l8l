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
                response_text = str(e.response.text)
                if (
                    e.response.status_code == 400
                    and schema
                    and (
                        "Invalid schema" in response_text
                        or "not supported" in response_text
                        or "response_format" in response_text
                    )
                ):
                    print(
                        "⚠️ Structured outputs failed, falling back to prompt-based approach..."
                    )
                    return await self._fallback_generate(
                        headers, client, messages, schema
                    )
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

    async def _fallback_generate(self, headers, client, messages, schema):
        """Fallback method using prompt-based JSON generation instead of structured outputs"""
        import json

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 18000,
        }

        # Add schema instruction to system prompt
        system_prompt = (
            messages[0]["content"]
            if messages and messages[0]["role"] == "system"
            else ""
        )
        system_prompt += f"\n\nIMPORTANT: Your response must be valid JSON matching this schema: {json.dumps(schema)}"

        modified_messages = [{"role": "system", "content": system_prompt}] + messages[
            1:
        ]

        payload["messages"] = modified_messages

        response = await client.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


class LLMClient:
    def __init__(self, config: LLMConfig):
        if config.provider.lower() != "openrouter":
            raise ValueError(f"Only OpenRouter provider is supported. Got: {config.provider}")
        self.provider = OpenRouterProvider(config)

    async def generate(self, messages: list, schema: Optional[Dict] = None) -> str:
        return await self.provider.generate(messages, schema)


def create_llm_client(
    provider: str, model: str, api_key: Optional[str] = None
) -> LLMClient:
    if provider.lower() != "openrouter":
        raise ValueError("Only OpenRouter provider is supported")
    
    if not api_key:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables")

    config = LLMConfig(provider=provider, api_key=api_key, model=model)

    return LLMClient(config)
