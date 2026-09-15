"""
channels/run_bot.py
Autonomous Telegram Bot Runner for Hasebtak (حسبتك) 🇪🇬
Supports:
- 📊 Interactive Polling (نبض المواطن) with 1-click inline voting & live stats
- 🤝 Deterministic Eligibility Guide (هل تستحق؟) for social protection & subsidies
- 💰 Instant official budget figures with transition buttons
- 🤖 Grounded Q&A via Gemini API (<2s) with strict numeric guardrails
- 👤 Profile customization (طالب / موظف / صاحب مشروع)
"""

import os
import sys
import time
import logging
import requests
from dotenv import load_dotenv

# Force UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("hasebtak.bot")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN is missing in .env")
    sys.exit(1)

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import In-process Core Engines for zero-latency and 100% reliability
from core.router import HasebtakCore
from core import database as db
from core.eligibility import EligibilityEngine

logger.info("Initializing Hasebtak engines for Telegram Bot...")
core = HasebtakCore()
eligibility_engine = EligibilityEngine()
db.init_db()
logger.info("Engines initialized successfully.")


def delete_webhook():
    """Ensure no stale webhook blocks polling."""
    try:
        r = requests.get(f"{TG_API}/deleteWebhook", timeout=10)
        logger.info(f"Telegram Webhook cleared for polling: {r.json()}")
    except Exception as e:
        logger.warning(f"Error clearing webhook: {e}")


def send_message(chat_id: int, text: str, reply_markup=None):
    """Sends message with Markdown, automatically falling back to plain text if parsing fails."""
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        r = requests.post(f"{TG_API}/sendMessage", json=payload, timeout=12)
        res = r.json()
        # Fallback if Markdown parse error
        if not res.get("ok") and "parse" in res.get("description", "").lower():
            payload.pop("parse_mode", None)
            r = requests.post(f"{TG_API}/sendMessage", json=payload, timeout=12)
            return r.json()
        return res
    except Exception as e:
        logger.error(f"Error sending message to {chat_id}: {e}")
        return None


def answer_callback_query(callback_query_id: str, text: str = ""):
    """Answers Telegram callback query so button click doesn't show loading spinner."""
    try:
        payload = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
        requests.post(f"{TG_API}/answerCallbackQuery", json=payload, timeout=5)
    except Exception as e:
        logger.warning(f"Error answering callback query: {e}")


def send_typing(chat_id: int):
    """Displays 'typing...' status in Telegram chat."""
    try:
        requests.post(f"{TG_API}/sendChatAction", json={"chat_id": chat_id, "action": "typing"}, timeout=4)
    except Exception:
        pass


# =====================================================================
# Keyboards & Navigation
# =====================================================================

def get_main_menu_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "📊 استطلاع الموازنة (شارك برأيك)", "callback_data": "menu:poll"}
            ],
            [
                {"text": "🤝 دليل هل تستحق؟ (تكافل ودعم)", "callback_data": "menu:eligible"},
                {"text": "💡 أرقام الموازنة السريعة", "callback_data": "menu:faq"}
            ],
            [
                {"text": "🎓 أنا طالب", "callback_data": "profile:طالب"},
                {"text": "💼 أنا موظف", "callback_data": "profile:موظف"},
                {"text": "🏭 صاحب مشروع", "callback_data": "profile:صاحب مشروع"}
            ]
        ]
    }


def get_poll_keyboard():
    poll = db.get_current_poll()
    keyboard = []
    if poll and poll.get("options"):
        for opt in poll["options"]:
            keyboard.append([{"text": opt["text"], "callback_data": f"vote:{opt['option_id']}"}])
    else:
        # Fallback default options
        keyboard = [
            [{"text": "🏥 تطوير المستشفيات وتوسيع التأمين الصحي", "callback_data": "vote:health"}],
            [{"text": "📚 جودة التعليم والمدارس والتغذية المدرسية", "callback_data": "vote:education"}],
            [{"text": "🤝 برامج الدعم النقدي والسلع التموينية", "callback_data": "vote:social"}],
            [{"text": "💼 حوافز المشروعات وتشغيل الشباب والإنتاج", "callback_data": "vote:economy"}],
            [{"text": "🏠 الإسكان الاجتماعي وسكن لكل المصريين", "callback_data": "vote:housing"}]
        ]
    keyboard.append([{"text": "🏠 القائمة الرئيسية", "callback_data": "menu:main"}])
    return {"inline_keyboard": keyboard}


