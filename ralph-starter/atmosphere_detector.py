#!/usr/bin/env python3
"""
Atmosphere Detector - SS-004: Atmosphere Matching to Task

Analyzes user directives to detect task type and set appropriate atmosphere.
Bug hunts = tense, new features = excited, routine = calm, crunch time = intense.
"""

import logging
import re
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class AtmosphereDetector:
    """
    Detects task atmosphere based on user directive content.

    This influences:
    - Scene mood (weather selection)
    - Worker energy levels
    - Dialogue tone
    - Pacing of responses
    """

    # Keywords and patterns for different task types
    TASK_PATTERNS = {
        "bug_hunt": {
            "keywords": [
                r"\bbug\b", r"\bfix\b", r"\bbreak", r"\bbroken\b", r"\bissue\b",
                r"\berror\b", r"\bcrash", r"\bfail", r"\bproblem\b", r"\bwrong\b",
                r"\bnot working\b", r"\bdebug\b", r"\btroubleshoot\b"
            ],
            "atmosphere": "tense",
            "mood_override": "stormy",  # Weather to suggest
            "energy": "focused_hunt",
            "description": "Bug hunt - tense, focused atmosphere"
        },
        "urgent": {
            "keywords": [
                r"\burgent\b", r"\basap\b", r"\bquickly\b", r"\bfast\b", r"\brushing\b",
                r"\bdeadline\b", r"\bemergency\b", r"\bcritical\b", r"\bnow\b",
                r"\bimmediately\b", r"\bhurry\b", r"\bpriority\b"
            ],
            "atmosphere": "urgent",
            "mood_override": "stormy",
            "energy": "crunch_mode",
            "description": "Urgent task - high pressure, fast-paced"
        },
        "new_feature": {
            "keywords": [
                r"\bnew\b", r"\badd\b", r"\bcreate\b", r"\bbuild\b", r"\bimplement\b",
                r"\bfeature\b", r"\bfunctionality\b", r"\bcapability\b", r"\benhance\b"
            ],
            "atmosphere": "excited",
            "mood_override": "sunny",
            "energy": "creative_energy",
            "description": "New feature - excited, creative energy"
        },
        "refactor": {
            "keywords": [
                r"\brefactor\b", r"\bclean up\b", r"\breorganize\b", r"\brestructure\b",
                r"\bimprove\b", r"\boptimize\b", r"\bsimplify\b", r"\bmodernize\b"
            ],
            "atmosphere": "focused",
            "mood_override": "overcast",
            "energy": "steady_grind",
            "description": "Refactor - calm, methodical work"
        },
        "routine": {
            "keywords": [
                r"\bupdate\b", r"\bchange\b", r"\bmodify\b", r"\badjust\b",
                r"\btweak\b", r"\bedit\b", r"\bsmall\b", r"\bquick\b", r"\bsimple\b"
            ],
            "atmosphere": "calm",
            "mood_override": None,  # Use default weather
            "energy": "comfortable",
            "description": "Routine task - calm, steady work"
        },
        "exploration": {
            "keywords": [
                r"\bexplore\b", r"\bresearch\b", r"\binvestigate\b", r"\bfind out\b",
                r"\blearn\b", r"\bunderstand\b", r"\banalyze\b", r"\bstudy\b"
            ],
            "atmosphere": "curious",
            "mood_override": "foggy",
            "energy": "investigative",
            "description": "Exploration - curious, investigative mood"
        },
        "testing": {
            "keywords": [
                r"\btest\b", r"\bvalidate\b", r"\bverify\b", r"\bcheck\b",
                r"\bqa\b", r"\bquality\b"
            ],
            "atmosphere": "methodical",
            "mood_override": "overcast",
            "energy": "systematic",
            "description": "Testing - methodical, systematic approach"
        }
    }

    def detect_atmosphere(self, user_message: str) -> Dict[str, any]:
        """
        Analyze user message to detect task atmosphere.

        Args:
            user_message: The user's directive or message

        Returns:
            Dictionary with atmosphere info:
            - task_type: Detected type (bug_hunt, new_feature, etc.)
            - atmosphere: Overall atmosphere (tense, excited, calm, etc.)
            - mood_override: Suggested weather/mood (or None for default)
            - energy: Worker energy level
            - description: Human-readable description
            - confidence: How confident we are (0.0-1.0)
        """
        if not user_message:
            return self._default_atmosphere()

        message_lower = user_message.lower()

        # Score each task type based on keyword matches
        scores = {}
        for task_type, config in self.TASK_PATTERNS.items():
            score = 0
            matched_keywords = []

            for pattern in config["keywords"]:
                if re.search(pattern, message_lower):
                    score += 1
                    matched_keywords.append(pattern)

            if score > 0:
                scores[task_type] = {
                    "score": score,
                    "config": config,
                    "matched": matched_keywords
                }

        # If no matches, return calm/routine default
        if not scores:
            logger.info("SS-004: No specific task type detected, using default calm atmosphere")
            return self._default_atmosphere()

        # Get highest scoring task type
        best_match = max(scores.items(), key=lambda x: x[1]["score"])
        task_type = best_match[0]
        config = best_match[1]["config"]
        match_count = best_match[1]["score"]

        # Calculate confidence (normalized, capped at 1.0)
        # More keyword matches = higher confidence
        confidence = min(match_count / 3.0, 1.0)

        logger.info(f"SS-004: Detected task type '{task_type}' with {match_count} keyword matches (confidence: {confidence:.2f})")

        return {
            "task_type": task_type,
            "atmosphere": config["atmosphere"],
            "mood_override": config["mood_override"],
            "energy": config["energy"],
            "description": config["description"],
            "confidence": confidence,
            "matched_keywords": best_match[1]["matched"]
        }

    def _default_atmosphere(self) -> Dict[str, any]:
        """Return default calm atmosphere for routine work."""
        return {
            "task_type": "routine",
            "atmosphere": "calm",
            "mood_override": None,
            "energy": "comfortable",
            "description": "Routine task - calm, steady work",
            "confidence": 0.5,
            "matched_keywords": []
        }

    def get_atmosphere_text(self, atmosphere_type: str) -> str:
        """
        Get descriptive text for atmosphere that can be used in responses.

        Args:
            atmosphere_type: The atmosphere type (tense, excited, calm, etc.)

        Returns:
            Descriptive text fragment
        """
        atmosphere_descriptions = {
            "tense": "The air is thick with focus. Something's broken and needs fixing",
            "urgent": "Energy crackles in the air. Deadline mode activated",
            "excited": "There's a buzz of creative energy. Time to build something new",
            "focused": "Calm determination fills the space. Time to make things better",
            "calm": "Steady, comfortable rhythm. Just another day at the keyboard",
            "curious": "Heads tilt. Questions form. Time to dig into the unknown",
            "methodical": "Systematic. Thorough. No stone left unturned"
        }

        return atmosphere_descriptions.get(
            atmosphere_type,
            "The team settles in for another day's work"
        )


