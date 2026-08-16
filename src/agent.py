from __future__ import annotations

import json
import logging

from openai import OpenAI

from src.config import Settings
from src.embed import get_embedder
from src.ingest import load_chunks
from src.store import VectorStore

log = logging.getLogger(__name__)

SYSTEM = """You are a personal knowledge agent over an Obsidian vault.
Use tools to find facts. Answer in the same language as the user.
If the notes do not contain the answer, say so. Do not invent.
Always cite note paths you used, like [path/note.md].
Keep answers short and practical.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_notes",
            "description": "Semantic search over vault notes. Call this first.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_note",
            "description": "Read a full note by relative path returned from search_notes.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
]


class KnowledgeAgent:
    def __init__(self, settings: Settings, store: VectorStore) -> None:
        self.settings = settings
        self.store = store
        self._embedder = None
        self.client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )

    @property
    def embedder(self):
        if self._embedder is None:
            self._embedder = get_embedder(self.settings.embed_model)
        return self._embedder

    def reindex(self) -> int:
        chunks = load_chunks(self.settings.vault_path)
        if not chunks:
            return self.store.replace_all([])
        vectors = self.embedder.embed_docs([c["text"] for c in chunks])
        rows = [{**chunk, "embedding": vec} for chunk, vec in zip(chunks, vectors)]
        return self.store.replace_all(rows)

    def search_notes(self, query: str, k: int = 5) -> str:
        hits = self.store.search(self.embedder.embed_query(query), k=k)
        if not hits:
            return "No matching notes."
        blocks = []
        for hit in hits:
            blocks.append(
                f"[{hit['path']}] score={hit['score']} :: {hit['heading']}\n{hit['text'][:900]}"
            )
        return "\n\n---\n\n".join(blocks)

    def read_note(self, path: str) -> str:
        text = self.store.read_note(path)
        if text is None:
            known = ", ".join(self.store.list_paths()[:30]) or "(empty index)"
            return f"Note not found: {path}. Known paths: {known}"
        return f"[{path}]\n{text[:4000]}"

    def _run_tool(self, name: str, raw_args: str, fallback_query: str) -> str:
        try:
            args = json.loads(raw_args or "{}")
        except json.JSONDecodeError:
            args = {}
        if name == "search_notes":
            return self.search_notes(str(args.get("query", fallback_query)))
        if name == "read_note":
            return self.read_note(str(args.get("path", "")))
        return f"Unknown tool: {name}"

    def ask(self, question: str) -> str:
        messages: list[dict] = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": question},
        ]
        for _ in range(5):
            response = self.client.chat.completions.create(
                model=self.settings.llm_model,
                messages=messages,
                tools=TOOLS,
                temperature=0.2,
            )
            msg = response.choices[0].message
            if not msg.tool_calls:
                return (msg.content or "").strip() or "Empty model response."

            messages.append(
                {
                    "role": "assistant",
                    "content": msg.content,
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {
                                "name": call.function.name,
                                "arguments": call.function.arguments,
                            },
                        }
                        for call in msg.tool_calls
                    ],
                }
            )
            for call in msg.tool_calls:
                result = self._run_tool(call.function.name, call.function.arguments, question)
                log.info("tool %s", call.function.name)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": result,
                    }
                )
        return "Stopped after too many tool calls. Try a narrower question."
