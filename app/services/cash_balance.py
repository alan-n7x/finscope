"""Serie diaria de saldo realizado vs projetado.

Funcao pura (sem I/O) para permitir testes unitarios deterministicos da
regra de projecao. Regras de negocio:

- realized usa exclusivamente lancamentos confirmados (POSTED) ate o dia de
  transicao; dias apos a transicao recebem None e nunca sao reescritos.
- projected comeca exatamente no ponto de transicao (ultimo saldo
  confirmado) e incorpora pendentes com data posterior a transicao.
  Pendentes com data na transicao ou antes (em atraso) entram na projecao
  a partir do primeiro dia apos a transicao, pois o impacto no caixa ainda
  esta por vir. Pendentes nunca alteram o realizado.
- A data efetiva do pendente e o proprio campo date do lancamento; o
  modelo nao possui data de vencimento separada, portanto nenhuma data e
  inventada.
- Transferencias nao entram na serie (consistente com income/expense do
  dashboard, que tambem as excluem do fluxo).
- Valores sao arredondados a 2 casas por dia, mesmo padrao do restante do
  modulo financeiro.
"""

from __future__ import annotations

import datetime


def compute_cash_balance(
    start_balance: float,
    posted_net_by_day: dict[int, float],
    pending_net_by_day: dict[int, float],
    year: int,
    month: int,
    transition_day: int,
) -> list[dict[str, float | int | str | None]]:
    """Calcula a serie diaria de saldo realizado e projetado.

    Args:
        start_balance: Saldo no dia anterior ao inicio do mes.
        posted_net_by_day: Mapa dia -> (receitas - despesas) confirmadas.
        pending_net_by_day: Mapa dia -> (receitas - despesas) pendentes.
        year: Ano do periodo.
        month: Mes do periodo (1-12).
        transition_day: Ultimo dia com dados confirmados. Dias acima dele
            tem realized None. Use 0 quando nao ha dia confirmado (mes
            futuro) e o ultimo dia do mes quando tudo esta confirmado.

    Returns:
        Lista com um item por dia do mes, cada um com day, date,
        realized_balance (None apos a transicao) e projected_balance
        (None antes da transicao).
    """
    if month == 12:
        last_day = 31
    else:
        last_day = (datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)).day
    transition_day = max(0, min(transition_day, last_day))

    running_posted = 0.0
    running_pending = 0.0
    carry = round(sum(
        net for day, net in pending_net_by_day.items() if day <= transition_day
    ), 2)
    realized_at_transition = round(start_balance, 2)
    series = []
    for day in range(1, last_day + 1):
        running_posted = round(running_posted + posted_net_by_day.get(day, 0.0), 2)
        if day <= transition_day:
            realized: float | None = round(start_balance + running_posted, 2)
            realized_at_transition = realized
            projected: float | None = realized if day == transition_day else None
        else:
            realized = None
            if day == transition_day + 1:
                running_pending = round(running_pending + carry, 2)
            running_pending = round(running_pending + pending_net_by_day.get(day, 0.0), 2)
            projected = round(realized_at_transition + running_pending, 2)
        series.append({
            "day": day,
            "date": datetime.date(year, month, day).isoformat(),
            "realized_balance": realized,
            "projected_balance": projected,
        })
    return series
