#!/usr/bin/env python3
"""
DA-001: GLM Design Agent Integration
Z.AI GLM models for design decisions (Frinky's brain)
"""

import logging
import aiohttp
from typing import List, Dict, Optional

from model_manager import ModelAdapter, ModelConfig

logger = logging.getLogger(__name__)


class GLMAdapter(ModelAdapter):
    """
    Adapter for Z.AI GLM models via Anthropic-compatible API.
    Used exclusively for design role (Frinky - UI/UX decisions).

    DA-003: Uses ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic
    """

    def __init__(self, config: ModelConfig):
        super().__init__(config)
        if not config.api_key:
            raise ValueError("GLM adapter requires an API key")
        if not config.base_url:
            raise ValueError("GLM adapter requires base_url (https://api.z.ai/api/anthropic)")
        self.api_key = config.api_key
        self.base_url = config.base_url

    async def generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        Call GLM API via Anthropic-compatible endpoint.
        Used for design decisions only.
        """
        url = f"{self.base_url}/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }

        # Convert to Anthropic format
        system_messages = [m["content"] for m in messages if m["role"] == "system"]
        conversation = [m for m in messages if m["role"] != "system"]

        payload = {
            "model": self.config.model_id,  # "GLM-4.7"
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
                        logger.error(f"GLM API error ({response.status}): {error_text}")
                        raise RuntimeError(f"GLM API returned {response.status}")

                    data = await response.json()
                    content = data["content"][0]["text"]

                    logger.info("GLM API call successful (Design Agent)")
                    return content

        except Exception as e:
            logger.error(f"GLM API error: {e}")
            raise

    async def is_available(self) -> bool:
        """Check if GLM API is available"""
        try:
            await self.generate(
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            return True
        except Exception as e:
            logger.warning(f"GLM availability check failed: {e}")
            return False

    async def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        GLM pricing is competitive with Claude.
        Using approximate pricing until official rates confirmed.
        """
        # Approximate: $0.001 per 1K tokens (both input and output)
        return ((input_tokens + output_tokens) / 1000) * 0.001
