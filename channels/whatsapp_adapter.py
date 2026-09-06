"""
channels/whatsapp_adapter.py
WhatsApp Channel Adapter (Meta Cloud API / Twilio Sandbox).
Matches the Ministry of Finance's official communication channel.
"""

import os
import requests
from typing import Dict, Any, Optional
from channels.base import BaseChannelAdapter, IncomingMessage, OutgoingMessage


class WhatsAppAdapter(BaseChannelAdapter):
    def __init__(self, token: Optional[str] = None, phone_number_id: Optional[str] = None):
        self.token = token or os.getenv("WHATSAPP_TOKEN", "")
        self.phone_number_id = phone_number_id or os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
        self.api_url = f"https://graph.facebook.com/v20.0/{self.phone_number_id}/messages" if self.phone_number_id else ""

    def parse_incoming(self, raw_payload: Dict[str, Any]) -> Optional[IncomingMessage]:
        """
        Parses Meta WhatsApp Cloud API webhook JSON payload.
        """
        try:
            entry = raw_payload.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            messages = value.get("messages", [])
            if not messages:
                return None

            msg = messages[0]
            user_id = msg.get("from", "")
            msg_type = msg.get("type", "")

            # Case 1: Interactive button reply
            if msg_type == "interactive":
                interactive = msg.get("interactive", {})
                btn_reply = interactive.get("button_reply", {})
                return IncomingMessage(
                    user_id=user_id,
                    channel="whatsapp",
                    text=btn_reply.get("id", "")
                )

            # Case 2: Voice message
            if msg_type == "audio":
                return IncomingMessage(
                    user_id=user_id,
                    channel="whatsapp",
                    text="",
                    is_voice=True,
                    metadata={"audio_id": msg.get("audio", {}).get("id")}
                )

            # Case 3: Text message
            text = msg.get("text", {}).get("body", "")
            return IncomingMessage(
                user_id=user_id,
                channel="whatsapp",
                text=text,
                is_voice=False
            )
        except Exception as e:
            print(f"[WhatsApp] Error parsing payload: {e}")
            return None

    def send_response(self, outgoing: OutgoingMessage) -> bool:
        """
        Sends message to citizen via Meta WhatsApp Cloud API.
        """
        if not self.token or not self.phone_number_id or self.token == "your_whatsapp_token_here":
            print(f"[WhatsApp Mock] To {outgoing.user_id}: {outgoing.text[:80]}...")
            return True

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        # If interactive buttons provided (up to 3 buttons supported by Meta)
        if outgoing.buttons and len(outgoing.buttons) <= 3:
            payload = {
                "messaging_product": "whatsapp",
                "to": outgoing.user_id,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": outgoing.text[:1024]},
                    "action": {
                        "buttons": [
                            {
                                "type": "reply",
                                "reply": {"id": btn["id"][:256], "title": btn["label"][:20]}
                            }
                            for btn in outgoing.buttons
                        ]
                    }
                }
            }
        else:
            payload = {
                "messaging_product": "whatsapp",
                "to": outgoing.user_id,
                "type": "text",
                "text": {"body": outgoing.text}
            }

        try:
            res = requests.post(self.api_url, headers=headers, json=payload, timeout=10)
            return res.status_code == 200
        except Exception as e:
            print(f"[WhatsApp] Error sending message: {e}")
            return False
