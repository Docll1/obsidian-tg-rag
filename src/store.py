from __future__ import annotations

import math
import sqlite3
import struct
from pathlib import Path


def _pack(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def _unpack(blob: bytes) -> list[float]:
    n = len(blob) // 4
    return list(struct.unpack(f"{n}f", blob))


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class VectorStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY,
                    path TEXT NOT NULL,
                    heading TEXT NOT NULL,
                    text TEXT NOT NULL,
                    embedding BLOB NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_path ON chunks(path)")

    def replace_all(self, rows: list[dict]) -> int:
        with self._connect() as conn:
            conn.execute("DELETE FROM chunks")
            conn.executemany(
                "INSERT INTO chunks(path, heading, text, embedding) VALUES (?, ?, ?, ?)",
                [
                    (r["path"], r["heading"], r["text"], _pack(r["embedding"]))
                    for r in rows
                ],
            )
        return len(rows)

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM chunks").fetchone()
            return int(row["n"])

    def search(self, query_vec: list[float], k: int = 5) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT path, heading, text, embedding FROM chunks").fetchall()
        scored = []
        for row in rows:
            score = cosine(query_vec, _unpack(row["embedding"]))
            scored.append(
                {
                    "path": row["path"],
                    "heading": row["heading"],
                    "text": row["text"],
                    "score": round(score, 4),
                }
            )
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:k]

    def read_note(self, path: str) -> str | None:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT heading, text FROM chunks WHERE path = ? ORDER BY id",
                (path,),
            ).fetchall()
        if not rows:
            return None
        parts = []
        for row in rows:
            title = row["heading"].strip()
            body = row["text"].strip()
            parts.append(f"## {title}\n{body}" if title else body)
        return "\n\n".join(parts)

    def list_paths(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT DISTINCT path FROM chunks ORDER BY path").fetchall()
        return [r["path"] for r in rows]
