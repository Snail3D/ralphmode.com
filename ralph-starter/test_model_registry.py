#!/usr/bin/env python3
"""
Quick test script for MM-002: Model Registry
Tests basic registry functionality
"""

import sys
import os
import tempfile
from model_manager import ModelRegistry, ModelConfig, ModelProvider, ModelRole

def test_registry():
    """Test basic registry operations"""
    print("Testing MM-002: Model Registry\n")

    # Use a temporary directory for testing
    test_dir = tempfile.mkdtemp()
    registry_path = os.path.join(test_dir, "test_registry.json")

    # Create registry
    print(f"1. Creating registry at {registry_path}")
    registry = ModelRegistry(registry_path)
    print("   ✅ Registry created\n")

    # Register a model
    print("2. Registering a test model")
    test_config = ModelConfig(
        provider=ModelProvider.GROQ,
        model_id="llama-3.1-70b-versatile",
        api_key="test_key_123",
        max_tokens=4096,
        temperature=0.7
    )

    registry.register(
        name="test_ralph",
        config=test_config,
        role=ModelRole.RALPH,
        tags=["test", "fast"],
        notes="Test model for Ralph"
    )
    print("   ✅ Model registered\n")

    # Retrieve the model
    print("3. Retrieving model from registry")
    retrieved = registry.get("test_ralph")
    if retrieved:
        print(f"   ✅ Retrieved: {retrieved.provider.value}/{retrieved.model_id}")
        assert retrieved.model_id == "llama-3.1-70b-versatile"
        assert retrieved.provider == ModelProvider.GROQ
        print("   ✅ Model data matches\n")
    else:
        print("   ❌ Failed to retrieve model")
        return False

    # Get metadata
    print("4. Getting model metadata")
    metadata = registry.get_metadata("test_ralph")
    if metadata:
        print(f"   Name: {metadata['name']}")
        print(f"   Provider: {metadata['provider']}")
        print(f"   Model ID: {metadata['model_id']}")
        print(f"   Role: {metadata['role']}")
        print(f"   Tags: {metadata['tags']}")
        print(f"   Notes: {metadata['notes']}")
        print(f"   Usage count: {metadata['usage_count']}")
        print("   ✅ Metadata retrieved\n")
    else:
        print("   ❌ Failed to get metadata")
        return False

    # Update usage
    print("5. Updating usage stats")
    registry.update_usage("test_ralph")
    metadata = registry.get_metadata("test_ralph")
    assert metadata['usage_count'] == 1
    print(f"   ✅ Usage count updated to {metadata['usage_count']}\n")

    # List models
    print("6. Listing models")
    models = registry.list_models()
    print(f"   Found {len(models)} model(s)")
    for model in models:
        print(f"   - {model['name']}: {model['config']['provider']}/{model['config']['model_id']}")
    print("   ✅ Models listed\n")

    # List with filters
    print("7. Testing filters")
    ralph_models = registry.list_models(role=ModelRole.RALPH)
    print(f"   Ralph models: {len(ralph_models)}")

    fast_models = registry.list_models(tags=["fast"])
    print(f"   Fast models: {len(fast_models)}")
    print("   ✅ Filters work\n")

    # Test persistence (create new registry instance)
    print("8. Testing persistence")
    registry2 = ModelRegistry(registry_path)
    retrieved2 = registry2.get("test_ralph")
    if retrieved2:
        print(f"   ✅ Model persisted and loaded: {retrieved2.model_id}")
    else:
        print("   ❌ Persistence failed")
        return False

    # Delete model
    print("\n9. Testing deletion")
    deleted = registry.delete("test_ralph")
    if deleted:
        print("   ✅ Model deleted")

        # Verify it's gone
        retrieved3 = registry.get("test_ralph")
        if retrieved3 is None:
            print("   ✅ Deletion confirmed\n")
        else:
            print("   ❌ Model still exists after deletion")
            return False
    else:
        print("   ❌ Delete failed")
        return False

    # Cleanup
    import shutil
    shutil.rmtree(test_dir)

    print("=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    try:
        success = test_registry()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
