"""
core/llm.py
LLM Client managing Google Gemini free tier with automatic model fallback.
Uses the new `google.genai` SDK (google-genai >= 1.0.0).
"""

import os
import logging
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("hasebtak.llm")

# Candidate models in order of preference (Gemini 3.x — updated Sep 2026)
# gemini-3.8-flash     : الأحدث والأسرع — الأولوية الأولى
# gemini-3.7-flash     : fallback ثاني
# gemini-3.6-flash     : fallback ثالث
# gemini-3.5-flash-lite: الأكثر توفراً — آخر خط دفاع
# Candidate models in order of preference (prioritizing fastest and highly available models)
GEMINI_MODELS = [
    "gemini-3.5-flash-lite",   # Instant (~0.8s) & highly available
    "gemini-3.6-flash",        # Excellent quality & fast (~1.8s)
    "gemini-3.8-flash",        # Latest capability model
    "gemini-3.7-flash",        # Fallback
]

SAFE_FALLBACK = (
    "أهلاً بيك! أنا 'حسبتك' المساعد الرقمي لموازنة المواطن. "
    "يرجى ضبط مفتاح GEMINI_API_KEY في ملف .env للتوليد الحي، "
    "ولكن يمكنك تصفح كافة أرقام الموازنة المؤكدة والاستطلاعات حالياً."
)

ERROR_FALLBACK = (
    "المعلومة دي مش متأكد منها حاليًا، "
    "بس تقدر تلاقي كل تفاصيل الموازنة الرسمية كاملة على موقع وزارة المالية mof.gov.eg 🙏"
)


class LLMClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.client = None
        self.client_ready = False
        self._init_client()

    def _init_client(self):
        """Initialize the new google.genai client."""
        if self.api_key and self.api_key not in ("", "your_gemini_api_key_here"):
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                self.client_ready = True
                logger.info("Gemini client initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                self.client_ready = False
        else:
            logger.warning("No valid GEMINI_API_KEY found. LLM calls will use fallback responses.")
            self.client_ready = False

    def generate(self, prompt: str, temperature: float = 0.2) -> str:
        """
        Generates grounded response using Gemini free tier with automatic model fallback.
        Low temperature (0.2) ensures strict factual consistency.
        """
        if not self.client_ready:
            return SAFE_FALLBACK

        last_error = None
        for model_name in GEMINI_MODELS:
            try:
                from google.genai import types
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=temperature,
                        max_output_tokens=4096,
                    ),
                )
                if response and response.text:
                    logger.info(f"Response generated successfully via {model_name}.")
                    return response.text.strip()
            except Exception as e:
                last_error = e
                logger.warning(f"Model {model_name} failed: {e}. Trying next fallback model...")
                continue

        logger.error(f"All Gemini models failed. Last error: {last_error}")
        return ERROR_FALLBACK
