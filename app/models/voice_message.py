from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class VoiceMessageMetadata(BaseModel):
    id: str
    chat_id: str
    sender_id: str
    url: str
    duration: float
    mime_type: str
    waveform_data: Optional[list[int]] = None
    created_at: datetime