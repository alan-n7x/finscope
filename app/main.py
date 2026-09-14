from pathlib import Path
from typing import Any
import datetime

from fastapi import FastAPI, HTTPException, Query, File, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.session import engine, get_db_session
from app.infra.repositories.finance_repository import FinanceRepository
from app.services.excel_export_service import ExcelExportService
from app.services.transaction_service import TransactionService
from app.schemas import (
    CashFlowResponse,
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
    if start_bot:
        await start_bot()
    try:
        yield
    finally:
        if stop_bot:
            await stop_bot()
        await engine.dispose()

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"

app = FastAPI(title="Finscope — Controle Financeiro", version="0.3.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# HEALTH & STATUS
# ============================================================================
@app.get("/health")
async def health(session: AsyncSession = Depends(get_db_session)) -> dict[str, str]:
    try:
        await session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="PostgreSQL indisponível") from exc
    return {
        "status": "ok",
        "engine": "postgresql",
        "version": "0.3.0"
    }


# ============================================================================
# FINANCIAL API ROUTES
# ============================================================================
@app.get("/api/dashboard", response_model=DashboardSummaryResponse)
async def get_dashboard(
    month: str | None = Query(default=None, description="Mes no formato YYYY-MM"),
    date: str | None = Query(default=None, description="Data de referencia no formato YYYY-MM-DD"),
    session: AsyncSession = Depends(get_db_session)
) -> DashboardSummaryResponse:
    repo = FinanceRepository(session)
    summary = await repo.get_dashboard_summary(month=month, date=date)
    return DashboardSummaryResponse(**summary)


@app.get("/api/options", response_model=FilterOptionsResponse)
async def get_options(
    session: AsyncSession = Depends(get_db_session)
) -> FilterOptionsResponse:
    repo = FinanceRepository(session)
    options = await repo.get_filter_options()
    return FilterOptionsResponse(**options)


@app.get("/api/transactions", response_model=list[TransactionItem])
async def list_transactions(
    month: str | None = Query(default=None),
    category: str | None = Query(default=None),
    search: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=200, le=500),
    session: AsyncSession = Depends(get_db_session)
) -> list[TransactionItem]:
    repo = FinanceRepository(session)
    txs = await repo.list_transactions(
        month=month,
        category=category,
        search=search,
        status=status,
        limit=limit,
    )
    return [TransactionItem(**t) for t in txs]


@app.post("/api/transactions", response_model=dict[str, Any])
async def create_transaction(
    payload: TransactionCreate,
    session: AsyncSession = Depends(get_db_session)
) -> dict[str, Any]:
    try:
        transaction, _ = await TransactionService(session).create(payload)
        await session.commit()
        await session.refresh(transaction, attribute_names=["account", "category"])
        return TransactionService.serialize(transaction)
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/debts", response_model=list[DebtItem])
async def list_debts(
    session: AsyncSession = Depends(get_db_session)
) -> list[DebtItem]:
    repo = FinanceRepository(session)
    debts = await repo.list_debts()
    return [DebtItem(**d) for d in debts]


@app.get("/api/dashboard/cash-flow", response_model=CashFlowResponse)
async def get_cash_flow(
    month: str | None = Query(default=None, description="Mes no formato YYYY-MM"),
    date: str | None = Query(default=None, description="Data de referencia no formato YYYY-MM-DD"),
    session: AsyncSession = Depends(get_db_session)
) -> CashFlowResponse:
    repo = FinanceRepository(session)
    cash_flow = await repo.get_cash_flow(month=month, date=date)
    return CashFlowResponse(**cash_flow)


# ============================================================================
# EXPORT & REPORTING (Excel sob Demanda)
# ============================================================================
@app.get("/api/reports/export-excel")
async def export_excel_report(
    month: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session)
):
    try:
        report_stream = await ExcelExportService.generate_financial_report(session, month=month)
        filename = f"finscope_relatorio_{month or datetime.date.today().strftime('%Y-%m')}.xlsx"
        return StreamingResponse(
            report_stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar relatório Excel: {e}")


# ============================================================================
# IMPORT & CONCILIAÇÃO BANCÁRIA
# ============================================================================
@app.post("/api/transactions/import/upload", response_model=ImportPreviewResponse)
async def upload_extrato(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
) -> ImportPreviewResponse:
    content = await file.read()
    filename = file.filename.lower()
    
    if filename.endswith(".ofx"):
        txs, snapshots, account_guess = import_engine.parse_ofx(content)
    elif filename.endswith(".pdf"):
        txs, snapshots, account_guess = import_engine.parse_itau_pdf(content)
    else:
        raise HTTPException(status_code=400, detail="Formato não suportado. Envie OFX ou PDF (Itaú).")
        
    db_txs = await FinanceRepository(session).list_transactions(limit=500)
    reconciled_txs = import_engine.reconcile_transactions(txs, db_txs)
    
    return ImportPreviewResponse(transactions=reconciled_txs, account_guess=account_guess, snapshots=snapshots)


@app.post("/api/transactions/import/confirm")
async def confirm_import(
    payload: ImportConfirmRequest,
    session: AsyncSession = Depends(get_db_session),
):
    success_count = 0
    snapshots_count = 0
    try:
        service = TransactionService(session)
        for t in payload.transactions:
            if t.status == "NEW":
                transaction, created = await service.create(
                    TransactionCreate(
                        date=t.date,
                        type=t.type,
                        category=t.category or "Outros",
                        description=t.description,
                        payment_method="Pix",
                        amount=t.amount,
                        essential=False,
                        paid=True,
                        obs="Importado via Extrato",
                        account=t.account or "Itaú - Conta corrente",
                    ),
                    external_id=f"import:{t.id}",
                )
                if created:
                    success_count += 1

        # Create or update balance snapshots from SALDO DO DIA lines
        account_name = "Itaú - Conta corrente"
        if payload.snapshots:
            from decimal import Decimal
            from sqlalchemy import select
            from app.infra.db.models import Account, AccountBalanceSnapshot

            account = await session.scalar(
                select(Account).where(func.lower(Account.name) == account_name.strip().lower())
            )
            if account:
                for snap in payload.snapshots:
                    snap_date = datetime.date.fromisoformat(snap.date)
                    existing = await session.scalar(
                        select(AccountBalanceSnapshot).where(
                            AccountBalanceSnapshot.account_id == account.id,
                            AccountBalanceSnapshot.snapshot_date == snap_date,
                        )
                    )
                    if existing:
                        existing.balance = Decimal(str(snap.balance))
                    else:
                        session.add(AccountBalanceSnapshot(
                            account_id=account.id,
                            snapshot_date=snap_date,
                            balance=Decimal(str(snap.balance)),
                        ))
                    snapshots_count += 1

        await session.commit()
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
            
    msg = f"Importação concluída. {success_count} itens adicionados."
    if snapshots_count:
        msg += f" {snapshots_count} saldos atualizados."
    return {"message": msg}


# ============================================================================
# FRONTEND SERVING
# ============================================================================
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
