import re
import datetime
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from app.config import get_settings
from app.infra.db.session import async_session_factory
from app.schemas import TransactionCreate
from app.services.transaction_service import TransactionService

router = Router()
settings = get_settings()

def is_allowed(user_id: int) -> bool:
    """Verifica se o usuário pode usar o bot (allowlist opcional por env).

    Args:
        user_id: Id do remetente no Telegram.

    Returns:
        True quando `TELEGRAM_ALLOWED_USER_ID` está vazio ou coincide.
    """
    if settings.telegram_allowed_user_id:
        return user_id == settings.telegram_allowed_user_id
    return True

@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    """Responde ao /start com boas-vindas e o formato de lançamento rápido.

    Args:
        message: Mensagem do comando recebido.
    """
    if not is_allowed(message.from_user.id):
        await message.answer("Desculpe, você não tem permissão para usar este bot.")
        return

    welcome_text = (
        "👋 Olá! Eu sou o Finscope Bot.\n\n"
        "Você pode me usar para lançar despesas rapidamente. "
        "Basta digitar o valor e a descrição. Por exemplo:\n\n"
        "`50 Almoço`\n"
        "`12.50 Uber`\n\n"
        "Os lançamentos são registrados no Finscope na categoria 'Outros'."
    )
    await message.answer(welcome_text, parse_mode="Markdown")


@router.message(F.text)
async def process_transaction(message: Message) -> None:
    """Registra despesa a partir de texto no formato "<Valor> <Descrição>".

    Exemplos: "50 Almoço", "12.50 Uber". Lançamento idempotente via
    `external_id` telegram:chat:message.

    Args:
        message: Mensagem de texto com valor e descrição.
    """
    if not is_allowed(message.from_user.id):
        return

    text = message.text.strip()
    
    # Regex to extract amount (can contain comma or dot) and description
    # E.g. "50.90 Almoço", "10,50 Uber"
    match = re.match(r"^([\d\.,]+)\s+(.+)$", text)
    
    if not match:
        await message.answer(
            "⚠️ Formato não reconhecido. Use o formato: `Valor Descrição`\n"
            "Exemplo: `50 Almoço`", 
            parse_mode="Markdown"
        )
        return
        
    val_str = match.group(1).replace(',', '.')
    description = match.group(2).strip()
    
    try:
        amount = float(val_str)
    except ValueError:
        await message.answer("⚠️ Valor inválido.")
        return

    today = datetime.datetime.now().strftime("%Y-%m-%d")

    try:
        async with async_session_factory() as session:
            await TransactionService(session).create(
                TransactionCreate(
                    date=today,
                    type="Despesa",
                    category="Outros",
                    description=description,
                    payment_method="Pix",
                    amount=amount,
                    essential=False,
                    paid=True,
                    obs="Lançado via Telegram",
                    account="Itaú - Conta corrente",
                ),
                external_id=f"telegram:{message.chat.id}:{message.message_id}",
            )
            await session.commit()
        await message.answer(f"✅ Lançado: **R$ {amount:.2f}** - {description}", parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Erro ao salvar lançamento:\n{str(e)}")
