#!/usr/bin/env python3
"""
MM-015: Ollama Adapter
Local AI models via Ollama
LF-001: Local AI as Default - Ollama is the preferred choice
"""

import logging
import aiohttp
from typing import List, Dict, Optional

from model_manager import ModelAdapter, ModelConfig

logger = logging.getLogger(__name__)


class OllamaAdapter(ModelAdapter):
    """
    Adapter for local models via Ollama.
    Zero API cost, privacy-first, works offline.

    LF-001: This should be the DEFAULT choice when available.
    """

    def __init__(self, config: ModelConfig):
        super().__init__(config)
        # Ollama runs locally, no API key needed
        self.base_url = config.base_url or "http://localhost:11434"

    async def generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        Call Ollama API (local) to generate a response.

        Ollama uses a chat completion endpoint similar to OpenAI.
        """
        url = f"{self.base_url}/api/chat"

        payload = {
            "model": self.config.model_id,
            "messages": messages,
            "stream": False,  # We want the full response at once
            "options": {
                "temperature": temperature or self.config.temperature,
                "num_predict": max_tokens or self.config.max_tokens,
            }
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Ollama API error ({response.status}): {error_text}")
                        raise RuntimeError(f"Ollama API returned {response.status}")

                    data = await response.json()
                    content = data["message"]["content"]

                    logger.info(f"Ollama API call successful (local model: {self.config.model_id})")
                    return content

        except aiohttp.ClientConnectorError:
            logger.error(f"Cannot connect to Ollama at {self.base_url}")
            raise RuntimeError(f"Ollama not running at {self.base_url}. Start with: ollama serve")

        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            raise

    async def is_available(self) -> bool:
        """
        Check if Ollama is running and the model is available.

        LF-002: Auto-detect Ollama on startup
        """
        try:
            # Check if Ollama server is running
            url = f"{self.base_url}/api/tags"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status != 200:
                        return False

                    data = await response.json()
                    models = data.get("models", [])

                    # Check if our specific model is available
                    model_names = [m["name"] for m in models]
                    is_available = self.config.model_id in model_names

                    if not is_available:
                        logger.warning(
                            f"Ollama is running but model '{self.config.model_id}' not found. "
                            f"Available models: {model_names}. "
                            f"Download with: ollama pull {self.config.model_id}"
                        )

                    return is_available

        except aiohttp.ClientConnectorError:
            logger.info(f"Ollama not detected at {self.base_url}")
            return False

        except Exception as e:
            logger.warning(f"Ollama availability check failed: {e}")
            return False

    async def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Local models are FREE! 🎉
        LF-014: Show users they're saving money
        """
        return 0.0  # Zero cost for local inference
