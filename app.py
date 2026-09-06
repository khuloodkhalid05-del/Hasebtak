"""
app.py
FastAPI Webhook Entrypoint and API Server for Hasebtak (حسبتك).
Serves Telegram webhooks, WhatsApp webhooks, REST APIs for apps/web,
and interactive CLI testing.
"""

import os
import sys
import logging

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("hasebtak.api")

from core.router import HasebtakCore
from core.voice import text_to_speech
from core import database as db
from channels.telegram_adapter import TelegramAdapter
from channels.whatsapp_adapter import WhatsAppAdapter
from channels.base import OutgoingMessage

app = FastAPI(
    title="حسبتك — Hasebtak API",
    description="المستشار الرقمي لموازنة المواطن 2026/2027 — وزارة المالية",
    version="1.0.0"
)

# Enable CORS for web applications and dashboards
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize engines and adapters
core = HasebtakCore()
telegram_adapter = TelegramAdapter()
whatsapp_adapter = WhatsAppAdapter()


# Request Schemas
class ChatRequest(BaseModel):
    user_id: Optional[str] = "demo_user"
    text: str
    user_profile: Optional[str] = "مواطن"
    voice_response: Optional[bool] = False


class PollVoteRequest(BaseModel):
    user_id: str
    poll_id: str
    option_id: str
    user_profile: Optional[str] = "مواطن"


class VotePayload(BaseModel):
    user_id: str
    poll_id: Optional[str] = "budget_priority_2026"
    choice: str


# REST API Endpoints
@app.get("/")
def read_root():
    return {
        "project": "حسبتك (Hasebtak)",
        "subtitle": "The Digital Advisor for Citizen Budget 2026/2027",
        "ministry": "Ministry of Finance - Egypt",
        "pillars": {
            "pillar1": "اسأل عن فلوسك (Ask About Your Money - Grounded RAG)",
            "pillar2": "هل تستحق؟ (Do You Qualify? - Social Protection Guide)",
            "pillar3": "نبض المواطن (Citizen's Pulse - Interactive Polling)"
        },
        "status": "Operational",
        "cost": "0 EGP"
    }


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "facts_count": len(core.grounding.facts),
        "llm_ready": core.llm.client_ready,
        "chroma_ready": core.grounding.collection is not None
    }


@app.post("/api/chat")
async def chat_api(req: ChatRequest):
    """
    Direct Chat API endpoint for Web UI, Mobile Apps, or testing.
    """
    if req.user_profile and req.user_profile != "مواطن":
        core.set_user_profile(req.user_id, req.user_profile)

    res = core.process_message(req.user_id, req.text)

    voice_path = None
    if req.voice_response and res.get("reply"):
        try:
            voice_path = text_to_speech(res["reply"])
        except Exception as e:
            logger.warning(f"Voice generation skipped: {e}")

    return {
        "user_id": req.user_id,
        "response": res.get("reply"),
        "type": res.get("type"),
        "options": res.get("options"),
        "guardrail_passed": res.get("guardrail_passed", True),
        "sources": res.get("sources", []),
        "voice_path": voice_path
    }


@app.get("/api/poll/active")
def get_active_poll():
    """Returns active poll question and live statistics."""
    poll = core.polls.get_active_poll()
    if not poll:
        return {"active": False}
    stats = core.polls.get_poll_stats(poll["id"])
    return {"active": True, "poll": poll, "stats": stats}


@app.post("/api/poll/vote")
def record_poll_vote(req: PollVoteRequest):
    """Submits anonymous vote."""
    result = core.polls.record_vote(
        user_channel_id=req.user_id,
        poll_id=req.poll_id,
        option_id=req.option_id,
        user_profile=req.user_profile
    )
    return result


# --- New REST Endpoints for n8n, Web, and Messaging Bot Integration ---

@app.post("/vote")
@app.post("/api/vote")
def submit_vote(payload: VotePayload):
    """
    Submits user vote to SQLite database.
    Guarantees duplicate vote prevention via UNIQUE(user_id, poll_id).
    Returns real-time percentage and transition feedback for n8n and bot.
    """
    return db.record_vote(payload.user_id, payload.poll_id, payload.choice)


@app.get("/poll/current")
@app.get("/api/poll/current")
def get_current_poll():
    """
    Fetches the current active poll and all its options from SQLite.
    """
    poll = db.get_current_poll()
    if not poll:
        return {"active": False, "message": "No active poll found"}
    return poll


