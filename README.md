# Revenue Autopilot

[![Deploy to Render](https://render.com/images/deploy-to-render.svg)](https://render.com/deploy?repo=https://github.com/sriyathid-commits/revenue-autopilot)

> **AI proposes. MoneyGuard evaluates. Policy authorizes. Simulator executes. Verification confirms.**

**Live demo:** https://revenue-autopilott.vercel.app  
**Backend API:** https://revenue-autopilot-backend.onrender.com  
**API docs:** https://revenue-autopilot-backend.onrender.com/docs

> This prototype uses synthetic/test-mode financial data and **does not move real money.**

---

## Problem

Failed payments, retries, and checkout abandonment leak GMV silently. Operations teams see dashboards but lack a closed loop that can **detect** leakage, **investigate** the cause, **decide** whether recovery is safe, **execute** it in a bounded way, and **verify** the outcome.

---

## Solution

A multi-agent AI pipeline with deterministic safety controls — every recovery proposal goes through MoneyGuard before any action is authorized.

```
EVENT
  → Revenue Detector        (detects at-risk clusters)
  → Payment Investigator     (gateway/method/failure analysis)
  → Customer Analyst         (intent + recovery probability)
  → Root Cause Agent         (combines evidence → named cause)
  → MoneyGuard               (AI SAFETY BOUNDARY — evaluates proposal)
  → Policy Engine            (deterministic authorization)
  → Recovery Simulator       (test-mode execution)
  → Verification Agent       (confirms outcome, counts recovered ₹)
  → Metrics + Audit trail
```

---

## Key Features

- **Multi-agent investigation** — 8 specialized agents, each with structured evidence
- **Revenue-at-risk detection** — IsolationForest + rule-based clustering
- **AI recovery proposals** — deterministic + optional LLM fallback
- **MoneyGuard** — safety boundary; AI can never directly authorize money movement
- **Policy Engine** — deterministic rules: risk, confidence, amount, retries
- **Human Review queue** — uncertain/high-risk incidents routed to manual approval
- **Audit trail** — full decision trace per incident, with agent confidence bars
- **Real-time WebSocket stream** — live incident/transaction/agent events
- **Idempotency** — duplicate recovery attempts are detected and blocked
- **Test-mode recovery** — deterministic simulation, no real payment rails

---

## Demo A — Recoverable Revenue

Gateway degradation on Razorpay test → Revenue Detector flags cluster → MoneyGuard approves alternate payment route → Policy authorizes → Simulator executes → Verification confirms → **₹ recovered**.

## Demo B — Unsafe Action Blocked

Suspicious rapid retries → Root Cause identifies risk signal → **MoneyGuard says STOP** → Policy blocks automatic action → Simulator executes NO_ACTION → **₹0 recovered**. This proves the system does not blindly retry every failure.

---

## Architecture

| Layer | Technology |
|---|---|
| Frontend | React + TypeScript + Vite + Recharts |
| Backend | FastAPI + Pydantic + Uvicorn |
| Real-time | WebSocket + asyncio event bus |
| Database | SQLite (local/Render) — `DATABASE_URL` for PostgreSQL |
| Simulator | Pandas + NumPy synthetic transactions with ground truth |
| ML assist | scikit-learn IsolationForest (supporting evidence only) |

---

## Multi-Agent System

| Agent | Role |
|---|---|
| Revenue Detector | Revenue at risk, clusters, confidence, evidence |
| Payment Investigator | Gateway/method/failure/baseline/retries |
| Customer Analyst | Intent, conversion and recovery probability |
| Root Cause | Combines evidence into a named cause |
| MoneyGuard | Allow, stop, or escalate — **never executes money movement** |
| Policy Engine | Deterministic authorization |
| Recovery Simulator | Test-mode execution |
| Verification | Confirms simulator outcome before counting recovered ₹ |

---

## MoneyGuard Rules (Deterministic)

- HIGH RISK → HUMAN_REVIEW
- LOW CONFIDENCE → HUMAN_REVIEW
- SUSPICIOUS RETRY → STOP
- VERY HIGH VALUE → HUMAN_REVIEW
- DUPLICATE ACTION → STOP
- HIGH CONFIDENCE + LOW RISK → bounded recovery action

---

## Local Setup

Requires Python 3.11+ and Node 20+.

```bash
# Backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
copy .env.example .env
uvicorn backend.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

- API: http://127.0.0.1:8000
- Docs: http://127.0.0.1:8000/docs
- UI: http://127.0.0.1:5173

---

## Deployment

- **Frontend:** Vercel — root directory `frontend`, env var `VITE_API_URL=<render-url>`
- **Backend:** Render — Docker, `render.yaml` blueprint

---

## Safety

- Synthetic/test-mode data only
- No real payment processor, bank, or refunds
- No real customer PII
- LLM is optional — app works fully without `OPENAI_API_KEY`
- Recovery outcomes are simulated deterministically
- MoneyGuard + Policy Engine are deterministic layers — AI cannot bypass them

---

## Hackathon Track

**Primary:** AI Revenue Recovery  
**Secondary:** AI Growth & Agentic Commerce
