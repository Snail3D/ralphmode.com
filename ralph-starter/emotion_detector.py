#!/usr/bin/env python3
"""
VE-001 to VE-004: Voice Emotion Detection

Analyzes audio to detect emotional tone from Mr. Worms' voice messages.
Ralph doesn't just hear words - he hears HOW they were said.
"""

import os
import logging
from typing import Dict, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class EmotionResult:
    """Result of emotion analysis."""
    primary_emotion: str
    confidence: float
    secondary_emotion: Optional[str] = None
    intensity: float = 0.5  # 0.0 = mild, 1.0 = intense

    # Raw features
    pitch_mean: float = 0.0
    pitch_variance: float = 0.0
    speed: float = 1.0  # 1.0 = normal
    volume: float = 0.5  # 0.0 = quiet, 1.0 = loud
    pause_ratio: float = 0.0  # ratio of silence to speech


# Emotion to scene translation
EMOTION_SCENES = {
    "frustrated": {
        "mr_worms_action": "*rubs temples*",
        "mr_worms_voice": "His voice is clipped, impatient.",
        "ralph_reaction": "*gulps nervously*",
        "ralph_thought": "Uh oh... Mr. Worms sounds upset...",
        "worker_mood": "tense"
    },
    "excited": {
        "mr_worms_action": "*leans forward, eyes bright*",
        "mr_worms_voice": "There's energy in his voice.",
        "ralph_reaction": "*perks up*",
        "ralph_thought": "Ooh! Mr. Worms sounds happy!",
        "worker_mood": "energized"
    },
    "tired": {
        "mr_worms_action": "*slumps slightly*",
        "mr_worms_voice": "His voice trails off, heavy.",
        "ralph_reaction": "*speaks softly*",
        "ralph_thought": "Mr. Worms sounds tired... I should help...",
        "worker_mood": "gentle"
    },
    "urgent": {
        "mr_worms_action": "*checks watch*",
        "mr_worms_voice": "Sharp. Staccato. No time for nonsense.",
        "ralph_reaction": "*snaps to attention*",
        "ralph_thought": "Fast! We need to move FAST!",
        "worker_mood": "focused"
    },
    "calm": {
        "mr_worms_action": "*settles back*",
        "mr_worms_voice": "Measured. Steady. In control.",
        "ralph_reaction": "*relaxes a bit*",
        "ralph_thought": "Okay... okay we're good...",
        "worker_mood": "relaxed"
    },
    "angry": {
        "mr_worms_action": "*jaw tightens*",
        "mr_worms_voice": "Low. Dangerous. Each word deliberate.",
        "ralph_reaction": "*shrinks back*",
        "ralph_thought": "Oh no oh no oh no...",
        "worker_mood": "scared"
    },
    "thinking": {
        "mr_worms_action": "*stares at ceiling*",
        "mr_worms_voice": "Slow. Contemplative. Working something out.",
        "ralph_reaction": "*waits quietly*",
        "ralph_thought": "Mr. Worms is thinking... I should wait...",
        "worker_mood": "attentive"
    },
    "neutral": {
        "mr_worms_action": "",
        "mr_worms_voice": "",
        "ralph_reaction": "",
        "ralph_thought": "",
        "worker_mood": "normal"
    }
}


def analyze_audio_features(audio_path: str) -> Dict[str, float]:
    """
    Extract audio features for emotion detection.
    Uses librosa for audio analysis.
    """
    try:
        import librosa
        import numpy as np
    except ImportError:
        logger.warning("librosa not installed - using fallback emotion detection")
        return {
            "pitch_mean": 150.0,
            "pitch_std": 30.0,
            "tempo": 1.0,
            "rms_mean": 0.5,
            "rms_std": 0.1,
            "zcr_mean": 0.05,
            "pause_ratio": 0.1
        }

    try:
        # Load audio
        y, sr = librosa.load(audio_path, sr=22050)

        # Pitch (fundamental frequency)
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
        pitch_values = []
        for t in range(pitches.shape[1]):
            index = magnitudes[:, t].argmax()
            pitch = pitches[index, t]
            if pitch > 0:
                pitch_values.append(pitch)

        pitch_mean = np.mean(pitch_values) if pitch_values else 150.0
        pitch_std = np.std(pitch_values) if pitch_values else 30.0

        # Tempo/speed
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        tempo = float(tempo) if hasattr(tempo, '__float__') else 120.0

        # Volume (RMS energy)
        rms = librosa.feature.rms(y=y)[0]
        rms_mean = float(np.mean(rms))
        rms_std = float(np.std(rms))

        # Zero crossing rate (correlates with noisiness/tension)
        zcr = librosa.feature.zero_crossing_rate(y)[0]
        zcr_mean = float(np.mean(zcr))

        # Pause detection (silence ratio)
        silence_threshold = 0.01
        silent_frames = np.sum(rms < silence_threshold)
        pause_ratio = silent_frames / len(rms) if len(rms) > 0 else 0.0

        return {
            "pitch_mean": pitch_mean,
            "pitch_std": pitch_std,
            "tempo": tempo / 120.0,  # Normalize to 1.0 = normal
            "rms_mean": rms_mean,
            "rms_std": rms_std,
            "zcr_mean": zcr_mean,
            "pause_ratio": pause_ratio
        }

    except Exception as e:
        logger.error(f"Error analyzing audio: {e}")
        return {
            "pitch_mean": 150.0,
            "pitch_std": 30.0,
            "tempo": 1.0,
            "rms_mean": 0.5,
            "rms_std": 0.1,
            "zcr_mean": 0.05,
            "pause_ratio": 0.1
        }


