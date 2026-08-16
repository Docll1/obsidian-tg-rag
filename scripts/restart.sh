#!/bin/sh
# Recreate the bot so it rereads .env. Do not use --build unless Python code changed.
set -e
cd "$(dirname "$0")/.."
docker rm -f obsidian-tg-rag-bot obsidian-tg-rag_bot_1 2>/dev/null || true
docker compose -p obsidian-tg-rag up -d "$@"
docker compose -p obsidian-tg-rag logs --tail=30
