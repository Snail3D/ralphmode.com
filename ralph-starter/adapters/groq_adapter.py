#!/usr/bin/env python3
"""
MM-012: Groq Adapter
Fast Llama/Mixtral via Groq API
"""

import os
import logging
import aiohttp
from typing import List, Dict, Optional, Any

from model_manager import ModelAdapter, ModelConfig

logger = logging.getLogger(__name__)


class GroqAdapter(ModelAdapter):
    """
    Adapter for Groq API - fast inference for Llama, Mixtral, etc.
    Currently used as default for Ralph personality and workers.
    """

    GROQ_API_BASE = "https://api.groq.com/openai/v1"

    # Groq pricing (as of 2025)
    PRICING = {
        "llama-3.3-70b-versatile": {"input": 0.00059, "output": 0.00079},  # per 1K tokens
        "llama-3.1-70b-versatile": {"input": 0.00059, "output": 0.00079},  # deprecated
        "llama-3.1-8b-instant": {"input": 0.00005, "output": 0.00008},
        "mixtral-8x7b-32768": {"input": 0.00027, "output": 0.00027},
    }

    def __init__(self, config: ModelConfig):
        super().__init__(config)
        if not config.api_key:
            raise ValueError("Groq adapter requires an API key")
        self.api_key = config.api_key
        self.base_url = config.base_url or self.GROQ_API_BASE

    async def generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        Call Groq API to generate a response.

        Args:
            messages: List of {"role": "user/assistant/system", "content": "..."}
            max_tokens: Max tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional Groq-specific options

        Returns:
            Generated text
        """
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.config.model_id,
            "messages": messages,
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": temperature or self.config.temperature,
            **kwargs
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Groq API error ({response.status}): {error_text}")
                        raise RuntimeError(f"Groq API returned {response.status}: {error_text}")

                    data = await response.json()
                    content = data["choices"][0]["message"]["content"]

                    # Log token usage
                    usage = data.get("usage", {})
                    logger.info(
                        f"Groq API call: {usage.get('prompt_tokens', 0)} in, "
                        f"{usage.get('completion_tokens', 0)} out"
                    )

                    return content

        except aiohttp.ClientError as e:
            logger.error(f"Groq API network error: {e}")
            raise RuntimeError(f"Failed to connect to Groq API: {e}")

        except Exception as e:
            logger.error(f"Groq API unexpected error: {e}")
            raise

    async def is_available(self) -> bool:
        """
        Check if Groq API is available.
        Makes a lightweight API call to verify connectivity.
        """
        try:
            # Try a minimal request
            await self.generate(
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            return True
        except Exception as e:
            logger.warning(f"Groq availability check failed: {e}")
            return False

    async def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Estimate cost for a Groq API call in USD.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        pricing = self.PRICING.get(self.config.model_id)

        if not pricing:
            logger.warning(f"No pricing data for {self.config.model_id}, using default")
            # Default to llama-3.1-70b pricing
            pricing = self.PRICING["llama-3.1-70b-versatile"]

        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]

        return input_cost + output_cost


def create_groq_adapter_from_env() -> Optional[GroqAdapter]:
    """
    Create a Groq adapter from environment variables.
    Returns None if GROQ_API_KEY is not set.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None

    config = ModelConfig(
        provider="groq",
        model_id=os.environ.get("GROQ_MODEL", "llama-3.1-70b-versatile"),
        api_key=api_key,
        max_tokens=int(os.environ.get("GROQ_MAX_TOKENS", "4096")),
        temperature=float(os.environ.get("GROQ_TEMPERATURE", "0.7"))
    )

    return GroqAdapter(config)
