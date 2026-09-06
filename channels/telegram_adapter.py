"""
channels/telegram_adapter.py
Telegram Bot Channel Adapter (100% Free Forever Channel).
Handles text, voice messages, inline keyboards, and webhook / polling dispatch.
"""

import os
import requests
from typing import Dict, Any, Optional, List
from channels.base import BaseChannelAdapter, IncomingMessage, OutgoingMessage


class TelegramAdapter(BaseChannelAdapter):
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.api_url = f"https://api.telegram.org/bot{self.token}" if self.token else ""

    def parse_incoming(self, update: Dict[str, Any]) -> Optional[IncomingMessage]:
        """
        Extracts user message or callback query from Telegram update JSON.
        """
        # Case 1: Callback Query (inline button click)
        if "callback_query" in update:
            cb = update["callback_query"]
            user_id = str(cb.get("from", {}).get("id", ""))
            data = cb.get("data", "")
            return IncomingMessage(
                user_id=user_id,
                channel="telegram",
                text=data,
                metadata={"callback_query_id": cb.get("id")}
            )

        # Case 2: Regular Message
        message = update.get("message")
        if not message:
            return None

        user_id = str(message.get("from", {}).get("id", ""))
        
        # Voice note
        if "voice" in message or "audio" in message:
            return IncomingMessage(
                user_id=user_id,
                channel="telegram",
                text="",
                is_voice=True,
                metadata={"file_id": message.get("voice", {}).get("file_id")}
            )

        # Text message
        text = message.get("text", "")
        return IncomingMessage(
            user_id=user_id,
            channel="telegram",
            text=text,
            is_voice=False
        )

    def send_response(self, outgoing: OutgoingMessage) -> bool:
        """
        Sends message to Telegram user with optional inline keyboard buttons or voice.
        """
        if not self.token or self.token == "your_telegram_bot_token_here":
            print(f"[Telegram Mock] To {outgoing.user_id}: {outgoing.text[:80]}...")
            return True

        # Send Voice if requested and audio file is available
        if outgoing.is_voice and outgoing.voice_audio_path and os.path.exists(outgoing.voice_audio_path):
            try:
                url = f"{self.api_url}/sendVoice"
                with open(outgoing.voice_audio_path, "rb") as audio:
                    files = {"voice": audio}
                    data = {"chat_id": outgoing.user_id, "caption": outgoing.text[:1024]}
                    res = requests.post(url, data=data, files=files, timeout=15)
                    return res.status_code == 200
            except Exception as e:
                print(f"[Telegram] Error sending voice: {e}. Falling back to text.")

        # Send Text Message
        payload: Dict[str, Any] = {
            "chat_id": outgoing.user_id,
            "text": outgoing.text,
            "parse_mode": "Markdown"
        }

        # Build inline keyboard buttons if available
        if outgoing.buttons:
            keyboard = []
            for btn in outgoing.buttons:
                keyboard.append([{"text": btn["label"], "callback_data": btn["id"]}])
            payload["reply_markup"] = {"inline_keyboard": keyboard}

        try:
            res = requests.post(f"{self.api_url}/sendMessage", json=payload, timeout=10)
            return res.status_code == 200
        except Exception as e:
            print(f"[Telegram] Error sending message: {e}")
            return False
