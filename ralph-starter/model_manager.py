#!/usr/bin/env python3
"""
MM-001: Model Abstraction Layer
Unified interface for all model types (Cloud APIs, Local AI)

This abstraction allows Ralph to:
- Switch between different AI providers without changing code
- Support multiple models in parallel (Ralph uses one, workers use another)
- Gracefully fallback when a model is unavailable
- Track costs and usage across all providers
"""

import os
import logging
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ModelProvider(Enum):
    """Supported model providers"""
    GROQ = "groq"              # Fast inference via Groq
    ANTHROPIC = "anthropic"    # Claude models
    OLLAMA = "ollama"          # Local models via Ollama
    LM_STUDIO = "lm_studio"    # LM Studio local models
    LLAMACPP = "llamacpp"      # Raw llama.cpp
    CUSTOM = "custom"          # User-provided endpoint
    GLM = "glm"                # Z.AI GLM models for design


class ModelRole(Enum):
    """Different roles that need AI models"""
    RALPH = "ralph"            # Ralph's personality
    WORKER = "worker"          # Worker agents (coding)
    BUILDER = "builder"        # Build loop (Claude Code integration)
    DESIGN = "design"          # Design decisions (Frinky/GLM)


@dataclass
class ModelConfig:
    """Configuration for a specific model"""
    provider: ModelProvider
    model_id: str              # e.g., "llama-3.1-70b-versatile" or "claude-sonnet-4"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 60
    metadata: Dict[str, Any] = None  # Extra provider-specific settings

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ModelAdapter(ABC):
    """Base class for all model adapters"""

    def __init__(self, config: ModelConfig):
        self.config = config
        self.provider = config.provider

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        Generate a response from the model.

        Args:
            messages: List of {"role": "user/assistant/system", "content": "..."}
            max_tokens: Override default max tokens
            temperature: Override default temperature
            **kwargs: Provider-specific options

        Returns:
            Generated text response
        """
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if this model is currently available"""
        pass

    @abstractmethod
    async def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost in USD for a request"""
        pass


class ModelManager:
    """
    MM-001: Central model management system

    Responsibilities:
    - Store configured models by role
    - Route requests to appropriate model
    - Handle fallbacks when models are unavailable
    - Track usage and costs
    """

    def __init__(self):
        self._models: Dict[ModelRole, ModelAdapter] = {}
        self._usage_stats: Dict[str, Dict[str, int]] = {}
        self._cost_tracking: List[Dict[str, Any]] = []
        logger.info("MM-001: Model Manager initialized")

    def register_model(self, role: ModelRole, adapter: ModelAdapter):
        """
        Register a model for a specific role.

        Example:
            manager.register_model(ModelRole.RALPH, groq_adapter)
            manager.register_model(ModelRole.BUILDER, anthropic_adapter)
        """
        self._models[role] = adapter
        logger.info(f"MM-001: Registered {adapter.provider.value} for {role.value}")

    def get_model(self, role: ModelRole) -> Optional[ModelAdapter]:
        """Get the configured model for a role"""
        return self._models.get(role)

    async def generate(
        self,
        role: ModelRole,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        Generate response using the model assigned to this role.

        Falls back to default model if role-specific model unavailable.
        """
        adapter = self.get_model(role)

        if not adapter:
            logger.warning(f"MM-001: No model configured for {role.value}")
            # Fall back to RALPH model as default
            adapter = self.get_model(ModelRole.RALPH)
            if not adapter:
                raise ValueError(f"No model available for {role.value} and no fallback configured")

        # Check if model is available
        if not await adapter.is_available():
            logger.error(f"MM-001: Model {adapter.config.model_id} is not available")
            raise RuntimeError(f"Model {adapter.config.model_id} is not available")

        # Generate response
        try:
            response = await adapter.generate(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )

            # Track usage
            self._track_usage(role, adapter.config.model_id)

            return response

        except Exception as e:
            logger.error(f"MM-001: Generation failed for {adapter.config.model_id}: {e}")
            raise

    def _track_usage(self, role: ModelRole, model_id: str):
        """Track model usage for analytics"""
        key = f"{role.value}:{model_id}"
        if key not in self._usage_stats:
            self._usage_stats[key] = {"requests": 0, "errors": 0}
        self._usage_stats[key]["requests"] += 1

    def get_usage_stats(self) -> Dict[str, Dict[str, int]]:
        """Get usage statistics across all models"""
        return self._usage_stats

    def list_configured_models(self) -> Dict[str, str]:
        """List all configured models by role"""
        return {
            role.value: adapter.config.model_id
            for role, adapter in self._models.items()
        }

    def switch_model(self, role: ModelRole, new_adapter: ModelAdapter) -> bool:
        """
        MM-004: Switch to a different model for a role without restarting.

        Args:
            role: The role to update (RALPH, WORKER, BUILDER, DESIGN)
            new_adapter: The new model adapter to use

        Returns:
            bool: True if switch was successful, False otherwise

        Example:
            # Switch Ralph to use Ollama instead of Groq
            ollama_config = ModelConfig(...)
            ollama_adapter = OllamaAdapter(ollama_config)
            manager.switch_model(ModelRole.RALPH, ollama_adapter)
        """
        try:
            old_adapter = self._models.get(role)
            old_model = old_adapter.config.model_id if old_adapter else "None"

            # Register the new model
            self.register_model(role, new_adapter)

            logger.info(
                f"MM-004: Switched {role.value} from {old_model} to {new_adapter.config.model_id}"
            )
            return True

        except Exception as e:
            logger.error(f"MM-004: Failed to switch model for {role.value}: {e}")
            return False

    def get_available_providers(self) -> Dict[str, bool]:
        """
        Check which providers are available (have API keys configured).

        Returns:
            Dict mapping provider name to availability status
        """
        providers = {
            "groq": bool(os.environ.get("GROQ_API_KEY")),
            "anthropic": bool(os.environ.get("ANTHROPIC_API_KEY")),
            "glm": bool(os.environ.get("GLM_API_KEY")),
            "ollama": os.environ.get("OLLAMA_ENABLED", "false").lower() == "true",
        }
        return providers


