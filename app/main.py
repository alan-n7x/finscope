from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import excel_engine
from app.schemas import (
    DashboardSummaryResponse,
    DebtItem,
    FilterOptionsResponse,
    TransactionCreate,
    TransactionItem,
    ImportPreviewResponse,
    ImportConfirmRequest
)
from app import import_engine
from contextlib import asynccontextmanager

try:
    from app.bot.main_bot import start_bot, stop_bot
except ImportError:
    start_bot, stop_bot = None, None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if start_bot:
        await start_bot()
    yield
    # Shutdown
    if stop_bot:
        await stop_bot()

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"

app = FastAPI(title="Finscope — Controle Financeiro", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
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

@app.post("/api/transactions/import/upload", response_model=ImportPreviewResponse)
async def upload_extrato(file: UploadFile = File(...)) -> ImportPreviewResponse:
    content = await file.read()
    filename = file.filename.lower()
    
    if filename.endswith(".ofx"):
        txs, account_guess = import_engine.parse_ofx(content)
    elif filename.endswith(".pdf"):
        txs, account_guess = import_engine.parse_itau_pdf(content)
    else:
        raise HTTPException(status_code=400, detail="Formato não suportado. Envie OFX ou PDF (Itaú).")
        
    # Get recent transactions to reconcile against
    db_txs = excel_engine.get_transactions(limit=500)
    
    # Reconcile
    reconciled_txs = import_engine.reconcile_transactions(txs, db_txs)
    
    return ImportPreviewResponse(transactions=reconciled_txs, account_guess=account_guess)

@app.post("/api/transactions/import/confirm")
async def confirm_import(payload: ImportConfirmRequest):
    # Map back to standard TransactionCreate structure
    success_count = 0
    for t in payload.transactions:
        if t.status == "NEW":
            # For simplicity, we just add the transactions one by one
            dt = {
                "date": t.date,
                "type": t.type,
                "category": t.category or "Outros",
                "description": t.description,
                "payment_method": "Pix", # default
                "amount": t.amount,
                "essential": False,
                "paid": True,
                "obs": "Importado via Extrato",
                "account": t.account or "Itaú - Conta corrente"
            }
            excel_engine.add_transaction(dt)
            success_count += 1
            
    return {"message": f"Importação concluída. {success_count} itens adicionados."}


# Frontend Serving (Vite dist if present, else fallback static)
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_react_app(full_path: str) -> FileResponse:
        return FileResponse(FRONTEND_DIST / "index.html")
else:
    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

    @app.get("/", include_in_schema=False)
    async def home() -> FileResponse:
        return FileResponse(BASE_DIR / "static" / "index.html")
