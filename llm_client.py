import json
import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
import httpx
from openai import OpenAI
from anthropic import Anthropic

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

class OpenAIProvider(LLMProvider):
    def __init__(self, config: LLMConfig):
        self.client = OpenAI(api_key=config.api_key)
        self.model = config.model

    async def generate(self, messages: list, schema: Optional[Dict] = None) -> str:
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1
        }

        if schema:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "response",
                    "schema": schema
                }
            }

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

class AnthropicProvider(LLMProvider):
    def __init__(self, config: LLMConfig):
        self.client = Anthropic(api_key=config.api_key)
        self.model = config.model

    async def generate(self, messages: list, schema: Optional[Dict] = None) -> str:
        system_msg = None
        user_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                user_messages.append(msg)

        kwargs = {
            "model": self.model,
            "max_tokens": 4000,
            "temperature": 0.1,
            "messages": user_messages
        }

        if system_msg:
            kwargs["system"] = system_msg

        response = self.client.messages.create(**kwargs)
        return response.content[0].text

class GroqProvider(LLMProvider):
    def __init__(self, config: LLMConfig):
        self.client = OpenAI(
            api_key=config.api_key,
            base_url="https://api.groq.com/openai/v1"
        )
        self.model = config.model

    async def generate(self, messages: list, schema: Optional[Dict] = None) -> str:
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1
        }

        if schema:
            kwargs["response_format"] = {"type": "json_object"}
            system_prompt = messages[0]["content"] if messages and messages[0]["role"] == "system" else ""
            system_prompt += f"\n\nRespond with valid JSON matching this schema: {json.dumps(schema)}"
            messages[0] = {"role": "system", "content": system_prompt}

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

class OpenRouterProvider(LLMProvider):
    def __init__(self, config: LLMConfig):
        self.api_key = config.api_key
        self.model = config.model
        self.base_url = "https://openrouter.ai/api/v1"

    async def generate(self, messages: list, schema: Optional[Dict] = None) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1
        }

        if schema:
            system_prompt = messages[0]["content"] if messages and messages[0]["role"] == "system" else ""
            system_prompt += f"\n\nIMPORTANT: You must respond with ONLY valid JSON matching this exact schema: {json.dumps(schema)}\n\nDo not include any thinking, explanation, or text outside the JSON. Only return the JSON object."
            messages[0] = {"role": "system", "content": system_prompt}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

class LLMClient:
    def __init__(self, config: LLMConfig):
        self.provider = self._create_provider(config)

    def _create_provider(self, config: LLMConfig) -> LLMProvider:
        provider_map = {
            "openai": OpenAIProvider,
            "anthropic": AnthropicProvider,
            "groq": GroqProvider,
            "openrouter": OpenRouterProvider
        }

        provider_class = provider_map.get(config.provider.lower())
        if not provider_class:
            raise ValueError(f"Unsupported provider: {config.provider}")

        return provider_class(config)

    async def generate(self, messages: list, schema: Optional[Dict] = None) -> str:
        return await self.provider.generate(messages, schema)

def create_llm_client(
    provider: str,
    model: str,
    api_key: Optional[str] = None
) -> LLMClient:
    if not api_key:
        env_key_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "groq": "GROQ_API_KEY",
            "openrouter": "OPENROUTER_API_KEY"
        }
        api_key = os.getenv(env_key_map.get(provider.lower(), f"{provider.upper()}_API_KEY"))

        if not api_key:
            raise ValueError(f"API key not found for {provider}")

    config = LLMConfig(
        provider=provider,
        api_key=api_key,
        model=model
    )

    return LLMClient(config)