"""
core/guardrail.py
Layer ④ — The Deterministic Numeric Guardrail.
Extracts all numbers from the LLM's response and verifies each against injected FACTS and CONTEXT.
Blocks ungrounded figures to guarantee zero hallucinated numbers.
"""

import re
import json
import logging
from typing import List, Dict, Any, Set, Tuple

logger = logging.getLogger("hasebtak.guardrail")

SAFE_FALLBACK_AR = (
    "المعلومة دي مش متأكد منها حاليًا في موازنة المواطن، "
    "بس تقدر تلاقي تفاصيل الموازنة الرسمية على موقع وزارة المالية mof.gov.eg 🙏"
)

# Standard numbers that are allowed as general conversational references (e.g., years, small counts)
ALLOWED_GENERAL_NUMBERS = {
    "2026", "2027", "2025", "2024", "2023",
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
    "18" # 18 months citizen bond
}


def normalize_digit_string(s: str) -> str:
    """Converts Eastern Arabic digits to Western Arabic (Latin) digits and removes commas."""
    arabic_indic = "٠١٢٣٤٥٦٧٨٩"
    latin = "0123456789"
    trans = str.maketrans(arabic_indic, latin)
    s = s.translate(trans)
    return s.replace(",", "")


def extract_numbers_from_text(text: str) -> Set[str]:
    """
    Extracts all numeric representations from text:
    - Floats (e.g. 862.9, 4.2, 17.75)
    - Integers (e.g. 8000, 100, 60)
    - Formatted numbers (e.g. 1,229.7)
    """
    if not text:
        return set()

    normalized = normalize_digit_string(text)
    # Find all sequences of digits, optionally including decimals
    # Matches patterns like 862.9, 1229.7, 5000, 14, 5
    raw_matches = re.findall(r'\b\d+(?:\.\d+)?\b', normalized)

    numbers = set()
    for m in raw_matches:
        # Standardize float representations: "862.90" -> "862.9", "8000.0" -> "8000"
        try:
            val = float(m)
            if val.is_integer():
                numbers.add(str(int(val)))
            else:
                numbers.add(str(val))
        except ValueError:
            numbers.add(m)

    return numbers


def extract_numbers_from_source(
    facts: List[Dict[str, Any]],
    chunks: List[Dict[str, Any]]
) -> Set[str]:
    """
    Extracts all valid grounded numbers from injected facts and chunks.
    """
    source_text = json.dumps(facts, ensure_ascii=False) if facts else ""
    for c in chunks:
        source_text += " " + c.get("text", "")
        source_text += " " + str(c.get("page", ""))

    return extract_numbers_from_text(source_text)


def validate_response(
    answer: str,
    facts: List[Dict[str, Any]],
    chunks: List[Dict[str, Any]]
) -> Tuple[bool, str, List[str]]:
    """
    Numeric Guardrail validator:
    - Extracts all numbers in answer.
    - Compares each against the source numbers.
    - If any number is not grounded and not an allowed general number, blocks the answer.
    
    Returns:
        (is_safe, final_answer, ungrounded_numbers)
    """
    answer_numbers = extract_numbers_from_text(answer)
    source_numbers = extract_numbers_from_source(facts, chunks)

    # Union with allowed general numbers
    valid_numbers = source_numbers.union(ALLOWED_GENERAL_NUMBERS)

    ungrounded = []
    for num in answer_numbers:
        if num not in valid_numbers:
            ungrounded.append(num)

    if ungrounded:
        logger.warning(
            f"[Guardrail BLOCK] Ungrounded numbers detected in response: {ungrounded}. "
            f"Answer blocked to prevent hallucination."
        )
        return False, SAFE_FALLBACK_AR, ungrounded

    return True, answer, []
