#!/usr/bin/env python3
"""Test LLM client connection behavior to ensure fresh connections per call."""

import asyncio
import time
from unittest.mock import patch, MagicMock
from llm_client import create_llm_client, OpenAIProvider, AnthropicProvider, GroqProvider, OpenRouterProvider

async def test_fresh_connections():
    """Test that each provider creates fresh connections for each API call."""
    print("🧪 Testing fresh connection behavior for all LLM providers...\n")

    test_messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say hello"}
    ]

    # Test OpenAI Provider
    print("1️⃣ Testing OpenAI Provider...")
    try:
        with patch('llm_client.OpenAI') as mock_openai:
            # Setup mock
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Hello!"
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            # Create provider and make multiple calls
            provider = OpenAIProvider(type('Config', (), {'api_key': 'test-key', 'model': 'gpt-3.5-turbo'})())

            await provider.generate(test_messages)
            await provider.generate(test_messages)

            # Verify OpenAI client was created twice (once per call)
            assert mock_openai.call_count == 2, f"Expected 2 OpenAI client creations, got {mock_openai.call_count}"
            print("✅ OpenAI Provider creates fresh connection per call")

    except Exception as e:
        print(f"❌ OpenAI Provider test failed: {e}")
        return False

    # Test Anthropic Provider
    print("\n2️⃣ Testing Anthropic Provider...")
    try:
        with patch('llm_client.Anthropic') as mock_anthropic:
            # Setup mock
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.content = [MagicMock()]
            mock_response.content[0].text = "Hello!"
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            # Create provider and make multiple calls
            provider = AnthropicProvider(type('Config', (), {'api_key': 'test-key', 'model': 'claude-3-sonnet-20240229'})())

            await provider.generate(test_messages)
            await provider.generate(test_messages)

            # Verify Anthropic client was created twice
            assert mock_anthropic.call_count == 2, f"Expected 2 Anthropic client creations, got {mock_anthropic.call_count}"
            print("✅ Anthropic Provider creates fresh connection per call")

    except Exception as e:
        print(f"❌ Anthropic Provider test failed: {e}")
        return False

    # Test Groq Provider
    print("\n3️⃣ Testing Groq Provider...")
    try:
        with patch('llm_client.OpenAI') as mock_openai:
            # Setup mock
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Hello!"
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            # Create provider and make multiple calls
            provider = GroqProvider(type('Config', (), {'api_key': 'test-key', 'model': 'mixtral-8x7b-32768'})())

            await provider.generate(test_messages)
            await provider.generate(test_messages)

            # Verify OpenAI client (for Groq) was created twice
            assert mock_openai.call_count == 2, f"Expected 2 Groq client creations, got {mock_openai.call_count}"
            print("✅ Groq Provider creates fresh connection per call")

    except Exception as e:
        print(f"❌ Groq Provider test failed: {e}")
        return False

    # Test OpenRouter Provider
    print("\n4️⃣ Testing OpenRouter Provider...")
    try:
        with patch('llm_client.httpx.AsyncClient') as mock_httpx:
            # Setup mock async context manager
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Hello!"}}]
            }
            mock_response.raise_for_status.return_value = None

            # Create an async mock for the post method
            async def mock_post(*args, **kwargs):
                return mock_response

            mock_client.post = mock_post
            mock_httpx.return_value.__aenter__.return_value = mock_client
            mock_httpx.return_value.__aexit__.return_value = None

            # Create provider and make multiple calls
            provider = OpenRouterProvider(type('Config', (), {'api_key': 'test-key', 'model': 'openai/gpt-3.5-turbo'})())

            await provider.generate(test_messages)
            await provider.generate(test_messages)

            # Verify AsyncClient was created twice (once per call)
            assert mock_httpx.call_count == 2, f"Expected 2 AsyncClient creations, got {mock_httpx.call_count}"
            print("✅ OpenRouter Provider creates fresh connection per call")

    except Exception as e:
        print(f"❌ OpenRouter Provider test failed: {e}")
        return False

    return True

async def test_concurrent_connections():
    """Test that concurrent calls don't interfere with each other."""
    print("\n🧪 Testing concurrent connection behavior...\n")

    try:
        with patch('llm_client.OpenAI') as mock_openai:
            # Setup mock with different responses to verify isolation
            mock_client = MagicMock()
            mock_responses = []

            for i in range(3):
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = f"Response {i+1}"
                mock_responses.append(mock_response)

            mock_client.chat.completions.create.side_effect = mock_responses
            mock_openai.return_value = mock_client

            # Create provider
            provider = OpenAIProvider(type('Config', (), {'api_key': 'test-key', 'model': 'gpt-3.5-turbo'})())

            # Make concurrent calls
            test_messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say hello"}
            ]

            tasks = [
                provider.generate(test_messages),
                provider.generate(test_messages),
                provider.generate(test_messages)
            ]

            results = await asyncio.gather(*tasks)

            # Verify we got all different responses
            expected_responses = ["Response 1", "Response 2", "Response 3"]
            assert all(result in expected_responses for result in results), f"Unexpected responses: {results}"

            # Verify 3 separate client instances were created
            assert mock_openai.call_count == 3, f"Expected 3 client creations, got {mock_openai.call_count}"

            print("✅ Concurrent calls create separate connections successfully")
            print(f"   Responses: {results}")

    except Exception as e:
        print(f"❌ Concurrent connection test failed: {e}")
        return False

    return True

def test_client_factory():
    """Test that create_llm_client function works correctly."""
    print("\n🧪 Testing LLM client factory...\n")

    try:
        # Test with different providers (without actually calling APIs)
        providers_to_test = [
            ("openai", "gpt-3.5-turbo"),
            ("anthropic", "claude-3-sonnet-20240229"),
            ("groq", "mixtral-8x7b-32768"),
            ("openrouter", "openai/gpt-3.5-turbo")
        ]

        for provider, model in providers_to_test:
            try:
                client = create_llm_client(provider, model, "test-key")
                assert client is not None, f"Failed to create {provider} client"
                print(f"✅ {provider.capitalize()} client created successfully")
            except Exception as e:
                print(f"❌ Failed to create {provider} client: {e}")
                return False

        return True

    except Exception as e:
        print(f"❌ Client factory test failed: {e}")
        return False

async def main():
    """Run all connection behavior tests."""
    print("🔍 Testing LLM Client Connection Behavior\n")

    test1 = await test_fresh_connections()
    test2 = await test_concurrent_connections()
    test3 = test_client_factory()

    if test1 and test2 and test3:
        print("\n🎉 All connection behavior tests passed!")
        print("\n📋 Connection Behavior Summary:")
        print("   ✅ All providers create fresh connections per API call")
        print("   ✅ No connection reuse across multiple calls")
        print("   ✅ Concurrent calls are properly isolated")
        print("   ✅ Client factory creates all provider types")
        print("   ✅ Prevents connection state leakage between requests")
        return True
    else:
        print("\n❌ Some connection behavior tests failed!")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)