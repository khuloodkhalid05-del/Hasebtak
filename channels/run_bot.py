"""
channels/run_bot.py
Autonomous Telegram Bot Runner for Hasebtak (حسبتك) 🇪🇬
Connects Telegram directly to the local FastAPI backend (port 8000) using Telegram Polling.
"""

import os
import sys
import time
import requests
from dotenv import load_dotenv

# Reconfigure stdout for UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

if not BOT_TOKEN:
    print("❌ ERROR: TELEGRAM_BOT_TOKEN is missing in .env")
    sys.exit(1)

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def delete_webhook():
    """Ensure no stale webhook blocks polling."""
    try:
        r = requests.get(f"{TG_API}/deleteWebhook", timeout=10)
        print("Telegram Webhook cleared for polling:", r.json())
    except Exception as e:
        print("Error clearing webhook:", e)


def send_message(chat_id: int, text: str, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        r = requests.post(f"{TG_API}/sendMessage", json=payload, timeout=10)
        return r.json()
    except Exception as e:
        print(f"Error sending message to {chat_id}:", e)
        return None


def answer_callback_query(callback_query_id: str, text: str = ""):
    try:
        payload = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
        requests.post(f"{TG_API}/answerCallbackQuery", json=payload, timeout=5)
    except Exception as e:
        print("Error answering callback query:", e)


def handle_start(chat_id: int):
    """Fetches active poll and sends welcome interactive message."""
    try:
        r = requests.get(f"{API_BASE}/poll/current", timeout=10)
        if r.status_code == 200:
            data = r.json()
            question = data.get("question", "ما هي أولويتك في موازنة الدولة؟")
            options = data.get("options", [])
            
            keyboard = []
            for opt in options:
                keyboard.append([{"text": opt["text"], "callback_data": f"vote:{opt['option_id']}"}])
            
            welcome_text = (
                "👋 *أهلاً بك في منصة 'حسبتك' — مستشارك الرقمي لموازنة المواطن 2026/2027* 🇪🇬\n\n"
                "📊 *استطلاع الأسبوع:*\n"
                f"{question}\n\n"
                "👇 *اضغط على خيارك المفضل لتسجيل رأيك فوراً:*"
            )
            send_message(chat_id, welcome_text, reply_markup={"inline_keyboard": keyboard})
            return
    except Exception as e:
        print("Error fetching poll in handle_start:", e)
    
    fallback_text = (
        "👋 *أهلاً بك في منصة 'حسبتك'* 🇪🇬\n\n"
        "المستشار الذكي لموازنة المواطن المصري 2026/2027.\n"
        "اسألني عن أي بند في الموازنة (الصحة، التعليم، الدعم، رغيف العيش، تكافل وكرامة...) وسأجيبك بأرقام معتمدة رسمياً."
    )
    send_message(chat_id, fallback_text)


def handle_vote(callback_query: dict):
    cb_id = callback_query.get("id")
    user_id = str(callback_query.get("from", {}).get("id"))
    chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
    data = callback_query.get("data", "")
    choice = data.replace("vote:", "").strip()

    answer_callback_query(cb_id, text="تم استلام صوتك! جارٍ الحساب...")

    try:
        payload = {
            "user_id": user_id,
            "poll_id": "budget_priority_2026",
            "choice": choice
        }
        r = requests.post(f"{API_BASE}/vote", json=payload, timeout=10)
        if r.status_code == 200:
            res = r.json()
            feedback = res.get("feedback_text", "✅ صوتك اتسجل بنجاح!")
            topic = res.get("related_topic", choice)
            
            # Button to transition into knowledge/fact
            keyboard = [
                [{"text": "💰 اعرف الرقم المخصص بالموازنة", "callback_data": f"budget:{topic}"}]
            ]
            send_message(chat_id, feedback, reply_markup={"inline_keyboard": keyboard})
            return
    except Exception as e:
        print("Error submitting vote:", e)

    send_message(chat_id, "✅ صوتك اتسجل في استطلاع الموازنة! شكراً لمشاركتك الفعالة.")


def handle_budget_info(callback_query: dict):
    cb_id = callback_query.get("id")
    chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
    data = callback_query.get("data", "")
    topic = data.replace("budget:", "").strip()

    answer_callback_query(cb_id)

    try:
        r = requests.get(f"{API_BASE}/budget/{topic}", timeout=10)
        if r.status_code == 200:
            res = r.json()
            summary = res.get("summary_text", "")
            response_text = (
                f"🏛️ *بيانات الموازنة المعتمدة 2026/2027:*\n\n"
                f"{summary}\n\n"
                f"💡 *تقدر تسألني أي سؤال إضافي عن الموازنة والدعم وأنا هجاوبك فوراً!*"
            )
            send_message(chat_id, response_text)
            return
    except Exception as e:
        print("Error fetching budget topic:", e)

    send_message(chat_id, "لم نتمكن من جلب تفاصيل هذا البند حالياً، يمكنك كتابة سؤالك مباشرة وسنجيبك فوراً.")


def handle_chat_question(message: dict):
    chat_id = message.get("chat", {}).get("id")
    user_id = str(message.get("from", {}).get("id"))
    text = message.get("text", "").strip()

    # Send typing action
    try:
        requests.post(f"{TG_API}/sendChatAction", json={"chat_id": chat_id, "action": "typing"}, timeout=5)
    except Exception:
        pass

    try:
        payload = {
            "user_id": user_id,
            "text": text,
            "user_profile": "مواطن"
        }
        r = requests.post(f"{API_BASE}/api/chat", json=payload, timeout=30)
        if r.status_code == 200:
            res = r.json()
            reply_text = res.get("response", "عذراً، حدث خطأ في معالجة الإجابة.")
            send_message(chat_id, reply_text)
            return
    except Exception as e:
        print("Error calling api/chat:", e)

    send_message(chat_id, "عذراً، يواجه النظام ضغطاً مؤقتاً في معالجة السؤال. برجاء المحاولة بعد لحظات.")


def run():
    print("=" * 60)
    print("🚀 Hasebtak Telegram Bot Runner Started!")
    print(f"📡 Backend API: {API_BASE}")
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

            updates = resp.json().get("result", [])
            for u in updates:
                offset = u["update_id"] + 1

                # 1. Handle Callback Queries (Inline Button clicks)
                if "callback_query" in u:
                    cb = u["callback_query"]
                    cb_data = cb.get("data", "")
                    if cb_data.startswith("vote:"):
                        handle_vote(cb)
                    elif cb_data.startswith("budget:"):
                        handle_budget_info(cb)
                    continue

                # 2. Handle Messages
                if "message" in u:
                    msg = u["message"]
                    chat_id = msg.get("chat", {}).get("id")
                    text = msg.get("text", "")

                    if text == "/start":
                        handle_start(chat_id)
                    elif text.startswith("/"):
                        handle_start(chat_id)
                    elif text:
                        handle_chat_question(msg)

        except requests.exceptions.RequestException:
            time.sleep(2)
        except Exception as ex:
            print("Unexpected loop error:", ex)
            time.sleep(2)


if __name__ == "__main__":
    run()
