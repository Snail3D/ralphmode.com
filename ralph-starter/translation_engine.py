#!/usr/bin/env python3
"""
Translation Engine - TL-002 & TL-003 & TL-005: Character Translation & Scene-Contextualized Output

TL-002: Translates user speech/text into theatrical Mr. Worms character actions and dialogue.
TL-003: Formats ALL bot output within the established scene context.
TL-005: Swear Word to Action Translation - broadcast-safe emotional expression.

The user says X, the chat shows a scene-based theatrical version.
Bot responses include actions, atmosphere, and stay within the fiction.

This is THE CORE MAGIC of Ralph Mode - turning plain text into immersive fiction.
"""

import os
import logging
import re
from typing import Dict, Optional, Tuple, List
from groq import Groq

# Import scene context if available
try:
    from scene_manager import get_time_of_day_context
    SCENE_MANAGER_AVAILABLE = True
except ImportError:
    SCENE_MANAGER_AVAILABLE = False
    def get_time_of_day_context():
        return {"time_key": "afternoon", "energy": "neutral", "worker_mood": "working", "description": ""}


# TL-005: Swear Word Detection and Translation
# Pattern-based detection for common profanity (case-insensitive)
SWEAR_PATTERNS = [
    # F-word and variations
    (r'\bfuck(?:ing|ed|er|s)?\b', 'intense'),
    # S-word and variations
    (r'\bshit(?:ty|tier|s)?\b', 'moderate'),
    # Other common profanity
    (r'\bdamn(?:ed|s|ing)?\b', 'mild'),
    (r'\bhell\b', 'mild'),
    (r'\bass(?:hole|es)?\b', 'moderate'),
    (r'\bbitch(?:es|y|ing)?\b', 'moderate'),
    (r'\bbastard(?:s)?\b', 'moderate'),
    (r'\bcrap(?:py|s)?\b', 'mild'),
    # Multi-word deity-based profanity
    (r'\bjesus christ\b', 'mild'),
    (r'\bgod ?damn(?:it|ed)?\b', 'mild'),
]

# Intensity to action mapping - conveys emotion without profanity
INTENSITY_ACTIONS = {
    'intense': [
        'jaw clenches tight',
        'fist slams on desk',
        'eyes blaze with intensity',
        'face flushes red',
        'jaw tightens, knuckles white',
        'teeth grind audibly',
        'veins pulse at temples',
        'hands ball into fists'
    ],
    'moderate': [
        'jaw tightens',
        'eyes narrow sharply',
        'face hardens',
        'lips press into thin line',
        'brow furrows deeply',
        'nostrils flare',
        'shoulders tense',
        'hand slaps desk'
    ],
    'mild': [
        'sighs heavily',
        'shakes head',
        'runs hand through hair',
        'pinches bridge of nose',
        'exhales slowly',
        'closes eyes briefly',
        'jaw sets',
        'taps desk impatiently'
    ]
}


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

        # TL-005: Compile swear patterns for efficiency
        self.swear_regex = [
            (re.compile(pattern, re.IGNORECASE), intensity)
            for pattern, intensity in SWEAR_PATTERNS
        ]

    def detect_swear_words(self, text: str) -> List[Tuple[str, str, str]]:
        """
        TL-005: Detect swear words in text and return matches with intensity.

        Args:
            text: The text to scan for profanity

        Returns:
            List of tuples: (matched_word, intensity, position_info)
        """
        matches = []
        for regex, intensity in self.swear_regex:
            for match in regex.finditer(text):
                matched_word = match.group(0)
                matches.append((matched_word, intensity, match.span()))

        # Sort by position (earliest first)
        matches.sort(key=lambda x: x[2][0])
        return matches

    def translate_swear_to_action(self, intensity: str, context_text: str = "") -> str:
        """
        TL-005: Translate swear word intensity to physical action.

        Args:
            intensity: The emotional intensity ('intense', 'moderate', 'mild')
            context_text: Optional context to help choose appropriate action

        Returns:
            A physical action description that conveys the emotion
        """
        import random

        actions = INTENSITY_ACTIONS.get(intensity, INTENSITY_ACTIONS['moderate'])

        # Use random.choice for variety (not verbatim same action)
        return random.choice(actions)

    def sanitize_swear_words(self, text: str, translate_to_actions: bool = True) -> Tuple[str, List[str]]:
        """
        TL-005: Remove swear words from text and optionally provide action alternatives.

        Args:
            text: The text to sanitize
            translate_to_actions: If True, suggest actions to replace emotional weight

        Returns:
            Tuple of (sanitized_text, list_of_suggested_actions)
        """
        matches = self.detect_swear_words(text)

        if not matches:
            return text, []

        # Build sanitized version by replacing swears
        sanitized = text
        actions = []
        offset = 0

        for matched_word, intensity, (start, end) in matches:
            # Adjust positions for previous replacements
            adjusted_start = start + offset
            adjusted_end = end + offset

            # Replace swear with empty space (removing it entirely)
            replacement = ""
            sanitized = sanitized[:adjusted_start] + replacement + sanitized[adjusted_end:]

            # Update offset
            offset += len(replacement) - (end - start)

            # Generate action to convey the emotion
            if translate_to_actions:
                action = self.translate_swear_to_action(intensity, text)
                actions.append(action)

        # Clean up extra whitespace and orphaned articles
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()

        # Remove orphaned "the" at start or after "what/where/when/why/how"
        sanitized = re.sub(r'\b(what|where|when|why|how)\s+the\s+(?=\w)', r'\1 ', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'^the\s+(?=\w)', '', sanitized, flags=re.IGNORECASE)

        # Clean up punctuation issues (comma at start, etc.)
        sanitized = re.sub(r'^[,;]\s*', '', sanitized)
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()

        return sanitized, actions

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

        # TL-005: Sanitize swear words and get suggested actions
        sanitized_input, swear_actions = self.sanitize_swear_words(user_input, translate_to_actions=True)

        # If no Groq client, fall back to basic formatting
        if not self.client:
            return self._basic_translation(sanitized_input, tone, swear_actions)

        # Get scene context
        scene_context = self._get_scene_context(context)

        # Build Groq prompt (using sanitized input)
        prompt = self._build_translation_prompt(sanitized_input, tone, scene_context, swear_actions)

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
            return self._basic_translation(sanitized_input, tone, swear_actions)

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
8. BROADCAST-SAFE: Never include profanity - use physical actions instead (jaw tightens, fist slams desk, etc.)
9. If suggested actions are provided, incorporate them to show emotional intensity

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

