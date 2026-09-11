import datetime

from app.services.daily_limit import compute_daily_limit


def _call(total=1000.0, pending=100.0, spent=0.0, ref="2026-09-11", month="2026-09"):
    return compute_daily_limit(
        total_balance=total,
        pending_month=pending,
        spent_ref_day=spent,
        ref_date=datetime.date.fromisoformat(ref),
        target_month=month,
    )


def test_positive_balance_normal():
    # free = 900, 20 dias restantes -> 45/dia, nada gasto -> NORMAL
    res = _call()
    assert res["free_balance"] == 900.0
    assert res["days_remaining"] == 20
    assert res["recommended_per_day"] == 45.0
    assert res["spent_today"] == 0.0
    assert res["remaining_today"] == 45.0
    assert res["status"] == "NORMAL"


def test_zero_balance_warning():
    # free = 0 -> cota zerada, sem margem -> WARNING (nao quebra)
    res = _call(total=100.0, pending=100.0)
    assert res["free_balance"] == 0.0
    assert res["recommended_per_day"] == 0.0
    assert res["remaining_today"] == 0.0
    assert res["status"] == "WARNING"


def test_negative_balance_exceeded():
    # pendencias maiores que o saldo -> EXCEEDED
    res = _call(total=100.0, pending=500.0)
    assert res["free_balance"] == -400.0
    assert res["recommended_per_day"] == -20.0
    assert res["status"] == "EXCEEDED"


def test_overspent_day_exceeded():
    # gastou no dia mais que a cota -> EXCEEDED
    res = _call(spent=60.0)
    assert res["remaining_today"] == -15.0
    assert res["status"] == "EXCEEDED"


def test_warning_threshold():
    # gastou >= 80% da cota -> WARNING
    res = _call(spent=36.0)
    assert res["status"] == "WARNING"


def test_last_day_of_month_single_day():
    res = _call(ref="2026-09-30", month="2026-09")
    assert res["days_remaining"] == 1
    assert res["recommended_per_day"] == 900.0


def test_api_shape_and_math():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        response = client.get("/api/dashboard?month=2026-09")
    assert response.status_code == 200
    data = response.json()
    for field in (
        "recommended_per_day",
        "spent_today",
        "remaining_today",
        "days_remaining",
        "free_balance",
        "status",
    ):
        assert field in data
    assert data["status"] in ("NORMAL", "WARNING", "EXCEEDED")
    assert data["days_remaining"] >= 1
    assert abs(data["recommended_per_day"] * data["days_remaining"] - data["free_balance"]) < 0.5
    assert abs(data["remaining_today"] - (data["recommended_per_day"] - data["spent_today"])) < 0.01
