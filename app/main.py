from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import excel_engine
from app.schemas import (
    DashboardSummaryResponse,
    DebtItem,
    FilterOptionsResponse,
    TransactionCreate,
    TransactionItem,
)

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Finscope — Controle Financeiro", version="0.2.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/", include_in_schema=False)
async def home() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/health")
async def health() -> dict[str, str]:
    excel_path = str(excel_engine.get_excel_path())
    return {"status": "ok", "engine": "excel-database", "excel_path": excel_path}


@app.get("/api/dashboard", response_model=DashboardSummaryResponse)
async def get_dashboard(month: str | None = Query(default=None, description="Mês no formato YYYY-MM")) -> DashboardSummaryResponse:
    summary = excel_engine.get_dashboard_summary(month=month)
    return DashboardSummaryResponse(**summary)


@app.get("/api/options", response_model=FilterOptionsResponse)
async def get_options() -> FilterOptionsResponse:
    options = excel_engine.get_filter_options()
    return FilterOptionsResponse(**options)


@app.get("/api/transactions", response_model=list[TransactionItem])
async def list_transactions(
    month: str | None = Query(default=None),
    category: str | None = Query(default=None),
    search: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=200, le=500),
) -> list[TransactionItem]:
    txs = excel_engine.get_transactions(
        month=month,
        category=category,
        search=search,
        status=status,
        limit=limit,
    )
    return [TransactionItem(**t) for t in txs]


@app.post("/api/transactions", response_model=dict[str, Any])
async def create_transaction(payload: TransactionCreate) -> dict[str, Any]:
    try:
        res = excel_engine.add_transaction(payload.model_dump())
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gravar na planilha: {e}")


@app.get("/api/debts", response_model=list[DebtItem])
async def list_debts() -> list[DebtItem]:
    debts = excel_engine.get_debts_summary()
    return [DebtItem(**d) for d in debts]
