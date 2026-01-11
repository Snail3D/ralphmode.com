#!/usr/bin/env python3
"""
MM-001: Model Abstraction Layer
Unified interface for all model types (Cloud APIs, Local AI)

This abstraction allows Ralph to:
- Switch between different AI providers without changing code
- Support multiple models in parallel (Ralph uses one, workers use another)
- Gracefully fallback when a model is unavailable
- Track costs and usage across all providers

MM-002: Model Registry
Persistent storage for model configurations with metadata
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
from pathlib import Path

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


class ModelRegistry:
    """
    MM-002: Model Registry

    Persistent storage for model configurations with metadata.
    Stores models to disk so they can be loaded across sessions.

    Metadata includes:
    - Registration timestamp
    - Last used timestamp
    - Total usage count
    - Custom tags/notes
    - Performance metrics
    - MM-008: Validation cache (test results)
    """

    def __init__(self, registry_path: Optional[str] = None):
        """
        Initialize the model registry.

        Args:
            registry_path: Path to the registry JSON file.
                          Defaults to ~/.ralph/model_registry.json
        """
        if registry_path is None:
            registry_path = os.path.join(
                os.path.expanduser("~"),
                ".ralph",
                "model_registry.json"
            )

        self.registry_path = Path(registry_path)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

        # In-memory cache of registered models
        self._registry: Dict[str, Dict[str, Any]] = {}

        # MM-008: Validation cache path
        self.validation_cache_path = self.registry_path.parent / "validation_cache.json"
        self._validation_cache: Dict[str, Dict[str, Any]] = {}

        # Load existing registry and validation cache
        self._load_registry()
        self._load_validation_cache()
        logger.info(f"MM-002: Model Registry initialized at {self.registry_path}")
        logger.info(f"MM-008: Validation cache initialized at {self.validation_cache_path}")

    def _load_registry(self):
        """Load the registry from disk"""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, 'r') as f:
                    self._registry = json.load(f)
                logger.info(f"MM-002: Loaded {len(self._registry)} models from registry")
            except Exception as e:
                logger.error(f"MM-002: Failed to load registry: {e}")
                self._registry = {}
        else:
            logger.info("MM-002: No existing registry found, starting fresh")
            self._registry = {}

    def _save_registry(self):
        """Save the registry to disk"""
        try:
            with open(self.registry_path, 'w') as f:
                json.dump(self._registry, f, indent=2)
            logger.debug(f"MM-002: Saved registry with {len(self._registry)} models")
        except Exception as e:
            logger.error(f"MM-002: Failed to save registry: {e}")

    def _load_validation_cache(self):
        """MM-008: Load validation cache from disk"""
        if self.validation_cache_path.exists():
            try:
                with open(self.validation_cache_path, 'r') as f:
                    self._validation_cache = json.load(f)
                logger.info(f"MM-008: Loaded validation cache with {len(self._validation_cache)} models")
            except Exception as e:
                logger.error(f"MM-008: Failed to load validation cache: {e}")
                self._validation_cache = {}
        else:
            logger.info("MM-008: No existing validation cache found, starting fresh")
            self._validation_cache = {}

    def _save_validation_cache(self):
        """MM-008: Save validation cache to disk"""
        try:
            with open(self.validation_cache_path, 'w') as f:
                json.dump(self._validation_cache, f, indent=2)
            logger.debug(f"MM-008: Saved validation cache with {len(self._validation_cache)} models")
        except Exception as e:
            logger.error(f"MM-008: Failed to save validation cache: {e}")

    def register(
        self,
        name: str,
        config: ModelConfig,
        role: Optional[ModelRole] = None,
        tags: Optional[List[str]] = None,
        notes: Optional[str] = None
    ):
        """
        Register a model configuration with metadata.

        Args:
            name: Unique name for this model configuration
            config: ModelConfig object
            role: Optional role this model is intended for
            tags: Optional list of tags (e.g., ["fast", "cheap", "local"])
            notes: Optional notes about this model
        """
        # Convert config to dict
        config_dict = {
            "provider": config.provider.value,
            "model_id": config.model_id,
            "api_key": config.api_key,
            "base_url": config.base_url,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "timeout": config.timeout,
            "metadata": config.metadata
        }

        # Build metadata
        now = datetime.utcnow().isoformat()

        # Preserve existing metadata if updating
        existing = self._registry.get(name, {})

        model_entry = {
            "config": config_dict,
            "role": role.value if role else existing.get("role"),
            "tags": tags or existing.get("tags", []),
            "notes": notes or existing.get("notes", ""),
            "registered_at": existing.get("registered_at", now),
            "updated_at": now,
            "last_used": existing.get("last_used"),
            "usage_count": existing.get("usage_count", 0)
        }

        self._registry[name] = model_entry
        self._save_registry()

        logger.info(f"MM-002: Registered model '{name}' ({config.provider.value}/{config.model_id})")

    def get(self, name: str) -> Optional[ModelConfig]:
        """
        Get a model configuration by name.

        Args:
            name: Name of the registered model

        Returns:
            ModelConfig object or None if not found
        """
        entry = self._registry.get(name)
        if not entry:
            return None

        config_dict = entry["config"]

        # Reconstruct ModelConfig
        config = ModelConfig(
            provider=ModelProvider(config_dict["provider"]),
            model_id=config_dict["model_id"],
            api_key=config_dict.get("api_key"),
            base_url=config_dict.get("base_url"),
            max_tokens=config_dict.get("max_tokens", 4096),
            temperature=config_dict.get("temperature", 0.7),
            timeout=config_dict.get("timeout", 60),
            metadata=config_dict.get("metadata", {})
        )

        return config

    def update_usage(self, name: str):
        """
        Update usage statistics for a model.

        Args:
            name: Name of the model
        """
        if name in self._registry:
            self._registry[name]["last_used"] = datetime.utcnow().isoformat()
            self._registry[name]["usage_count"] = self._registry[name].get("usage_count", 0) + 1
            self._save_registry()

    def list_models(
        self,
        role: Optional[ModelRole] = None,
        tags: Optional[List[str]] = None,
        provider: Optional[ModelProvider] = None
    ) -> List[Dict[str, Any]]:
        """
        List registered models with optional filters.

        Args:
            role: Filter by role
            tags: Filter by tags (must have ALL specified tags)
            provider: Filter by provider

        Returns:
            List of model entries with metadata
        """
        results = []

        for name, entry in self._registry.items():
            # Apply filters
            if role and entry.get("role") != role.value:
                continue

            if tags and not all(tag in entry.get("tags", []) for tag in tags):
                continue

            if provider and entry["config"]["provider"] != provider.value:
                continue

            # Add name to entry for convenience
            result = {"name": name, **entry}
            results.append(result)

        return results

    def delete(self, name: str) -> bool:
        """
        Delete a model from the registry.

        Args:
            name: Name of the model to delete

        Returns:
            True if deleted, False if not found
        """
        if name in self._registry:
            del self._registry[name]
            self._save_registry()
            logger.info(f"MM-002: Deleted model '{name}' from registry")
            return True
        return False

    def get_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a model without the full config.

        Args:
            name: Name of the model

        Returns:
            Metadata dict or None if not found
        """
        entry = self._registry.get(name)
        if not entry:
            return None

        return {
            "name": name,
            "provider": entry["config"]["provider"],
            "model_id": entry["config"]["model_id"],
            "role": entry.get("role"),
            "tags": entry.get("tags", []),
            "notes": entry.get("notes", ""),
            "registered_at": entry.get("registered_at"),
            "updated_at": entry.get("updated_at"),
            "last_used": entry.get("last_used"),
            "usage_count": entry.get("usage_count", 0)
        }

    def record_test_result(
        self,
        name: str,
        test_name: str,
        passed: bool,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        MM-008: Record a test result for a model.

        Args:
            name: Name of the model
            test_name: Name of the test (e.g., "basic_generation", "code_quality", "speed")
            passed: Whether the test passed
            details: Optional details about the test (error message, metrics, etc.)

        Example:
            registry.record_test_result(
                "ralph_groq_llama-3.1-70b",
                "basic_generation",
                passed=True,
                details={"latency_ms": 234, "tokens": 150}
            )
        """
        if name not in self._validation_cache:
            self._validation_cache[name] = {
                "tests": {},
                "last_validated": None,
                "total_tests": 0,
                "passed_tests": 0
            }

        # Record the test
        test_result = {
            "passed": passed,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details or {}
        }

        self._validation_cache[name]["tests"][test_name] = test_result
        self._validation_cache[name]["last_validated"] = datetime.utcnow().isoformat()

        # Update counters
        self._validation_cache[name]["total_tests"] = len(self._validation_cache[name]["tests"])
        self._validation_cache[name]["passed_tests"] = sum(
            1 for t in self._validation_cache[name]["tests"].values() if t["passed"]
        )

        self._save_validation_cache()
        logger.info(f"MM-008: Recorded test '{test_name}' for '{name}': {'PASS' if passed else 'FAIL'}")

    def get_test_results(self, name: str) -> Optional[Dict[str, Any]]:
        """
        MM-008: Get all test results for a model.

        Args:
            name: Name of the model

        Returns:
            Dict with test results or None if no tests recorded

        Example:
            results = registry.get_test_results("ralph_groq_llama-3.1-70b")
            if results and results["passed_tests"] == results["total_tests"]:
                print("All tests passed!")
        """
        return self._validation_cache.get(name)

    def get_test_result(self, name: str, test_name: str) -> Optional[Dict[str, Any]]:
        """
        MM-008: Get a specific test result for a model.

        Args:
            name: Name of the model
            test_name: Name of the test

        Returns:
            Test result dict or None if not found

        Example:
            result = registry.get_test_result("ralph_groq_llama-3.1-70b", "basic_generation")
            if result and result["passed"]:
                print(f"Test passed at {result['timestamp']}")
        """
        cache_entry = self._validation_cache.get(name)
        if not cache_entry:
            return None
        return cache_entry["tests"].get(test_name)

    def model_passed_test(self, name: str, test_name: str) -> bool:
        """
        MM-008: Quick check if a model passed a specific test.

        Args:
            name: Name of the model
            test_name: Name of the test

        Returns:
            True if the test was recorded and passed, False otherwise

        Example:
            if registry.model_passed_test("ralph_groq_llama-3.1-70b", "basic_generation"):
                print("Model is validated for basic generation!")
        """
        result = self.get_test_result(name, test_name)
        return result["passed"] if result else False

    def list_validated_models(
        self,
        test_name: Optional[str] = None,
        all_tests_passed: bool = False
    ) -> List[str]:
        """
        MM-008: List models that passed validation.

        Args:
            test_name: Filter by specific test name
            all_tests_passed: If True, only return models that passed ALL tests

        Returns:
            List of model names

        Example:
            # Get all models that passed basic_generation
            models = registry.list_validated_models(test_name="basic_generation")

            # Get all models that passed ALL tests
            models = registry.list_validated_models(all_tests_passed=True)
        """
        validated = []

        for name, cache_entry in self._validation_cache.items():
            if test_name:
                # Check specific test
                test_result = cache_entry["tests"].get(test_name)
                if test_result and test_result["passed"]:
                    validated.append(name)
            elif all_tests_passed:
                # Check if all tests passed
                if (cache_entry["total_tests"] > 0 and
                    cache_entry["passed_tests"] == cache_entry["total_tests"]):
                    validated.append(name)
            else:
                # Return all models with any passed tests
                if cache_entry["passed_tests"] > 0:
                    validated.append(name)

        return validated

    def clear_test_results(self, name: str, test_name: Optional[str] = None):
        """
        MM-008: Clear test results for a model.

        Args:
            name: Name of the model
            test_name: Optional specific test to clear. If None, clears all tests.

        Example:
            # Clear specific test
            registry.clear_test_results("my_model", "basic_generation")

            # Clear all tests
            registry.clear_test_results("my_model")
        """
        if name not in self._validation_cache:
            return

        if test_name:
            # Clear specific test
            if test_name in self._validation_cache[name]["tests"]:
                del self._validation_cache[name]["tests"][test_name]
                logger.info(f"MM-008: Cleared test '{test_name}' for '{name}'")
        else:
            # Clear all tests
            self._validation_cache[name]["tests"] = {}
            logger.info(f"MM-008: Cleared all tests for '{name}'")

        # Update counters
        self._validation_cache[name]["total_tests"] = len(self._validation_cache[name]["tests"])
        self._validation_cache[name]["passed_tests"] = sum(
            1 for t in self._validation_cache[name]["tests"].values() if t["passed"]
        )

        self._save_validation_cache()


class ModelManager:
    """
    MM-001: Central model management system
    MM-002: Integrated with ModelRegistry for persistent storage

    Responsibilities:
    - Store configured models by role
    - Route requests to appropriate model
    - Handle fallbacks when models are unavailable
    - Track usage and costs
    - Persist model configurations
    """

    def __init__(self, registry_path: Optional[str] = None):
        self._models: Dict[ModelRole, ModelAdapter] = {}
        self._usage_stats: Dict[str, Dict[str, int]] = {}
        self._cost_tracking: List[Dict[str, Any]] = []

        # MM-002: Initialize model registry for persistence
        self.registry = ModelRegistry(registry_path)

        logger.info("MM-001: Model Manager initialized")
        logger.info(f"MM-002: Connected to registry with {len(self.registry._registry)} stored models")

    def register_model(
        self,
        role: ModelRole,
        adapter: ModelAdapter,
        save_to_registry: bool = True,
        registry_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        notes: Optional[str] = None
    ):
        """
        Register a model for a specific role.

        Args:
            role: The role to assign this model to
            adapter: The model adapter instance
            save_to_registry: Whether to persist to registry (default: True)
            registry_name: Name to save in registry (default: "{role}_{provider}_{model_id}")
            tags: Optional tags for registry
            notes: Optional notes for registry

        Example:
            manager.register_model(ModelRole.RALPH, groq_adapter)
            manager.register_model(ModelRole.BUILDER, anthropic_adapter, tags=["primary"])
        """
        self._models[role] = adapter
        logger.info(f"MM-001: Registered {adapter.provider.value} for {role.value}")

        # MM-002: Optionally save to persistent registry
        if save_to_registry:
            if registry_name is None:
                # Generate a default name
                registry_name = f"{role.value}_{adapter.provider.value}_{adapter.config.model_id}"

            self.registry.register(
                name=registry_name,
                config=adapter.config,
                role=role,
                tags=tags,
                notes=notes
            )

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

    def load_from_registry(self, registry_name: str) -> Optional[ModelAdapter]:
        """
        MM-002: Load a model configuration from the registry and create an adapter.

        Args:
            registry_name: Name of the model in the registry

        Returns:
            ModelAdapter instance or None if not found/failed

        Example:
            adapter = manager.load_from_registry("ralph_groq_llama-3.1-70b")
            if adapter:
                manager.register_model(ModelRole.RALPH, adapter, save_to_registry=False)
        """
        config = self.registry.get(registry_name)
        if not config:
            logger.warning(f"MM-002: Model '{registry_name}' not found in registry")
            return None

        try:
            # Import the appropriate adapter based on provider
            if config.provider == ModelProvider.GROQ:
                from adapters.groq_adapter import GroqAdapter
                adapter = GroqAdapter(config)
            elif config.provider == ModelProvider.ANTHROPIC:
                from adapters.anthropic_adapter import AnthropicAdapter
                adapter = AnthropicAdapter(config)
            elif config.provider == ModelProvider.GLM:
                from adapters.glm_adapter import GLMAdapter
                adapter = GLMAdapter(config)
            elif config.provider == ModelProvider.OLLAMA:
                from adapters.ollama_adapter import OllamaAdapter
                adapter = OllamaAdapter(config)
            else:
                logger.error(f"MM-002: Unsupported provider {config.provider}")
                return None

            # Update usage stats in registry
            self.registry.update_usage(registry_name)

            logger.info(f"MM-002: Loaded model '{registry_name}' from registry")
            return adapter

        except Exception as e:
            logger.error(f"MM-002: Failed to load model '{registry_name}': {e}")
            return None

    def list_registry_models(
        self,
        role: Optional[ModelRole] = None,
        tags: Optional[List[str]] = None,
        provider: Optional[ModelProvider] = None
    ) -> List[Dict[str, Any]]:
        """
        MM-002: List models in the registry with optional filters.

        Args:
            role: Filter by role
            tags: Filter by tags
            provider: Filter by provider

        Returns:
            List of model metadata dicts
        """
        return self.registry.list_models(role=role, tags=tags, provider=provider)

    def record_test(
        self,
        model_name: str,
        test_name: str,
        passed: bool,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        MM-008: Record a validation test result for a model.

        Convenience wrapper around registry.record_test_result.

        Args:
            model_name: Name of the model in registry
            test_name: Name of the test
            passed: Whether the test passed
            details: Optional test details

        Example:
            manager.record_test("ralph_groq_llama-3.1-70b", "basic_generation", True)
        """
        self.registry.record_test_result(model_name, test_name, passed, details)

    def get_validated_models(
        self,
        test_name: Optional[str] = None,
        all_tests_passed: bool = False
    ) -> List[str]:
        """
        MM-008: Get list of models that passed validation.

        Args:
            test_name: Filter by specific test
            all_tests_passed: Only return models that passed ALL tests

        Returns:
            List of validated model names

        Example:
            # Get models that passed generation test
            validated = manager.get_validated_models(test_name="basic_generation")

            # Get fully validated models
            validated = manager.get_validated_models(all_tests_passed=True)
        """
        return self.registry.list_validated_models(test_name, all_tests_passed)

    def is_model_validated(self, model_name: str, test_name: str) -> bool:
        """
        MM-008: Check if a model passed a specific test.

        Args:
            model_name: Name of the model
            test_name: Name of the test

        Returns:
            True if test passed, False otherwise

        Example:
            if manager.is_model_validated("my_model", "basic_generation"):
                print("Model is safe to use!")
        """
        return self.registry.model_passed_test(model_name, test_name)

    def recommend_models(
        self,
        use_case: Optional[str] = None,
        priority: str = "balanced",
        hardware_constraint: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        MM-023: Suggest models by use case.

        Recommends models based on:
        - Use case (personality, coding, design, general)
        - Priority (cost, speed, quality, privacy)
        - Hardware constraints (cpu_only, gpu_available, cloud_only)

        Args:
            use_case: What you're using the model for
                - "personality" - Ralph's character interactions
                - "coding" - Worker agents doing actual coding
                - "design" - UI/UX decisions (Frinky)
                - "general" - General purpose recommendations
                - None - Show all recommendations
            priority: What matters most to you
                - "cost" - Cheapest options (local > free tier > paid)
                - "speed" - Fastest responses
                - "quality" - Best output quality
                - "privacy" - Data stays local
                - "balanced" - Good mix of all factors
            hardware_constraint: Your hardware situation
                - "cpu_only" - No GPU, recommend lighter models
                - "gpu_available" - Can run larger local models
                - "cloud_only" - Only want cloud APIs
                - None - Show all options

        Returns:
            List of recommendations with metadata and reasoning

        Example:
            # Get cheap models for personality work
            recs = manager.recommend_models(use_case="personality", priority="cost")

            # Get best quality coding models
            recs = manager.recommend_models(use_case="coding", priority="quality")

            # Get local models for privacy
            recs = manager.recommend_models(priority="privacy")
        """
        recommendations = []

        # Define model recommendations database
        # Each recommendation includes: provider, model, use cases, pros/cons
        model_database = [
            {
                "provider": ModelProvider.OLLAMA,
                "model_id": "llama3.1:8b",
                "name": "Llama 3.1 8B (Ollama)",
                "use_cases": ["personality", "general"],
                "pros": ["100% free", "runs locally", "private", "fast on CPU"],
                "cons": ["needs 8GB RAM", "not great for complex coding"],
                "cost_score": 10,  # 10 = free, 0 = most expensive
                "speed_score": 8,
                "quality_score": 6,
                "privacy_score": 10,
                "requires": "cpu_only",
                "role": ModelRole.RALPH
            },
            {
                "provider": ModelProvider.OLLAMA,
                "model_id": "llama3.1:70b",
                "name": "Llama 3.1 70B (Ollama)",
                "use_cases": ["coding", "general"],
                "pros": ["100% free", "high quality", "private", "excellent for coding"],
                "cons": ["needs GPU + 48GB RAM", "slow on CPU"],
                "cost_score": 10,
                "speed_score": 5,
                "quality_score": 9,
                "privacy_score": 10,
                "requires": "gpu_available",
                "role": ModelRole.WORKER
            },
            {
                "provider": ModelProvider.GROQ,
                "model_id": "llama-3.1-70b-versatile",
                "name": "Llama 3.1 70B (Groq)",
                "use_cases": ["personality", "coding", "general"],
                "pros": ["super fast (500+ tokens/sec)", "free tier", "great quality", "good for Ralph personality"],
                "cons": ["cloud-based", "free tier has limits", "data leaves your machine"],
                "cost_score": 8,  # Free tier, then paid
                "speed_score": 10,
                "quality_score": 9,
                "privacy_score": 3,
                "requires": "cloud_only",
                "role": ModelRole.RALPH
            },
            {
                "provider": ModelProvider.GROQ,
                "model_id": "llama-3.3-70b-versatile",
                "name": "Llama 3.3 70B (Groq)",
                "use_cases": ["coding", "general"],
                "pros": ["newest Llama", "excellent coding", "very fast", "free tier"],
                "cons": ["cloud-based", "data leaves your machine"],
                "cost_score": 8,
                "speed_score": 10,
                "quality_score": 9,
                "privacy_score": 3,
                "requires": "cloud_only",
                "role": ModelRole.WORKER
            },
            {
                "provider": ModelProvider.ANTHROPIC,
                "model_id": "claude-sonnet-4",
                "name": "Claude Sonnet 4",
                "use_cases": ["coding", "general"],
                "pros": ["best coding quality", "excellent reasoning", "reliable", "follows instructions well"],
                "cons": ["expensive ($3/$15 per 1M tokens)", "slower than Groq", "cloud-based"],
                "cost_score": 3,
                "speed_score": 6,
                "quality_score": 10,
                "privacy_score": 3,
                "requires": "cloud_only",
                "role": ModelRole.BUILDER
            },
            {
                "provider": ModelProvider.GLM,
                "model_id": "GLM-4.7",
                "name": "GLM-4.7 (Z.AI)",
                "use_cases": ["design", "general"],
                "pros": ["great for design decisions", "affordable", "good aesthetic sense"],
                "cons": ["cloud-based", "not ideal for complex coding"],
                "cost_score": 7,
                "speed_score": 7,
                "quality_score": 7,
                "privacy_score": 3,
                "requires": "cloud_only",
                "role": ModelRole.DESIGN
            },
            {
                "provider": ModelProvider.OLLAMA,
                "model_id": "codellama:13b",
                "name": "CodeLlama 13B (Ollama)",
                "use_cases": ["coding"],
                "pros": ["free", "local", "specialized for code", "runs on CPU"],
                "cons": ["not as good as Claude", "verbose responses"],
                "cost_score": 10,
                "speed_score": 7,
                "quality_score": 7,
                "privacy_score": 10,
                "requires": "cpu_only",
                "role": ModelRole.WORKER
            },
            {
                "provider": ModelProvider.OLLAMA,
                "model_id": "mistral:7b",
                "name": "Mistral 7B (Ollama)",
                "use_cases": ["personality", "general"],
                "pros": ["free", "fast", "good for chat", "runs on CPU"],
                "cons": ["less capable than Llama 3.1", "shorter context"],
                "cost_score": 10,
                "speed_score": 9,
                "quality_score": 6,
                "privacy_score": 10,
                "requires": "cpu_only",
                "role": ModelRole.RALPH
            }
        ]

        # Filter by use case
        if use_case:
            filtered = [m for m in model_database if use_case in m["use_cases"]]
        else:
            filtered = model_database

        # Filter by hardware constraint
        if hardware_constraint:
            filtered = [m for m in filtered if m["requires"] == hardware_constraint]

        # Sort by priority
        if priority == "cost":
            filtered.sort(key=lambda x: x["cost_score"], reverse=True)
        elif priority == "speed":
            filtered.sort(key=lambda x: x["speed_score"], reverse=True)
        elif priority == "quality":
            filtered.sort(key=lambda x: x["quality_score"], reverse=True)
        elif priority == "privacy":
            filtered.sort(key=lambda x: x["privacy_score"], reverse=True)
        else:  # balanced
            # Balanced score = average of all scores
            filtered.sort(
                key=lambda x: (x["cost_score"] + x["speed_score"] + x["quality_score"] + x["privacy_score"]) / 4,
                reverse=True
            )

        # Format recommendations
        for model in filtered:
            recommendation = {
                "provider": model["provider"].value,
                "model_id": model["model_id"],
                "name": model["name"],
                "role": model["role"].value,
                "use_cases": model["use_cases"],
                "pros": model["pros"],
                "cons": model["cons"],
                "scores": {
                    "cost": model["cost_score"],
                    "speed": model["speed_score"],
                    "quality": model["quality_score"],
                    "privacy": model["privacy_score"]
                },
                "hardware_requirement": model["requires"],
                "reasoning": self._generate_reasoning(model, use_case, priority)
            }
            recommendations.append(recommendation)

        return recommendations

    def _generate_reasoning(
        self,
        model: Dict[str, Any],
        use_case: Optional[str],
        priority: str
    ) -> str:
        """Generate human-readable reasoning for why a model is recommended"""
        reasons = []

        # Why it fits the use case
        if use_case:
            use_case_reasons = {
                "personality": "Great for Ralph's character interactions and banter",
                "coding": "Excellent at understanding and generating code",
                "design": "Strong at making aesthetic and UI/UX decisions",
                "general": "Versatile for various tasks"
            }
            if use_case in use_case_reasons:
                reasons.append(use_case_reasons[use_case])

        # Why it fits the priority
        if priority == "cost":
            if model["cost_score"] >= 8:
                reasons.append("Free or very affordable")
        elif priority == "speed":
            if model["speed_score"] >= 8:
                reasons.append("Extremely fast responses")
        elif priority == "quality":
            if model["quality_score"] >= 8:
                reasons.append("Top-tier output quality")
        elif priority == "privacy":
            if model["privacy_score"] >= 8:
                reasons.append("Runs locally, your data stays private")
        else:  # balanced
            avg_score = (model["cost_score"] + model["speed_score"] +
                        model["quality_score"] + model["privacy_score"]) / 4
            if avg_score >= 8:
                reasons.append("Well-rounded with no major weaknesses")

        # Add top pro
        if model["pros"]:
            reasons.append(model["pros"][0])

        return ". ".join(reasons) + "."

    async def discover_local_models(self) -> List[Dict[str, Any]]:
        """
        MM-019: Auto-detect running local models.

        Scans common ports and endpoints to find local AI servers:
        - Ollama (port 11434)
        - LM Studio (port 1234)
        - llama.cpp (port 8080)

        Returns:
            List of discovered model servers with metadata

        Example:
            discovered = await manager.discover_local_models()
            for server in discovered:
                print(f"Found {server['provider']} at {server['base_url']}")
                print(f"Available models: {server['models']}")
        """
        import aiohttp
        import asyncio

        discovered = []

        # Check Ollama
        ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as session:
                async with session.get(f"{ollama_url}/api/tags") as response:
                    if response.status == 200:
                        data = await response.json()
                        models = [model["name"] for model in data.get("models", [])]
                        discovered.append({
                            "provider": ModelProvider.OLLAMA.value,
                            "base_url": ollama_url,
                            "models": models,
                            "status": "running",
                            "version": data.get("version", "unknown")
                        })
                        logger.info(f"MM-019: Discovered Ollama at {ollama_url} with {len(models)} models")
        except Exception as e:
            logger.debug(f"MM-019: Ollama not found at {ollama_url}: {e}")

        # Check LM Studio
        lmstudio_url = os.environ.get("LM_STUDIO_BASE_URL", "http://localhost:1234")
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as session:
                async with session.get(f"{lmstudio_url}/v1/models") as response:
                    if response.status == 200:
                        data = await response.json()
                        models = [model["id"] for model in data.get("data", [])]
                        discovered.append({
                            "provider": ModelProvider.LM_STUDIO.value,
                            "base_url": lmstudio_url,
                            "models": models,
                            "status": "running",
                            "version": "unknown"
                        })
                        logger.info(f"MM-019: Discovered LM Studio at {lmstudio_url} with {len(models)} models")
        except Exception as e:
            logger.debug(f"MM-019: LM Studio not found at {lmstudio_url}: {e}")

        # Check llama.cpp server
        llamacpp_url = os.environ.get("LLAMACPP_BASE_URL", "http://localhost:8080")
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as session:
                async with session.get(f"{llamacpp_url}/v1/models") as response:
                    if response.status == 200:
                        data = await response.json()
                        models = [model["id"] for model in data.get("data", [])]
                        discovered.append({
                            "provider": ModelProvider.LLAMACPP.value,
                            "base_url": llamacpp_url,
                            "models": models,
                            "status": "running",
                            "version": "unknown"
                        })
                        logger.info(f"MM-019: Discovered llama.cpp at {llamacpp_url} with {len(models)} models")
        except Exception as e:
            logger.debug(f"MM-019: llama.cpp not found at {llamacpp_url}: {e}")

        if not discovered:
            logger.info("MM-019: No local model servers discovered")
        else:
            logger.info(f"MM-019: Total discovered: {len(discovered)} local model servers")

        return discovered

    async def auto_register_local_models(
        self,
        role: Optional[ModelRole] = None,
        prefer_provider: Optional[ModelProvider] = None
    ) -> List[str]:
        """
        MM-019: Discover and auto-register local models.

        Convenience method that discovers local models and registers them
        in the ModelRegistry for easy use.

        Args:
            role: Optional role to assign to discovered models
            prefer_provider: If multiple providers found, prefer this one

        Returns:
            List of registered model names

        Example:
            # Auto-register any local models found
            registered = await manager.auto_register_local_models()

            # Register for a specific role
            registered = await manager.auto_register_local_models(role=ModelRole.RALPH)

            # Prefer Ollama if multiple providers running
            registered = await manager.auto_register_local_models(
                prefer_provider=ModelProvider.OLLAMA
            )
        """
        discovered = await self.discover_local_models()
        registered_names = []

        if not discovered:
            logger.info("MM-019: No local models found to auto-register")
            return registered_names

        # Sort by preference if specified
        if prefer_provider:
            discovered.sort(
                key=lambda x: 0 if x["provider"] == prefer_provider.value else 1
            )

        for server in discovered:
            provider = ModelProvider(server["provider"])

            # Register each model found
            for model_id in server["models"]:
                config = ModelConfig(
                    provider=provider,
                    model_id=model_id,
                    base_url=server["base_url"]
                )

                # Generate a registry name
                registry_name = f"local_{provider.value}_{model_id}".replace(":", "_").replace("/", "_")

                # Register in the registry
                self.registry.register(
                    name=registry_name,
                    config=config,
                    role=role,
                    tags=["local", "auto-discovered", provider.value],
                    notes=f"Auto-discovered from {server['base_url']}"
                )

                registered_names.append(registry_name)
                logger.info(f"MM-019: Auto-registered {registry_name}")

        logger.info(f"MM-019: Auto-registered {len(registered_names)} local models")
        return registered_names

    async def retest_model(
        self,
        model_name: str,
        test_suite: Optional[List[str]] = None,
        clear_existing: bool = True
    ) -> Dict[str, Any]:
        """
        MM-009: Re-test Trigger - Manual re-validation of models.

        Clears existing validation cache and re-runs tests for a model.
        Useful when:
        - A model was updated
        - You want to verify a model still works
        - Previous tests failed and you've fixed the issue

        Args:
            model_name: Name of the model in registry to retest
            test_suite: List of test names to run. If None, runs all standard tests.
            clear_existing: Whether to clear existing test results first (default: True)

        Returns:
            Dict with test results summary:
            {
                "model_name": str,
                "total_tests": int,
                "passed_tests": int,
                "failed_tests": int,
                "test_results": {test_name: {"passed": bool, "details": {...}}}
            }

        Example:
            # Re-test a model completely
            results = await manager.retest_model("ralph_groq_llama-3.1-70b")

            # Re-test specific tests only
            results = await manager.retest_model(
                "my_model",
                test_suite=["basic_generation", "code_quality"]
            )

            # Re-test but keep old results
            results = await manager.retest_model("my_model", clear_existing=False)
        """
        logger.info(f"MM-009: Starting re-test for model '{model_name}'")

        # Check if model exists
        config = self.registry.get(model_name)
        if not config:
            logger.error(f"MM-009: Model '{model_name}' not found in registry")
            return {
                "model_name": model_name,
                "error": "Model not found in registry",
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "test_results": {}
            }

        # Clear existing results if requested
        if clear_existing:
            if test_suite:
                # Clear only specified tests
                for test_name in test_suite:
                    self.registry.clear_test_results(model_name, test_name)
                logger.info(f"MM-009: Cleared {len(test_suite)} test(s) for '{model_name}'")
            else:
                # Clear all tests
                self.registry.clear_test_results(model_name)
                logger.info(f"MM-009: Cleared all tests for '{model_name}'")

        # Define standard test suite if not provided
        if not test_suite:
            test_suite = ["basic_generation", "response_quality", "availability"]

        # Run tests
        test_results = {}

        # Load the adapter for this model
        adapter = self.load_from_registry(model_name)
        if not adapter:
            logger.error(f"MM-009: Failed to load adapter for '{model_name}'")
            return {
                "model_name": model_name,
                "error": "Failed to load model adapter",
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "test_results": {}
            }

        # Test 1: Availability
        if "availability" in test_suite:
            try:
                is_available = await adapter.is_available()
                self.registry.record_test_result(
                    model_name,
                    "availability",
                    passed=is_available,
                    details={"timestamp": datetime.utcnow().isoformat()}
                )
                test_results["availability"] = {
                    "passed": is_available,
                    "details": {"available": is_available}
                }
                logger.info(f"MM-009: Availability test: {'PASS' if is_available else 'FAIL'}")
            except Exception as e:
                logger.error(f"MM-009: Availability test failed with exception: {e}")
                self.registry.record_test_result(
                    model_name,
                    "availability",
                    passed=False,
                    details={"error": str(e)}
                )
                test_results["availability"] = {
                    "passed": False,
                    "details": {"error": str(e)}
                }

        # Test 2: Basic Generation
        if "basic_generation" in test_suite:
            try:
                test_messages = [{"role": "user", "content": "Say 'test successful' if you can read this."}]
                response = await adapter.generate(
                    messages=test_messages,
                    max_tokens=50,
                    temperature=0.3
                )
                # Check if we got a response
                passed = bool(response and len(response) > 0)
                self.registry.record_test_result(
                    model_name,
                    "basic_generation",
                    passed=passed,
                    details={
                        "response_length": len(response) if response else 0,
                        "response_preview": response[:100] if response else ""
                    }
                )
                test_results["basic_generation"] = {
                    "passed": passed,
                    "details": {"response_length": len(response) if response else 0}
                }
                logger.info(f"MM-009: Basic generation test: {'PASS' if passed else 'FAIL'}")
            except Exception as e:
                logger.error(f"MM-009: Basic generation test failed with exception: {e}")
                self.registry.record_test_result(
                    model_name,
                    "basic_generation",
                    passed=False,
                    details={"error": str(e)}
                )
                test_results["basic_generation"] = {
                    "passed": False,
                    "details": {"error": str(e)}
                }

        # Test 3: Response Quality
        if "response_quality" in test_suite:
            try:
                test_messages = [
                    {"role": "user", "content": "What is 2+2? Answer with just the number."}
                ]
                response = await adapter.generate(
                    messages=test_messages,
                    max_tokens=10,
                    temperature=0.0
                )
                # Check if response contains "4"
                passed = "4" in response if response else False
                self.registry.record_test_result(
                    model_name,
                    "response_quality",
                    passed=passed,
                    details={
                        "expected": "4",
                        "response": response[:50] if response else ""
                    }
                )
                test_results["response_quality"] = {
                    "passed": passed,
                    "details": {"response": response[:50] if response else ""}
                }
                logger.info(f"MM-009: Response quality test: {'PASS' if passed else 'FAIL'}")
            except Exception as e:
                logger.error(f"MM-009: Response quality test failed with exception: {e}")
                self.registry.record_test_result(
                    model_name,
                    "response_quality",
                    passed=False,
                    details={"error": str(e)}
                )
                test_results["response_quality"] = {
                    "passed": False,
                    "details": {"error": str(e)}
                }

        # Compile results
        total_tests = len(test_results)
        passed_tests = sum(1 for r in test_results.values() if r["passed"])
        failed_tests = total_tests - passed_tests

        result_summary = {
            "model_name": model_name,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "test_results": test_results
        }

        logger.info(
            f"MM-009: Re-test complete for '{model_name}': "
            f"{passed_tests}/{total_tests} tests passed"
        )

        return result_summary


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
