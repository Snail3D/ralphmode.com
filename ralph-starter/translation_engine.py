#!/usr/bin/env python3
"""
Translation Engine - TL-002: Character Translation Engine

Translates user speech/text into theatrical Mr. Worms character actions and dialogue.
The user says X, the chat shows a scene-based theatrical version.

This is THE CORE MAGIC of Ralph Mode - turning plain text into immersive fiction.
"""

import os
import logging
from typing import Dict, Optional, Tuple
from groq import Groq

# Import scene context if available
try:
    from scene_manager import get_time_of_day_context
    SCENE_MANAGER_AVAILABLE = True
except ImportError:
    SCENE_MANAGER_AVAILABLE = False
    def get_time_of_day_context():
        return {"time_key": "afternoon", "energy": "neutral", "worker_mood": "working", "description": ""}


class TranslationEngine:
    """
    Translates user input into theatrical Mr. Worms character presentation.

    Takes: "Fix the login bug"
    Returns: "*Mr. Worms bursts through the door, jaw clenched*\n'We've got a problem with the login system. Fix it.'"
    """

    def __init__(self, groq_api_key: Optional[str] = None):
        """Initialize translation engine with Groq API."""
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        if not self.groq_api_key:
            logging.warning("TL-002: No GROQ_API_KEY - translation will be basic")
            self.client = None
        else:
            self.client = Groq(api_key=self.groq_api_key)

    # Mr. Worms character profile
    MR_WORMS_PROFILE = {
        "name": "Mr. Worms",
        "role": "CEO / The Boss / The User",
        "personality": [
            "High-powered executive",
            "Direct and no-nonsense when frustrated",
            "Appreciative when things work well",
            "Can be demanding but fair",
            "Expressive body language (sighs, nods, taps desk)"
        ],
        "speech_patterns": [
            "Clear and concise",
            "Sometimes terse when stressed",
            "Professional but human",
            "Occasionally enthusiastic about good work"
        ],
        "typical_actions": [
            "enters/storms in",
            "leans back in chair",
            "taps desk thoughtfully",
            "nods approvingly",
            "sighs heavily",
            "raises an eyebrow",
            "glances at watch",
            "jaw tightens",
            "eyes narrow",
            "smiles slightly"
        ]
    }

    def translate_to_scene(
        self,
        user_input: str,
        tone: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> str:
        """
        Translate user input into theatrical Mr. Worms scene.

        Args:
            user_input: The raw user message (text, transcribed voice, etc.)
            tone: Optional detected tone (urgent, calm, frustrated, pleased)
            context: Optional context dict (current scene, time of day, etc.)

        Returns:
            Theatrical scene description with Mr. Worms actions and dialogue
        """
        if not user_input or not user_input.strip():
            return "*Mr. Worms enters, looks around expectantly*"

        # If no Groq client, fall back to basic formatting
        if not self.client:
            return self._basic_translation(user_input, tone)

        # Get scene context
        scene_context = self._get_scene_context(context)

        # Build Groq prompt
        prompt = self._build_translation_prompt(user_input, tone, scene_context)

        try:
            # Call Groq for translation
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.8,  # Creative but not random
                max_tokens=300,
            )

            translated = response.choices[0].message.content.strip()
            return translated

        except Exception as e:
            logging.error(f"TL-002: Groq translation failed: {e}")
            return self._basic_translation(user_input, tone)

    def _get_system_prompt(self) -> str:
        """Get the system prompt for Groq translation."""
        return """You are a theatrical narrator translating user messages into scene descriptions.

Your job: Take what the user says and present it as if Mr. Worms (the CEO) said/did it in a scene.

Rules:
1. Always include stage directions in asterisks (*Mr. Worms enters*)
2. Put dialogue in quotes ("We need to fix this")
3. Match the tone to the emotion (frustrated = tense actions, pleased = calm actions)
4. Keep it concise - 1-3 sentences max
5. Never break character or mention the translation
6. The meaning MUST stay the same - just the presentation changes
7. Make it feel like reading a screenplay

Mr. Worms character:
- CEO/Boss type
- Direct and professional
- Expressive through body language
- Sometimes stressed, sometimes pleased
- Human, not robotic

Example:
Input: "Fix the login bug"
Output: *Mr. Worms storms in, jaw tight*
"We've got a login issue. Get it fixed."

Example:
Input: "Great work on the feature!"
Output: *Mr. Worms leans back, nodding with approval*
"Excellent work on that feature, team."

Now translate user input into Mr. Worms theatrical scenes."""

    def _build_translation_prompt(
        self,
        user_input: str,
        tone: Optional[str],
        scene_context: Dict
    ) -> str:
        """Build the translation prompt for Groq."""
        parts = [f"User message: {user_input}"]

        if tone:
            parts.append(f"Detected tone: {tone}")

        if scene_context.get("time_key"):
            parts.append(f"Time of day: {scene_context['time_key']} ({scene_context.get('worker_mood', '')})")

        if scene_context.get("description"):
            parts.append(f"Current atmosphere: {scene_context['description']}")

        parts.append("\nTranslate this into a Mr. Worms theatrical scene:")

        return "\n".join(parts)

    def _get_scene_context(self, context: Optional[Dict]) -> Dict:
        """Get current scene context (time of day, mood, etc.)."""
        if context:
            return context

        # Try to get live context from scene manager
        if SCENE_MANAGER_AVAILABLE:
            try:
                return get_time_of_day_context()
            except Exception as e:
                logging.error(f"TL-002: Failed to get scene context: {e}")

        return {
            "time_key": "afternoon",
            "energy": "neutral",
            "worker_mood": "working",
            "description": ""
        }

    def _basic_translation(self, user_input: str, tone: Optional[str]) -> str:
        """
        Fallback translation when Groq is unavailable.
        Simple pattern-based formatting.
        """
        # Determine action based on tone or input
        action = self._infer_action(user_input, tone)

        # Format as scene
        return f"*Mr. Worms {action}*\n\"{user_input}\""

    def _infer_action(self, user_input: str, tone: Optional[str]) -> str:
        """Infer Mr. Worms' action from input/tone."""
        input_lower = user_input.lower()

        # Tone-based
        if tone:
            tone_actions = {
                "urgent": "storms in, eyes intense",
                "frustrated": "enters with jaw tight",
                "pleased": "walks in with a slight smile",
                "calm": "enters calmly",
                "excited": "bounds in energetically"
            }
            if tone in tone_actions:
                return tone_actions[tone]

        # Content-based fallback
        if any(word in input_lower for word in ["bug", "error", "problem", "issue", "fix"]):
            return "enters, brow furrowed"
        elif any(word in input_lower for word in ["great", "good", "excellent", "nice", "thanks"]):
            return "nods approvingly"
        elif "?" in user_input:
            return "looks up inquisitively"
        elif "!" in user_input:
            return "speaks with emphasis"
        else:
            return "enters"


