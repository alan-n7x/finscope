from __future__ import annotations

import io
import datetime
from decimal import Decimal
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.repositories.finance_repository import FinanceRepository


class ExcelExportService:
    @staticmethod
    async def generate_financial_report(session: AsyncSession, month: str | None = None) -> io.BytesIO:
        repo = FinanceRepository(session)
        summary = await repo.get_dashboard_summary(month=month)
        transactions = await repo.list_transactions(month=month, limit=1000)
        debts = await repo.list_debts()

        wb = openpyxl.Workbook()

        # ====================================================================
        # ABA 1: Visão Geral / Resumo
        # ====================================================================
        ws_resumo = wb.active
        ws_resumo.title = "Resumo Mensal"
        ws_resumo.views.sheetView[0].showGridLines = True

        header_font = Font(name="Segoe UI", size=14, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        
        ws_resumo.merge_cells("A1:D1")
        title_cell = ws_resumo["A1"]
        title_cell.value = f"Finscope — Relatório Financeiro ({summary['month']})"
        title_cell.font = header_font
        title_cell.fill = header_fill
        title_cell.alignment = Alignment(horizontal="center", vertical="center")
        ws_resumo.row_dimensions[1].height = 35

        # KPIs
        kpi_labels = [
            ("Saldo Total em Conta", summary["total_balance"]),
            ("Receitas do Mês", summary["income_month"]),
            ("Despesas do Mês", summary["expense_month"]),
            ("Resultado Líquido", summary["net_month"]),
        ]

        bold_font = Font(name="Segoe UI", size=11, bold=True)
        for i, (label, val) in enumerate(kpi_labels, start=3):
            ws_resumo.cell(row=i, column=1, value=label).font = bold_font
            val_cell = ws_resumo.cell(row=i, column=2, value=val)
            val_cell.number_format = 'R$ #,##0.00'
            val_cell.font = bold_font

        # Contas
        ws_resumo.cell(row=8, column=1, value="Conta Bancária").font = header_font
        ws_resumo.cell(row=8, column=1).fill = header_fill
        ws_resumo.cell(row=8, column=2, value="Saldo Atual").font = header_font
        ws_resumo.cell(row=8, column=2).fill = header_fill

        for idx, acc in enumerate(summary["accounts"], start=9):
            ws_resumo.cell(row=idx, column=1, value=acc["name"])
            c = ws_resumo.cell(row=idx, column=2, value=acc["balance"])
            c.number_format = 'R$ #,##0.00'

        # ====================================================================
        # ABA 2: Lançamentos / Extrato
        # ====================================================================
        ws_txs = wb.create_sheet(title="Lancamentos")
        ws_txs.views.sheetView[0].showGridLines = True

        headers = ["Data", "Tipo", "Categoria", "Descrição", "Forma Pagamento", "Valor", "Essencial", "Pago", "Conta", "Obs"]
        for col_idx, h in enumerate(headers, start=1):
            cell = ws_txs.cell(row=1, column=col_idx, value=h)
            cell.font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="334155", end_color="334155", fill_type="solid")
            cell.alignment = Alignment(horizontal="center")

        for row_idx, t in enumerate(transactions, start=2):
            ws_txs.cell(row=row_idx, column=1, value=t["date"])
            ws_txs.cell(row=row_idx, column=2, value=t["type"])
            ws_txs.cell(row=row_idx, column=3, value=t["category"])
            ws_txs.cell(row=row_idx, column=4, value=t["description"])
            ws_txs.cell(row=row_idx, column=5, value=t["payment_method"])
            v_cell = ws_txs.cell(row=row_idx, column=6, value=t["amount"])
            v_cell.number_format = 'R$ #,##0.00'
            ws_txs.cell(row=row_idx, column=7, value=t["essential"])
            ws_txs.cell(row=row_idx, column=8, value=t["paid"])
            ws_txs.cell(row=row_idx, column=9, value=t["account"])
            ws_txs.cell(row=row_idx, column=10, value=t["obs"])

        # Ajuste de largura das colunas
        for ws in [ws_resumo, ws_txs]:
            for col in ws.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = openpyxl.utils.get_column_letter(col[0].column)
                ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output
