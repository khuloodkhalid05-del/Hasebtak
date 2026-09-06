# "حسبتك" (Hasebtak) — Implementation Plan
### The Digital Advisor for the Citizen Budget 2026/2027
**A zero-cost, AI-powered conversational platform for Egypt's Ministry of Finance**

> Prepared for the *Citizen Budget 2026/2027 Innovation Competition*.
> This document is written to be **built for real** by a small student team using **only free tools**.

---

## 0. TL;DR (read this first)

**What it is:** A WhatsApp (and Telegram) chatbot that turns the Ministry's 70-page Citizen Budget report into a simple Egyptian-Arabic conversation — by **text and voice** — so any citizen can ask "where does my money go?" and get an accurate, sourced answer in seconds.

**Three pillars in one bot:**
1. **اسأل عن فلوسك (Ask About Your Money)** — RAG chatbot answering in Egyptian colloquial Arabic, text + voice, tailored to the user's profile (student / employee / business owner).
2. **هل تستحق؟ (Do You Qualify?)** — a guided, informational self-check that points citizens to social-protection programs (Takaful & Karama, etc.) and the official channels to apply.
3. **نبض المواطن (Citizen's Pulse)** — a weekly one-tap poll that lets the Ministry hear young citizens' views and turns feedback into an analytics dashboard.

**The core promise (and the hard technical challenge):**
> *Strict adherence to official figures, zero improvisation.*
The bot must **never invent a number**. This plan solves that with a **hybrid grounding design**: a hand-verified **Facts Ledger** + **vector RAG** + a **strict grounded prompt** + a **numeric guardrail** that blocks any figure not found in the source.

**Cost:** **0 EGP.** Every component below maps to a genuinely free tier (see §11).

**Critical constraint you must know:** WhatsApp service replies are **free only until 1 October 2026** (Meta's 2025→2026 pricing change). The engine is therefore **channel-agnostic**: WhatsApp for the demo/pilot, **Telegram as the free-forever channel**. This is both a cost decision and a resilience story judges will respect.

---

## 1. Problem statement (grounded in the Ministry's own report)

The Citizen Budget report itself publishes Egypt's scores on the international **Open Budget Survey (OBS 2025)**:

| Dimension | Score (out of 100) | Trend |
|---|---|---|
| Budget **Transparency** | 59 | ▲ from 49 (2023) |
| Budget **Oversight** | 59 | ▲ from 54 (2023) |
| **Public Participation** | **35** | flat since 2023 |

**The gap is clear:** transparency and oversight have improved sharply, but **public participation is stuck at 35/100**. The information is *published* — but it is locked inside a 70-page PDF that most citizens will never open. The report explicitly states the Ministry wants to use *"AI tools to improve data visualization and citizen participation."* **Hasebtak is a direct execution of a goal the Ministry has already declared** — not an outside suggestion.

**Design principle:** meet citizens where they already are. WhatsApp is Egypt's most-used app, and the Ministry already runs an official WhatsApp channel — so the bot rides an existing habit instead of asking people to learn something new.

---

## 2. What makes this idea competition-winning

1. **It's grounded in real numbers from the actual report** (see the Facts Ledger in Appendix A), not generic claims.
2. **It solves the report's own weakest KPI** (participation 35/100).
3. **It's genuinely free and genuinely buildable** by students in weeks.
4. **It's safe**: no personal data stored, no eligibility "verdicts," clear hand-off to official channels.
5. **It's honest about hallucination** — the #1 risk of any budget chatbot — and engineers around it instead of hand-waving.
6. **It's resilient** — channel-agnostic, so it survives WhatsApp's pricing changes.

---

## 3. System architecture (high level)

```
                         ┌───────────────────────────────────────────┐
   Citizen               │              HASEBTAK CORE ENGINE          │
   (WhatsApp / Telegram) │                                            │
        │  text / voice   │  ┌─────────────┐   ┌──────────────────┐  │
        ▼                 │  │  Router /    │──▶│ Pillar 1: RAG Q&A │  │
  ┌───────────┐  webhook  │  │  Intent      │   │ (grounded answer) │  │
  │  Channel   │────────▶ │  │  detection   │──▶│ Pillar 2: Eligible│  │
  │  Adapter   │◀──────── │  │              │   │ guide (Q-tree)    │  │
  └───────────┘  reply    │  └─────────────┘──▶│ Pillar 3: Poll     │  │
        ▲                 │         │           └──────────────────┘  │
        │                 │         ▼                                  │
        │                 │  ┌──────────────────────────────────────┐│
   voice out (TTS)        │  │  GROUNDING LAYER                       ││
        │                 │  │  ① Facts Ledger (verified JSON)        ││
        │                 │  │  ② Vector store (RAG over prose)       ││
        │                 │  │  ③ Grounded prompt + numeric guardrail ││
        │                 │  └──────────────────────────────────────┘│
        │                 │         │                    │            │
        │                 │         ▼                    ▼            │
        │                 │  ┌────────────┐      ┌──────────────┐    │
        │                 │  │  LLM (free) │      │  Poll / feedback│  │
        │                 │  │  Gemini/Groq│      │  DB (free)     │  │
        │                 │  └────────────┘      └──────────────┘    │
        │                 └───────────────────────────────────────────┘
        │                                              │
        │                                              ▼
        └──────── STT (voice in) ──────────    Analytics dashboard (free)
```

**Two ideas make this architecture strong:**

- **Channel Adapter pattern** — the core engine speaks a neutral message format; a thin adapter translates WhatsApp/Telegram specifics. Adding a channel = writing one adapter, not rebuilding the bot.
- **Grounding Layer** — a dedicated module that sits *between* the user and the LLM and guarantees factual answers. This is the heart of the project.

---

## 4. The Grounding Layer — how we guarantee "no invented numbers"

This is the single most important part of the plan. A naive "PDF → chunks → vector search → LLM" pipeline **will hallucinate figures**, which is fatal for a government budget tool. We use four layers of defense.

### Layer ① — The Facts Ledger (the anchor)
A **hand-verified structured file** (`facts_ledger.json`) containing every key figure from the report, each with an exact source citation. This is the source of truth for numbers. Because it's curated by humans, it is **immune to Arabic PDF extraction errors** (right-to-left text extraction can garble digits — see §5).

Example entry (real data from the report):
```json
{
  "id": "health_allocation_2627",
  "topic": "health",
  "value_egp": 862900000000,
  "display_ar": "862.9 مليار جنيه",
  "label_ar": "مخصصات قطاع الصحة لموازنة 2026/2027",
  "growth_pct": 39.6,
  "gdp_pct": 4.2,
  "source": "Citizen Budget 2026/2027, Health section (p.26–27)",
  "keywords": ["صحة", "الصحة", "علاج", "مستشفيات", "تأمين صحي"]
}
```

At query time the router matches the user's topic to ledger entries and **injects the exact verified figures** into the prompt. The LLM's job becomes *explaining* verified numbers in simple Arabic — **not recalling them**.

### Layer ② — Vector RAG (the context)
The report's prose (explanations, initiatives, reforms) is chunked and embedded into a vector store. This supplies the *narrative context* around the numbers ("why did health spending rise?", "what is the universal health insurance rollout?").

- **Embeddings (free):** `intfloat/multilingual-e5-large` or `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` (strong Arabic support, runs locally, zero cost). Alternative: Gemini `text-embedding-004` (free tier).
- **Vector store (free):** **ChromaDB** (local, open-source) for the MVP; **Supabase pgvector** (free tier) if you want it hosted.
- **Chunking:** ~300–500 tokens with 15% overlap, chunk **per sub-section** (the report is already well-sectioned), keep the section heading inside each chunk as metadata for citation.

### Layer ③ — The Grounded Prompt (the discipline)
A strict system prompt forces the model to answer **only** from the injected context and to **refuse gracefully** when the answer isn't there. (Full prompt in Appendix B.) Key rules:
- Answer only from the provided `FACTS` and `CONTEXT`.
- Never calculate, estimate, or infer a number that isn't explicitly present.
- Every figure in the answer must be traceable to a `FACTS` entry.
- If the info isn't in context → say so in Egyptian Arabic and offer the official source, **do not guess**.
- Always append a short source line (section + page).

### Layer ④ — The Numeric Guardrail (the safety net)
A deterministic post-processor that runs **after** the LLM and **before** the reply is sent:
1. Extract every number (Arabic + Latin digits) from the model's answer.
2. Check each against the numbers present in the injected `FACTS`/`CONTEXT`.
3. If a number appears in the answer but **not** in the source → **block the reply**, log it, and return a safe fallback ("معنديش رقم مؤكد عن ده حاليًا — تقدر تشوفه في التقرير الرسمي هنا…").

This closes the loop: even if the prompt discipline slips, an ungrounded figure can never reach the citizen.

> **Why this combination wins:** the Ledger removes the *need* to recall numbers, the prompt removes the *permission* to invent them, and the guardrail removes the *ability* for any invented number to escape. Three independent locks on the same door.

---

## 5. Data preparation pipeline (from the 70-page PDF to a working knowledge base)

The source is `Citizen_Budget_26-27_August_20.pdf` (70 pages, A4, Arabic, InDesign export with an embedded text layer).

**Step-by-step:**

1. **Extract text** — `pdftotext -layout` (poppler-utils, free). *Note:* the report has a real text layer, so OCR isn't required.
2. **⚠️ Arabic RTL caveat** — extracted Arabic can arrive with reshaped/reversed digit groups and broken ligatures. **Do not trust extracted numbers blindly.** This is precisely why every critical figure goes into the **hand-verified Facts Ledger** (§4①). Treat extracted prose as "good enough for context," and treat the Ledger as the numeric source of truth.
3. **Clean & normalize** — strip page furniture, normalize Arabic (unify أ/إ/آ→ا where helpful for search, normalize ة/ه, convert Arabic-Indic digits ٠١٢٣ ↔ Latin for matching). Use `camel-tools` or simple regex (both free).
4. **Section-aware chunking** — split on the report's own headings (Minister's message, "يعني إيه موازنة؟", pillars, social protection, health & education, tax reforms, fiscal risks, debt, transparency unit…). Store `{text, section_title_ar, page, topic}`.
5. **Embed & index** — run chunks through the multilingual embedding model → store vectors + metadata in ChromaDB.
6. **Build the Facts Ledger** — a human (team member) reads the key figures and enters each into `facts_ledger.json` with source pages. Budget ~4–6 hours for this; it is the highest-leverage task in the project. (Appendix A gives you a large head start with figures already extracted from the report.)
7. **Build the Eligibility Q-tree** — a small YAML/JSON decision tree for Pillar 2 (Appendix D), pointing to official application channels.

**Output artifacts:** `chroma_db/`, `facts_ledger.json`, `eligibility_tree.yaml`, `poll_bank.json`.

---

## 6. Pillar 1 — اسأل عن فلوسك (Ask About Your Money)

**Goal:** instant, accurate, Egyptian-Arabic answers about the budget, by text **and voice**, adapted to who's asking.

**Flow:**
1. User sends a message (text or voice note).
2. If voice → **STT** transcribes to Arabic text.
3. **Intent + topic detection** → is this a budget question? which topic (health, education, subsidies, taxes, debt, wages…)?
4. **Grounding Layer** retrieves Facts Ledger entries + top-k RAG chunks for that topic.
5. **Personalization:** if the user has picked a profile (student / employee / business owner), add a profile hint to the prompt so examples are relevant (e.g., a student hears about student transport subsidies and health-insurance-for-students; a business owner hears about the simplified tax system and the "White List").
6. **LLM** produces a grounded Egyptian-Arabic answer.
7. **Numeric guardrail** validates.
8. Reply is sent as **text**, and — when the user came in by voice or opts in — also as a **voice note (TTS)**.

**Voice pipeline (free, and a real accessibility win for elderly / visually-impaired users, which the report explicitly calls out):**
- **Speech-to-Text (Arabic):** **Groq Whisper-large-v3** (free tier, very fast) or local **faster-whisper** (open-source, runs on CPU).
- **Text-to-Speech (Egyptian Arabic):** **`edge-tts`** (free, Microsoft Edge voices) with Egyptian voices **`ar-EG-SalmaNeural`** (female) and **`ar-EG-ShakirNeural`** (male). Fallback: `gTTS` (free).

**Personalization onboarding:** first contact → a 3-button menu ("أنا طالب / موظف / صاحب مشروع") stored against the user's channel ID (no name, no personal data — see §10).

---

## 7. Pillar 2 — هل تستحق؟ (Do You Qualify?)

**Goal:** help citizens understand social-protection programs and reach the right official channel — **without ever issuing an eligibility verdict.**

**Why "guide," not "decision":** real eligibility for programs like **Takaful & Karama** (the report notes **4.7 million beneficiary families, 55.2 billion EGP**) is decided by the Ministry of Social Solidarity through official assessment. An AI bot must **not** claim someone qualifies or doesn't — that would be both inaccurate and harmful. So Pillar 2 is strictly **informational + directional**.

**Flow (a short decision tree, not free-form AI):**
1. Bot explains the program in simple Arabic (what it is, who it's broadly for), pulling text from the report/official sources.
2. Asks 3–5 **general, non-sensitive** questions ("Is there a program you're asking about?", "Do you want cash support, ration support, or health coverage info?").
3. Based on answers, returns: a plain-language summary of the relevant program(s) **+ the official application channel** (Ministry of Social Solidarity / nearest office / official portal) **+ a clear disclaimer**: *"دي معلومة استرشادية — القرار النهائي بيكون من الجهة الرسمية."*
4. **No sensitive data is requested or stored** (no ID number, no income figure, no household details).

**Implementation:** a deterministic Q-tree (`eligibility_tree.yaml`, Appendix D). Deterministic = predictable = safe, and it needs **zero** LLM calls, which also saves quota.

---

## 8. Pillar 3 — نبض المواطن (Citizen's Pulse)

**Goal:** a free, always-on feedback channel that turns citizen sentiment into data for policymakers — closing the participation gap (35/100).

**Flow:**
1. **Weekly one-tap poll** delivered via WhatsApp **interactive list/buttons** (or Telegram native polls). Example: *"لو معاك جنيه إضافي للإنفاق العام، تصرفه في: صحة / تعليم / دعم / بنية تحتية؟"*
2. User taps an option → response stored **anonymously** (channel ID hashed, only the answer + timestamp + optional profile bucket).
3. **Analytics dashboard** aggregates results (never individual-level) → simple charts the Ministry can read.
4. Optional open-ended follow-up ("عايز تضيف حاجة؟") whose free-text answers are summarized by the LLM into themes (no raw text shown, privacy-preserving).

**Storage (free):** **Supabase** (Postgres free tier) *or* **Google Sheets API** (free, dead-simple to analyze — great for a student project).
**Dashboard (free):** **Google Looker Studio** (connects to Sheets, free) *or* a **Streamlit** app hosted on **Hugging Face Spaces** (free).

**Poll design tips:** keep it to one question/week, mutually-exclusive options, rotate a small bank (`poll_bank.json`), and always tie each poll to a real budget topic so the data is policy-useful.

---

## 9. Recommended free tech stack (with the "why")

| Layer | Choice (free) | Why |
|---|---|---|
| **Language / framework** | **Python + FastAPI** | Best control over the grounding logic; huge free ecosystem; easy webhooks. |
| **LLM** | **Google Gemini 2.5 Flash** (free tier) — primary; **Groq (Llama 3.x)** — backup | Gemini free tier ≈ 15 RPM / 1,500 req-day / 1M TPM, no card, no expiry. Groq is a fast free fallback + free Whisper. |
| **Embeddings** | `multilingual-e5-large` / `paraphrase-multilingual-mpnet-base-v2` (local) or Gemini `text-embedding-004` | Strong Arabic; local = zero cost + no rate limits. |
| **Vector store** | **ChromaDB** (local) → **Supabase pgvector** (hosted) | Free, open-source, simple. |
| **STT (voice→text)** | **Groq Whisper-large-v3** or **faster-whisper** (local) | Free, fast, good Arabic. |
| **TTS (text→voice)** | **`edge-tts`** (`ar-EG-SalmaNeural`) | Free, natural Egyptian Arabic — key accessibility feature. |
| **Channel: primary/demo** | **WhatsApp Cloud API** (Meta) test number / **Twilio WhatsApp Sandbox** | Matches Ministry's existing channel; free for dev + until 1 Oct 2026 for service replies. |
| **Channel: free-forever** | **Telegram Bot API** | 100% free, unlimited, no per-message fees — the sustainable channel. |
| **Poll/feedback DB** | **Supabase** or **Google Sheets API** | Free tiers; Sheets is trivially analyzable. |
| **Dashboard** | **Looker Studio** or **Streamlit on HF Spaces** | Free hosted analytics. |
| **Hosting (bot backend)** | **Hugging Face Spaces** / **Render free** / **Fly.io** / **Oracle Cloud always-free VM** | Free webhook hosting. Oracle always-free VM avoids cold starts. |
| **Secrets / config** | environment variables (never in code) | Security (see §10). |
| **Repo / CI** | **GitHub** (free) | Version control + free Actions. |

> **Low-code alternative:** you *can* wire the channels with **n8n** (free, self-hosted), but keep the **grounding logic in Python** — the anti-hallucination guarantees are too important to leave to a no-code flow.

---

## 10. Security, privacy & safety ("آمن معلوماتيًا")

The concept promises information security. Concrete measures:

- **No PII storage.** Store only a **hashed** channel ID + the user's chosen profile bucket (student/employee/business). Never store names, phone numbers in clear, ID numbers, or income data.
- **Pillar 2 asks nothing sensitive** — no ID, no income, no household details. Ever.
- **Poll data is anonymous & aggregate-only.** Dashboards never expose individual responses.
- **Secrets in environment variables**, never committed. Use a `.env` + `.gitignore`.
- **Input sanitization & rate limiting** per user to prevent abuse and protect free-tier quotas.
- **Grounded-answer guarantee** (§4) is itself a safety control — it prevents the bot from stating false official figures.
- **Clear disclaimers** on guidance (Pillar 2) and a standing "for official/binding info, see mof.gov.eg / budget.gov.eg" footer.
- **Human-in-the-loop for content updates:** the Facts Ledger is only updated by a team member against the official PDF, never auto-scraped.
- **Data minimization by default** — if you don't need it to answer, don't ask for it.

---

## 11. Zero-cost proof (the competition requirement)

| Component | Service | Free? | Notes |
|---|---|---|---|
| LLM inference | Gemini Flash free tier | ✅ | ~1,500 req/day, no card. Groq as backup. |
| Embeddings | local sentence-transformers | ✅ | runs on your laptop / free host. |
| Vector DB | ChromaDB (local) | ✅ | open-source. |
| STT | faster-whisper (local) / Groq | ✅ | free. |
| TTS | edge-tts | ✅ | free. |
| WhatsApp (demo) | Meta test number / Twilio sandbox | ✅ | free for development. |
| Telegram (prod) | Telegram Bot API | ✅ | free forever. |
| Feedback DB | Google Sheets / Supabase free | ✅ | free tiers. |
| Dashboard | Looker Studio / HF Spaces | ✅ | free. |
| Hosting | HF Spaces / Oracle always-free | ✅ | free. |
| Repo/CI | GitHub | ✅ | free. |
| **Total** | | **0 EGP** | |

**The one honest asterisk:** a *production* WhatsApp deployment at scale becomes paid after **1 Oct 2026** (Meta ends free in-window service replies). Mitigations: (a) demo/pilot on WhatsApp before that date; (b) run production on **Telegram** (free forever); (c) if the Ministry adopts it officially, they already hold a WhatsApp Business Account and absorb messaging cost as an existing operating expense. **None of this affects the competition's free-build requirement.**

---

## 12. Build roadmap (phased, realistic for a student team)

> The competition idea-submission window runs to **10 September 2026** — so **Phase 1 is your demoable MVP for the submission**, and Phases 2–3 are the full project you present as the roadmap.

### Phase 0 — Setup (½–1 day)
- Create GitHub repo, Python env, get free API keys (Gemini, Telegram bot token, Twilio sandbox / Meta test number).
- Repo skeleton (Appendix E).

### Phase 1 — MVP: Pillar 1 text-only, on Telegram (3–5 days) ← *demo-ready*
- Run the data pipeline (§5): extract, chunk, embed → ChromaDB.
- Build the **Facts Ledger** for the top ~30 figures (Appendix A gives you most).
- Implement the **Grounding Layer** (Ledger lookup + RAG + grounded prompt + numeric guardrail).
- Wire a **Telegram adapter** (fastest free channel to demo) + FastAPI webhook.
- **Deliverable:** a working bot that answers budget questions accurately in Egyptian Arabic with sources. *This alone is a strong competition demo.*

### Phase 2 — Full three pillars + WhatsApp + voice (1–2 weeks)
- Add **WhatsApp adapter** (Cloud API/Twilio) — same core engine.
- Add **voice**: STT (Whisper) + TTS (edge-tts).
- Add **profile onboarding** + personalization.
- Build **Pillar 2** (eligibility Q-tree) and **Pillar 3** (weekly poll + Sheets/Supabase storage).
- Stand up the **dashboard** (Looker Studio / Streamlit).

### Phase 3 — Pilot, evaluation & polish (ongoing)
- **Accuracy eval:** write ~50 test questions with known correct answers from the report; measure grounded-answer rate and guardrail catches (target: 0 ungrounded numbers reach the user).
- **User testing** with ~10–20 people (friends/classmates) for clarity of the Egyptian-Arabic tone.
- Add more Ledger entries, tune retrieval (k, thresholds), refine prompts.
- Prepare the pitch: live demo + the architecture story (grounding + resilience).

---

## 13. Success metrics (what you'll show judges)

- **Factual accuracy:** % of answers fully grounded in the report; number of hallucinated figures that reached a user (**target: 0**, enforced by the guardrail).
- **Coverage:** number of budget topics answerable (health, education, subsidies, taxes, wages, debt, fiscal risks, PPP, social protection…).
- **Accessibility:** voice in/out working in Egyptian Arabic.
- **Participation:** poll responses collected in the pilot (a direct dent in the 35/100 KPI).
- **Cost:** 0 EGP, demonstrably.

---

## 14. Risks & mitigations

| Risk | Mitigation |
|---|---|
| **LLM hallucinates a number** | Facts Ledger + grounded prompt + **numeric guardrail** (blocks ungrounded figures). |
| **Arabic PDF extraction garbles digits** | Never trust extracted numbers; the Ledger is hand-verified. |
| **Egyptian-Arabic tone feels robotic** | Few-shot examples in the prompt (Appendix C) + user testing to tune. |
| **Free LLM daily quota hit** | Route Pillar 2/3 through deterministic logic (no LLM); Groq as a second free key; cache common answers. |
| **WhatsApp becomes paid (Oct 2026)** | Channel-agnostic engine; Telegram is free forever; demo before the date. |
| **Host cold-starts / downtime** | Oracle always-free VM (no sleep) or HF Spaces; keep webhook lightweight. |
| **Scope creep before deadline** | Ship Phase 1 (text, Telegram, Pillar 1) first — it's already demoable. |
| **Sensitive-data risk in Pillar 2** | Ask nothing sensitive; store nothing; hand off to official channels. |

---

## 15. Future scaling (beyond the competition)

- **More channels:** Facebook Messenger, a web widget, IVR phone line (for non-smartphone users).
- **Live data:** connect to the Ministry's published data feeds so figures update automatically each budget cycle (with human verification).
- **Participatory budgeting integration:** the report describes the National Participatory Budgeting Model rolling out to 27 governorates — Pillar 3 could feed real citizen priorities into those sessions.
- **Multi-year memory:** let citizens compare this year's budget to last year's.
- **Analytics for policymakers:** sentiment trends by topic/governorate to inform the Citizen Budget report itself.

---

# Appendices

## Appendix A — Facts Ledger starter data (verified from the report)

> These figures are extracted from *Citizen Budget 2026/2027*. **Re-confirm each against the PDF before shipping** (this is the human-verification step). Values are for FY **2026/2027** unless noted.

**Headline budget figures**
- Total **expenditures**: **5,187,975 million EGP** (~5.2 trillion) — (Financial Profile table, p.12)
- Total **revenues**: **4,056,375 million EGP** (~4.1 trillion) — (p.12/p.38)
- Total **tax revenue**: **3,529,294 million EGP** (~3.5 trillion) — (p.12/p.38)
- **Primary surplus** target: **~1.2 trillion EGP (5% of GDP)** — (p.13)
- **Overall deficit** target: **4.9% of GDP** (down ~2.4 pts) — (p.13)
- **Budget-sector debt** target: **78.1% of GDP by June 2027** (from ~84.2% June 2026) — (p.13/p.53)
- GDP (market price) target: **24.5 trillion EGP** — (p.11)
- Real GDP growth target: **5.4%** — (p.11)
- Inflation (deflator) target: **9.3%** — (p.11)
- Unemployment target: **6.2%** — (p.11)

**Wages & social protection**
- **Wages & compensation**: **822.8 billion EGP** (+143.7B, ~21.2% YoY, highest in 10 yrs) — (p.19)
- Public-sector wage increase from **1 July 2026**, total cost **~100 billion EGP** — (p.19)
- **Minimum wage** raised to **8,000 EGP** — (p.19)
- **Subsidies, grants & social benefits**: **836.8 billion EGP** (+12.7% YoY) — (p.20)
- **Electricity subsidy**: **104.2 billion EGP** (+39%) — (p.20)
- **Ration/food-commodity subsidy**: **178.3 billion EGP** (+11.4%, 60M+ citizens) — (p.20)
- **Takaful & Karama + equal-opportunity program**: **55.2 billion EGP**, **4.7 million families** — (p.21)
- Ramadan 2026 social package: **40.3 billion EGP** — (p.25)

**Health & education (constitutional entitlements)**
- **Health allocation**: **862.9 billion EGP** (4.2% of GDP, **+39.6%**) — (p.26–27)
- **Education allocation**: **1,229.7 billion EGP** (6% of GDP, **+17.9%**) — (p.26/p.31)
- **Scientific research**: **205.2 billion EGP** (1% of GDP) — (p.26)
- Unified Procurement Authority: **90.5 billion EGP** (+25%/yr) — (p.26)
- State-funded treatment: **47.5 billion EGP** (+69%) — (p.26)

**Economic-activity support programs (total 90 billion EGP)** — (p.14)
- Export burden refund / exporter support: **48 billion EGP**
- Tourism sector support: **6.7 billion EGP**
- Production-sector facilities financing: **6 billion EGP**
- Car industry (green vehicles): **5.5 billion EGP**
- SME/entrepreneurship cash incentives: **5 billion EGP**
- Priority-industry incentives: **2 billion EGP**

**Tax reform & debt**
- Revenue increase target: **+~875 billion EGP** in tax revenue — (p.38)
- Tax-to-GDP target: **14.4%** (10-year high) — (p.42)
- Target: onboard **100,000 new taxpayers** to the simplified system — (p.42)
- **Citizen Bond (سند المواطن):** net-of-tax annual yield **17.75%**, monthly payout, **18 months**, min investment **10,000 EGP**, face value **1,000 EGP** — (p.51)
- VAT on medical devices cut **14% → 5%** — (p.40)
- Real-estate self-use exemption raised **2M → 8M EGP** — (p.43)

**Transparency KPIs (OBS 2025, published June 2026)**
- Transparency **59/100**, Oversight **59/100**, Public Participation **35/100** — (p.55)
- Egypt ranked **#22–23** globally on transparency (▲10 pts) — (p.56/p.62)

> *(Copy these into `facts_ledger.json` in the schema shown in §4①, adding `keywords` for retrieval.)*

---

## Appendix B — Grounded system prompt (drop-in)

```
أنت "حسبتك"، المساعد الرقمي لموازنة المواطن المصري لوزارة المالية.
مهمتك: تشرح معلومات الموازنة بالعامية المصرية البسيطة والودودة.

قواعد صارمة لازم تلتزم بيها:
1. جاوب فقط من المعلومات الموجودة في [الأرقام المؤكدة] و[السياق] التحت.
2. ممنوع تمامًا تخترع أو تحسب أو تتوقع أي رقم مش موجود صراحة في المصدر.
3. أي رقم بتقوله لازم يكون موجود في [الأرقام المؤكدة]. لو مش موجود، ماتقولوش.
4. لو المعلومة مش موجودة في السياق، قول بصراحة: "المعلومة دي مش متأكد منها
   حاليًا، بس تقدر تلاقيها في التقرير الرسمي على mof.gov.eg" — وماتخمنش.
5. اكتب بالعامية المصرية، مختصر وواضح (2–4 جمل)، من غير مصطلحات معقدة.
6. في آخر أي إجابة فيها رقم، ضيف سطر المصدر، مثال:
   "📄 المصدر: تقرير موازنة المواطن 2026/2027، قسم الصحة".
7. لو المستخدم اختار نوعه (طالب/موظف/صاحب مشروع)، اضرب أمثلة تخصه.

[الأرقام المؤكدة]
{facts_json_here}

[السياق]
{retrieved_chunks_here}

[نوع المستخدم]: {user_profile}
[سؤال المستخدم]: {user_question}
```

---

## Appendix C — Few-shot tone examples (Egyptian Arabic)

```
مثال 1
المستخدم: فلوس الصحة بقت كام السنة دي؟
حسبتك: مخصصات الصحة في موازنة 2026/2027 بقت 862.9 مليار جنيه، بزيادة 39.6%
عن السنة اللي فاتت — يعني تقريبًا 4.2% من الناتج المحلي. 💙
📄 المصدر: تقرير موازنة المواطن 2026/2027، قسم الصحة.

مثال 2 (المستخدم طالب)
المستخدم: في حاجة ليا كطالب؟
حسبتك: أيوة! في مخصصات لدعم التأمين الصحي للطلبة، ودعم لاشتراكات الطلبة في
القطارات والمترو. عايز أفصّلك واحدة منهم؟
📄 المصدر: تقرير موازنة المواطن 2026/2027.

مثال 3 (معلومة مش موجودة)
المستخدم: ميزانية وزارة كذا كام بالظبط؟
حسبتك: الرقم ده مش متأكد منه حاليًا، بس تقدر تلاقي تفاصيل الموازنة الرسمية
على mof.gov.eg. 🙏
```

---

## Appendix D — Eligibility Q-tree skeleton (Pillar 2)

```yaml
start:
  message_ar: "أهلاً! أقدر أساعدك تعرف عن برامج الحماية الاجتماعية. تحب تعرف عن إيه؟"
  options:
    - label_ar: "دعم نقدي (تكافل وكرامة)"
      goto: takaful
    - label_ar: "دعم السلع التموينية"
      goto: rations
    - label_ar: "التأمين الصحي الشامل"
      goto: health_insurance

takaful:
  info_ar: >
    برنامج تكافل وكرامة بيقدم دعم نقدي للأسر الأولى بالرعاية.
    في موازنة 2026/2027 مخصصله 55.2 مليار جنيه ويستفيد منه حوالي 4.7 مليون أسرة.
  action_ar: >
    التقديم والاستعلام بيكون من خلال وزارة التضامن الاجتماعي أو أقرب وحدة اجتماعية.
  disclaimer_ar: "ℹ️ دي معلومة استرشادية — القرار النهائي بيكون من الجهة الرسمية."
  official_channel: "وزارة التضامن الاجتماعي / أقرب مكتب تضامن"

rations:
  info_ar: >
    دعم السلع التموينية في موازنة 2026/2027 مخصصله 178.3 مليار جنيه
    ويستفيد منه أكتر من 60 مليون مواطن.
  action_ar: "الاستعلام عن البطاقة التموينية من خلال منظومة الدعم/تموين مصر."
  disclaimer_ar: "ℹ️ دي معلومة استرشادية — القرار النهائي بيكون من الجهة الرسمية."

health_insurance:
  info_ar: >
    منظومة التأمين الصحي الشامل بتتطبق تدريجيًا على المحافظات،
    والخزانة العامة بتتحمل اشتراكات غير القادرين.
  action_ar: "الاستعلام من خلال هيئة التأمين الصحي الشامل."
  disclaimer_ar: "ℹ️ دي معلومة استرشادية — القرار النهائي بيكون من الجهة الرسمية."
```

> **Rule:** Pillar 2 never asks for ID number, income, or household details, and stores nothing.

---

## Appendix E — Suggested repository structure

```
hasebtak/
├── README.md
├── requirements.txt
├── .env.example              # keys as placeholders (never commit real .env)
├── .gitignore
├── data/
│   ├── source_pdf/           # the citizen budget PDF
│   ├── facts_ledger.json     # ← hand-verified numbers (source of truth)
│   ├── eligibility_tree.yaml
│   └── poll_bank.json
├── ingestion/
│   ├── extract.py            # pdftotext + clean + normalize (Arabic)
│   ├── chunk.py              # section-aware chunking
│   └── embed_index.py        # build ChromaDB
├── core/
│   ├── router.py             # intent + topic detection, pillar routing
│   ├── grounding.py          # ledger lookup + RAG retrieval
│   ├── prompt.py             # grounded prompt assembly
│   ├── guardrail.py          # numeric guardrail (blocks ungrounded numbers)
│   ├── llm.py                # Gemini/Groq client (with fallback)
│   ├── voice.py              # STT (whisper) + TTS (edge-tts)
│   ├── eligibility.py        # Pillar 2 Q-tree engine
│   └── polls.py              # Pillar 3 poll + storage
├── channels/
│   ├── base.py               # neutral message interface
│   ├── telegram_adapter.py   # free-forever channel
│   └── whatsapp_adapter.py   # Cloud API / Twilio
├── dashboard/
│   └── app.py                # Streamlit analytics (or use Looker Studio)
├── tests/
│   └── eval_questions.json   # ~50 Q&A for accuracy testing
└── app.py                    # FastAPI webhook entrypoint
```

---

## Appendix F — Minimal grounded-answer pseudocode (the core loop)

```python
def answer_budget_question(user_text, user_profile):
    # 1. find verified figures for this topic
    facts = facts_ledger.lookup(user_text)            # exact numbers + sources
    # 2. retrieve narrative context
    chunks = vector_store.search(user_text, k=4)      # explanations
    # 3. build a strictly grounded prompt
    prompt = build_grounded_prompt(facts, chunks, user_profile, user_text)
    # 4. generate
    draft = llm.generate(prompt)                      # Gemini free tier
    # 5. SAFETY NET: block any number not present in facts/chunks
    if guardrail.has_ungrounded_number(draft, facts, chunks):
        return SAFE_FALLBACK_AR                        # never ship an invented figure
    return draft
```

---

### Final note
Start with **Phase 1** — a text-only Telegram bot answering budget questions accurately with sources. It is fully free, buildable in under a week, and already a compelling competition demo. Everything else (voice, WhatsApp, eligibility, polls, dashboard) layers cleanly on top of the same core engine.

**The story you tell judges:** *"We didn't just build a chatbot — we built one that cannot lie about public money, works on the app every Egyptian already uses, costs nothing, and survives WhatsApp's pricing changes. It directly attacks the one budget-transparency score Egypt hasn't moved: public participation."*
