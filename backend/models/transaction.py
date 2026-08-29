"""Pydantic models for synthetic transactions."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PaymentStatus(str, Enum):
    PAYMENT_STARTED = "PAYMENT_STARTED"
    PAYMENT_SUCCESS = "PAYMENT_SUCCESS"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    PAYMENT_RETRY = "PAYMENT_RETRY"
    CHECKOUT_ABANDONED = "CHECKOUT_ABANDONED"
    SETTLEMENT_PENDING = "SETTLEMENT_PENDING"
    SETTLEMENT_COMPLETED = "SETTLEMENT_COMPLETED"


class RecoveryStatus(str, Enum):
    NONE = "NONE"
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    VERIFIED = "VERIFIED"
    BLOCKED = "BLOCKED"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    FAILED = "FAILED"


class RecoveryAction(str, Enum):
    SAFE_RETRY = "SAFE_RETRY"
    ALTERNATE_PAYMENT = "ALTERNATE_PAYMENT"
    PERSONALIZED_OFFER = "PERSONALIZED_OFFER"
    RECOVERY_MESSAGE = "RECOVERY_MESSAGE"
    STOP = "STOP"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    NONE = "NONE"


class RootCause(str, Enum):
    GATEWAY_DEGRADATION = "gateway_degradation"
    PAYMENT_METHOD_FAILURE = "payment_method_failure"
    CUSTOMER_ABANDONMENT = "customer_abandonment"
    RETRY_PROBLEM = "retry_problem"
    RISK_SIGNAL = "risk_signal"
    TEMPORARY_FAILURE = "temporary_failure"
    UNKNOWN = "unknown"


class Transaction(BaseModel):
    transaction_id: str
    merchant_id: str
    customer_id: str
    amount: float
    currency: str = "INR"
    payment_method: str
    gateway: str
    timestamp: datetime
    status: PaymentStatus
    failure_reason: Optional[str] = None
    device_id: str
    customer_segment: str
    cart_value: float
    retry_count: int = 0
    risk_score: float = Field(ge=0, le=1)
    revenue_at_risk: float = 0.0
    recovery_status: RecoveryStatus = RecoveryStatus.NONE
    recovery_action: RecoveryAction = RecoveryAction.NONE
    scenario: Optional[str] = None
    ground_truth_anomaly: bool = False
    ground_truth_root_cause: Optional[str] = None
    ground_truth_suspicious: bool = False
    ground_truth_should_recover: bool = False
    detected_anomaly: bool = False
    detected_root_cause: Optional[str] = None


class TransactionListResponse(BaseModel):
    total: int
    items: list[Transaction]
