"""LLM API wrapper module for AgentMove.

This module provides a unified interface for interacting with various LLM platforms:
- SiliconFlow
- OpenAI
- DeepInfra
- OpenRouter
- vLLM (local deployment)
"""

from __future__ import annotations

import argparse
import os
from typing import Any

import httpx
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_random_exponential

from config import ATTEMPT_COUNTER, PROXY, VLLM_URL, WAIT_TIME_MAX, WAIT_TIME_MIN
from utils import token_count


def get_api_key(platform: str, model_name: str | None = None) -> str:
    """Get API key for the specified platform.
    
    Args:
        platform: Platform name.
        model_name: Optional model name (not used currently).
        
    Returns:
        API key string.
        
    Raises:
        KeyError: If API key environment variable is not set.
    """
    platform_keys = {
        "OpenAI": "OpenAI_API_KEY",
        "DeepInfra": "DeepInfra_API_KEY",
        "vllm": "vllm_KEY",
        "SiliconFlow": "SiliconFlow_API_KEY",
        "OpenRouter": "OpenRouter_API_KEY",
    }
    key_name = platform_keys.get(platform)
    if key_name is None:
        raise ValueError(f"Unknown platform: {platform}")
    return os.environ[key_name]


class LLMAPI:
    """LLM API client for multiple platforms.
    
    Attributes:
        model_name: Short name of the model.
        platform: Platform hosting the model.
        client: OpenAI client instance.
    """
    
    # Supported platforms in priority order
    PLATFORM_LIST: list[str] = ["SiliconFlow", "OpenAI", "DeepInfra", "vllm", "OpenRouter"]
    
    # Models supported by each platform
    MODEL_PLATFORMS: dict[str, list[str]] = {
        "SiliconFlow": [
            'qwen2.5-72b', 'qwen2.5-7b', 'qwen2-1.5b', 'qwen2-7b', 'qwen2-14b',
            'qwen2-72b', 'glm4-9b', 'glm3-6b', 'deepseekv2',
            'qwen2-1.5b-pro', 'qwen2-7b-pro', 'glm4-9b-pro', 'glm3-6b-pro'
        ],
        "OpenAI": [],
        "OpenRouter": ['gpt35turbo', 'gpt4turbo', 'gpt4o', 'gpt4omini'],
        "DeepInfra": [
            'llama4-17b', 'llama3-8b', 'llama3-70b', 'gemma2-9b', 'gemma2-27b',
            'mistral7bv2', 'llama3.1-8b', 'llama3.1-70b', 'mistral7bv3', 'llama3.1-405b'
        ],
        "vllm": ['llama3-8B-local', 'gemma2-2b-local', 'chatglm3-citygpt', 'chatglm3-6B-local']
    }
    
    # Model name to API model name mapping
    MODEL_MAPPER: dict[str, str] = {
        'qwen2.5-7b': "Qwen/Qwen2.5-7B-Instruct",
        'qwen2.5-72b': "Qwen/Qwen2.5-72B-Instruct",
        'gpt35turbo': 'gpt-3.5-turbo-0125',
        'gpt4turbo': 'gpt-4-turbo-2024-04-09',
        'gpt4o': 'gpt-4o-2024-05-13',
        'gpt4omini': 'gpt-4o-mini-2024-07-18',
        'llama3-8b': 'meta-llama/Meta-Llama-3-8B-Instruct',
        'llama3.1-8b': 'meta-llama/Meta-Llama-3.1-8B-Instruct',
        'llama3-8b-pro': 'Pro/meta-llama/Meta-Llama-3-8B-Instruct',
        'llama3-70b': 'meta-llama/Meta-Llama-3-70B-Instruct',
        'llama3.1-70b': 'meta-llama/Meta-Llama-3.1-70B-Instruct',
        'llama3.1-405b': 'meta-llama/Meta-Llama-3.1-405B-Instruct',
        "llama4-17b": "meta-llama/Llama-4-Scout-17B-16E-Instruct",
        'llama2-7b': 'meta-llama/Llama-2-7b-chat-hf',
        'llama2-13b': 'meta-llama/Llama-2-13b-chat-hf',
        'llama2-70b': 'meta-llama/Llama-2-70b-chat-hf',
        'gemma2-9b': 'google/gemma-2-9b-it',
        'gemma2-9b-pro': 'Pro/google/gemma-2-9b-it',
        'gemma2-27b': 'google/gemma-2-27b-it',
        'mistral7bv2': 'mistralai/Mistral-7B-Instruct-v0.2',
        'mistral7bv3': 'mistralai/Mistral-7B-Instruct-v0.3',
        'mistral7bv2-pro': 'Pro/mistralai/Mistral-7B-Instruct-v0.2',
        'qwen2-1.5b': 'Qwen/Qwen2-1.5B-Instruct',
        'qwen2-1.5b-pro': 'Pro/Qwen/Qwen2-1.5B-Instruct',
        'qwen2-7b': 'Qwen/Qwen2-7B-Instruct',
        'qwen2-7b-pro': "Pro/Qwen/Qwen2-7B-Instruct",
        'qwen2-14b': 'Qwen/Qwen2-57B-A14B-Instruct',
        'qwen2-72b': 'Qwen/Qwen2-72B-Instruct',
        'glm4-9b': 'THUDM/glm-4-9b-chat',
        'glm4-9b-pro': 'Pro/THUDM/glm-4-9b-chat',
        'glm3-6b': 'THUDM/chatglm3-6b',
        'glm3-6b-pro': 'Pro/THUDM/chatglm3-6b',
        'deepseekv2': 'deepseek-ai/DeepSeek-V2-Chat',
        'llama3-8B-local': 'llama3-8B-local',
        'gemma2-2b-local': 'gemma2-2b-local',
        'chatglm3-citygpt': 'chatglm3-citygpt',
        'chatglm3-6B-local': 'chatglm3-6B-local'
    }

    def __init__(self, model_name: str, platform: str | None = None) -> None:
        """Initialize LLM API client.
        
        Args:
            model_name: Short name of the model.
            platform: Platform name (auto-detected if None).
            
        Raises:
            ValueError: If model or platform is invalid.
        """
        self.model_name = model_name
        self.platform: str | None = None
        self.client: OpenAI
        
        # Validate model name
        all_models = []
        for models in self.MODEL_PLATFORMS.values():
            all_models.extend(models)
        
        if self.model_name not in all_models:
            raise ValueError(f'Invalid model name! Supported: {", ".join(all_models)}')
        
        # Determine platform
        if platform is not None and platform in self.PLATFORM_LIST:
            self.platform = platform
        else:
            for p in self.PLATFORM_LIST:
                if self.model_name in self.MODEL_PLATFORMS[p]:
                    self.platform = p
                    break

        if self.platform is None:
            raise ValueError(f"Invalid API platform for model: {self.model_name}")

        if self.model_name not in self.MODEL_PLATFORMS[self.platform]:
            raise ValueError(
                f'Model {self.model_name} not available on platform {self.platform}'
            )
        
        # Initialize client
        self._init_client()
    
    def _init_client(self) -> None:
        """Initialize the OpenAI client for the selected platform."""
        if self.platform == "OpenAI":
            self.client = OpenAI(
                api_key=get_api_key(self.platform),
                http_client=httpx.Client(proxies=PROXY),
            )
        elif self.platform == "OpenRouter":
            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=get_api_key(self.platform),
                http_client=httpx.Client(proxies=PROXY),
            )
        elif self.platform == "DeepInfra":
            self.client = OpenAI(
                base_url="https://api.deepinfra.com/v1/openai",
                api_key=get_api_key(self.platform),
                http_client=httpx.Client(proxies=PROXY),
            )
        elif self.platform == "SiliconFlow":
            self.client = OpenAI(
                base_url="https://api.siliconflow.cn/v1",
                api_key=get_api_key(self.platform, self.model_name)
            )
        elif self.platform == 'vllm':
            self.client = OpenAI(
                base_url=VLLM_URL,
                api_key=get_api_key(self.platform)
            )
    
    def get_client(self) -> OpenAI:
        """Get the OpenAI client instance."""
        return self.client
    
    def get_model_name(self) -> str:
        """Get the API model name."""
        return self.MODEL_MAPPER[self.model_name]
    
    def get_platform_name(self) -> str | None:
        """Get the platform name."""
        return self.platform

    def get_supported_models(self) -> dict[str, list[str]]:
        """Get dict of supported models by platform."""
        return self.MODEL_PLATFORMS


