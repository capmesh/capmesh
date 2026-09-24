import pytest


def test_embedding_engine_loads():
    from capmesh.resolver.embeddings import EmbeddingEngine
    engine = EmbeddingEngine()
    assert engine is not None


def test_embed_returns_vector():
    from capmesh.resolver.embeddings import EmbeddingEngine
    engine = EmbeddingEngine()
    if not engine.available:
        pytest.skip("sentence-transformers not installed")
    vec = engine.embed("read code from a repository")
    assert isinstance(vec, list)
    assert len(vec) > 0
    assert all(isinstance(x, float) for x in vec)


def test_similarity_same_text():
    from capmesh.resolver.embeddings import EmbeddingEngine
    engine = EmbeddingEngine()
    if not engine.available:
        pytest.skip("sentence-transformers not installed")
    a = engine.embed("security scan")
    b = engine.embed("security scan")
    sim = engine.similarity(a, b)
    assert sim > 0.99


def test_similarity_related():
    from capmesh.resolver.embeddings import EmbeddingEngine
    engine = EmbeddingEngine()
    if not engine.available:
        pytest.skip("sentence-transformers not installed")
    a = engine.embed("scan for security vulnerabilities")
    b = engine.embed("security code review")
    c = engine.embed("deploy to production")
    sim_related = engine.similarity(a, b)
    sim_unrelated = engine.similarity(a, c)
    assert sim_related > sim_unrelated


def test_embed_batch():
    from capmesh.resolver.embeddings import EmbeddingEngine
    engine = EmbeddingEngine()
    if not engine.available:
        pytest.skip("sentence-transformers not installed")
    vecs = engine.embed_batch(["read a repo", "security scan", "deploy"])
    assert len(vecs) == 3
    assert all(len(v) > 0 for v in vecs)


def test_engine_not_available_without_dep(monkeypatch):
    """If sentence-transformers is not installed, engine.available is False."""
    from capmesh.resolver import embeddings
    monkeypatch.setattr(embeddings, "_ST_AVAILABLE", False)
    engine = embeddings.EmbeddingEngine()
    assert engine.available is False
    assert engine.embed("test") is None
