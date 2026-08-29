"""Controlled leakage scenarios with ground-truth labels."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ScenarioName = Literal[
    "normal",
    "gateway_degradation",
    "checkout_abandonment",
    "repeated_failures",
    "suspicious_retry",
    "legitimate_anomaly",
    "mixed",
    "demo_recoverable",
    "demo_unsafe",
]


@dataclass(frozen=True)
class ScenarioSpec:
    name: ScenarioName
    description: str
    injected_failure_rate: float | None = None
    baseline_failure_rate: float = 0.045
    high_value_abandon_boost: float = 0.0
    retry_storm: bool = False
    suspicious: bool = False
    legitimate_spike: bool = False
    target_gateway: str = "razorpay_test"
    target_method: str = "card"


SCENARIOS: dict[str, ScenarioSpec] = {
    "normal": ScenarioSpec(
        name="normal",
        description="Baseline commerce with 4–5% organic payment failures.",
        injected_failure_rate=0.045,
    ),
    "gateway_degradation": ScenarioSpec(
        name="gateway_degradation",
        description="Gateway degradation lifts failure rate from ~4–5% to 15–20%.",
        injected_failure_rate=0.18,
        target_gateway="razorpay_test",
    ),
    "checkout_abandonment": ScenarioSpec(
        name="checkout_abandonment",
        description="High-value customers abandon checkout before capture.",
        high_value_abandon_boost=0.35,
    ),
    "repeated_failures": ScenarioSpec(
        name="repeated_failures",
        description="Customers retry the same failed payment multiple times.",
        retry_storm=True,
        injected_failure_rate=0.12,
    ),
    "suspicious_retry": ScenarioSpec(
        name="suspicious_retry",
        description="Rapid repeated attempts from the same customer/device.",
        suspicious=True,
        retry_storm=True,
        injected_failure_rate=0.22,
    ),
    "legitimate_anomaly": ScenarioSpec(
        name="legitimate_anomaly",
        description="Unusual but legitimate volume spike (festival / payroll day).",
        legitimate_spike=True,
        injected_failure_rate=0.05,
    ),
    "mixed": ScenarioSpec(
        name="mixed",
        description="Blend of baseline traffic and injected leakage scenarios.",
        injected_failure_rate=0.08,
    ),
    "demo_recoverable": ScenarioSpec(
        name="demo_recoverable",
        description="Demo A — recoverable gateway degradation.",
        injected_failure_rate=0.18,
        target_gateway="razorpay_test",
    ),
    "demo_unsafe": ScenarioSpec(
        name="demo_unsafe",
        description="Demo B — suspicious rapid retries; recovery must be blocked.",
        suspicious=True,
        retry_storm=True,
        injected_failure_rate=0.25,
    ),
}


def get_scenario(name: str) -> ScenarioSpec:
    if name not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {name}")
    return SCENARIOS[name]