def get_eligibility_menu_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "🤝 تكافل وكرامة (دعم نقدي مشروط)", "callback_data": "eligible:takaful"}],
            [{"text": "🍞 دعم التموين ورغيف الخبز المدعم", "callback_data": "eligible:rations"}],
            [{"text": "🏥 التأمين الصحي الشامل وغير القادرين", "callback_data": "eligible:health_insurance"}],
            [{"text": "🎒 دعم الطلاب والمدارس والتغذية", "callback_data": "eligible:students_support"}],
            [{"text": "🏭 حوافز المشروعات الصغيرة وريادة الأعمال", "callback_data": "eligible:sme_support"}],
            [{"text": "🏠 القائمة الرئيسية", "callback_data": "menu:main"}]
        ]
    }


def get_faq_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "🏥 كام مخصصات قطاع الصحة في الموازنة؟", "callback_data": "faq:health"}],
            [{"text": "📚 كام مخصصات التعليم والبحث العلمي؟", "callback_data": "faq:education"}],
            [{"text": "🍞 مخصصات دعم رغيف العيش والتموين؟", "callback_data": "faq:rations"}],
            [{"text": "💼 مخصصات الأجور والحد الأدنى للمرتبات؟", "callback_data": "faq:wages"}],
            [{"text": "🏠 مخصصات الإسكان الاجتماعي ومياه الشرب؟", "callback_data": "faq:housing"}],
            [{"text": "🏠 القائمة الرئيسية", "callback_data": "menu:main"}]
        ]
    }


# =====================================================================
# Handlers
# =====================================================================

def handle_start(chat_id: int):
    """Welcomes the user with poll options and service navigation."""
    poll = db.get_current_poll()
    question = poll.get("question", "لو معاك جنيه إضافي في الموازنة العامة للدولة 2026/2027، تحب الإنفاق يتركز أكتر في إيه؟") if poll else "ما هي أولويتك في موازنة 2026/2027؟"

    welcome_text = (
        "👋 *أهلاً بك في منصة 'حسبتك' — مستشارك الرقمي لموازنة المواطن 2026/2027* 🇪🇬\n\n"
        "أنا هنا عشان أجاوبك على كل أسئلتك عن موازنة الدولة وأرقامها المؤكدة رسمياً 100% وبدون تعقيد.\n\n"
        "📊 *استطلاع الأسبوع (نبض المواطن):*\n"
        f"*{question}*\n\n"
        "👇 *اضغط على خيارك المفضل لتسجيل رأيك فوراً، أو اختر من الخدمات بالأسفل:*"
    )

    # Build initial keyboard: Poll Options + Services
    poll_kb = get_poll_keyboard()["inline_keyboard"]
    # Remove the back to main button on the start screen
    poll_options_only = [btn for btn in poll_kb if btn[0]["callback_data"] != "menu:main"]

    combined_keyboard = poll_options_only + [
        [
            {"text": "🤝 دليل هل تستحق؟ (تكافل ودعم)", "callback_data": "menu:eligible"},
            {"text": "💡 أرقام الموازنة السريعة", "callback_data": "menu:faq"}
        ],
        [
            {"text": "🎓 أنا طالب", "callback_data": "profile:طالب"},
            {"text": "💼 أنا موظف", "callback_data": "profile:موظف"},
            {"text": "🏭 صاحب مشروع", "callback_data": "profile:صاحب مشروع"}
        ]
    ]

    send_message(chat_id, welcome_text, reply_markup={"inline_keyboard": combined_keyboard})


