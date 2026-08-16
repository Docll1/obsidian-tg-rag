from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from src.agent import KnowledgeAgent
from src.config import Settings
from src.store import VectorStore

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("bot")


def allowed(update: Update, settings: Settings) -> bool:
    user = update.effective_user
    if user is None:
        return False
    if not settings.allowed_user_ids:
        return True
    return user.id in settings.allowed_user_ids


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.application.bot_data["settings"]
    user = update.effective_user
    uid = user.id if user else "?"
    if settings.allowed_user_ids and not allowed(update, settings):
        await update.message.reply_text(
            f"Access denied. Your Telegram id is {uid}. Add it to TELEGRAM_ALLOWED_USER_IDS."
        )
        return
    n = context.application.bot_data["store"].count()
    await update.message.reply_text(
        "Knowledge agent over an Obsidian vault.\n"
        "Ask a question, or /reindex after you add notes.\n"
        f"Indexed chunks: {n}\n"
        f"Your id: {uid}"
    )


async def cmd_reindex(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.application.bot_data["settings"]
    if not allowed(update, settings):
        await update.message.reply_text("Access denied.")
        return
    await update.message.reply_text("Reindexing vault…")
    agent: KnowledgeAgent = context.application.bot_data["agent"]
    n = agent.reindex()
    await update.message.reply_text(f"Done. {n} chunks indexed.")


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.application.bot_data["settings"]
    if update.message is None or not update.message.text:
        return
    if not allowed(update, settings):
        uid = update.effective_user.id if update.effective_user else "?"
        await update.message.reply_text(
            f"Access denied. Your Telegram id is {uid}."
        )
        return
    agent: KnowledgeAgent = context.application.bot_data["agent"]
    await update.message.chat.send_action("typing")
    try:
        answer = agent.ask(update.message.text)
    except Exception:
        log.exception("ask failed")
        await update.message.reply_text("Agent error. Check server logs.")
        return
    await update.message.reply_text(answer[:4000])


def main() -> None:
    settings = Settings.load()
    store = VectorStore(settings.index_path)
    agent = KnowledgeAgent(settings, store)
    if store.count() == 0:
        log.info("empty index, ingesting %s", settings.vault_path)
        n = agent.reindex()
        log.info("indexed %s chunks", n)

    app = Application.builder().token(settings.telegram_token).build()
    app.bot_data["settings"] = settings
    app.bot_data["store"] = store
    app.bot_data["agent"] = agent
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("reindex", cmd_reindex))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    log.info("bot polling")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
