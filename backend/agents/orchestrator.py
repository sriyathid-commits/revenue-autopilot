"""EVENT → DETECT → INVESTIGATE → ROOT CAUSE → MONEYGUARD → POLICY → RECOVERY → VERIFY."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from backend.agents import safe_agent
from backend.agents.customer_agent import analyze_customers
from backend.agents.moneyguard_agent import evaluate_moneyguard
from backend.agents.payment_agent import investigate_payments
from backend.agents.revenue_agent import detect_revenue_risk
from backend.agents.rootcause_agent import identify_root_cause
from backend.agents.verification_agent import verify_recovery
from backend.models.agent_result import AgentResult
from backend.models.transaction import RecoveryAction, RecoveryStatus
from backend.policies.policy_engine import policy_engine
from backend.services.audit_service import log_audit
from backend.services.database import AgentResultRow, IncidentRow, TransactionRow
from backend.services.recovery_service import simulate_recovery
from backend.services.transaction_service import (
    incident_has_recovery,
    mark_detected,
    mark_recovery,
    parse_ids,
)


def new_trace_id() -> str:
    return "tr_" + uuid.uuid4().hex[:16]


def new_incident_id() -> str:
    return "inc_" + uuid.uuid4().hex[:12]


def persist_agent(session: Session, result: AgentResult) -> None:
    session.add(
        AgentResultRow(
            agent=result.agent,
            trace_id=result.trace_id,
            incident_id=result.incident_id,
            confidence=result.confidence,
            decision=result.decision,
            explanation=result.explanation,
            evidence_json=json.dumps(result.evidence, default=str),
            payload_json=json.dumps(result.payload, default=str),
            timestamp=result.timestamp,
            ok=result.ok,
            error=result.error,
        )
    )


def run_batch(session: Session, transactions: list[dict[str, Any]] | None = None, max_incidents: int = 12) -> list[dict[str, Any]]:
    if transactions is None:
        rows = session.query(TransactionRow).all()
        from backend.services.transaction_service import row_to_transaction

        transactions = [row_to_transaction(r).model_dump() for r in rows]
    detection = detect_revenue_risk(transactions)
    clusters = detection.get("clusters") or []
    results = []
    for cluster in clusters[:max_incidents]:
        results.append(run_incident_pipeline(session, transactions, cluster, detection))
    return results


def run_incident_pipeline(
    session: Session,
    transactions: list[dict[str, Any]],
    cluster: dict[str, Any],
    detection: dict[str, Any] | None = None,
    scenario: str | None = None,
    execute: bool = True,
) -> dict[str, Any]:
    trace_id = new_trace_id()
    incident_id = new_incident_id()
    steps: list[dict[str, Any]] = []
    now = datetime.utcnow()
    tx_ids = list(cluster.get("transaction_ids") or [])
    amount = float(cluster.get("revenue_at_risk") or 0.0)
    merchant = "unknown"
    if tx_ids:
        focus = [t for t in transactions if t["transaction_id"] in set(tx_ids)]
        if focus:
            merchant = str(focus[0].get("merchant_id") or "unknown")
            if not scenario:
                scenario = focus[0].get("scenario")
    else:
        focus = []

    detection = detection or detect_revenue_risk(transactions)
    rev = safe_agent(
        "revenue_detector",
        trace_id,
        incident_id,
        lambda: {
            **detection,
            "revenue_at_risk": amount or detection.get("revenue_at_risk"),
            "affected_transactions": tx_ids or detection.get("affected_transactions"),
        },
        {"revenue_at_risk": amount, "affected_transactions": tx_ids, "confidence": 0.4, "reason": "fallback"},
    )
    persist_agent(session, rev)
    log_audit(session, trace_id=trace_id, incident_id=incident_id, agent=rev.agent, event="ANOMALY_DETECTED", decision=rev.decision, evidence=rev.evidence)
    log_audit(session, trace_id=trace_id, incident_id=incident_id, agent=rev.agent, event="REVENUE_RISK_CALCULATED", decision=str(amount), evidence={"revenue_at_risk": amount})
    steps.append(_step("ANOMALY DETECTED", rev))
    steps.append(_step("REVENUE AT RISK IDENTIFIED", rev, extra=f"₹{amount:,.2f}"))

    pay = safe_agent(
        "payment_investigator",
        trace_id,
        incident_id,
        lambda: investigate_payments(transactions, cluster),
        {"root_cause_candidates": ["unknown"], "confidence": 0.3, "evidence": {}, "decision": "unknown"},
    )
    persist_agent(session, pay)
    log_audit(session, trace_id=trace_id, incident_id=incident_id, agent=pay.agent, event="PAYMENT_INVESTIGATION", decision=pay.decision, evidence=pay.evidence)
    steps.append(_step("PAYMENT INVESTIGATION", pay))

    cust = safe_agent(
        "customer_agent",
        trace_id,
        incident_id,
        lambda: analyze_customers(transactions, cluster),
        {"intent": "unknown", "confidence": 0.3, "recovery_probability": 0.2},
    )
    persist_agent(session, cust)
    log_audit(session, trace_id=trace_id, incident_id=incident_id, agent=cust.agent, event="CUSTOMER_ANALYSIS", decision=cust.decision, evidence=cust.evidence)
    steps.append(_step("CUSTOMER ANALYSIS", cust))

    rc = safe_agent(
        "root_cause",
        trace_id,
        incident_id,
        lambda: identify_root_cause(pay.payload, cust.payload, rev.payload, cluster),
        {"root_cause": "unknown", "confidence": 0.3, "evidence": {}, "explanation": "fallback"},
    )
    persist_agent(session, rc)
    log_audit(session, trace_id=trace_id, incident_id=incident_id, agent=rc.agent, event="ROOT_CAUSE_IDENTIFIED", decision=rc.decision, evidence=rc.evidence)
    steps.append(_step("ROOT CAUSE FOUND", rc))

    root_cause = str(rc.payload.get("root_cause") or "unknown")
    confidence = float(rc.payload.get("confidence") or rc.confidence)
    risk_score = float(cluster.get("max_risk") or (max((t.get("risk_score") or 0) for t in focus) if focus else 0.2))
    retry_count = int(cluster.get("max_retry") or (max((t.get("retry_count") or 0) for t in focus) if focus else 0))
    unit_amount = max((float(t.get("amount") or 0) for t in focus), default=amount)
    suspicious = bool(cluster.get("suspicious") or root_cause == "risk_signal")
    duplicate = incident_has_recovery(session, tx_ids)
    recovery_p = float(cust.payload.get("recovery_probability") or 0.3)

    mg = safe_agent(
        "moneyguard",
        trace_id,
        incident_id,
        lambda: evaluate_moneyguard(
            root_cause=root_cause,
            confidence=confidence,
            risk_score=risk_score,
            amount=unit_amount,
            retry_count=retry_count,
            suspicious_retry=suspicious,
            duplicate_action=duplicate,
            customer_recovery_probability=recovery_p,
        ),
        {"approved": False, "action": "HUMAN_REVIEW", "reason": "fallback", "decision": "HUMAN_REVIEW"},
    )
    persist_agent(session, mg)
    log_audit(
        session,
        trace_id=trace_id,
        incident_id=incident_id,
        agent=mg.agent,
        event="MONEYGUARD_DECISION",
        decision=mg.decision,
        evidence=mg.evidence,
        action=str(mg.payload.get("action")),
        result=str(mg.payload.get("reason")),
    )
    steps.append(_step("MONEYGUARD", mg))

    proposed = RecoveryAction(str(mg.payload.get("action") or "HUMAN_REVIEW"))
    policy = policy_engine.evaluate(
        proposed_action=proposed,
        risk_score=risk_score,
        confidence=confidence,
        amount=unit_amount,
        retry_count=retry_count,
        customer_risk=risk_score,
        duplicate_action=duplicate,
        suspicious_retry=suspicious,
        root_cause=root_cause,
    )
    pol_payload = {
        "allowed": policy.allowed,
        "action": policy.action.value,
        "risk_level": policy.risk_level,
        "requires_human_review": policy.requires_human_review,
        "reason": policy.reason,
        "checks": policy.checks,
        "decision": policy.action.value,
        "explanation": policy.reason,
        "confidence": confidence,
        "evidence": policy.checks,
    }
    pol = AgentResult(
        agent="policy_engine",
        trace_id=trace_id,
        incident_id=incident_id,
        confidence=confidence,
        decision=policy.action.value,
        explanation=policy.reason,
        evidence=policy.checks,
        payload=pol_payload,
        timestamp=datetime.utcnow(),
        ok=True,
    )
    persist_agent(session, pol)
    log_audit(
        session,
        trace_id=trace_id,
        incident_id=incident_id,
        agent=pol.agent,
        event="POLICY_DECISION",
        decision=pol.decision,
        evidence=policy.checks,
        action=policy.action.value,
        result=policy.reason,
    )
    steps.append(_step("POLICY DECISION", pol))

    sim = {"success": False, "revenue_recovered": 0.0, "action": policy.action.value, "payment_outcome": "NO_ACTION", "policy_compliant": True}
    if execute:
        sim = simulate_recovery(
            action=policy.action.value,
            root_cause=root_cause,
            amount=amount,
            allowed=policy.allowed,
            transaction_count=max(1, len(tx_ids)),
        )
    rec = AgentResult(
        agent="recovery_simulator",
        trace_id=trace_id,
        incident_id=incident_id,
        confidence=0.9,
        decision=sim.get("payment_outcome") or "NO_ACTION",
        explanation=str(sim.get("explanation") or ""),
        evidence=sim,
        payload=sim,
        timestamp=datetime.utcnow(),
        ok=True,
    )
    persist_agent(session, rec)
    log_audit(
        session,
        trace_id=trace_id,
        incident_id=incident_id,
        agent=rec.agent,
        event="RECOVERY_EXECUTED",
        decision=rec.decision,
        evidence=sim,
        action=policy.action.value,
        result=str(sim.get("payment_outcome")),
    )
    steps.append(_step("RECOVERY", rec, extra=str(sim.get("payment_outcome"))))

    ver_payload = verify_recovery(
        simulator_result=sim,
        policy_allowed=policy.allowed,
        moneyguard_approved=bool(mg.payload.get("approved")),
        duplicate=duplicate,
    )
    ver = AgentResult(
        agent="verification",
        trace_id=trace_id,
        incident_id=incident_id,
        confidence=float(ver_payload.get("confidence") or 0.9),
        decision=str(ver_payload.get("final_status")),
        explanation=str(ver_payload.get("explanation") or ""),
        evidence=dict(ver_payload.get("evidence") or {}),
        payload=ver_payload,
        timestamp=datetime.utcnow(),
        ok=True,
    )
    persist_agent(session, ver)
    recovered = float(ver_payload.get("revenue_recovered") or 0.0)
    log_audit(
        session,
        trace_id=trace_id,
        incident_id=incident_id,
        agent=ver.agent,
        event="RECOVERY_VERIFIED",
        decision=ver.decision,
        evidence=ver.evidence,
        action=policy.action.value,
        result=f"revenue_recovered={recovered}",
    )
    extra = f"₹{recovered:,.2f}" if recovered else ver.decision
    steps.append(_step("VERIFICATION", ver, extra=extra))
    if recovered > 0:
        steps.append(
            {
                "title": "REVENUE RECOVERED",
                "agent": "verification",
                "status": "VERIFIED",
                "confidence": ver.confidence,
                "evidence": ver.evidence,
                "explanation": f"Test-mode recovered ₹{recovered:,.2f}",
                "decision": f"₹{recovered:,.2f}",
            }
        )

    status = RecoveryStatus.VERIFIED if recovered > 0 else RecoveryStatus(policy.action.value if policy.action in {RecoveryAction.STOP, RecoveryAction.HUMAN_REVIEW} else RecoveryStatus.FAILED)
    if policy.action == RecoveryAction.STOP:
        status = RecoveryStatus.BLOCKED
    elif policy.action == RecoveryAction.HUMAN_REVIEW:
        status = RecoveryStatus.HUMAN_REVIEW
    elif recovered > 0:
        status = RecoveryStatus.VERIFIED
    elif policy.allowed:
        status = RecoveryStatus.FAILED

    incident = IncidentRow(
        incident_id=incident_id,
        merchant_id=merchant,
        amount=amount,
        currency="INR",
        root_cause=root_cause,
        risk_level=str(mg.payload.get("risk_level") or policy.risk_level),
        action=policy.action.value,
        status=status.value,
        trace_id=trace_id,
        scenario=scenario,
        revenue_at_risk=amount,
        revenue_recovered=recovered,
        confidence=confidence,
        transaction_ids_json=json.dumps(tx_ids),
        explanation=str(rc.payload.get("explanation") or ""),
        moneyguard_reason=str(mg.payload.get("reason") or ""),
        policy_reason=policy.reason,
        verified=bool(ver_payload.get("verified")),
        created_at=now,
        updated_at=datetime.utcnow(),
    )
    session.add(incident)
    mark_detected(session, tx_ids, root_cause)
    mark_recovery(session, tx_ids, policy.action.value, status.value)
    session.flush()

    return {
        "incident_id": incident_id,
        "trace_id": trace_id,
        "scenario": scenario,
        "root_cause": root_cause,
        "action": policy.action.value,
        "status": status.value,
        "revenue_at_risk": amount,
        "revenue_recovered": recovered,
        "risk_level": incident.risk_level,
        "confidence": confidence,
        "merchant_id": merchant,
        "steps": steps,
        "moneyguard_reason": incident.moneyguard_reason,
        "policy_reason": incident.policy_reason,
        "verified": incident.verified,
    }


def _step(title: str, result: AgentResult, extra: str | None = None) -> dict[str, Any]:
    return {
        "title": title,
        "agent": result.agent,
        "status": "ok" if result.ok else "fallback",
        "confidence": result.confidence,
        "evidence": result.evidence,
        "explanation": result.explanation,
        "decision": extra or result.decision,
        "error": result.error,
    }


def rerun_recovery(session: Session, incident_id: str) -> dict[str, Any]:
    inc = session.query(IncidentRow).filter(IncidentRow.incident_id == incident_id).one_or_none()
    if not inc:
        raise KeyError(incident_id)
    ids = parse_ids(inc.transaction_ids_json)
    from backend.services.transaction_service import transactions_as_dicts

    txs = transactions_as_dicts(session, ids)
    all_txs = transactions_as_dicts(session)
    cluster = {
        "transaction_ids": ids,
        "revenue_at_risk": inc.revenue_at_risk,
        "max_risk": max((t.get("risk_score") or 0) for t in txs) if txs else 0.2,
        "max_retry": max((t.get("retry_count") or 0) for t in txs) if txs else 0,
        "suspicious": inc.root_cause == "risk_signal",
        "kind": "suspicious_retry" if inc.root_cause == "risk_signal" else "gateway_failure",
        "gateway": txs[0]["gateway"] if txs else "unknown",
    }
    return run_incident_pipeline(session, all_txs, cluster, scenario=inc.scenario, execute=True)
