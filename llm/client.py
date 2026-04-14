"""DashScope API configuration and LLM client."""

import os
import requests
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv, find_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import get_llm_config

load_dotenv(find_dotenv(usecwd=True))


class DashScopeConfig(BaseModel):
    """DashScope API configuration."""

    api_key: str
    base_url: str = "https://coding.dashscope.aliyuncs.com/v1"
    model: str = "qwen3.5-plus"
    max_tokens: int = 2048
    temperature: float = 0.7
    timeout: int = 90


class LLMClient:
    """
    Client for DashScope Qwen LLM API.

    Supports qwen-plus, qwen-turbo, qwen-max models.
    API documentation: https://help.aliyun.com/zh/dashscope/
    """

    def __init__(self, config: Optional[DashScopeConfig] = None):
        """
        Initialize LLM client.

        Args:
            config: DashScope configuration. If None, reads from environment.
        """
        if config is None:
            llm_config = get_llm_config()
            api_key = llm_config.api_key

            if not api_key:
                raise ValueError(
                    "DASHSCOPE_API_KEY not found. Please set the environment variable "
                    "or provide a DashScopeConfig. For local testing, place a .env file "
                    "in the project root with DASHSCOPE_API_KEY=sk-... and restart."
                )

            config = DashScopeConfig(
                api_key=api_key,
                model=llm_config.model,
                max_tokens=llm_config.max_tokens,
                temperature=llm_config.temperature,
                timeout=llm_config.timeout,
            )

        self.config = config
        self.session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update({
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        })

    def chat(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Send chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            system_prompt: Optional system prompt to prepend.
            **kwargs: Additional parameters for API.

        Returns:
            AI response content string.
        """
        # Build messages with optional system prompt
        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})
        api_messages.extend(messages)

        payload = {
            "model": self.config.model,
            "messages": api_messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            **kwargs
        }

        try:
            response = self.session.post(
                f"{self.config.base_url}/chat/completions",
                json=payload,
                timeout=kwargs.get("timeout", self.config.timeout)
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"API request failed: {str(e)}")
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Invalid API response format: {str(e)}")

    def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        system_prompt: Optional[str] = None
    ) -> dict:
        """
        Send chat completion request with function calling support.

        Args:
            messages: List of message dicts.
            tools: List of tool definitions for function calling.
            system_prompt: Optional system prompt.

        Returns:
            Response dict with potential tool calls.
        """
        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})
        api_messages.extend(messages)

        payload = {
            "model": self.config.model,
            "messages": api_messages,
            "tools": tools,
            "tool_choice": "auto",
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature
        }

        try:
            response = self.session.post(
                f"{self.config.base_url}/chat/completions",
                json=payload,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"API request failed: {str(e)}")
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Invalid API response format: {str(e)}")


def get_llm_client() -> LLMClient:
    """Get LLM client from environment config."""
    return LLMClient()
