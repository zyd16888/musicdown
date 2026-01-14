import asyncio
from typing import Optional

from telegram import Message, Update
from telegram.ext import ContextTypes


async def ensure_private_chat(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    notice: str = "⚠️ 这是一个私聊命令，请私聊使用。",
    delay: int = 5,
) -> bool:
    chat = update.effective_chat
    if not chat or chat.type == "private":
        return True

    message: Optional[Message] = update.effective_message
    try:
        reply = await message.reply_text(notice) if message else None
    except Exception:
        reply = None

    async def cleanup():
        await asyncio.sleep(delay)
        for msg in (reply, message):
            if not msg:
                continue
            try:
                await msg.delete()
            except Exception:
                pass

    context.application.create_task(cleanup())
    return False