# Global singleton instance
_model_manager: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    """Get the global ModelManager instance"""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager


def initialize_default_models():
    """
    Initialize default model configuration from environment variables.
    This is called at startup to set up the system with available models.
    """
    manager = get_model_manager()

    # Try to set up Groq (current default for Ralph)
    groq_api_key = os.environ.get("GROQ_API_KEY")
    if groq_api_key:
        from adapters.groq_adapter import GroqAdapter
        groq_config = ModelConfig(
            provider=ModelProvider.GROQ,
            model_id=os.environ.get("GROQ_MODEL", "llama-3.1-70b-versatile"),
            api_key=groq_api_key,
            max_tokens=int(os.environ.get("GROQ_MAX_TOKENS", "4096")),
            temperature=float(os.environ.get("GROQ_TEMPERATURE", "0.7"))
        )
        groq_adapter = GroqAdapter(groq_config)
        manager.register_model(ModelRole.RALPH, groq_adapter)
        manager.register_model(ModelRole.WORKER, groq_adapter)
        logger.info("MM-001: Groq configured as default for Ralph and Workers")

    # Try to set up Anthropic for builder role
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
    if anthropic_api_key:
        from adapters.anthropic_adapter import AnthropicAdapter
        anthropic_config = ModelConfig(
            provider=ModelProvider.ANTHROPIC,
            model_id=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4"),
            api_key=anthropic_api_key,
            max_tokens=int(os.environ.get("ANTHROPIC_MAX_TOKENS", "8192"))
        )
        anthropic_adapter = AnthropicAdapter(anthropic_config)
        manager.register_model(ModelRole.BUILDER, anthropic_adapter)
        logger.info("MM-001: Anthropic configured for Builder role")

    # Try to set up GLM for design role
    glm_api_key = os.environ.get("GLM_API_KEY")
    if glm_api_key:
        from adapters.glm_adapter import GLMAdapter
        glm_config = ModelConfig(
            provider=ModelProvider.GLM,
            model_id="GLM-4.7",
            api_key=glm_api_key,
            base_url="https://api.z.ai/api/anthropic"
        )
        glm_adapter = GLMAdapter(glm_config)
        manager.register_model(ModelRole.DESIGN, glm_adapter)
        logger.info("MM-001: GLM configured for Design role (Frinky)")

    # Check for Ollama (local AI)
    if os.environ.get("OLLAMA_ENABLED", "false").lower() == "true":
        from adapters.ollama_adapter import OllamaAdapter
        ollama_config = ModelConfig(
            provider=ModelProvider.OLLAMA,
            model_id=os.environ.get("OLLAMA_MODEL", "llama3.1"),
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        )
        ollama_adapter = OllamaAdapter(ollama_config)
        # Only use Ollama if it's actually running
        import asyncio
        if asyncio.run(ollama_adapter.is_available()):
            manager.register_model(ModelRole.RALPH, ollama_adapter)
            logger.info("MM-001: Ollama configured as default (local AI)")
        else:
            logger.warning("MM-001: Ollama enabled but not available at " + ollama_config.base_url)

    # Log final configuration
    configured = manager.list_configured_models()
    if not configured:
        logger.error("MM-001: No models configured! Set GROQ_API_KEY or ANTHROPIC_API_KEY")
    else:
        logger.info(f"MM-001: Configured models: {configured}")
