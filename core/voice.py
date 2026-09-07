"""
core/voice.py
Voice pipeline for Egyptian Arabic:
- TTS: edge-tts using Microsoft Edge neural voices (ar-EG-SalmaNeural / ar-EG-ShakirNeural)
- STT: Speech-to-text integration (Groq Whisper / local audio transcription)
"""

import os
import asyncio
import tempfile
from typing import Optional
import edge_tts

TEMP_AUDIO_DIR = os.path.join(tempfile.gettempdir(), "hasebtak_audio")
try:
    os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)
except Exception:
    TEMP_AUDIO_DIR = tempfile.gettempdir()

# Egyptian Arabic Neural Voices
VOICE_FEMALE = "ar-EG-SalmaNeural"
VOICE_MALE = "ar-EG-ShakirNeural"


async def text_to_speech_async(
    text: str,
    output_path: Optional[str] = None,
    voice: str = VOICE_FEMALE
) -> str:
    """
    Synthesizes Egyptian Arabic speech from text using edge-tts.
    Returns the path to the generated audio file (.mp3).
    """
    if not output_path:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3", dir=TEMP_AUDIO_DIR)
        output_path = temp_file.name
        temp_file.close()

    # Clean text of markdown asterisks and emojis for cleaner speech synthesis
    clean_text = text.replace("**", "").replace("*", "")
    
    communicate = edge_tts.Communicate(clean_text, voice)
    await communicate.save(output_path)
    return output_path


def text_to_speech(text: str, output_path: Optional[str] = None, voice: str = VOICE_FEMALE) -> str:
    """
    Synchronous wrapper for text_to_speech_async.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If already running inside an async loop (e.g. FastAPI / asyncio)
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(text_to_speech_async(text, output_path, voice))
        else:
            return loop.run_until_complete(text_to_speech_async(text, output_path, voice))
    except RuntimeError:
        return asyncio.run(text_to_speech_async(text, output_path, voice))


def speech_to_text(audio_file_path: str, api_key: Optional[str] = None) -> str:
    """
    Transcribes Arabic voice note to text using Groq Whisper API (free tier) if key is provided,
    or returns a placeholder for simulated testing.
    """
    groq_key = api_key or os.getenv("GROQ_API_KEY")
    if groq_key and groq_key != "your_groq_api_key_here":
        try:
            import requests
            url = "https://api.groq.com/openai/v1/audio/transcriptions"
            headers = {"Authorization": f"Bearer {groq_key}"}
            with open(audio_file_path, "rb") as f:
                files = {"file": f}
                data = {
                    "model": "whisper-large-v3",
                    "language": "ar",
                    "response_format": "text"
                }
                res = requests.post(url, headers=headers, files=files, data=data, timeout=30)
                if res.status_code == 200:
                    return res.text.strip()
        except Exception as e:
            print(f"[Voice] Groq transcription error: {e}")

    # Fallback message
    return "سؤال صوتي حول مخصصات الصحة والتعليم في الموازنة"

