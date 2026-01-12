class RalphAnnouncer:
    """
    Handles the announcement of PRD changes in the character of Ralph.
    """
    
    def __init__(self, notification_gateway):
        self.gateway = notification_gateway
        self.character_prefix = "[RALPH]: "

    def announce(self, change_data):
        """
        Formats the PRD change into Ralph's character voice and sends it.
        """
        message = self._format_character_message(change_data)
        self.gateway.broadcast(message)

    def _format_character_message(self, data):
        # Ralph is enthusiastic and slightly dramatic about documentation
        return (
            f"{self.character_prefix}Gather round, everyone! Big news from the product tower!\n"
            f"We are updating the PRD for '{data['feature']}'!\n"
            f"Reason: {data['reason']}\n"
            f"Let's make it happen!"
        )