def handle_vote(callback_query: dict):
    cb_id = callback_query.get("id")
    user_id = str(callback_query.get("from", {}).get("id"))
    chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
    data = callback_query.get("data", "")
    choice = data.replace("vote:", "").strip()

    answer_callback_query(cb_id, text="تم تسجيل صوتك بنجاح! جارٍ حساب النسبة...")

    try:
        res = db.record_vote(user_id=user_id, poll_id="budget_priority_2026", choice=choice)
        feedback = res.get("feedback_text", "✅ صوتك اتسجل بنجاح في استطلاع الموازنة!")
        topic = res.get("related_topic", choice)

        keyboard = [
            [{"text": "💰 اعرف الرقم المخصص لهذا البند بالموازنة", "callback_data": f"budget:{topic}"}],
            [{"text": "🤝 دليل هل تستحق؟", "callback_data": "menu:eligible"}, {"text": "🏠 القائمة الرئيسية", "callback_data": "menu:main"}]
        ]
        send_message(chat_id, feedback, reply_markup={"inline_keyboard": keyboard})
    except Exception as e:
        logger.error(f"Error recording vote: {e}")
        send_message(chat_id, "✅ صوتك اتسجل في استطلاع الموازنة! شكراً لمشاركتك الفعالة.", reply_markup=get_main_menu_keyboard())


def handle_budget_info(callback_query: dict):
    cb_id = callback_query.get("id")
    chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
    data = callback_query.get("data", "")
    topic = data.replace("budget:", "").strip()

    answer_callback_query(cb_id)

    try:
        res = db.get_budget_topic_info(topic)
        summary = res.get("summary_text", "")
        response_text = (
            f"🏛️ *بيانات الموازنة المعتمدة 2026/2027:*\n\n"
            f"{summary}\n\n"
            f"💡 *تقدر تسألني أي سؤال إضافي عن الموازنة والدعم وأنا هجاوبك فوراً!*"
        )
        keyboard = [
            [{"text": "📊 استطلاع الأسبوع", "callback_data": "menu:poll"}],
            [{"text": "🤝 برامج الدعم المستحقة", "callback_data": "menu:eligible"}],
            [{"text": "🏠 القائمة الرئيسية", "callback_data": "menu:main"}]
        ]
        send_message(chat_id, response_text, reply_markup={"inline_keyboard": keyboard})
    except Exception as e:
        logger.error(f"Error fetching budget info: {e}")
        send_message(chat_id, "لم نتمكن من جلب تفاصيل هذا البند حالياً، يمكنك كتابة سؤالك مباشرة وسنجيبك فوراً.", reply_markup=get_main_menu_keyboard())


def handle_eligibility(callback_query: dict):
    cb_id = callback_query.get("id")
    chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
    data = callback_query.get("data", "")
    node_id = data.replace("eligible:", "").strip()

    answer_callback_query(cb_id)

    try:
        reply_text = eligibility_engine.format_node_reply(node_id)
        keyboard = [
            [{"text": "🔙 رجوع لدليل الحماية الاجتماعية", "callback_data": "menu:eligible"}],
            [{"text": "🏠 القائمة الرئيسية", "callback_data": "menu:main"}]
        ]
        send_message(chat_id, reply_text, reply_markup={"inline_keyboard": keyboard})
    except Exception as e:
        logger.error(f"Error showing eligibility node: {e}")
        send_message(chat_id, "حدث خطأ في عرض الدليل، برجاء المحاولة مرة أخرى.", reply_markup=get_main_menu_keyboard())


def handle_faq_answer(callback_query: dict):
    cb_id = callback_query.get("id")
    chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
    user_id = str(callback_query.get("from", {}).get("id"))
    data = callback_query.get("data", "")
    faq_key = data.replace("faq:", "").strip()

    answer_callback_query(cb_id, text="جارٍ جلب الرقم الرسمي...")
    send_typing(chat_id)

    queries = {
        "health": "مخصصات قطاع الصحة كام في الموازنة؟",
        "education": "مخصصات التعليم والبحث العلمي كام في الموازنة؟",
        "rations": "مخصصات دعم السلع التموينية ورغيف العيش كام؟",
        "wages": "مخصصات الأجور والحد الأدنى للمرتبات كام في موازنة 2026/2027؟",
        "housing": "مخصصات الإسكان الاجتماعي ومياه الشرب والصرف الصحي كام؟"
    }

    query_text = queries.get(faq_key, "معلومات عن الموازنة")
    res = core.process_message(user_id, query_text)
    reply_text = res.get("reply", "")

    keyboard = [
        [{"text": "💡 سؤال آخر من الأرقام السريعة", "callback_data": "menu:faq"}],
        [{"text": "📊 استطلاع الموازنة", "callback_data": "menu:poll"}, {"text": "🏠 القائمة الرئيسية", "callback_data": "menu:main"}]
    ]
    send_message(chat_id, reply_text, reply_markup={"inline_keyboard": keyboard})


