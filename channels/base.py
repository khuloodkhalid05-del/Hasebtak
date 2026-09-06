"""
channels/base.py
Neutral message interface and ChannelAdapter base class.
Decouples messaging platforms (Telegram, WhatsApp, Web) from the Hasebtak core engine.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel


class IncomingMessage(BaseModel):
    user_id: str
    channel: str  # 'telegram', 'whatsapp', 'web'
    text: str
    is_voice: bool = False
    voice_audio_path: Optional[str] = None
    metadata: Dict[str, Any] = {}


class OutgoingMessage(BaseModel):
    user_id: str
    text: str
    is_voice: bool = False
    voice_audio_path: Optional[str] = None
    buttons: Optional[List[Dict[str, str]]] = None  # [{'id': '...', 'label': '...'}]
    metadata: Dict[str, Any] = {}


class BaseChannelAdapter(ABC):
    @abstractmethod
    def parse_incoming(self, raw_payload: Dict[str, Any]) -> Optional[IncomingMessage]:
        """Parses platform-specific webhook payload into a standardized IncomingMessage."""
        pass

    @abstractmethod
    def send_response(self, outgoing: OutgoingMessage) -> bool:
        """Sends formatted message back to the user on that channel."""
        pass
