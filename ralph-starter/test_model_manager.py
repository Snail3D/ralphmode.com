#!/usr/bin/env python3
"""
Quick test script for MM-001: Model Abstraction Layer
"""

import asyncio
import os
from model_manager import (
    get_model_manager,
    ModelRole,
    ModelProvider,
    ModelConfig
)
from adapters.groq_adapter import GroqAdapter


async def test_model_manager():
    """Test the model manager with a simple Groq call"""
    print("=" * 60)
    print("MM-001: Testing Model Abstraction Layer")
    print("=" * 60)

    # Get the manager
    manager = get_model_manager()
    print("\n✅ Model Manager created")

    # Check if GROQ_API_KEY is set
    if not os.environ.get("GROQ_API_KEY"):
        print("\n❌ GROQ_API_KEY not set - cannot test")
        print("   Set it with: export GROQ_API_KEY=your_key_here")
        return

    # Create a Groq adapter
    # Note: Using llama-3.3-70b-versatile (current model as of 2025)
    config = ModelConfig(
        provider=ModelProvider.GROQ,
        model_id="llama-3.3-70b-versatile",
        api_key=os.environ.get("GROQ_API_KEY"),
        max_tokens=100,
        temperature=0.7
    )
    groq_adapter = GroqAdapter(config)
    print(f"✅ Groq adapter created for model: {config.model_id}")

    # Register it for Ralph role
    manager.register_model(ModelRole.RALPH, groq_adapter)
    print(f"✅ Registered Groq for {ModelRole.RALPH.value} role")

    # Test a simple generation
    print("\n🧪 Testing generation...")
    messages = [
        {"role": "system", "content": "You are Ralph Wiggum, the lovable but confused boss."},
        {"role": "user", "content": "Say hi to the CEO in one short sentence."}
    ]

    try:
        response = await manager.generate(
            role=ModelRole.RALPH,
            messages=messages,
            max_tokens=50
        )
        print(f"\n✅ Generation successful!")
        print(f"📝 Response: {response}")

        # Check usage stats
        stats = manager.get_usage_stats()
        print(f"\n📊 Usage stats: {stats}")

        # List configured models
        configured = manager.list_configured_models()
        print(f"📋 Configured models: {configured}")

        print("\n" + "=" * 60)
        print("✅ MM-001: All tests passed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Generation failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_model_manager())
