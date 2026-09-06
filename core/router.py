"""
core/router.py
Central orchestrator and intent router for Hasebtak.
Routes requests across:
- Pillar 1: اسأل عن فلوسك (Ask About Your Money - Grounded RAG + Guardrail)
- Pillar 2: هل تستحق؟ (Do You Qualify? - Deterministic Q-Tree)
- Pillar 3: نبض المواطن (Citizen's Pulse - Polling)
- User Profile onboarding & management
"""

import os
import re
from typing import Dict, Any, Optional

from core.grounding import GroundingEngine
from core.prompt import build_grounded_prompt
from core.guardrail import validate_response, SAFE_FALLBACK_AR
from core.llm import LLMClient
from core.eligibility import EligibilityEngine
from core.polls import PollEngine


class HasebtakCore:
    def __init__(self):
        self.grounding = GroundingEngine()
        self.llm = LLMClient()
        self.eligibility = EligibilityEngine()
        self.polls = PollEngine()
        # In-memory session profile storage (mapped to anonymous user channel hash/id)
        self.user_profiles: Dict[str, str] = {}

    def set_user_profile(self, user_id: str, profile: str):
        """Sets user profile: 'طالب', 'موظف', or 'صاحب مشروع'."""
        self.user_profiles[user_id] = profile

    def get_user_profile(self, user_id: str) -> str:
        return self.user_profiles.get(user_id, "مواطن")

    def detect_intent(self, text: str) -> str:
        """
        Classifies incoming message into intent:
        - 'menu': Start or Help commands
        - 'profile_select': User choosing their profile
        - 'pillar2_eligibility': Requesting social protection guide
        - 'pillar3_poll': Requesting Citizen's Pulse poll
        - 'pillar1_qa': Budget question (default)
        """
        clean = text.strip().lower()

        if clean in ["/start", "ابدأ", "البداية", "القائمة", "help", "/help", "مساعدة"]:
            return "menu"

        if any(p in clean for p in ["أنا طالب", "طالب", "انا طالب"]) and len(clean.split()) <= 3:
            return "set_profile_student"
        if any(p in clean for p in ["أنا موظف", "موظف", "انا موظف"]) and len(clean.split()) <= 3:
            return "set_profile_employee"
        if any(p in clean for p in ["صاحب مشروع", "أنا صاحب مشروع", "انا صاحب مشروع", "رائد أعمال"]) and len(clean.split()) <= 4:
            return "set_profile_business"

        if clean.startswith("/eligible") or any(k in clean for k in ["هل تستحق", "هل استحق", "هل أستحق", "دليل الحماية", "استحقاق", "إستحقاق", "شروط تكافل", "تكافل وكرامة", "بطاقة التموين"]):
            return "pillar2_eligibility"

        if clean.startswith("/poll") or any(k in clean for k in ["نبض المواطن", "استطلاع", "استبيان", "تصويت", "شارك برأيك"]):
            return "pillar3_poll"

        return "pillar1_qa"

    def answer_budget_question(self, user_query: str, user_profile: str = "مواطن") -> Dict[str, Any]:
        """
        The core grounded Q&A loop:
        1. Lookup verified figures in Facts Ledger
        2. Retrieve narrative context from ChromaDB
        3. Build strict grounded prompt with Egyptian Arabic tone
        4. Generate response via LLM
        5. Numeric Guardrail validation: block ungrounded figures
        """
        # Step 1 & 2: Grounding retrieval
        grounded_data = self.grounding.get_grounded_context(user_query, profile=user_profile)
        facts = grounded_data.get("facts", [])
        chunks = grounded_data.get("chunks", [])

        # If no relevant facts or chunks matched at all, give safe fallback immediately
        if not facts and not chunks:
            return {
                "reply": SAFE_FALLBACK_AR,
                "is_grounded": True,
                "guardrail_passed": True,
                "sources": ["mof.gov.eg"]
            }

        # Step 3: Build Grounded Prompt
        prompt = build_grounded_prompt(facts, chunks, user_query, user_profile)

        # Step 4: Generate Draft Response
        raw_answer = self.llm.generate(prompt)

        # Step 5: Numeric Guardrail Check
        is_safe, final_answer, ungrounded_numbers = validate_response(raw_answer, facts, chunks)

        sources = []
        for f in facts:
            if "source" in f:
                sources.append(f["source"])
        for c in chunks:
            if "section_title_ar" in c:
                sources.append(f"{c['section_title_ar']} (ص {c.get('page', '')})")

        return {
            "reply": final_answer,
            "raw_answer": raw_answer,
            "is_grounded": is_safe,
            "guardrail_passed": is_safe,
            "blocked_numbers": ungrounded_numbers,
            "sources": list(set(sources))
        }

    def process_message(self, user_id: str, text: str) -> Dict[str, Any]:
        """
        Primary entrypoint for any channel (Telegram, WhatsApp, Web API).
        """
        intent = self.detect_intent(text)
        current_profile = self.get_user_profile(user_id)

        if intent == "menu":
            menu_text = (
                "👋 أهلاً بك في منصة **'حسبتك'** — مستشارك الرقمي لموازنة المواطن 2026/2027 🇪🇬\n\n"
                "أنا هنا عشان أحول أرقام الموازنة لحديث بسيط ومفهوم من غير تعقيد وبأرقام رسمية مؤكدة 100%.\n\n"
                "اختر من القائمة أو اسألني مباشرة:\n"
                "1️⃣ **اسأل عن فلوسك**: اسألني عن أي قطاع (الصحة، التعليم، المرتبات، الدعم، الضرائب، سند المواطن...)\n"
                "2️⃣ **هل تستحق؟**: دليل برامج الحماية والدعم وكيفية التقديم الرسمي (/eligible)\n"
                "3️⃣ **نبض المواطن**: استطلاع الرأي الأسبوعي لإيصال صوتك لوزارة المالية (/poll)\n\n"
                "💡 *لتخصيص الإجابات حسب فئتك، اضغط أو اكتب:*\n"
                "- 'أنا طالب' 🎓\n"
                "- 'أنا موظف' 💼\n"
                "- 'أنا صاحب مشروع' 🏭"
            )
            return {"type": "text", "reply": menu_text, "intent": intent}

        if intent == "set_profile_student":
            self.set_user_profile(user_id, "طالب")
            return {
                "type": "text",
                "reply": "تمام يا بطل! 🎓 تم ضبط فئتك: **طالب**. هركز في إجاباتي على دعم التأمين الصحي للطلبة، التغذية المدرسية، واشتراكات المترو والقطارات.",
                "intent": intent
            }

        if intent == "set_profile_employee":
            self.set_user_profile(user_id, "موظف")
            return {
                "type": "text",
                "reply": "أهلاً بحضرتك! 💼 تم ضبط فئتك: **موظف**. هركز في إجاباتي على بنود الأجور، الحد الأدنى (8000 ج)، حزمة يوليو 2026، والعلاوات.",
                "intent": intent
            }

        if intent == "set_profile_business":
            self.set_user_profile(user_id, "صاحب مشروع")
            return {
                "type": "text",
                "reply": "أهلاً بك يا فندم! 🏭 تم ضبط فئتك: **صاحب مشروع**. هركز في إجاباتي على حوافز المشروعات الصغيرة، المنظومة الضريبية المبسطة، وتسهيلات الإنتاج.",
                "intent": intent
            }

        if intent == "pillar2_eligibility":
            reply_text = self.eligibility.format_node_reply("start")
            options = self.eligibility.get_node("start").get("options", [])
            return {
                "type": "interactive",
                "reply": reply_text,
                "options": options,
                "intent": intent
            }

        if intent == "pillar3_poll":
            poll = self.polls.get_active_poll()
            if not poll:
                return {"type": "text", "reply": "لا يوجد استطلاع نشط حالياً.", "intent": intent}

            stats = self.polls.get_poll_stats(poll["id"])
            poll_text = (
                f"🗳️ **نبض المواطن — استطلاع الأسبوع**\n"
                f"*{poll['question_ar']}*\n\n"
                f"📌 الموضوع: {poll['topic']}\n"
                f"👥 إجمالي المشاركات حتى الآن: {stats['total_votes']}\n\n"
                f"اختر رقم إجابتك أو اضغط على الخيار للتصويت:"
            )
            return {
                "type": "poll",
                "poll_id": poll["id"],
                "reply": poll_text,
                "options": poll["options"],
                "stats": stats,
                "intent": intent
            }

        # Pillar 1 Q&A
        qa_result = self.answer_budget_question(text, current_profile)
        return {
            "type": "text",
            "reply": qa_result["reply"],
            "guardrail_passed": qa_result["guardrail_passed"],
            "sources": qa_result.get("sources", []),
            "intent": "pillar1_qa"
        }
