"""Guarda-corpo estático contra SQL bruto interpolado.

O erro ``invalid input value for enum transaction_type_enum: "'INCOME'"``
nasce quando um valor de enum é montado como texto (por exemplo,
``t.type = '''INCOME'''``). O ORM e ``text().bindparams()`` não têm esse
problema; este teste impede que ``text()`` receba expressões dinâmicas em
``app/`` e ``scripts/``.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIRS = (ROOT / "app", ROOT / "scripts")


def _python_files() -> list[Path]:
    """Lista os módulos de produção e scripts versionados."""
    return sorted(
        path
        for base in SOURCE_DIRS
        for path in base.rglob("*.py")
    )


def _text_calls(tree: ast.AST):
    """Percorre chamadas ``text(...)`` no módulo."""
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "text"
        ):
            yield node


def test_text_recebe_apenas_string_literal():
    """``text()`` não pode receber f-string, concatenação ou ``.format()``."""
    problems: list[str] = []

    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for call in _text_calls(tree):
            relative = path.relative_to(ROOT)
            if not call.args:
                problems.append(f"{relative}:{call.lineno}: text() sem SQL")
                continue

            argument = call.args[0]
            is_static_string = (
                isinstance(argument, ast.Constant)
                and isinstance(argument.value, str)
            )
            if not is_static_string:
                problems.append(
                    f"{relative}:{call.lineno}: text() recebeu SQL dinâmico; "
                    "use bindparams/ORM em vez de interpolar valores."
                )

    assert not problems, "SQL bruto interpolado encontrado:\n" + "\n".join(problems)
