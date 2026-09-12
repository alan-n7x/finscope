"""Calculo do limite diario recomendado de gastos.

Funcao pura (sem I/O) para permitir testes unitarios deterministicos dos
cenarios de saldo positivo, zerado e negativo.
"""

from __future__ import annotations

import datetime
from typing import Literal

DailyLimitStatus = Literal["NORMAL", "WARNING", "EXCEEDED"]

WARNING_THRESHOLD = 0.8


def compute_daily_limit(
    total_balance: float,
    pending_month: float,
    spent_ref_day: float,
    ref_date: datetime.date,
    target_month: str,
) -> dict[str, float | int | str]:
    """Calcula o limite diario recomendado a partir de agregados do mes.

    - free_balance: saldo total menos despesas pendentes do mes alvo.
    - days_remaining: dias de ref_date ate o fim do mes alvo (minimo 1).
    - recommended_per_day: free_balance / days_remaining.
    - remaining_today: recommended_per_day - gastos na data de referencia.
    - status: EXCEEDED se estourou (ou sem saldo livre), WARNING se
      consumiu >= 80% da cota ou nao ha margem, NORMAL caso contrario.
    """
    year_str, month_str = target_month.split("-")
    year, month = int(year_str), int(month_str)
    if month == 12:
        last_day = datetime.date(year, 12, 31)
    else:
        last_day = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)

    days_remaining = max((last_day - ref_date).days + 1, 1)

    free_balance = round(total_balance - pending_month, 2)
    recommended_per_day = round(free_balance / days_remaining, 2)
    spent = round(spent_ref_day, 2)
    remaining_today = round(recommended_per_day - spent, 2)

    if free_balance < 0 or remaining_today < 0:
        status: DailyLimitStatus = "EXCEEDED"
    elif recommended_per_day <= 0 or spent >= WARNING_THRESHOLD * recommended_per_day:
        status = "WARNING"
    else:
        status = "NORMAL"

    return {
        "recommended_per_day": recommended_per_day,
        "spent_today": spent,
        "remaining_today": remaining_today,
        "days_remaining": days_remaining,
        "free_balance": free_balance,
        "status": status,
    }
