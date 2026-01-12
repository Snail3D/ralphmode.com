from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from datetime import datetime
from app.services.voice_discovery import VoiceDiscoveryService
from app.models.voice_message import VoiceMessageMetadata
from app.db.session import get_db
from app.db.repositories.message_repository import MessageRepository

router = APIRouter()

@router.get("/voice-messages", response_model=List[VoiceMessageMetadata])
async def get_voice_messages(
    chat_id: Optional[str] = Query(None),
    since: Optional[datetime] = Query(None),
    current_user_id: str = "mock_user_id", # In real app, from auth dependency
    db_session = Depends(get_db)
):
    repo = MessageRepository(db_session)
    service = VoiceDiscoveryService(repo)
    
    messages = await service.discover_voice_messages(
        user_id=current_user_id,
        chat_id=chat_id,
        since=since
    )
    return messages