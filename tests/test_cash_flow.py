from fastapi.testclient import TestClient

from app.main import app


def test_cash_flow_shape_and_accumulation():
    with TestClient(app) as client:
        response = client.get("/api/dashboard/cash-flow?month=2026-09")
    assert response.status_code == 200
    data = response.json()
    assert data["month"] == "2026-09"
    days = data["days"]
    assert len(days) == 30
    assert [d["day"] for d in days] == list(range(1, 31))

    acc_income = 0.0
    acc_expense = 0.0
    for d in days:
        for field in ("income", "expense", "cumulative_income", "cumulative_expense", "net"):
            assert d[field] >= 0 or field == "net"
        acc_income = round(acc_income + d["income"], 2)
        acc_expense = round(acc_expense + d["expense"], 2)
        assert d["cumulative_income"] == acc_income
        assert d["cumulative_expense"] == acc_expense
        assert d["net"] == round(acc_income - acc_expense, 2)


def test_cash_flow_matches_dashboard_totals():
    with TestClient(app) as client:
        flow = client.get("/api/dashboard/cash-flow?month=2026-08").json()
        summary = client.get("/api/dashboard?month=2026-08").json()
    last = flow["days"][-1]
    assert abs(last["cumulative_income"] - summary["income_month"]) < 0.01
    assert abs(last["cumulative_expense"] - summary["expense_month"]) < 0.01


def test_cash_flow_february_day_count():
    with TestClient(app) as client:
        response = client.get("/api/dashboard/cash-flow?month=2026-02")
    assert response.status_code == 200
    assert len(response.json()["days"]) == 28