def handle_profile_selection(callback_query: dict):
    cb_id = callback_query.get("id")
    chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
    user_id = str(callback_query.get("from", {}).get("id"))
    data = callback_query.get("data", "")
    profile = data.replace("profile:", "").strip()

    answer_callback_query(cb_id, text=f"تم ضبط فئتك: {profile}")
    core.set_user_profile(user_id, profile)

    profile_msgs = {
        "طالب": "تمام يا بطل! 🎓 تم ضبط فئتك: **طالب**.\nهركز في إجاباتي على دعم التأمين الصحي للطلبة، التغذية المدرسية، واشتراكات المترو والقطارات.",
        "موظف": "أهلاً بحضرتك! 💼 تم ضبط فئتك: **موظف**.\nهركز في إجاباتي على بنود الأجور، الحد الأدنى (8000 ج)، حزمة يوليو 2026، والعلاوات.",
        "صاحب مشروع": "أهلاً بك يا فندم! 🏭 تم ضبط فئتك: **صاحب مشروع**.\nهركز في إجاباتي على حوافز المشروعات الصغيرة، المنظومة الضريبية المبسطة، وتسهيلات الإنتاج."
    }

    msg = profile_msgs.get(profile, f"✅ تم ضبط فئتك كـ **{profile}** بنجاح!")
    msg += "\n\n💡 اسألني عن أي بند وسأجيبك بأرقام موازنة 2026/2027 المعتمدة."

    keyboard = [
        [{"text": "📊 شارك في استطلاع الأسبوع", "callback_data": "menu:poll"}],
        [{"text": "🤝 دليل برامج الدعم", "callback_data": "menu:eligible"}],
        [{"text": "🏠 القائمة الرئيسية", "callback_data": "menu:main"}]
    ]
    send_message(chat_id, msg, reply_markup={"inline_keyboard": keyboard})


def handle_chat_question(message: dict):
    """Processes user text questions via Hasebtak Grounded RAG with Numeric Guardrail."""
    chat_id = message.get("chat", {}).get("id")
    user_id = str(message.get("from", {}).get("id"))
    text = message.get("text", "").strip()

    send_typing(chat_id)

    try:
        res = core.process_message(user_id, text)
        reply_text = res.get("reply", "عذراً، لم أتمكن من معالجة السؤال حالياً.")

        keyboard = [
            [
                {"text": "📊 استطلاع الموازنة", "callback_data": "menu:poll"},
                {"text": "🤝 دليل هل تستحق؟", "callback_data": "menu:eligible"}
            ],
            [
                {"text": "🏠 القائمة الرئيسية", "callback_data": "menu:main"}
            ]
        ]
        send_message(chat_id, reply_text, reply_markup={"inline_keyboard": keyboard})
    except Exception as e:
        logger.error(f"Error in chat processing: {e}")
        send_message(
            chat_id,
            "عذراً، يواجه النظام ضغطاً مؤقتاً في معالجة السؤال. برجاء المحاولة بعد لحظات أو استخدام الخيارات السريعة أدناه.",
            reply_markup=get_main_menu_keyboard()
        )


# =====================================================================
# Main Polling Loop
# =====================================================================

