from typing import List, Optional
from datetime import datetime
from app.models.voice_message import VoiceMessageMetadata
from app.db.repositories.message_repository import MessageRepository

class VoiceDiscoveryService:
    def __init__(self, message_repo: MessageRepository):
        self.message_repo = message_repo

    async def discover_voice_messages(
        self, 
        user_id: str, 
        chat_id: Optional[str] = None, 
        since: Optional[datetime] = None
    ) -> List[VoiceMessageMetadata]:
        """
        Retrieves voice messages relevant to the user for the discovery phase.
        """
        criteria = {"recipient_id": user_id, "type": "voice"}
        if chat_id:
            criteria["chat_id"] = chat_id
        if since:
            criteria["since"] = since
            
        raw_messages = await self.message_repo.find_messages(criteria)
        
        return [
            VoiceMessageMetadata(
                id=msg["id"],
                chat_id=msg["chat_id"],
                sender_id=msg["sender_id"],
                url=msg["media_url"],
                duration=msg["metadata"]["duration"],
                mime_type=msg["metadata"]["mime_type"],
                waveform_data=msg["metadata"].get("waveform"),
                created_at=msg["created_at"]
            )
            for msg in raw_messages
        ]