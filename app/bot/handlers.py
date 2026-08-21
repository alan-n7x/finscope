import re
import datetime
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from app import excel_engine
from app.config import get_settings

router = Router()
settings = get_settings()

def is_allowed(user_id: int) -> bool:
    """
    Checks if the user is authorized to use the bot.
    If TELEGRAM_ALLOWED_USER_ID is set, only that user is allowed.
    """
    if settings.telegram_allowed_user_id:
        return user_id == settings.telegram_allowed_user_id
    return True

@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    """
    Handles the /start command.
    Welcomes the user and explains how to use the bot.
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
        "Os lançamentos vão direto para a sua planilha na categoria 'Outros'."
    )
    await message.answer(welcome_text, parse_mode="Markdown")


@router.message(F.text)
async def process_transaction(message: Message) -> None:
    """
    Processes a generic text message containing a quick transaction.
    Expects format: "<Valor> <Descrição>"
    Example: "50.90 Almoço Padaria"
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

    # Add to Excel
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    dt = {
        'date': today,
        'type': 'Despesa',
        'category': 'Outros',
        'description': description,
        'payment_method': 'Pix', 
        'amount': amount,
        'essential': False,
        'paid': True,
        'obs': 'Lançado via Telegram',
        'account': 'Itaú - Conta corrente'
    }
    
    try:
        excel_engine.add_transaction(dt)
        await message.answer(f"✅ Lançado: **R$ {amount:.2f}** - {description}", parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Erro ao salvar na planilha:\n{str(e)}")
