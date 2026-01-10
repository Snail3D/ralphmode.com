#!/usr/bin/env python3
"""
Voice Handler - VO-002: Voice Message Transcription
Handles voice messages, transcribes them using Groq's Whisper API, and processes intent.
"""

import os
import logging
import tempfile
from typing import Optional, Tuple
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


class VoiceHandler:
    """Handle voice message transcription and processing."""

    def __init__(self, groq_api_key: str):
        """Initialize voice handler with Groq API key."""
        self.groq_api_key = groq_api_key
        self.supported_formats = ['.ogg', '.mp3', '.m4a', '.wav', '.opus']

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

    def extract_intent(self, transcribed_text: str) -> Tuple[str, Optional[str]]:
        """
        Extract intent from transcribed text.

        Args:
            transcribed_text: Text from voice transcription

        Returns:
            Tuple of (intent_type, extracted_message)
            Intent types: 'boss_message', 'command', 'feedback', 'general'
        """
        text = transcribed_text.strip().lower()

        # Check for boss/CEO commands
        boss_keywords = ['boss:', 'hey boss', 'ralph', 'mr. worms', 'ceo']
        if any(keyword in text for keyword in boss_keywords):
            # Extract the actual message after the keyword
            for keyword in boss_keywords:
                if keyword in text:
                    parts = text.split(keyword, 1)
                    if len(parts) > 1:
                        return ('boss_message', parts[1].strip())
            return ('boss_message', transcribed_text)

        # Check for commands
        command_keywords = ['/start', '/help', '/status', '/stop', '/feedback']
        for cmd in command_keywords:
            if text.startswith(cmd):
                return ('command', transcribed_text)

        # Check for feedback intent
        feedback_keywords = ['feedback', 'suggestion', 'bug report', 'feature request']
        if any(keyword in text for keyword in feedback_keywords):
            return ('feedback', transcribed_text)

        # Default to general message
        return ('general', transcribed_text)


def get_voice_handler(groq_api_key: str) -> VoiceHandler:
    """Factory function to get voice handler instance."""
    return VoiceHandler(groq_api_key)