@app.get("/poll/results")
@app.get("/poll/{poll_id}/results")
@app.get("/api/poll/results")
@app.get("/api/poll/{poll_id}/results")
def get_poll_results(poll_id: Optional[str] = None):
    """
    Calculates live vote counts and percentages for all options of a poll.
    """
    return db.get_poll_results(poll_id)


@app.get("/budget/{topic}")
@app.get("/api/budget/{topic}")
def get_budget_topic(topic: str):
    """
    Retrieves verified budget figures for the chosen topic.
    Powers the '💰 اعرف الرقم' transition from poll vote to financial education.
    """
    return db.get_budget_topic_info(topic)



# Channel Webhooks
@app.post("/webhook/telegram")
async def telegram_webhook(req: Request, background_tasks: BackgroundTasks):
    """
    Webhook handler for Telegram Bot (Free-Forever Channel).
    """
    try:
        update_data = await req.json()
        incoming = telegram_adapter.parse_incoming(update_data)
        if not incoming:
            return {"ok": True}

        # Process message through Hasebtak core
        res = core.process_message(incoming.user_id, incoming.text)
        reply_text = res.get("reply", "")

        # Format buttons if available
        buttons = []
        if res.get("options"):
            buttons = [
                {"id": opt.get("id", opt.get("goto", "")), "label": opt.get("label", opt.get("label_ar", ""))}
                for opt in res["options"]
            ]

        outgoing = OutgoingMessage(
            user_id=incoming.user_id,
            text=reply_text,
            buttons=buttons if buttons else None
        )

        background_tasks.add_task(telegram_adapter.send_response, outgoing)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Telegram webhook error: {e}")
        return {"ok": False, "error": str(e)}


@app.get("/webhook/whatsapp")
def whatsapp_verify(request: Request):
    """
    Meta WhatsApp Cloud API Webhook Verification Endpoint.
    """
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "hasebtak_secret_verify_token")
    if mode == "subscribe" and token == verify_token:
        logger.info("WhatsApp webhook verified successfully.")
        return Response(content=challenge, media_type="text/plain")
    return Response(content="Verification failed", status_code=403)


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(req: Request, background_tasks: BackgroundTasks):
    """
    Webhook handler for Meta WhatsApp Cloud API.
    """
    try:
        payload = await req.json()
        incoming = whatsapp_adapter.parse_incoming(payload)
        if not incoming:
            return {"status": "ignored"}

        res = core.process_message(incoming.user_id, incoming.text)
        outgoing = OutgoingMessage(
            user_id=incoming.user_id,
            text=res.get("reply", "")
        )
        background_tasks.add_task(whatsapp_adapter.send_response, outgoing)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"WhatsApp webhook error: {e}")
        return {"status": "error", "message": str(e)}


# Interactive CLI Demo when run directly
def run_cli():
    print("=" * 65)
    print("  مرحباً بك في تشغيل منصة 'حسبتك' — المستشار الرقمي لموازنة المواطن")
    print("  موازنة جمهورية مصر العربية 2026/2027 (تكلفة التشغيل: 0 جنيه)")
    print("=" * 65)
    print("اختر فئتك: (1: طالب | 2: موظف | 3: صاحب مشروع | 4: مواطن عام)")
    choice = input("اختيارك (افتراضي 4): ").strip()
    profile_map = {"1": "طالب", "2": "موظف", "3": "صاحب مشروع", "4": "مواطن"}
    profile = profile_map.get(choice, "مواطن")
    print(f"تم ضبط الفئة: [{profile}]. يمكنك الآن كتابة أي سؤال أو 'خروج'.\n")

    while True:
        try:
            q = input(f"\n[أنت ({profile})]: ").strip()
            if not q or q.lower() in ["خروج", "exit", "quit"]:
                print("مع السلامة! حسبتك في خدمتك دائماً 🙏")
                break

            res = core.process_message("cli_user", q)
            print("\n[حسبتك]:")
            print(res.get("reply"))
            if res.get("sources"):
                print(f"\n📌 المصادر المؤكدة: {res['sources']}")
        except KeyboardInterrupt:
            print("\nتم إنهاء الجلسة.")
            break


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "cli":
        run_cli()
    else:
        print("Starting Hasebtak FastAPI Web Server on http://localhost:8000 ...")
        print("To run interactive terminal CLI instead, use: python app.py cli")
        uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)