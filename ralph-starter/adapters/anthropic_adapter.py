#!/usr/bin/env python3
"""
MM-010: Anthropic Adapter
Claude models via Anthropic API
"""

import os
import logging
import aiohttp
from typing import List, Dict, Optional

from model_manager import ModelAdapter, ModelConfig

logger = logging.getLogger(__name__)


class AnthropicAdapter(ModelAdapter):
    """
    Adapter for Anthropic Claude models.
    Used for Builder role (high-quality code generation).
    """

    ANTHROPIC_API_BASE = "https://api.anthropic.com/v1"

    # Claude pricing (as of 2025)
    PRICING = {
        "claude-sonnet-4": {"input": 0.003, "output": 0.015},  # per 1K tokens
        "claude-opus-4": {"input": 0.015, "output": 0.075},
        "claude-haiku-4": {"input": 0.00025, "output": 0.00125},
    }

    def __init__(self, config: ModelConfig):
        super().__init__(config)
        if not config.api_key:
            raise ValueError("Anthropic adapter requires an API key")
        self.api_key = config.api_key
        self.base_url = config.base_url or self.ANTHROPIC_API_BASE

    async def generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """Call Anthropic API to generate a response"""
        url = f"{self.base_url}/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }

        # Convert OpenAI-style messages to Anthropic format
        system_messages = [m["content"] for m in messages if m["role"] == "system"]
        conversation = [m for m in messages if m["role"] != "system"]

        payload = {
            "model": self.config.model_id,
            "messages": conversation,
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": temperature or self.config.temperature,
            **kwargs
        }

        if system_messages:
            payload["system"] = "\n\n".join(system_messages)

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
                        logger.error(f"Anthropic API error ({response.status}): {error_text}")
                        raise RuntimeError(f"Anthropic API returned {response.status}")

                    data = await response.json()
                    content = data["content"][0]["text"]

                    # Log usage
                    usage = data.get("usage", {})
                    logger.info(
                        f"Anthropic API call: {usage.get('input_tokens', 0)} in, "
                        f"{usage.get('output_tokens', 0)} out"
                    )

                    return content

        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise

    async def is_available(self) -> bool:
        """Check if Anthropic API is available"""
        try:
            await self.generate(
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            return True
        except Exception as e:
            logger.warning(f"Anthropic availability check failed: {e}")
            return False

    async def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for Anthropic API call in USD"""
        pricing = self.PRICING.get(self.config.model_id, self.PRICING["claude-sonnet-4"])
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        return input_cost + output_cost
