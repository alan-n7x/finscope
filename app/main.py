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
    """Gerencia bot do Telegram e pool do banco durante o ciclo de vida do app.

    Args:
        app: Instância FastAPI (não utilizada diretamente).
    """
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
    """Verifica disponibilidade do PostgreSQL.

    Raises:
        HTTPException: 503 quando o banco não responde.

    Returns:
        Status, engine e versão da aplicação.
    """
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
    """Retorna saldos, agregados do mês e limite diário na referência dada.

    Args:
        month: Mês no formato YYYY-MM.
        date: Data de referência no formato YYYY-MM-DD.
        session: Sessão injetada pelo FastAPI.

    Returns:
        Resumo do dashboard conforme `DashboardSummaryResponse`.
    """
    repo = FinanceRepository(session)
    summary = await repo.get_dashboard_summary(month=month, date=date)
    return DashboardSummaryResponse(**summary)


@app.get("/api/options", response_model=FilterOptionsResponse)
async def get_options(
    session: AsyncSession = Depends(get_db_session)
) -> FilterOptionsResponse:
    """Retorna opções distintas para os filtros da interface.

    Args:
        session: Sessão injetada pelo FastAPI.

    Returns:
        Categorias, formas de pagamento, contas, meses e tipos.
    """
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
    """Lista lançamentos com filtros opcionais (mês, categoria, busca, status).

    Args:
        month: Mês no formato YYYY-MM.
        category: Substring da categoria.
        search: Substring da descrição/observações.
        status: "Sim" (pago) ou "Não" (pendente).
        limit: Máximo de itens (até 500).
        session: Sessão injetada pelo FastAPI.

    Returns:
        Lançamentos serializados, mais recentes primeiro.
    """
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
    """Cria um lançamento manual no ledger (conta e categoria auto-resolvidas).

    Args:
        payload: Dados do lançamento (`TransactionCreate`).
        session: Sessão injetada pelo FastAPI.

    Raises:
        HTTPException: 422 quando conta/tipo/data são inválidos.

    Returns:
        Lançamento criado, serializado.
    """
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
    """Lista dívidas ordenadas pelo maior saldo devedor.

    Args:
        session: Sessão injetada pelo FastAPI.

    Returns:
        Dívidas serializadas.
    """
    repo = FinanceRepository(session)
    debts = await repo.list_debts()
    return [DebtItem(**d) for d in debts]


@app.get("/api/dashboard/cash-flow", response_model=CashFlowResponse)
async def get_cash_flow(
    month: str | None = Query(default=None, description="Mes no formato YYYY-MM"),
    date: str | None = Query(default=None, description="Data de referencia no formato YYYY-MM-DD"),
    session: AsyncSession = Depends(get_db_session)
) -> CashFlowResponse:
    """Retorna o fluxo de caixa diário (realizado + projetado) do mês alvo.

    Args:
        month: Mês no formato YYYY-MM.
        date: Data de referência no formato YYYY-MM-DD.
        session: Sessão injetada pelo FastAPI.

    Returns:
        Série diária com transição realizado/projetado.
    """
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
    """Gera e baixa o relatório financeiro em .xlsx do mês (ou atual).

    Args:
        month: Mês no formato YYYY-MM.
        session: Sessão injetada pelo FastAPI.

    Raises:
        HTTPException: 500 quando a geração do relatório falha.

    Returns:
        Stream do arquivo Excel para download.
    """
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
    """Processa OFX ou PDF do Itaú e devolve o preview com conciliação.

    Args:
        file: Arquivo enviado (.ofx ou .pdf).
        session: Sessão injetada pelo FastAPI.

    Raises:
        HTTPException: 400 para formato não suportado.

    Returns:
        Transações (NEW/MATCHED), palpite de conta e snapshots de saldo.
    """
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
    """Confirma a importação: grava itens NEW (idempotente) e saldos da conta.

    Args:
        payload: Transações revisadas, snapshots e conta do import.
        session: Sessão injetada pelo FastAPI.

    Raises:
        HTTPException: 422 quando conta/tipo/data são inválidos.

    Returns:
        Mensagem com quantidades de itens e saldos atualizados.
    """
    success_count = 0
    snapshots_count = 0
    try:
        service = TransactionService(session)
        fallback_account = import_engine.resolve_import_account(
            payload.account, list(payload.transactions)
        )
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
                        account=t.account or fallback_account,
                    ),
                    external_id=f"import:{t.id}",
                )
                if created:
                    success_count += 1

        # Create or update balance snapshots na conta correta (Itaú ou Inter)
        account_name = fallback_account
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
        """Serve o SPA para qualquer rota não-API (fallback do frontend).

        Args:
            full_path: Caminho requisitado (ignorado, sempre devolve o index).

        Returns:
            O `index.html` do build do frontend.
        """
        return FileResponse(FRONTEND_DIST / "index.html")
else:
    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

    @app.get("/", include_in_schema=False)
    async def home() -> FileResponse:
        """Serve a página inicial legada quando o build do frontend não existe.

        Returns:
            A página estática de `app/static/index.html`.
        """
        return FileResponse(BASE_DIR / "static" / "index.html")
