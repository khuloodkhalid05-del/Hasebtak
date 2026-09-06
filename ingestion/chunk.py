"""
ingestion/chunk.py
Section-aware chunking for Citizen Budget documents.
Splits text respecting Arabic headings and paragraphs with ~300-500 tokens and 15% overlap.
"""

import re
from typing import List, Dict, Any


def chunk_section_text(
    text: str,
    section_title_ar: str,
    page: int,
    topic: str,
    chunk_size: int = 400,
    overlap: int = 60
) -> List[Dict[str, Any]]:
    """
    Splits narrative section text into overlapping chunks, maintaining section and page metadata.
    """
    words = text.split()
    chunks = []
    
    if len(words) <= chunk_size:
        return [{
            "id": f"chunk_p{page}_{abs(hash(text[:30])) % 10000}",
            "section_title_ar": section_title_ar,
            "page": page,
            "topic": topic,
            "text": text.strip()
        }]

    start = 0
    idx = 1
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        chunk_text = " ".join(chunk_words)

        chunks.append({
            "id": f"chunk_p{page}_{idx}",
            "section_title_ar": section_title_ar,
            "page": page,
            "topic": topic,
            "text": chunk_text.strip()
        })

        if end == len(words):
            break
        start += (chunk_size - overlap)
        idx += 1

    return chunks


def identify_section_topic(title: str, text: str) -> str:
    """
    Infers the high-level budget topic based on Arabic keywords.
    """
    title_lower = title.lower()
    text_lower = text.lower()
    content = f"{title_lower} {text_lower}"

    if any(k in content for k in ["صحة", "مستشفى", "تأمين صحي", "علاج", "دواء"]):
        return "الصحة"
    if any(k in content for k in ["تعليم", "مدارس", "جامعات", "معلم", "بحث علمي"]):
        return "التعليم"
    if any(k in content for k in ["تكافل", "كرامة", "تموين", "خبز", "دعم", "حماية اجتماعية"]):
        return "الدعم والحماية الاجتماعية"
    if any(k in content for k in ["أجور", "مرتبات", "حد أدنى", "عاملين"]):
        return "الأجور والعاملين"
    if any(k in content for k in ["ضرائب", "ضريبة", "قيمة مضافة", "فحص ضريبي"]):
        return "الضرائب"
    if any(k in content for k in ["دين", "فائض", "عجز", "سندات", "صكوك", "اقتراض"]):
        return "الدين والمؤشرات المالية"
    if any(k in content for k in ["شفافية", "مشاركة", "موازنة مفتوحة", "obs"]):
        return "الشفافية والمشاركة"
    
    return "الموازنة العامة"
