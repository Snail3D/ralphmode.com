#!/usr/bin/env python3
"""
Voice Handler - VO-004: Voice-to-Intent Pipeline
Handles voice messages: transcription, tone analysis, and intent extraction.

VE-009/VE-010: Now includes AUDIO-BASED emotion detection.
Ralph doesn't just hear words - he hears HOW they were said.
"""

import os
import logging
import tempfile
import json
from typing import Optional, Tuple, Dict, Any
from telegram import Update
from telegram.ext import ContextTypes

# VE-009: Import audio-based emotion detector
try:
    from emotion_detector import detect_emotion, get_scene_translation, EmotionResult
    EMOTION_DETECTOR_AVAILABLE = True
except ImportError:
    EMOTION_DETECTOR_AVAILABLE = False

logger = logging.getLogger(__name__)


class VoiceHandler:
    """Handle voice message transcription and processing - VO-004 Voice-to-Intent Pipeline."""

    def __init__(self, groq_api_key: str):
        """Initialize voice handler with Groq API key."""
        self.groq_api_key = groq_api_key
        self.supported_formats = ['.ogg', '.mp3', '.m4a', '.wav', '.opus']

    async def process_voice_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> Optional[Dict[str, Any]]:
        """
        VO-004 + VE-009/VE-010: Full voice-to-intent pipeline with emotion detection.
        Process voice message through complete pipeline:
        1. Download audio
        2. Analyze audio for emotion (VE-009 - AUDIO-BASED)
        3. Transcribe audio
        4. Analyze tone from text
        5. Combine audio emotion + text tone
        6. Extract intent
        7. Handle unclear audio gracefully

        Ralph doesn't just hear words - he hears HOW they were said.

        Args:
            update: Telegram update object with voice message
            context: Bot context

        Returns:
            Dictionary with complete analysis: {
                'transcription': str,
                'tone': dict,
                'intent': dict,
                'audio_emotion': dict,  # NEW: Audio-based emotion
                'scene_translation': dict,  # NEW: How Ralph "sees" the emotion
                'success': bool
            }
        """
        try:
            # Step 0: Download audio file first (needed for both emotion and transcription)
            voice = update.message.voice
            if not voice:
                logger.error("VO-004: No voice message in update")
                return self._empty_result()

            voice_file = await context.bot.get_file(voice.file_id)
            with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as tmp_file:
                tmp_path = tmp_file.name
                await voice_file.download_to_drive(tmp_path)

            logger.info(f"VO-004: Downloaded voice file to {tmp_path}")

            # Step 1: VE-009 - Analyze AUDIO for emotion (before transcription)
            audio_emotion = None
            scene_translation = {}
            if EMOTION_DETECTOR_AVAILABLE:
                try:
                    audio_emotion = detect_emotion(tmp_path)
                    scene_translation = get_scene_translation(audio_emotion)
                    logger.info(f"VE-009: Audio emotion detected: {audio_emotion.primary_emotion} "
                               f"(confidence: {audio_emotion.confidence:.2f})")
                except Exception as e:
                    logger.error(f"VE-009: Audio emotion detection failed: {e}")
                    audio_emotion = None

            # Step 2: Transcribe
            transcription = await self._call_groq_whisper(tmp_path)

            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except Exception as e:
                logger.warning(f"VO-002: Failed to delete temp file {tmp_path}: {e}")

            if not transcription:
                logger.error("VO-004: Transcription failed")
                return {
                    'transcription': None,
                    'tone': self._fallback_tone(),
                    'intent': self._fallback_intent(''),
                    'audio_emotion': self._audio_emotion_to_dict(audio_emotion),
                    'scene_translation': scene_translation,
                    'success': False
                }

            # Step 3: Analyze tone from TEXT
            tone_data = await self.analyze_tone(transcription)

            # Step 4: VE-011 - Combine audio emotion with text tone
            if audio_emotion and audio_emotion.primary_emotion != "neutral":
                # Audio emotion takes precedence - it's what they actually SOUNDED like
                tone_data['audio_emotion'] = audio_emotion.primary_emotion
                tone_data['audio_confidence'] = audio_emotion.confidence
                tone_data['audio_intensity'] = audio_emotion.intensity
                # Override text-based tone if audio is confident
                if audio_emotion.confidence > 0.5:
                    tone_data['primary_tone'] = audio_emotion.primary_emotion
                    tone_data['intensity'] = 'high' if audio_emotion.intensity > 0.7 else 'medium' if audio_emotion.intensity > 0.4 else 'low'

            # Step 5: Extract intent (passing combined tone for context)
            intent_data = await self.extract_intent(transcription, tone_data)

            # Step 6: Check if we need clarification
            if intent_data.get('needs_clarification', False):
                logger.warning(f"VO-004: Voice message needs clarification: {transcription}")

            logger.info(f"VO-004: Pipeline complete - Intent: {intent_data['intent_type']}, "
                       f"Tone: {tone_data['primary_tone']}, Audio: {audio_emotion.primary_emotion if audio_emotion else 'N/A'}")

            return {
                'transcription': transcription,
                'tone': tone_data,
                'intent': intent_data,
                'audio_emotion': self._audio_emotion_to_dict(audio_emotion),
                'scene_translation': scene_translation,
                'success': True
            }

        except Exception as e:
            logger.error(f"VO-004: Error in voice pipeline: {e}")
            return {
                'transcription': None,
                'tone': self._fallback_tone(),
                'intent': self._fallback_intent(''),
                'audio_emotion': None,
                'scene_translation': {},
                'success': False
            }

    def _audio_emotion_to_dict(self, emotion) -> Optional[Dict[str, Any]]:
        """Convert EmotionResult to dictionary."""
        if emotion is None:
            return None
        return {
            'primary_emotion': emotion.primary_emotion,
            'confidence': emotion.confidence,
            'intensity': emotion.intensity,
            'secondary_emotion': emotion.secondary_emotion,
            'pitch_mean': emotion.pitch_mean,
            'speed': emotion.speed,
            'volume': emotion.volume
        }

    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result for failed pipeline."""
        return {
            'transcription': None,
            'tone': self._fallback_tone(),
            'intent': self._fallback_intent(''),
            'audio_emotion': None,
            'scene_translation': {},
            'success': False
        }

    async def transcribe_voice(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> Optional[str]:
        """
        Transcribe voice message using Groq's Whisper API.

        Args:
            update: Telegram update object with voice message
            context: Bot context

        Returns:
            Transcribed text or None if failed
        """
        try:
            voice = update.message.voice
            if not voice:
                logger.error("VO-002: No voice message in update")
                return None

            # Download voice file to temporary location
            voice_file = await context.bot.get_file(voice.file_id)

            # Create temporary file with proper extension (.ogg for Telegram voice)
            with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as tmp_file:
                tmp_path = tmp_file.name
                await voice_file.download_to_drive(tmp_path)

            logger.info(f"VO-002: Downloaded voice file to {tmp_path}")

            # Transcribe using Groq Whisper API
            transcription = await self._call_groq_whisper(tmp_path)

            # Clean up temporary file
            try:
                os.unlink(tmp_path)
            except Exception as e:
                logger.warning(f"VO-002: Failed to delete temp file {tmp_path}: {e}")

            if transcription:
                logger.info(f"VO-002: Transcribed voice message: {transcription[:100]}...")
            else:
                logger.error("VO-002: Transcription returned empty")

            return transcription

        except Exception as e:
            logger.error(f"VO-002: Error transcribing voice message: {e}")
            return None

    async def _call_groq_whisper(self, audio_path: str) -> Optional[str]:
        """
        Call Groq's Whisper API for transcription.

        Args:
            audio_path: Path to audio file

        Returns:
            Transcribed text or None if failed
        """
        try:
            import aiohttp

            url = "https://api.groq.com/openai/v1/audio/transcriptions"
            headers = {
                "Authorization": f"Bearer {self.groq_api_key}"
            }

            # Read audio file
            with open(audio_path, 'rb') as f:
                audio_data = f.read()

            # Prepare multipart form data
            data = aiohttp.FormData()
            data.add_field('file', audio_data, filename='audio.ogg', content_type='audio/ogg')
            data.add_field('model', 'whisper-large-v3')
            data.add_field('response_format', 'json')
            data.add_field('language', 'en')  # Can be made configurable

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, data=data, timeout=30) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get('text', '').strip()
                    else:
                        error_text = await response.text()
                        logger.error(f"VO-002: Groq Whisper API error {response.status}: {error_text}")
                        return None

        except Exception as e:
            logger.error(f"VO-002: Error calling Groq Whisper API: {e}")
            return None

    async def analyze_tone(self, transcribed_text: str) -> Dict[str, Any]:
        """
        Analyze tone of transcribed text using Groq LLM.
        VO-004: Tone analysis component.

        Args:
            transcribed_text: Text from voice transcription

        Returns:
            Dictionary with tone analysis: {
                'primary_tone': str,  # angry, happy, questioning, neutral, frustrated, excited, etc.
                'intensity': str,     # low, medium, high
                'confidence': str,    # low, medium, high
                'description': str    # Brief description of tone
            }
        """
        try:
            import aiohttp

            # VO-004: Ask LLM to analyze tone
            prompt = f"""Analyze the tone of this voice message transcription. Return a JSON object with:
- primary_tone: One of: angry, happy, questioning, neutral, frustrated, excited, concerned, urgent, casual, professional
- intensity: low, medium, or high
- confidence: low, medium, or high (how clear the tone is)
- description: Brief 1-sentence description

Transcription: "{transcribed_text}"

Return ONLY valid JSON, no other text."""

            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 200
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=15) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result['choices'][0]['message']['content'].strip()

                        # Try to parse JSON from response
                        # Handle cases where LLM wraps JSON in code blocks
                        if '```json' in content:
                            content = content.split('```json')[1].split('```')[0].strip()
                        elif '```' in content:
                            content = content.split('```')[1].split('```')[0].strip()

                        tone_data = json.loads(content)
                        logger.info(f"VO-004: Tone analysis: {tone_data}")
                        return tone_data
                    else:
                        error_text = await response.text()
                        logger.error(f"VO-004: Groq tone analysis error {response.status}: {error_text}")
                        return self._fallback_tone()

        except Exception as e:
            logger.error(f"VO-004: Error analyzing tone: {e}")
            return self._fallback_tone()

    def _fallback_tone(self) -> Dict[str, Any]:
        """Return default tone when analysis fails."""
        return {
            'primary_tone': 'neutral',
            'intensity': 'medium',
            'confidence': 'low',
            'description': 'Unable to analyze tone, treating as neutral'
        }

    async def extract_intent(self, transcribed_text: str, tone_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract intent from transcribed text using LLM analysis.
        VO-004: Intent extraction component.

        Args:
            transcribed_text: Text from voice transcription
            tone_data: Tone analysis results

        Returns:
            Dictionary with intent analysis: {
                'intent_type': str,      # boss_message, command, feedback, question, work_request, etc.
                'confidence': str,       # low, medium, high
                'action_required': bool, # Does this need a response/action?
                'extracted_message': str,# Clean message for processing
                'clarity': str,          # clear, unclear, ambiguous
                'needs_clarification': bool
            }
        """
        try:
            import aiohttp

            # VO-004: Use LLM to extract intent
            prompt = f"""Analyze this voice message transcription and determine the user's intent. Consider the tone analysis as context.

Transcription: "{transcribed_text}"
Tone: {tone_data.get('primary_tone', 'neutral')} ({tone_data.get('intensity', 'medium')} intensity)

Classify the intent as ONE of:
- boss_message: User giving instructions/commands to their AI dev team
- question: User asking a question
- feedback: User providing feedback about the bot
- work_request: User requesting work to be done on their code
- status_check: User checking on progress
- command: Bot command (like /start, /help)
- unclear: Cannot determine intent

Return ONLY valid JSON with:
- intent_type: (one of the above)
- confidence: low, medium, or high
- action_required: true or false
- extracted_message: cleaned up version of the message
- clarity: clear, unclear, or ambiguous
- needs_clarification: true if you can't understand what user wants

JSON only, no other text."""

            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 300
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=15) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result['choices'][0]['message']['content'].strip()

                        # Handle JSON extraction
                        if '```json' in content:
                            content = content.split('```json')[1].split('```')[0].strip()
                        elif '```' in content:
                            content = content.split('```')[1].split('```')[0].strip()

                        intent_data = json.loads(content)
                        logger.info(f"VO-004: Intent extracted: {intent_data}")
                        return intent_data
                    else:
                        error_text = await response.text()
                        logger.error(f"VO-004: Intent extraction error {response.status}: {error_text}")
                        return self._fallback_intent(transcribed_text)

        except Exception as e:
            logger.error(f"VO-004: Error extracting intent: {e}")
            return self._fallback_intent(transcribed_text)

    def _fallback_intent(self, transcribed_text: str) -> Dict[str, Any]:
        """
        Fallback intent extraction using simple keyword matching.
        VO-004: Handle unclear audio gracefully.
        """
        text = transcribed_text.strip().lower()

        # Simple keyword-based fallback
        if any(word in text for word in ['boss:', 'hey boss', 'ralph', 'ceo', 'team']):
            return {
                'intent_type': 'boss_message',
                'confidence': 'medium',
                'action_required': True,
                'extracted_message': transcribed_text,
                'clarity': 'clear',
                'needs_clarification': False
            }
        elif any(word in text for word in ['?', 'what', 'how', 'when', 'where', 'why', 'who']):
            return {
                'intent_type': 'question',
                'confidence': 'medium',
                'action_required': True,
                'extracted_message': transcribed_text,
                'clarity': 'clear',
                'needs_clarification': False
            }
        elif any(word in text for word in ['fix', 'build', 'create', 'add', 'update', 'change']):
            return {
                'intent_type': 'work_request',
                'confidence': 'medium',
                'action_required': True,
                'extracted_message': transcribed_text,
                'clarity': 'clear',
                'needs_clarification': False
            }
        else:
            # Default unclear
            return {
                'intent_type': 'unclear',
                'confidence': 'low',
                'action_required': False,
                'extracted_message': transcribed_text,
                'clarity': 'unclear',
                'needs_clarification': True
            }


def get_voice_handler(groq_api_key: str) -> VoiceHandler:
    """Factory function to get voice handler instance."""
    return VoiceHandler(groq_api_key)
