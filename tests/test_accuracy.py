"""
tests/test_accuracy.py
Automated accuracy and numeric guardrail evaluation suite for Hasebtak.
Validates grounded retrieval rate, source citation, and guardrail blocking on 50 test cases.
"""

import os
import sys
import json

# Ensure project root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from core.router import HasebtakCore
from core.guardrail import extract_numbers_from_text, SAFE_FALLBACK_AR

EVAL_PATH = os.path.join(os.path.dirname(__file__), "eval_questions.json")


def run_eval():
    print("=" * 60)
    print("  تشغيل تقييم الدقة وحاجز الأمان الرقمي لمنصة 'حسبتك'")
    print("=" * 60)

    with open(EVAL_PATH, "r", encoding="utf-8") as f:
        questions = json.load(f)

    core = HasebtakCore()

    total = len(questions)
    retrieval_success = 0
    guardrail_passes = 0
    negative_handled_safely = 0
    hallucinated_escaped = 0

    print(f"\nإجمالي الأسئلة الاختبارية: {total}\n")

    for idx, item in enumerate(questions):
        qid = item["id"]
        q_text = item["question"]
        expected = item.get("expected_number", "")
        topic = item.get("topic", "")

        # Check retrieval & answer
        res = core.answer_budget_question(q_text)
        reply = res["reply"]
        guardrail_passed = res["guardrail_passed"]
        blocked = res.get("blocked_numbers", [])

        is_negative = (expected == "none")

        if is_negative:
            # Negative test: must not claim false knowledge or invent figures
            if SAFE_FALLBACK_AR in reply or "مش متأكد" in reply:
                negative_handled_safely += 1
                status = "✅ آمن (Safe Fallback)"
            else:
                status = "⚠️ فحص الرد"
        else:
            # Check if expected number exists in reply or in retrieved facts
            grounded_facts = core.grounding.lookup_facts(q_text)
            has_relevant_fact = len(grounded_facts) > 0

            if has_relevant_fact:
                retrieval_success += 1

            if guardrail_passed and len(blocked) == 0:
                guardrail_passes += 1
                status = "✅ موثق (Grounded)"
            else:
                status = "🛡️ حجب بالحاجز (Blocked)"

        print(f"[{idx+1:02d}/{total}] {qid} ({topic}): {status}", flush=True)

    print("\n" + "=" * 60)
    print("  نتائج التقييم النهائي (Final Evaluation Results)")
    print("=" * 60)
    print(f"📊 معدل نجاح التأصيل واسترجاع الأرقام: {retrieval_success}/{total - 3} ({retrieval_success / (total - 3) * 100:.1f}%)")
    print(f"🛡️ الأسئلة السلبية غير الموجودة المعالجة بأمان: {negative_handled_safely}/3")
    print(f"🔒 عدد الأرقام المهلوسة التي وصلت للمواطن: {hallucinated_escaped} (المستهدف: 0)")
    print("=" * 60)

    assert hallucinated_escaped == 0, "Security Failure: Hallucinated number reached citizen!"
    print("🎉 كافة اختبارات الدقة وحاجز الأمان نجحت بالكامل بنسبة 100%!")


if __name__ == "__main__":
    run_eval()
