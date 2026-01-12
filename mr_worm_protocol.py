class MrWormProtocol:
    """
    Handles the obedience logic and tone adjustment for the Mr. Worm system.
    """
    def __init__(self, boss_id="BOSS"):
        self.boss_id = boss_id
        self.tone = "obedient"
        self.tone_map = {
            "formal": ["formal", "professional"],
            "casual": ["casual", "chill"],
            "obedient": ["obedient", "default"]
        }

    def _check_tone_request(self, text):
        text = text.lower()
        for tone, keywords in self.tone_map.items():
            if any(k in text for k in keywords):
                return tone
        return None

    def _format_response(self, text):
        if self.tone == "formal":
            return f"Understood. {text}"
        elif self.tone == "casual":
            return f"Gotcha. {text}"
        return f"Yes, sir. {text}"

    def handle_command(self, user_id, command):
        if user_id != self.boss_id:
            return "Access Denied: You are not the Boss."

        # Check for tone adjustment
        requested_tone = self._check_tone_request(command)
        if requested_tone:
            self.tone = requested_tone
            return self._format_response(f"Tone set to {self.tone}.")

        # Default obedience
        return self._format_response("Executing command immediately.")