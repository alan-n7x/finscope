"""Recategoriza lançamentos importados que ficaram em "Outros".

O script aplica as mesmas regras conservadoras de `app.categorization` aos
lançamentos já gravados, sem tocar em categorias editadas manualmente:

- considera apenas `external_id LIKE 'import:%'`;
- considera apenas a categoria atual `Outros`;
- por padrão roda em **dry-run** (não grava nada);
- `--apply` confirma a gravação;
- `--month YYYY-MM` limita a um mês.

Uso:

    # ver o que mudaria
    uv run python scripts/recategorize_transactions.py --month 2026-11

    # aplicar
    uv run python scripts/recategorize_transactions.py --month 2026-11 --apply

Também funciona dentro do container:

    docker compose exec backend uv run python scripts/recategorize_transactions.py --apply
"""
from __future__ import annotations

import argparse
import asyncio
import datetime
import pathlib
import sys
from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))

from app.categorization import FALLBACK_CATEGORY, categorize
from app.import_rules import is_self_transfer
from app.infra.db.models import Category, Transaction, TransactionType
from app.infra.db.session import async_session_factory

TYPE_LABELS = {
    TransactionType.INCOME: "Receita",
    TransactionType.EXPENSE: "Despesa",
    TransactionType.TRANSFER: "Transferência",
}

SAMPLE_LIMIT = 40


def _month_range(month: str) -> tuple[datetime.date, datetime.date]:
    """Converte ``YYYY-MM`` no intervalo [primeiro dia, primeiro dia seguinte).

    Raises:
        ValueError: Quando o mês não está no formato esperado.
    """
    try:
        year_str, month_str = month.split("-")
        start = datetime.date(int(year_str), int(month_str), 1)
    except (ValueError, AttributeError) as exc:
        raise ValueError("Use --month no formato YYYY-MM (ex.: 2026-11).") from exc

    end = (
        datetime.date(start.year + 1, 1, 1)
        if start.month == 12
        else datetime.date(start.year, start.month + 1, 1)
    )
    return start, end


def _signed_amount(transaction: Transaction) -> float:
    """Valor com sinal coerente com o tipo do lançamento."""
    amount = float(transaction.amount)
    return amount if transaction.type == TransactionType.INCOME else -amount


def _proposed_category(transaction: Transaction) -> str:
    """Executa as regras de categorização para um lançamento do banco."""
    return categorize(
        transaction.description,
        is_self=is_self_transfer(transaction.description),
        amount=_signed_amount(transaction),
        tx_type=TYPE_LABELS[transaction.type],
    )


async def _get_or_create_category(session, user_id, name: str) -> Category:
    """Busca a categoria do usuário ou cria uma nova com o nome canônico."""
    category = await session.scalar(
        select(Category).where(
            Category.user_id == user_id,
            func.lower(Category.name) == name.lower(),
        )
    )
    if category is None:
        category = Category(user_id=user_id, name=name)
        session.add(category)
        await session.flush()
    return category


async def run(month: str | None, apply: bool) -> int:
    """Executa a recategorização e devolve o código de saída do processo.

    Args:
        month: Mês opcional no formato ``YYYY-MM``.
        apply: Quando False, apenas imprime o que mudaria.

    Returns:
        0 em sucesso; 2 quando o mês é inválido.
    """
    stmt = (
        select(Transaction)
        .options(
            selectinload(Transaction.account),
            selectinload(Transaction.category),
        )
        .join(Category, Transaction.category_id == Category.id)
        .where(
            Transaction.external_id.like("import:%"),
            func.lower(Category.name) == FALLBACK_CATEGORY.lower(),
        )
        .order_by(Transaction.date, Transaction.created_at)
    )

    if month is not None:
        try:
            start, end = _month_range(month)
        except ValueError as exc:
            print(f"ERRO: {exc}")
            return 2
        stmt = stmt.where(Transaction.date >= start, Transaction.date < end)

    async with async_session_factory() as session:
        transactions = (await session.execute(stmt)).scalars().all()

        changes: list[tuple[Transaction, str]] = []
        for transaction in transactions:
            new_category = _proposed_category(transaction)
            if new_category != FALLBACK_CATEGORY:
                changes.append((transaction, new_category))

        mode = "APLICAR" if apply else "DRY-RUN"
        scope = f"mês {month}" if month else "todos os meses"
        print(f"[{mode}] {len(transactions)} lançamento(s) importado(s) em Outros ({scope}).")

        if not changes:
            print("Nenhuma recategorização necessária.")
            return 0

        for transaction, new_category in changes[:SAMPLE_LIMIT]:
            description = transaction.description.replace("\n", " ")[:70]
            print(
                f"  {transaction.date}  {description!r}  "
                f"Outros -> {new_category}"
            )
        if len(changes) > SAMPLE_LIMIT:
            print(f"  ... e mais {len(changes) - SAMPLE_LIMIT} lançamento(s).")

        counter = Counter(new_category for _, new_category in changes)
        print("\nResumo:")
        for category, count in counter.most_common():
            print(f"  {category}: {count}")

        if not apply:
            print("\nNada foi gravado. Rode novamente com --apply para aplicar.")
            return 0

        cache: dict[tuple, Category] = {}
        for transaction, new_category in changes:
            user_id = transaction.account.user_id
            key = (user_id, new_category)
            category = cache.get(key)
            if category is None:
                category = await _get_or_create_category(session, user_id, new_category)
                cache[key] = category
            transaction.category_id = category.id

        await session.commit()
        print(f"\n{len(changes)} lançamento(s) recategorizado(s).")
        return 0


def main() -> int:
    """Ponto de entrada do script."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--month",
        help="Limita a um mês no formato YYYY-MM (padrão: todos).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Grava as mudanças (sem esta flag o script é dry-run).",
    )
    args = parser.parse_args()
    return asyncio.run(run(args.month, args.apply))


if __name__ == "__main__":
    raise SystemExit(main())