# Global instance
_translation_engine = None


def get_translation_engine() -> TranslationEngine:
    """Get or create global translation engine instance."""
    global _translation_engine
    if _translation_engine is None:
        _translation_engine = TranslationEngine()
    return _translation_engine


def translate_to_scene(
    user_input: str,
    tone: Optional[str] = None,
    context: Optional[Dict] = None
) -> str:
    """
    Convenience function: Translate user input to theatrical scene.

    Args:
        user_input: The user's message
        tone: Optional detected tone
        context: Optional scene context

    Returns:
        Theatrical Mr. Worms scene description
    """
    engine = get_translation_engine()
    return engine.translate_to_scene(user_input, tone, context)


if __name__ == "__main__":
    # Test the translation engine
    print("Testing Translation Engine (TL-002)...\n")
    print("=" * 60)

    test_inputs = [
        ("Fix the login bug", "urgent"),
        ("Great work on the new feature!", "pleased"),
        ("What's the status on the deployment?", "calm"),
        ("This is taking too long", "frustrated"),
        ("Add dark mode to the app", None),
    ]

    engine = TranslationEngine()

    for user_input, tone in test_inputs:
        print(f"\nInput: {user_input}")
        print(f"Tone: {tone or 'auto-detect'}")
        print("-" * 60)

        translation = engine.translate_to_scene(user_input, tone)
        print(translation)
        print("=" * 60)