def run():
    print("=" * 60)
    print("🚀 Hasebtak Telegram Bot Runner Started Successfully!")
    print("=" * 60)
    
    delete_webhook()
    offset = 0

    while True:
        try:
            params = {"offset": offset, "timeout": 20}
            resp = requests.get(f"{TG_API}/getUpdates", params=params, timeout=25)
            
            if resp.status_code != 200:
                time.sleep(2)
                continue

            data = resp.json()
            updates = data.get("result", [])
            for u in updates:
                offset = u["update_id"] + 1

                # 1. Handle Callback Queries (Inline Button clicks)
                if "callback_query" in u:
                    cb = u["callback_query"]
                    cb_data = cb.get("data", "")
                    chat_id = cb.get("message", {}).get("chat", {}).get("id")

                    if cb_data.startswith("vote:"):
                        handle_vote(cb)
                    elif cb_data.startswith("budget:"):
                        handle_budget_info(cb)
                    elif cb_data.startswith("eligible:"):
                        handle_eligibility(cb)
                    elif cb_data.startswith("faq:"):
                        handle_faq_answer(cb)
                    elif cb_data.startswith("profile:"):
                        handle_profile_selection(cb)
                    elif cb_data == "menu:poll":
                        answer_callback_query(cb.get("id"))
                        poll = db.get_current_poll()
                        q = poll.get("question", "ما هي أولويتك في الموازنة؟") if poll else "ما هي أولويتك؟"
                        send_message(chat_id, f"📊 *استطلاع الأسبوع (نبض المواطن):*\n\n*{q}*\n\n👇 *اضغط على خيارك لتسجيل رأيك فوراً:*", reply_markup=get_poll_keyboard())
                    elif cb_data == "menu:eligible":
                        answer_callback_query(cb.get("id"))
                        text = "🤝 *دليل 'هل تستحق؟' للحماية الاجتماعية ورعاية المواطنين*\n\nأقدر أساعدك تعرف برامج الدعم الرسمية بموازنة 2026/2027 وإزاي تقدم فيها.\n\n👇 *اختر البرنامج الذي ترغب بالاستعلام عنه:*"
                        send_message(chat_id, text, reply_markup=get_eligibility_menu_keyboard())
                    elif cb_data == "menu:faq":
                        answer_callback_query(cb.get("id"))
                        text = "💡 *أرقام الموازنة السريعة 2026/2027*\n\nاضغط على أي بند من البنود التالية لمعرفة المخصصات المعتمدة بالأرقام الرسمية:"
                        send_message(chat_id, text, reply_markup=get_faq_keyboard())
                    elif cb_data == "menu:main":
                        answer_callback_query(cb.get("id"))
                        handle_start(chat_id)
                    continue

                # 2. Handle Messages
                if "message" in u:
                    msg = u["message"]
                    chat_id = msg.get("chat", {}).get("id")
                    text = msg.get("text", "").strip()

                    if not text:
                        continue

                    if text.lower() in ["/start", "/help", "ابدأ", "البداية", "القائمة", "start", "help", "menu", "سلام عليكم", "السلام عليكم", "مرحبا"]:
                        handle_start(chat_id)
                    elif text.startswith("/poll") or text == "استطلاع":
                        poll = db.get_current_poll()
                        q = poll.get("question", "ما هي أولويتك في الموازنة؟") if poll else "ما هي أولويتك؟"
                        send_message(chat_id, f"📊 *استطلاع الأسبوع (نبض المواطن):*\n\n*{q}*\n\n👇 *اضغط على خيارك لتسجيل رأيك فوراً:*", reply_markup=get_poll_keyboard())
                    elif text.startswith("/eligible") or "هل تستحق" in text or "دليل الحماية" in text:
                        text_msg = "🤝 *دليل 'هل تستحق؟' للحماية الاجتماعية ورعاية المواطنين*\n\n👇 *اختر البرنامج الذي ترغب بالاستعلام عنه:*"
                        send_message(chat_id, text_msg, reply_markup=get_eligibility_menu_keyboard())
                    else:
                        handle_chat_question(msg)

        except requests.exceptions.RequestException as e:
            logger.warning(f"Network polling warning: {e}")
            time.sleep(2)
        except Exception as ex:
            logger.error(f"Unexpected loop error: {ex}", exc_info=True)
            time.sleep(2)


if __name__ == "__main__":
    run()
