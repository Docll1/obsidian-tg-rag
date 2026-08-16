from __future__ import annotations

import logging
import threading

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
_index_lock = threading.Lock()
_index_ready = threading.Event()


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
    status = "ready" if _index_ready.is_set() else "building index, wait a minute"
    await update.message.reply_text(
        "Knowledge agent over an Obsidian vault.\n"
        "Ask a question, or /reindex after you add notes.\n"
        f"Indexed chunks: {n} ({status})\n"
        f"Your id: {uid}"
    )


async def cmd_reindex(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.application.bot_data["settings"]
    if not allowed(update, settings):
        await update.message.reply_text("Access denied.")
        return
    await update.message.reply_text("Reindexing vault…")
    agent: KnowledgeAgent = context.application.bot_data["agent"]
    with _index_lock:
        n = agent.reindex()
        _index_ready.set()
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
    if not _index_ready.is_set():
        await update.message.reply_text("Index is still building. Try /start in a minute.")
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


def _build_index(agent: KnowledgeAgent, store: VectorStore, vault_path) -> None:
    try:
        if store.count() == 0:
            log.info("empty index, ingesting %s", vault_path)
            n = agent.reindex()
            log.info("indexed %s chunks", n)
        else:
            log.info("loaded existing index, %s chunks", store.count())
        _index_ready.set()
    except Exception:
        log.exception("index build failed")


def main() -> None:
    settings = Settings.load()
    store = VectorStore(settings.index_path)
    agent = KnowledgeAgent(settings, store)
    threading.Thread(
        target=_build_index,
        args=(agent, store, settings.vault_path),
        daemon=True,
    ).start()

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
