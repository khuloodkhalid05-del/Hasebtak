"""
core/grounding.py
Grounding Layer (Layers ① and ②):
- Layer ①: Hand-verified Facts Ledger lookup (exact numbers & citations)
- Layer ②: ChromaDB Vector Store retrieval for narrative context
"""

import os
import json
import re
from typing import List, Dict, Any, Optional

FACTS_LEDGER_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "facts_ledger.json")
CHUNKS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "report_narrative_chunks.json")
CHROMA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_db")


class GroundingEngine:
    def __init__(self, ledger_path: str = FACTS_LEDGER_PATH, chroma_dir: str = CHROMA_DIR):
        self.ledger_path = ledger_path
        self.chroma_dir = chroma_dir
        self.facts: List[Dict[str, Any]] = self._load_ledger()
        self.narrative_chunks: List[Dict[str, Any]] = self._load_chunks()
        self.chroma_client = None
        self.collection = None
        self._init_chroma()

    def _load_ledger(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.ledger_path):
            return []
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_chunks(self) -> List[Dict[str, Any]]:
        if not os.path.exists(CHUNKS_PATH):
            return []
        with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def _init_chroma(self):
        try:
            import chromadb
            if os.path.exists(self.chroma_dir) and os.listdir(self.chroma_dir):
                self.chroma_client = chromadb.PersistentClient(path=self.chroma_dir)
                self.collection = self.chroma_client.get_or_create_collection("hasebtak_narratives")
        except Exception:
            self.collection = None

    def lookup_facts(self, query: str, profile: Optional[str] = None, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Matches user query against verified Facts Ledger keywords, topics, and labels.
        Applies profile-aware weighting.
        """
        query_normalized = query.lower()
        # Remove common Arabic punctuation and normalize
        clean_query = re.sub(r'[؟!.,:]', '', query_normalized)
        words = set(clean_query.split())

        scored_facts = []

        # Profile affinities
        profile_keywords = {
            "طالب": ["طلاب", "طلبة", "مدارس", "تغذية", "تعليم", "تأمين صحي للطلبة", "اشتراكات"],
            "موظف": ["أجور", "مرتبات", "حد أدنى", "علاوة", "العاملين بالدولة", "زيادة المرتبات"],
            "صاحب مشروع": ["مشروعات", "ضرائب", "تيسيرات ضريبية", "سند المواطن", "تسهيلات", "تصدير", "صناعة"],
            "مواطن": ["دعم", "تموين", "خبز", "كهرباء", "معاش", "تكافل وكرامة", "سند المواطن"]
        }

        user_pref_keywords = []
        if profile:
            for p_key, kw_list in profile_keywords.items():
                if p_key in profile:
                    user_pref_keywords.extend(kw_list)
            
            # Sub-category extra affinities
            if "صحة" in profile or "طبيب" in profile or "علاج" in profile:
                user_pref_keywords.extend(["صحة", "أطباء", "مستشفيات", "علاج", "شراء موحد", "تأمين صحي"])
            if "تعليم" in profile or "معلم" in profile or "مدرس" in profile:
                user_pref_keywords.extend(["تعليم", "مدارس", "معلم", "مدرسين", "تغذية"])
            if "معاش" in profile or "متقاعد" in profile:
                user_pref_keywords.extend(["معاش", "تكافل وكرامة", "حماية اجتماعية", "رمضان", "غير القادرين"])
            if "تصدير" in profile or "صناع" in profile:
                user_pref_keywords.extend(["تصدير", "رد الأعباء", "سيارات", "إنتاج"])

        for fact in self.facts:
            score = 0
            keywords = fact.get("keywords", [])
            topic = fact.get("topic", "")
            label = fact.get("label_ar", "")
            
            # Check direct phrase match
            for kw in keywords:
                if kw in query_normalized:
                    score += 5
                elif any(w in kw for w in words if len(w) > 2):
                    score += 2

            if topic in query_normalized:
                score += 4

            if any(w in label for w in words if len(w) > 2):
                score += 2

            # Profile affinity bonus
            if user_pref_keywords:
                if any(pref_kw in keywords for pref_kw in user_pref_keywords):
                    score += 1.5

            if score > 0:
                scored_facts.append((score, fact))

        # Sort descending by score
        scored_facts.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored_facts[:max_results]]

    def search_chunks(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieves top-k narrative chunks from ChromaDB.
        """
        if not self.collection:
            # Fallback to pure in-memory keyword matching from JSON
            if not self.narrative_chunks:
                return []
            q_words = set(re.sub(r'[؟!.,:]', '', query.lower()).split())
            scored = []
            for c in self.narrative_chunks:
                text = c.get("text", "").lower()
                title = c.get("section_title_ar", "").lower()
                topic = c.get("topic", "").lower()
                score = sum(1 for w in q_words if w in text or w in title or w in topic)
                if score > 0:
                    scored.append((score, c))
            scored.sort(key=lambda x: x[0], reverse=True)
            return [item[1] for item in scored[:k]]

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=min(k, self.collection.count() or 1)
            )

            chunks = []
            if results and results.get("documents") and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                    chunks.append({
                        "text": doc,
                        "section_title_ar": metadata.get("section_title_ar", ""),
                        "page": metadata.get("page", 1),
                        "topic": metadata.get("topic", "")
                    })
            return chunks
        except Exception as e:
            return []

    def get_grounded_context(self, query: str, profile: Optional[str] = None) -> Dict[str, Any]:
        """
        Consolidates Layer ① Facts and Layer ② Vector chunks into a single grounded package.
        """
        facts = self.lookup_facts(query, profile=profile, max_results=4)
        chunks = self.search_chunks(query, k=3)
        return {
            "facts": facts,
            "chunks": chunks
        }