Example (with emotional intensity):
Input: "This is taking way too long" + Suggested action: "jaw clenches tight"
Output: *Mr. Worms bursts in, jaw clenched tight*
"This is taking way too long."

Now translate user input into Mr. Worms theatrical scenes."""

    def _build_translation_prompt(
        self,
        user_input: str,
        tone: Optional[str],
        scene_context: Dict,
        swear_actions: Optional[List[str]] = None
    ) -> str:
        """Build the translation prompt for Groq."""
        parts = [f"User message: {user_input}"]

        if tone:
            parts.append(f"Detected tone: {tone}")

        # TL-005: Include suggested actions from swear word translation
        if swear_actions:
            actions_str = ", ".join(swear_actions)
            parts.append(f"Suggested actions (emotional intensity): {actions_str}")

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

    def _basic_translation(
        self,
        user_input: str,
        tone: Optional[str],
        swear_actions: Optional[List[str]] = None
    ) -> str:
        """
        Fallback translation when Groq is unavailable.
        Simple pattern-based formatting.
        """
        # TL-005: Use swear action if available, otherwise infer from tone/input
        if swear_actions and len(swear_actions) > 0:
            action = swear_actions[0]  # Use the first suggested action
        else:
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

    def format_scene_output(
        self,
        speaker: str,
        message: str,
        action: Optional[str] = None,
        include_atmosphere: bool = False
    ) -> str:
        """
        TL-003: Format bot output as scene description.

        Args:
            speaker: Who is speaking (Ralph, Stool, Gomer, etc.)
            message: What they're saying
            action: Optional action description
            include_atmosphere: Whether to include atmospheric details

        Returns:
            Formatted scene output with actions and dialogue
        """
        parts = []

        # Add atmospheric context if requested
        if include_atmosphere:
            scene_context = self._get_scene_context(None)
            if scene_context.get('description'):
                parts.append(f"_{scene_context['description']}_\n")

        # Add action if provided
        if action:
            parts.append(f"*{action}*")

        # Add speaker and dialogue
        if message:
            # If message already has formatting, use it as-is
            if message.startswith('*') or message.startswith('_'):
                parts.append(message)
            else:
                # Otherwise, format as dialogue with speaker
                parts.append(f'"{message}"')
                if parts[-2:] == []:  # If no action, add speaker tag
                    parts[-1] = f"**{speaker}:** {parts[-1]}"

        return "\n".join(parts)

    def add_scene_atmosphere(self, message: str) -> str:
        """
        TL-003: Add atmospheric context to a message.

        Args:
            message: The message to enhance with atmosphere

        Returns:
            Message with atmospheric context prepended
        """
        scene_context = self._get_scene_context(None)

        # Only add atmosphere if we have description
        if not scene_context.get('description'):
            return message

        # Atmospheric prefix
        atmosphere = f"_{scene_context['description']}_\n\n"

        return atmosphere + message


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


def format_scene_output(
    speaker: str,
    message: str,
    action: Optional[str] = None,
    include_atmosphere: bool = False
) -> str:
    """
    TL-003: Format bot output as scene description (convenience function).

    Args:
        speaker: Who is speaking (Ralph, Stool, etc.)
        message: What they're saying
        action: Optional action description
        include_atmosphere: Whether to include atmospheric details

    Returns:
        Formatted scene output
    """
    engine = get_translation_engine()
    return engine.format_scene_output(speaker, message, action, include_atmosphere)


def add_scene_atmosphere(message: str) -> str:
    """
    TL-003: Add atmospheric context to a message (convenience function).

    Args:
        message: The message to enhance

    Returns:
        Message with atmosphere
    """
    engine = get_translation_engine()
    return engine.add_scene_atmosphere(message)


if __name__ == "__main__":
    # Test the translation engine
    print("Testing Translation Engine (TL-002 & TL-005)...\n")
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

    # TL-005: Test swear word translation
    print("\n\nTesting TL-005: Swear Word to Action Translation...\n")
    print("=" * 60)

    swear_test_inputs = [
        ("What the fuck is taking so long", "frustrated"),
        ("This shit doesn't work", "frustrated"),
        ("Damn it, we have another bug", "frustrated"),
        ("Fix this fucking login issue", "urgent"),
        ("Hell, that was fast!", "pleased"),
    ]

    for user_input, tone in swear_test_inputs:
        print(f"\nOriginal Input: {user_input}")
        print(f"Tone: {tone}")
        print("-" * 60)

        # Show sanitization process
        sanitized, actions = engine.sanitize_swear_words(user_input)
        print(f"Sanitized: {sanitized}")
        print(f"Suggested Actions: {actions}")
        print()

        # Show final translation
        translation = engine.translate_to_scene(user_input, tone)
        print("Final Translation:")
        print(translation)
        print("=" * 60)
