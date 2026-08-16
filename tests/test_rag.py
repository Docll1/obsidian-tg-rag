from src.ingest import chunk_markdown
from src.store import cosine


def test_chunk_splits_headings():
    text = "# Title\n\nintro\n\n## DNS\n\nA record maps name to IPv4.\n\n## TLS\n\nHTTPS uses 443."
    chunks = chunk_markdown(text, "net.md")
    headings = {c["heading"] for c in chunks}
    assert "DNS" in headings
    assert "TLS" in headings
    assert all(c["path"] == "net.md" for c in chunks)


def test_cosine_identical_is_one():
    v = [1.0, 0.0, 0.0]
    assert abs(cosine(v, v) - 1.0) < 1e-6


def test_cosine_orthogonal_is_zero():
    assert abs(cosine([1.0, 0.0], [0.0, 1.0])) < 1e-6
