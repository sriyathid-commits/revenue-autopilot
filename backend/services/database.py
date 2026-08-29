"""SQLAlchemy persistence. SQLite locally; DATABASE_URL can point at PostgreSQL."""

from __future__ import annotations

from datetime import datetime
from typing import Generator

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
    event,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session

from backend.config import get_settings


class Base(DeclarativeBase):
    pass


class TransactionRow(Base):
    __tablename__ = "transactions"

    transaction_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    merchant_id: Mapped[str] = mapped_column(String(64), index=True)
    customer_id: Mapped[str] = mapped_column(String(64), index=True)
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    payment_method: Mapped[str] = mapped_column(String(32))
    gateway: Mapped[str] = mapped_column(String(32), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    failure_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    customer_segment: Mapped[str] = mapped_column(String(32))
    cart_value: Mapped[float] = mapped_column(Float)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    revenue_at_risk: Mapped[float] = mapped_column(Float, default=0.0)
    recovery_status: Mapped[str] = mapped_column(String(32), default="NONE")
    recovery_action: Mapped[str] = mapped_column(String(32), default="NONE")
    scenario: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ground_truth_anomaly: Mapped[bool] = mapped_column(Boolean, default=False)
    ground_truth_root_cause: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ground_truth_suspicious: Mapped[bool] = mapped_column(Boolean, default=False)
    ground_truth_should_recover: Mapped[bool] = mapped_column(Boolean, default=False)
    detected_anomaly: Mapped[bool] = mapped_column(Boolean, default=False)
    detected_root_cause: Mapped[str | None] = mapped_column(String(64), nullable=True)


class IncidentRow(Base):
    __tablename__ = "incidents"

    incident_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    merchant_id: Mapped[str] = mapped_column(String(64), index=True)
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    root_cause: Mapped[str | None] = mapped_column(String(64), nullable=True)
    risk_level: Mapped[str] = mapped_column(String(16), default="MEDIUM")
    action: Mapped[str] = mapped_column(String(32), default="NONE")
    status: Mapped[str] = mapped_column(String(32), default="PENDING")
    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    scenario: Mapped[str | None] = mapped_column(String(64), nullable=True)
    revenue_at_risk: Mapped[float] = mapped_column(Float, default=0.0)
    revenue_recovered: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    transaction_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    explanation: Mapped[str] = mapped_column(Text, default="")
    moneyguard_reason: Mapped[str] = mapped_column(Text, default="")
    policy_reason: Mapped[str] = mapped_column(Text, default="")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class AgentResultRow(Base):
    __tablename__ = "agent_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent: Mapped[str] = mapped_column(String(64), index=True)
    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    incident_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    decision: Mapped[str] = mapped_column(Text, default="")
    explanation: Mapped[str] = mapped_column(Text, default="")
    evidence_json: Mapped[str] = mapped_column(Text, default="{}")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    ok: Mapped[bool] = mapped_column(Boolean, default=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class AuditRow(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    incident_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    agent: Mapped[str] = mapped_column(String(64))
    event: Mapped[str] = mapped_column(String(64), index=True)
    decision: Mapped[str] = mapped_column(Text, default="")
    evidence_json: Mapped[str] = mapped_column(Text, default="{}")
    action: Mapped[str | None] = mapped_column(String(32), nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)


class EvaluationRow(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    payload_json: Mapped[str] = mapped_column(Text)


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        settings = get_settings()
        url = settings.database_url
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, connect_args=connect_args, future=True)

        if url.startswith("sqlite"):

            @event.listens_for(_engine, "connect")
            def _sqlite_pragma(dbapi_connection, connection_record):  # type: ignore[no-untyped-def]
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.close()

        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)
        Base.metadata.create_all(_engine)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_engine() -> None:
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def reset_database() -> None:
    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