class LLMWrapper:
    """High-level wrapper for LLM interactions with retry logic.
    
    Attributes:
        model_name: Short name of the model.
        hyperparams: Model hyperparameters.
    """
    
    DEFAULT_HYPERPARAMS: dict[str, Any] = {
        'temperature': 0.,  # Make the LLM basically deterministic
        'max_new_tokens': 100,  # Not used in OpenAI API
        'max_tokens': 1000,  # Max tokens in completion
        'max_input_tokens': 2000  # Max input tokens
    }

    def __init__(self, model_name: str, platform: str | None = None) -> None:
        """Initialize LLM wrapper.
        
        Args:
            model_name: Short name of the model.
            platform: Platform name (auto-detected if None).
        """
        self.model_name = model_name
        self.hyperparams = self.DEFAULT_HYPERPARAMS.copy()
        
        self.llm_api = LLMAPI(self.model_name, platform=platform)
        self.client = self.llm_api.get_client()
        self.api_model_name = self.llm_api.get_model_name()

    @retry(
        wait=wait_random_exponential(min=WAIT_TIME_MIN, max=WAIT_TIME_MAX),
        stop=stop_after_attempt(ATTEMPT_COUNTER)
    )
    def get_response(self, prompt_text: str) -> str | None:
        """Get response from LLM.
        
        Args:
            prompt_text: Prompt to send to the model.
            
        Returns:
            Model response text.
        """
        system_messages: list[dict[str, str]] = []
        if "gpt" in self.model_name:
            system_messages = [{
                "role": "system",
                "content": "You are a helpful assistant who predicts user next location."
            }]
        
        # Truncate if too long
        if token_count(prompt_text) > self.hyperparams['max_input_tokens']:
            max_chars = min(self.hyperparams['max_input_tokens'] * 3, len(prompt_text))
            prompt_text = prompt_text[-max_chars:]
        
        response = self.client.chat.completions.create(
            model=self.api_model_name,
            messages=system_messages + [{"role": "user", "content": prompt_text}],
            max_tokens=self.hyperparams["max_tokens"],
            temperature=self.hyperparams["temperature"]
        )
        return response.choices[0].message.content


if __name__ == "__main__":
    prompt_text = "Who are you?"

    parser = argparse.ArgumentParser()
    parser.add_argument('--model_name', type=str, default="llama3-8b")
    parser.add_argument(
        "--platform",
        type=str,
        default="SiliconFlow",
        choices=["SiliconFlow", "OpenAI", "DeepInfra"]
    )
    args = parser.parse_args()

    llm = LLMWrapper(model_name=args.model_name, platform=args.platform)
    print(llm.get_response(prompt_text))
