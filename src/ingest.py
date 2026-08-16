from __future__ import annotations

import re
from pathlib import Path

SKIP_DIR_NAMES = {".obsidian", ".trash", ".git"}
SKIP_FILE_PARTS = ("сопроводительн", "долг", "вакансии")


def iter_markdown(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*.md"):
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        name = path.name.lower()
        if any(part in name for part in SKIP_FILE_PARTS):
            continue
        files.append(path)
    return sorted(files)


def chunk_markdown(text: str, rel_path: str, max_chars: int = 1200) -> list[dict]:
    text = text.replace("\r\n", "\n").strip()
    if not text:
        return []

    sections = re.split(r"(?m)^#{1,3}\s+", text)
    headings = re.findall(r"(?m)^#{1,3}\s+(.+)$", text)
    chunks: list[dict] = []

    if len(sections) == 1:
        pieces = _split_long(text, max_chars)
        for i, piece in enumerate(pieces):
            chunks.append({"path": rel_path, "heading": rel_path, "text": piece if i == 0 else f"{rel_path} (part {i+1})\n{piece}"})
        return chunks

    intro = sections[0].strip()
    if intro:
        chunks.append({"path": rel_path, "heading": Path(rel_path).stem, "text": intro})

    for heading, body in zip(headings, sections[1:]):
        body = body.strip()
        if not body:
            continue
        block = f"{heading.strip()}\n{body}"
        for i, piece in enumerate(_split_long(block, max_chars)):
            title = heading.strip() if i == 0 else f"{heading.strip()} (part {i+1})"
            chunks.append({"path": rel_path, "heading": title, "text": piece})
    return chunks


def _split_long(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    parts: list[str] = []
    buf: list[str] = []
    size = 0
    for para in text.split("\n\n"):
        extra = len(para) + 2
        if buf and size + extra > max_chars:
            parts.append("\n\n".join(buf).strip())
            buf, size = [para], extra
        else:
            buf.append(para)
            size += extra
    if buf:
        parts.append("\n\n".join(buf).strip())
    return [p for p in parts if p]


def load_chunks(vault: Path) -> list[dict]:
    chunks: list[dict] = []
    for path in iter_markdown(vault):
        rel = path.relative_to(vault).as_posix()
        raw = path.read_text(encoding="utf-8", errors="ignore")
        chunks.extend(chunk_markdown(raw, rel))
    return chunks
