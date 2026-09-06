"""
core/llm.py
LLM Client managing Google Gemini free tier with automatic model fallback.
"""

import os
import logging
from typing import Optional
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

logger = logging.getLogger("hasebtak.llm")

# Candidate models in order of preference
GEMINI_MODELS = [
    "gemini-3.6-flash",
    "gemini-flash-latest",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-3.7-flash"
]


class LLMClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.client_ready = False
        self._init_client()

    def _init_client(self):
        if self.api_key and self.api_key != "your_gemini_api_key_here":
            try:
                genai.configure(api_key=self.api_key)
                self.client_ready = True
            except Exception as e:
                logger.error(f"Failed to configure Gemini client: {e}")
                self.client_ready = False
        else:
            logger.warning("No valid GEMINI_API_KEY found. LLM calls will use fallback responses.")
            self.client_ready = False

    def generate(self, prompt: str, temperature: float = 0.2) -> str:
        """
        Generates grounded response using Gemini Flash free tier with automatic model fallback.
        Low temperature (0.2) ensures strict factual consistency.
        """
        if not self.client_ready:
            return (
                "أهلاً بيك! أنا 'حسبتك' المساعد الرقمي لموازنة المواطن. "
                "يرجى ضبط مفتاح API في ملف .env للتوليد الحي، "
                "ولكن يمكنك تصفح كافة أرقام الموازنة المؤكدة والاستطلاعات حالياً."
            )

        last_error = None
        for model_name in GEMINI_MODELS:
            try:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    generation_config={
                        "temperature": temperature,
                        "max_output_tokens": 4096,
                    }
                )
                response = model.generate_content(prompt)
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                last_error = e
                logger.warning(f"Model {model_name} failed: {e}. Trying next fallback model...")
                continue

        logger.error(f"All Gemini models failed. Last error: {last_error}")
        return "المعلومة دي مش متأكد منها حاليًا، بس تقدر تلاقي كل تفاصيل الموازنة الرسمية كاملة على موقع وزارة المالية mof.gov.eg 🙏"
