"""
GLM Client - Z.AI API Integration for Ralph Mode

Two-tier model strategy:
- GLM-4.7 (paid): Build layer - actual code generation
- GLM-4.5-Flash (free): Personality layer - Ralph/worker interactions

Cost savings: 32x cheaper than Opus, personality layer is FREE
"""

import os
import requests
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# API Configuration
GLM_API_KEY = os.getenv("GLM_API_KEY", "")
GLM_API_BASE = "https://api.z.ai/api/paas/v4/chat/completions"

# Model assignments
BUILDER_MODEL = "glm-4.7"        # Paid - for actual coding
PERSONALITY_MODEL = "glm-4.5-flash"  # FREE - for Ralph/workers


class GLMClient:
    """Client for Z.AI GLM API with model routing."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or GLM_API_KEY
        self.base_url = GLM_API_BASE

        if not self.api_key:
            raise ValueError("GLM_API_KEY not set in environment")

    def _make_request(self, model: str, messages: list, max_tokens: int = 4000,
                      temperature: float = 0.7) -> dict:
        """Make API request to GLM."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        response = requests.post(
            self.base_url,
            headers=headers,
            json=payload,
            timeout=300  # 5 min for thinking model
        )

        return response.json()

    def build(self, prompt: str, system_prompt: Optional[str] = None,
              max_tokens: int = 4000) -> str:
        """
        Use GLM-4.7 for code generation and building.
        This is the PAID model for actual work.
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        response = self._make_request(
            model=BUILDER_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.3  # Lower temp for code
        )

        if "choices" in response and response["choices"]:
            return response["choices"][0]["message"].get("content", "")

        error = response.get("error", {}).get("message", "Unknown error")
        raise Exception(f"GLM build error: {error}")

    def personality(self, prompt: str, character: str = "ralph",
                    context: Optional[str] = None) -> str:
        """
        Use GLM-4.5-Flash (FREE) for personality/theater.
        Handles Ralph, workers, and all entertainment.
        """
        # Character system prompts
        characters = {
            "ralph": """You are Ralph Wiggum, the lovably confused boss of a dev team.
You say things like "unpossible", misspell words, pick your nose, and are genuinely innocent.
You're not pretending to be dumb - you actually are confused, but sweet.""",

            "stool": """You are Stool, a senior developer. Competent, slightly cynical,
gets things done. You sigh a lot but deliver quality work.""",

            "gomer": """You are Gomer, an eager junior developer. Enthusiastic, asks good questions,
learning every day. You're excited about everything.""",

            "mona": """You are Mona, the QA lead. Detail-oriented, catches every edge case,
nothing escapes your testing. Professional but friendly.""",

            "gus": """You are Gus, the DevOps engineer. "The server room is my happy place."
Infrastructure wizard, calm under pressure, speaks in metaphors about pipes and servers.""",

            "withers": """You are Withers, the backroom supervisor. Smithers-type personality.
Competent, organized, loyal to Mr. Worms. Short words, clear actions, efficient."""
        }

        system_prompt = characters.get(character.lower(), characters["ralph"])

        if context:
            system_prompt += f"\n\nContext: {context}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        response = self._make_request(
            model=PERSONALITY_MODEL,
            messages=messages,
            max_tokens=500,  # Personality responses should be shorter
            temperature=0.8  # Higher temp for creativity
        )

        if "choices" in response and response["choices"]:
            return response["choices"][0]["message"].get("content", "")

        # Fallback for free tier issues
        return "*Ralph scratches his head* Um... my brain did a thing..."

    def get_usage_stats(self, response: dict) -> dict:
        """Extract token usage from response."""
        usage = response.get("usage", {})
        return {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "reasoning_tokens": usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "cached_tokens": usage.get("prompt_tokens_details", {}).get("cached_tokens", 0)
        }


# Convenience functions
_client = None

def get_client() -> GLMClient:
    """Get or create singleton client."""
    global _client
    if _client is None:
        _client = GLMClient()
    return _client

def build(prompt: str, system_prompt: Optional[str] = None) -> str:
    """Quick build call using GLM-4.7."""
    return get_client().build(prompt, system_prompt)

def ralph_says(prompt: str, context: Optional[str] = None) -> str:
    """Get a Ralph response (FREE)."""
    return get_client().personality(prompt, "ralph", context)

def worker_says(worker: str, prompt: str, context: Optional[str] = None) -> str:
    """Get a worker response (FREE)."""
    return get_client().personality(prompt, worker, context)


if __name__ == "__main__":
    # Test both tiers
    print("Testing GLM Client...")
    print("=" * 60)

    client = GLMClient()

    # Test FREE personality layer
    print("\n1. Testing FREE personality layer (GLM-4.5-Flash):")
    ralph_response = client.personality(
        "What do you think about this new feature request?",
        character="ralph"
    )
    print(f"Ralph: {ralph_response}")

    # Test PAID build layer
    print("\n2. Testing PAID build layer (GLM-4.7):")
    code = client.build(
        "Write a Python function to check if a string is a valid email. Code only.",
        system_prompt="You are an expert Python developer. Write clean, concise code."
    )
    print(f"Code:\n{code}")

    print("\n" + "=" * 60)
    print("GLM Client working!")
