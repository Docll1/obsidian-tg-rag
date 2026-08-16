from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _ids(raw: str) -> set[int]:
    out: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part:
            out.add(int(part))
    return out


@dataclass(frozen=True)
class Settings:
    telegram_token: str
    llm_api_key: str
    llm_base_url: str
    llm_model: str
    embed_model: str
    allowed_user_ids: set[int]
    vault_path: Path
    index_path: Path

    @classmethod
    def load(cls) -> "Settings":
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        llm_key = os.getenv("LLM_API_KEY", "").strip()
        if not token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")
        if not llm_key:
            raise RuntimeError(
                "LLM_API_KEY is missing. Get a DeepSeek key at https://platform.deepseek.com/api_keys"
            )
        return cls(
            telegram_token=token,
            llm_api_key=llm_key,
            llm_base_url=os.getenv("LLM_BASE_URL", "https://api.deepseek.com").rstrip("/"),
            llm_model=os.getenv("LLM_MODEL", "deepseek-chat"),
            embed_model=os.getenv("EMBED_MODEL", "intfloat/multilingual-e5-small"),
            allowed_user_ids=_ids(os.getenv("TELEGRAM_ALLOWED_USER_IDS", "")),
            vault_path=Path(os.getenv("VAULT_PATH", "./vault")),
            index_path=Path(os.getenv("INDEX_PATH", "./data/index/vault.sqlite")),
        )
