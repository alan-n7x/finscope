from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["engine"] in ["postgresql-primary", "excel-database"]


def test_dashboard_endpoint():
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "total_balance" in data
    assert "income_month" in data
    assert "expense_month" in data
    assert "accounts" in data


def test_options_endpoint():
    response = client.get("/api/options")
    assert response.status_code == 200
    data = response.json()
    assert "categories" in data
    assert "months" in data


def test_transactions_endpoint():
    response = client.get("/api/transactions?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        first = data[0]
        assert "amount" in first
        assert "description" in first
        assert "category" in first
