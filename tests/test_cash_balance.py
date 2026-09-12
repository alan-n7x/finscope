import datetime

from app.services.cash_balance import compute_cash_balance


def _series(start=1000.0, posted=None, pending=None, year=2026, month=9, transition=11):
    return compute_cash_balance(
        start_balance=start,
        posted_net_by_day=posted or {},
        pending_net_by_day=pending or {},
        year=year,
        month=month,
        transition_day=transition,
    )


def _by_day(series):
    return {item["day"]: item for item in series}


def test_empty_month_flat_series():
    s = _by_day(_series())
    assert len(s) == 30
    assert all(v["realized_balance"] == 1000.0 for k, v in s.items() if k <= 11)
    assert all(v["realized_balance"] is None for k, v in s.items() if k > 11)
    assert all(v["projected_balance"] is None for k, v in s.items() if k < 11)
    assert all(v["projected_balance"] == 1000.0 for k, v in s.items() if k >= 11)


def test_confirmed_income_and_expense():
    s = _by_day(_series(posted={3: 200.0, 5: -50.0}))
    assert s[2]["realized_balance"] == 1000.0
    assert s[3]["realized_balance"] == 1200.0
    assert s[5]["realized_balance"] == 1150.0
    assert s[11]["realized_balance"] == 1150.0
    assert s[12]["realized_balance"] is None


def test_pending_income_and_expense_only_projected():
    s = _by_day(_series(pending={15: 300.0, 20: -100.0}))
    assert all(v["realized_balance"] == 1000.0 for k, v in s.items() if k <= 11)
    assert s[11]["projected_balance"] == 1000.0
    assert s[14]["projected_balance"] == 1000.0
    assert s[15]["projected_balance"] == 1300.0
    assert s[20]["projected_balance"] == 1200.0
    assert s[30]["projected_balance"] == 1200.0


def test_same_day_mixed_and_multiple_entries():
    # +100 -30 +10 no mesmo dia = +80 liquido
    s = _by_day(_series(posted={7: 80.0}, pending={7: -20.0}))
    assert s[7]["realized_balance"] == 1080.0
    # pendente no dia <= transicao nao afeta nem realizado nem projecao
    assert s[11]["projected_balance"] == 1080.0


def test_negative_balance():
    s = _by_day(_series(start=50.0, posted={2: -200.0}))
    assert s[2]["realized_balance"] == -150.0
    assert s[11]["projected_balance"] == -150.0


def test_transition_continuity():
    s = _by_day(_series(posted={11: -40.0}, pending={12: -10.0}))
    assert s[11]["realized_balance"] == s[11]["projected_balance"]
    assert s[12]["projected_balance"] == s[11]["realized_balance"] - 10.0


def test_overdue_pending_carried_forward():
    # pendente com data <= transicao (em atraso) entra na projecao no
    # primeiro dia apos a transicao; realizado intacto
    s = _by_day(_series(pending={5: -500.0}))
    assert s[11]["realized_balance"] == 1000.0
    assert s[11]["projected_balance"] == 1000.0
    assert s[12]["projected_balance"] == 500.0
    assert s[30]["projected_balance"] == 500.0


def test_cents_rounding():
    s = _by_day(_series(start=100.0, posted={1: 10.015, 2: 10.015, 3: 10.015}))
    assert s[3]["realized_balance"] == 130.05


def test_due_on_last_day():
    s = _by_day(_series(pending={30: -250.0}))
    assert s[29]["projected_balance"] == 1000.0
    assert s[30]["projected_balance"] == 750.0


def test_all_confirmed_past_month():
    s = _by_day(_series(posted={28: -100.0}, transition=30))
    assert all(v["realized_balance"] is not None for v in s.values())
    assert all(v["projected_balance"] is None for k, v in s.items() if k < 30)
    assert s[30]["projected_balance"] == s[30]["realized_balance"] == 900.0


def test_future_month_no_realized():
    s = _by_day(_series(pending={5: -100.0}, month=12, transition=0))
    assert all(v["realized_balance"] is None for v in s.values())
    assert s[1]["projected_balance"] == 1000.0
    assert s[5]["projected_balance"] == 900.0


def test_february_day_count_and_month_change():
    assert len(_series(year=2026, month=2, transition=28)) == 28
    assert len(_series(year=2026, month=12, transition=31)) == 31


def test_api_realized_matches_dashboard_and_projection():
    from fastapi.testclient import TestClient

    from app.main import app

    today = datetime.date.today()
    month = today.strftime("%Y-%m")
    with TestClient(app) as client:
        flow = client.get(f"/api/dashboard/cash-flow?month={month}").json()
        summary = client.get(f"/api/dashboard?month={month}").json()
        txs = client.get(f"/api/transactions?month={month}&limit=500").json()
    assert flow["transition_date"] == today.isoformat()
    assert flow["has_projection"] is True
    by_day = {d["day"]: d for d in flow["days"]}
    # realizado no ponto de transicao == saldo oficial do dashboard
    assert abs(by_day[today.day]["realized_balance"] - summary["total_balance"]) < 0.01
    assert by_day[today.day]["projected_balance"] == by_day[today.day]["realized_balance"]
    assert by_day[today.day + 1]["realized_balance"] is None
    assert by_day[today.day - 1]["projected_balance"] is None
    # projecao final = transicao + TODAS as pendencias do mes (inclui atrasadas)
    pending_net = sum(
        t["amount"] if t["type"] == "Receita" else -t["amount"]
        for t in txs if t.get("paid") == "Não" and t["type"] in ("Receita", "Despesa")
    )
    expected_final = round(by_day[today.day]["realized_balance"] + pending_net, 2)
    assert flow["final_projected_balance"] == expected_final
    assert flow["final_projected_balance"] == by_day[len(by_day)]["projected_balance"]


def test_api_past_month_all_realized():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        flow = client.get("/api/dashboard/cash-flow?month=2026-08").json()
    assert flow["transition_date"] == "2026-08-31"
    assert all(d["realized_balance"] is not None for d in flow["days"])
    last = flow["days"][-1]
    assert last["projected_balance"] == last["realized_balance"]
    assert flow["final_projected_balance"] == last["realized_balance"]
