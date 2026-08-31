from simulator.generator import generate_transactions


def test_same_seed_is_deterministic():
    a = generate_transactions(n=80, scenario="demo_unsafe", seed=11)
    b = generate_transactions(n=80, scenario="demo_unsafe", seed=11)
    assert list(a["transaction_id"]) == list(b["transaction_id"])
    assert list(a["amount"]) == list(b["amount"])


def test_generate_supported_sizes():
    df = generate_transactions(n=100, scenario="normal", seed=1)
    assert len(df) == 100
    required = {
        "transaction_id",
        "merchant_id",
        "customer_id",
        "amount",
        "currency",
        "payment_method",
        "gateway",
        "timestamp",
        "status",
        "device_id",
        "customer_segment",
        "cart_value",
        "retry_count",
        "risk_score",
        "revenue_at_risk",
        "recovery_status",
        "recovery_action",
    }
    assert required.issubset(df.columns)


def test_gateway_degradation_elevates_failures():
    normal = generate_transactions(n=1000, scenario="normal", seed=2)
    degraded = generate_transactions(n=1000, scenario="gateway_degradation", seed=2)
    n_fail = normal["status"].isin(["PAYMENT_FAILED", "PAYMENT_RETRY"]).mean()
    d_fail = degraded[degraded["gateway"] == "razorpay_test"]["status"].isin(
        ["PAYMENT_FAILED", "PAYMENT_RETRY"]
    ).mean()
    assert n_fail < 0.12
    assert d_fail > 0.10


def test_suspicious_retry_ground_truth():
    df = generate_transactions(n=80, scenario="suspicious_retry", seed=3)
    assert df["ground_truth_suspicious"].any()
    assert (df["ground_truth_should_recover"] == False).any()  # noqa: E712
