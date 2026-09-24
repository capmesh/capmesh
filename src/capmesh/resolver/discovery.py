"""
Natural language capability discovery.

Maps natural language queries to capability IDs using keyword matching,
capability descriptions, and ID decomposition.

No LLM required. Deterministic and fast.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from capmesh.registry.registry import Registry


@dataclass
class DiscoveryResult:
    capability: str
    contract: str
    score: float
    reason: str


class CapabilityDiscovery:
    """Discovers capabilities from natural language queries."""

    def __init__(self, registry: Registry, embedding_engine=None) -> None:
        self._registry = registry
        self._embedding_engine = embedding_engine
        self._capability_embeddings: dict[str, list[float]] = {}

    def discover(self, query: str, contract: str = "v1", limit: int = 5) -> list[DiscoveryResult]:
        """Find capabilities matching a natural language query.

        Scoring:
        1. Exact match on capability ID (score 1.0)
        2. All query words found in capability ID parts (score 0.8)
        3. Partial word matches in ID + description (score 0.3-0.7)

        When an embedding_engine is available, semantic similarity is used
        and merged with keyword results (semantic has priority).
        """
        query_lower = query.lower().strip()
        query_words = self._tokenize(query_lower)

        # Get all unique capabilities from registry
        all_artifacts = self._registry.list()
        capability_map: dict[str, str] = {}  # capability -> best description
        for artifact in all_artifacts:
            manifest = self._registry.get(artifact.namespace, artifact.name, artifact.version)
            if manifest is None:
                continue
            for cap in manifest.provides:
                if cap.capability not in capability_map or cap.description:
                    capability_map[cap.capability] = cap.description

        # Try semantic search first if embedding engine is available
        if self._embedding_engine and self._embedding_engine.available:
            semantic_results = self._semantic_search(query, capability_map, contract)
            if semantic_results:
                keyword_results = self._keyword_search(query_lower, query_words, capability_map, contract)
                return self._merge_results(semantic_results, keyword_results, limit)

        # Fall back to keyword matching
        return self._keyword_search(query_lower, query_words, capability_map, contract)[:limit]

    def _semantic_search(self, query: str, capability_map: dict[str, str], contract: str) -> list[DiscoveryResult]:
        """Search capabilities using embedding similarity."""
        engine = self._embedding_engine

        # Embed capabilities (cached)
        for cap_id, desc in capability_map.items():
            if cap_id not in self._capability_embeddings:
                text = f"{cap_id.replace('.', ' ')} {desc}"
                vec = engine.embed(text)
                if vec:
                    self._capability_embeddings[cap_id] = vec

        # Embed query
        query_vec = engine.embed(query)
        if query_vec is None:
            return []

        results = []
        for cap_id, cap_vec in self._capability_embeddings.items():
            score = engine.similarity(query_vec, cap_vec)
            if score > 0.25:
                results.append(DiscoveryResult(
                    capability=cap_id,
                    contract=contract,
                    score=round(score, 3),
                    reason=f"semantic similarity ({score:.2f})",
                ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results

    def _keyword_search(self, query_lower: str, query_words: list[str],
                        capability_map: dict[str, str], contract: str) -> list[DiscoveryResult]:
        """Search capabilities using keyword and synonym matching."""
        results = []
        for cap_id, description in capability_map.items():
            score, reason = self._score(query_lower, query_words, cap_id, description)
            if score > 0.0:
                results.append(DiscoveryResult(
                    capability=cap_id,
                    contract=contract,
                    score=score,
                    reason=reason,
                ))
        results.sort(key=lambda r: r.score, reverse=True)
        return results

    def _merge_results(self, semantic: list[DiscoveryResult], keyword: list[DiscoveryResult],
                       limit: int) -> list[DiscoveryResult]:
        """Merge semantic and keyword results. Semantic gets priority, deduped."""
        seen: set[str] = set()
        merged: list[DiscoveryResult] = []
        for r in semantic:
            if r.capability not in seen:
                seen.add(r.capability)
                merged.append(r)
        for r in keyword:
            if r.capability not in seen:
                seen.add(r.capability)
                merged.append(r)
        return merged[:limit]

    def discover_one(self, query: str, contract: str = "v1") -> DiscoveryResult | None:
        """Find the best matching capability, or None."""
        results = self.discover(query, contract, limit=1)
        return results[0] if results else None

    def _score(self, query: str, query_words: list[str], cap_id: str, description: str) -> tuple[float, str]:
        """Score a capability against the query. Returns (score, reason)."""
        cap_lower = cap_id.lower()

        # Exact match
        if query == cap_lower:
            return 1.0, "exact match"

        # Query is a substring of the capability ID
        if query in cap_lower:
            return 0.9, f"query is substring of '{cap_id}'"

        # Decompose capability ID into words: "security.code.review" -> ["security", "code", "review"]
        cap_parts = self._tokenize(cap_lower)

        # All description words
        desc_words = self._tokenize(description.lower()) if description else []
        all_target_words = set(cap_parts + desc_words)

        # All query words found in capability parts
        if query_words and all(qw in all_target_words for qw in query_words):
            return 0.8, f"all query words found in '{cap_id}'"

        # Partial matches — count how many query words match
        if query_words:
            matches = sum(1 for qw in query_words if any(
                qw in tw or tw in qw for tw in all_target_words
            ))
            if matches > 0:
                score = 0.3 + (0.4 * matches / len(query_words))
                matched = [qw for qw in query_words if any(qw in tw or tw in qw for tw in all_target_words)]
                return round(score, 2), f"partial match: {', '.join(matched)}"

        # Synonym/related word matching
        synonyms = {
            "repo": ["repository"], "repository": ["repo"],
            "code": ["repository", "source"], "source": ["code", "repository"],
            "security": ["scan", "review", "vulnerability"],
            "scan": ["security", "analyze"], "review": ["code", "security"],
            "notify": ["notification", "send", "alert", "slack", "message"],
            "notification": ["notify", "send", "alert"],
            "send": ["notify", "notification"],
            "alert": ["notify", "notification", "incident"],
            "bug": ["issue", "ticket"], "ticket": ["issue", "bug"],
            "issue": ["bug", "ticket", "create"],
            "deploy": ["release", "ship"], "release": ["deploy", "ship"],
            "test": ["generate", "coverage"], "coverage": ["test"],
            "perf": ["performance"], "performance": ["perf"],
            "monitor": ["metrics", "observability"], "metrics": ["monitor", "query"],
            "db": ["database", "data", "query"], "database": ["db", "data", "query"],
            "docs": ["documentation", "generate"], "documentation": ["docs"],
            "read": ["repository", "fetch", "get"], "fetch": ["read", "get"],
            "store": ["artifact", "save", "upload"], "save": ["store", "artifact"],
            "analyze": ["analysis", "scan", "review"],
        }

        expanded_query = set(query_words)
        for qw in query_words:
            if qw in synonyms:
                expanded_query.update(synonyms[qw])

        if expanded_query:
            matches = sum(1 for ew in expanded_query if any(
                ew in tw or tw in ew for tw in all_target_words
            ))
            if matches > 0:
                score = 0.2 + (0.3 * matches / len(expanded_query))
                return round(min(score, 0.7), 2), f"synonym match ({matches} related words)"

        return 0.0, ""

    def _tokenize(self, text: str) -> list[str]:
        """Split text into words, handling dots, dashes, underscores, spaces."""
        return [w for w in re.split(r'[.\-_\s/]+', text) if w and len(w) > 1]