# Global instance for easy import
_atmosphere_detector = AtmosphereDetector()


def detect_atmosphere(user_message: str) -> Dict[str, any]:
    """
    Convenience function to detect atmosphere from user message.

    Args:
        user_message: User's directive or message

    Returns:
        Atmosphere info dictionary
    """
    return _atmosphere_detector.detect_atmosphere(user_message)


def get_atmosphere_text(atmosphere_type: str) -> str:
    """
    Convenience function to get atmosphere description text.

    Args:
        atmosphere_type: Atmosphere type

    Returns:
        Descriptive text
    """
    return _atmosphere_detector.get_atmosphere_text(atmosphere_type)


if __name__ == "__main__":
    # Test the atmosphere detector
    print("Testing Atmosphere Detector...\n")
    print("=" * 60)

    test_messages = [
        "Fix the login bug ASAP!",
        "Add a new dashboard feature",
        "Update the README",
        "Refactor the auth module to be cleaner",
        "Investigate why the API is slow",
        "Test the checkout flow",
        "Something is broken in production and we need it fixed now!",
        "Let's build a cool new animation feature",
        "Just a quick tweak to the colors"
    ]

    for msg in test_messages:
        print(f"\nMessage: '{msg}'")
        result = detect_atmosphere(msg)
        print(f"  Task Type: {result['task_type']}")
        print(f"  Atmosphere: {result['atmosphere']}")
        print(f"  Energy: {result['energy']}")
        print(f"  Confidence: {result['confidence']:.2f}")
        print(f"  Mood Override: {result['mood_override']}")
        print(f"  Description: {result['description']}")
        print(f"  Matched: {', '.join(result['matched_keywords'][:3])}")
        print(f"\n  Scene Text: {get_atmosphere_text(result['atmosphere'])}")
        print("-" * 60)
