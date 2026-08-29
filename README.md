# Revenue Autopilot

**Detect. Decide. Recover. Verify.**

Production-style fintech prototype for **AI Revenue Recovery**, with a secondary path into **AI Growth & Agentic Commerce**.

> This prototype uses synthetic/test-mode financial data and does not move real money.

## Problem

Failed payments, retries, and checkout abandonment leak GMV. Teams see dashboards, not a closed loop that can **detect** leakage, **explain** it, **decide** whether an action is safe, **recover** in a bounded way, and **verify** that recovered revenue is real.

## Business impact

Operators get:

- ₹ revenue at risk from actual failed/abandoned events
- ₹ revenue recovered only after the recovery simulator confirms success
- Recovery rate, human escalations, and stopped actions from the same pipeline
- Proof the system is not blindly autonomous (unsafe retries are blocked)

## Solution

EVENT → DETECT → INVESTIGATE → ROOT CAUSE → MONEYGUARD → POLICY CHECK → RECOVERY → VERIFICATION → METRICS → AUDIT

Every workflow has a `trace_id`. Agents return structured data (not chat). An optional LLM provider exists, but **no API key is required**.

## Architecture

- **Frontend:** React + TypeScript + Vite + Recharts (ops dashboard)
- **Backend:** FastAPI + Pydantic + Uvicorn
- **Data:** SQLite locally; `DATABASE_URL` can be PostgreSQL for Render
- **Simulator:** Pandas/NumPy synthetic transactions with ground truth
- **ML assist:** scikit-learn IsolationForest as supporting evidence only

```
EVENT
  → Revenue Detector
  → Payment Investigator + Customer Agent
  → Root Cause Agent
  → MoneyGuard
  → Policy Engine
  → Recovery Simulator (test mode)
  → Verification Agent
  → Metrics + Audit trail
```

## Multi-agent system

| Agent | Role |
| --- | --- |
| Revenue Detector | Revenue at risk, clusters, confidence, evidence |
| Payment Investigator | Gateway/method/failure/baseline/retries |
| Customer Agent | Intent, conversion and recovery probability |
| Root Cause | Combines evidence into a named cause |
| MoneyGuard | Allow, stop, or escalate — never executes money movement |
| Policy Engine | Deterministic authorization |
| Verification | Confirms simulator outcome before counting recovered ₹ |

## MoneyGuard

AI can **propose**. MoneyGuard **evaluates**. Policy **authorizes**. The simulator **executes in test mode**. Verification **confirms**.

Rules (deterministic):

- HIGH RISK → HUMAN_REVIEW
- LOW CONFIDENCE → HUMAN_REVIEW
- SUSPICIOUS RETRY → STOP
- VERY HIGH VALUE (single transaction) → HUMAN_REVIEW
- DUPLICATE ACTION → STOP
- HIGH CONFIDENCE + LOW RISK → bounded recovery action

## Policy Engine

Evaluates risk, confidence, amount, retry count, customer risk, duplicate-action risk, and action type. Returns `allowed`, `action`, `risk_level`, `requires_human_review`, `reason`.

## Recovery engine

Test-mode only. Actions: `SAFE_RETRY`, `ALTERNATE_PAYMENT`, `PERSONALIZED_OFFER`, `RECOVERY_MESSAGE`, `STOP`, `HUMAN_REVIEW`. Success is simulated from root cause + action. Revenue is counted only if verification agrees.

## Verification

Checks payment outcome, recovered amount, duplicate recovery, policy compliance. Never claims recovery without simulator confirmation.

## Synthetic data

Statuses: `PAYMENT_STARTED`, `PAYMENT_SUCCESS`, `PAYMENT_FAILED`, `PAYMENT_RETRY`, `CHECKOUT_ABANDONED`, `SETTLEMENT_PENDING`, `SETTLEMENT_COMPLETED`.

Scenarios: gateway degradation (4–5% → 15–20%), high-value checkout abandonment, repeated failures, suspicious retries, legitimate anomalies. Ground truth is stored for evaluation. Sizes: 100 / 1,000 / 10,000 / 50,000.

## Evaluation

Precision, recall, root-cause accuracy, recovery success rate, false intervention rate, human escalation rate, revenue at risk detected, revenue recovered — all from data.

## Metrics

Computed from the database: GMV, transactions, revenue at risk, potential recovery, revenue recovered, recovery rate, successful interventions, human escalations, stopped actions, false interventions, average investigation time. **Not hard-coded.**

## Installation

Requires Python 3.11+ and Node 20+.

```bash
cd revenue-autopilot
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env   # or cp .env.example .env
```

## Backend setup

From the repository root:

```bash
uvicorn backend.main:app --reload --port 8000
```

API: http://127.0.0.1:8000  
Docs: http://127.0.0.1:8000/docs  
Health: http://127.0.0.1:8000/health

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

UI: http://127.0.0.1:5173  

Vite proxies `/api` and `/health` to the backend. For a deployed API set `VITE_API_URL`.

## Demo instructions

1. Start backend and frontend.
2. Open the dashboard.
3. Click **Run live demo**.
4. **Demo A** injects gateway degradation; MoneyGuard may approve alternate payment; verification may credit recovered ₹.
5. **Demo B** injects suspicious retries; MoneyGuard/policy stop automatic action; recovered ₹ stays 0.
6. Inspect Incidents → investigation pipeline and audit trail.
7. Open Evaluation for ground-truth scores.

## Screenshots

Capture the dashboard KPIs, live demo timeline, incident investigation pipeline, and evaluation page after running the live demo.

## Limitations

- No production payment processor, bank, or refunds
- No real customer PII
- LLM is optional and unused unless `OPENAI_API_KEY` is set
- Recovery outcomes are simulated
- SQLite is for local/hackathon use

## Future roadmap

- PostgreSQL on Render + Vercel frontend
- Merchant SSO and role-based review queues
- Webhooks from sandbox gateways
- Offer catalog for personalized recovery
- Longer-horizon causal evaluation

## Hackathon track

**Primary:** AI Revenue Recovery  
**Secondary:** AI Growth & Agentic Commerce

## Deployment readiness

- Frontend: Vercel (`frontend/`, SPA rewrite in `vercel.json`)
- Backend: Render / Docker (`Dockerfile`, `docker-compose.yml`)
- Database: set `DATABASE_URL` to PostgreSQL; SQLAlchemy models are dialect-friendly

Local functionality is the default. Do not connect production money rails.