def classify_emotion(features: Dict[str, float]) -> EmotionResult:
    """
    Classify emotion based on audio features.

    Heuristic rules based on voice analysis research:
    - High pitch + fast = excited/anxious
    - Low pitch + slow = tired/sad
    - High volume + fast = angry/urgent
    - High pitch variance = emotional/frustrated
    - Many pauses = thinking/hesitant
    """
    pitch = features.get("pitch_mean", 150.0)
    pitch_var = features.get("pitch_std", 30.0)
    speed = features.get("tempo", 1.0)
    volume = features.get("rms_mean", 0.5)
    pauses = features.get("pause_ratio", 0.1)

    # Normalize features
    pitch_norm = (pitch - 100) / 200  # 0-1 scale roughly
    speed_norm = speed  # Already normalized
    volume_norm = min(volume * 5, 1.0)  # Scale up

    # Score each emotion
    scores = {}

    # Frustrated: high variance, medium-fast, medium-high volume
    scores["frustrated"] = (
        (pitch_var / 50) * 0.4 +
        speed_norm * 0.3 +
        volume_norm * 0.3
    )

    # Excited: high pitch, fast, high volume
    scores["excited"] = (
        pitch_norm * 0.3 +
        speed_norm * 0.4 +
        volume_norm * 0.3
    )

    # Tired: low pitch, slow, low volume
    scores["tired"] = (
        (1 - pitch_norm) * 0.3 +
        (1 - speed_norm) * 0.4 +
        (1 - volume_norm) * 0.3
    )

    # Urgent: fast, sharp (high zcr), high volume
    scores["urgent"] = (
        speed_norm * 0.5 +
        volume_norm * 0.3 +
        features.get("zcr_mean", 0.05) * 4
    )

    # Angry: low pitch, high volume, sharp
    scores["angry"] = (
        (1 - pitch_norm) * 0.3 +
        volume_norm * 0.5 +
        features.get("zcr_mean", 0.05) * 4
    )

    # Thinking: many pauses, slower
    scores["thinking"] = (
        pauses * 2 +
        (1 - speed_norm) * 0.3
    )

    # Calm: medium everything, low variance
    scores["calm"] = (
        (1 - abs(pitch_norm - 0.5)) * 0.4 +
        (1 - abs(speed_norm - 1.0)) * 0.3 +
        (1 - pitch_var / 50) * 0.3
    )

    # Find primary and secondary emotions
    sorted_emotions = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    primary = sorted_emotions[0]
    secondary = sorted_emotions[1] if len(sorted_emotions) > 1 else None

    # Calculate confidence (difference between top two)
    confidence = primary[1] - (secondary[1] if secondary else 0)
    confidence = min(max(confidence, 0.3), 1.0)

    # If confidence is low, default to neutral
    if primary[1] < 0.3:
        return EmotionResult(
            primary_emotion="neutral",
            confidence=0.5,
            intensity=0.5,
            pitch_mean=pitch,
            pitch_variance=pitch_var,
            speed=speed,
            volume=volume_norm,
            pause_ratio=pauses
        )

    return EmotionResult(
        primary_emotion=primary[0],
        confidence=confidence,
        secondary_emotion=secondary[0] if secondary and secondary[1] > 0.2 else None,
        intensity=min(primary[1], 1.0),
        pitch_mean=pitch,
        pitch_variance=pitch_var,
        speed=speed,
        volume=volume_norm,
        pause_ratio=pauses
    )


def detect_emotion(audio_path: str) -> EmotionResult:
    """
    Main entry point: analyze audio file and return emotion.
    """
    features = analyze_audio_features(audio_path)
    result = classify_emotion(features)

    logger.info(f"Emotion detected: {result.primary_emotion} "
                f"(confidence: {result.confidence:.2f}, intensity: {result.intensity:.2f})")

    return result


def get_scene_translation(emotion: EmotionResult) -> Dict[str, str]:
    """
    Get scene translation elements for the detected emotion.
    """
    scene = EMOTION_SCENES.get(emotion.primary_emotion, EMOTION_SCENES["neutral"])

    # Adjust intensity
    if emotion.intensity > 0.7:
        # Intensify the scene elements
        scene = scene.copy()
        if emotion.primary_emotion == "angry":
            scene["mr_worms_action"] = "*slams desk*"
            scene["ralph_reaction"] = "*jumps back, terrified*"
        elif emotion.primary_emotion == "excited":
            scene["mr_worms_action"] = "*practically jumping out of chair*"
            scene["ralph_reaction"] = "*bounces excitedly*"

    return scene


def format_emotional_message(transcript: str, emotion: EmotionResult) -> str:
    """
    Format a message with emotional context for the scene.
    """
    scene = get_scene_translation(emotion)

    if emotion.primary_emotion == "neutral":
        return f'Mr. Worms: "{transcript}"'

    parts = []

    if scene.get("mr_worms_action"):
        parts.append(scene["mr_worms_action"])

    parts.append(f'Mr. Worms: "{transcript}"')

    if scene.get("mr_worms_voice"):
        parts.append(f"_{scene['mr_worms_voice']}_")

    return "\n".join(parts)


# Test function
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
        result = detect_emotion(audio_file)
        print(f"Primary: {result.primary_emotion}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Intensity: {result.intensity:.2f}")
        if result.secondary_emotion:
            print(f"Secondary: {result.secondary_emotion}")

        scene = get_scene_translation(result)
        print(f"\nScene translation:")
        for key, value in scene.items():
            if value:
                print(f"  {key}: {value}")
    else:
        print("Usage: python emotion_detector.py <audio_file>")
