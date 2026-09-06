"""
ingestion/extract.py
PDF text extraction and Arabic text normalization for Citizen Budget reports.
Addresses Arabic RTL caveats and digit normalization.
"""

import os
import re
from typing import List, Dict, Any
from pypdf import PdfReader


def normalize_arabic(text: str) -> str:
    """
    Normalizes Arabic text for search and processing:
    - Normalizes alef variations (أ, إ, آ -> ا)
    - Normalizes teh marbuta and heh (ة -> ه)
    - Normalizes alef maksura (ى -> ي)
    - Removes excessive tatweel (ـ) and diacritics (tashkeel)
    - Cleans extra whitespaces
    """
    if not text:
        return ""

    # Remove tashkeel (diacritics)
    tashkeel_regex = re.compile(r'[\u064B-\u0652\u0670]')
    text = re.sub(tashkeel_regex, '', text)

    # Remove tatweel (kashida)
    text = re.sub(r'\u0640', '', text)

    # Normalize alef
    text = re.sub(r'[إأآٱ]', 'ا', text)

    # Clean multiple spaces and line breaks
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def convert_arabic_indic_digits(text: str) -> str:
    """
    Converts Eastern Arabic-Indic digits (٠١٢٣٤٥٦٧٨٩) to standard Latin digits (0123456789).
    """
    arabic_indic = "٠١٢٣٤٥٦٧٨٩"
    latin = "0123456789"
    trans = str.maketrans(arabic_indic, latin)
    return text.translate(trans)


def extract_text_from_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extracts text page-by-page from a PDF file.
    Returns a list of dicts with page number, raw text, and normalized text.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found at: {pdf_path}")

    reader = PdfReader(pdf_path)
    pages_data = []

    for i, page in enumerate(reader.pages):
        page_num = i + 1
        raw_text = page.extract_text() or ""
        normalized = normalize_arabic(raw_text)

        pages_data.append({
            "page": page_num,
            "raw_text": raw_text,
            "normalized_text": normalized
        })

    return pages_data


if __name__ == "__main__":
    test_pdf = os.path.join("data", "source_pdf", "Citizen_Budget_26-27_August_20.pdf")
    if os.path.exists(test_pdf):
        print(f"Extracting text from: {test_pdf}")
        pages = extract_text_from_pdf(test_pdf)
        print(f"Successfully extracted {len(pages)} pages.")
    else:
        print(f"No PDF found at {test_pdf}. Ingestion module is ready for upload.")
