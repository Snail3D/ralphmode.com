import random

class PersonalityEngine:
    def __init__(self):
        self.intensity = 50  # Default mid-point

    def set_intensity(self, level: int):
        if not 0 <= level <= 100:
            raise ValueError("Intensity must be between 0 (serious) and 100 (full Ralph).")
        self.intensity = level

    def get_intensity(self) -> int:
        return self.intensity

    def process_message(self, text: str) -> str:
        """
        Adjusts the message based on the current intensity level.
        0: Serious/Professional
        100: Full Ralph (Chaotic/Energetic)
        """
        if self.intensity == 0:
            return self._format_serious(text)
        
        if self.intensity == 100:
            return self._format_full_ralph(text)

        # Mixed behavior based on probability
        if random.random() < (self.intensity / 100.0):
            return self._format_full_ralph(text)
        else:
            return self._format_serious(text)

    def _format_serious(self, text: str) -> str:
        return text.strip().capitalize()

    def _format_full_ralph(self, text: str) -> str:
        # "Full Ralph" implementation: All caps, aggressive punctuation, emojis
        ralphified = text.upper()
        if not ralphified.endswith(('!', '?')):
            ralphified += "!!!"
        ralphified += " 🤪🔥"
        return ralphified

# Singleton instance for integration
personality_service = PersonalityEngine()