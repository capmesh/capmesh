from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from capmesh.models.enums import Kind, Status
from capmesh.models.manifest import Manifest
from capmesh.models.serialization import (
    compute_digest,
    manifest_from_yaml,
    manifest_to_yaml,
)


class DuplicateVersionError(Exception):
    """Raised when pushing same name+version with different digest."""


@dataclass
class ArtifactRecord:
    namespace: str
    name: str
    kind: Kind
    version: str
    digest: str
    manifest_path: str
    created_at: str
    tags: list[str] = field(default_factory=list)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    namespace TEXT NOT NULL,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    version TEXT NOT NULL,
    digest TEXT NOT NULL,
    manifest_path TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(namespace, name, version)
);

CREATE TABLE IF NOT EXISTS capabilities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id INTEGER NOT NULL,
    capability TEXT NOT NULL,
    contract TEXT NOT NULL,
    direction TEXT NOT NULL,
    FOREIGN KEY (artifact_id) REFERENCES artifacts(id)
);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id INTEGER NOT NULL,
    tag TEXT NOT NULL,
    FOREIGN KEY (artifact_id) REFERENCES artifacts(id),
    UNIQUE(artifact_id, tag)
);

CREATE TABLE IF NOT EXISTS governance (
    artifact_id INTEGER PRIMARY KEY,
    visibility TEXT NOT NULL,
    status TEXT NOT NULL,
    owner TEXT NOT NULL,
    environment TEXT NOT NULL DEFAULT '[]',
    FOREIGN KEY (artifact_id) REFERENCES artifacts(id)
);

CREATE INDEX IF NOT EXISTS idx_capabilities_lookup
ON capabilities(capability, contract, direction);

CREATE INDEX IF NOT EXISTS idx_artifacts_namespace
ON artifacts(namespace);

CREATE INDEX IF NOT EXISTS idx_governance_status
ON governance(status);
"""


class Storage:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._artifacts_dir = root / "artifacts"
        self._db_path = root / "registry.db"
        self._conn: sqlite3.Connection | None = None

    def init(self) -> None:
        self._artifacts_dir.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)

    @property
    def _db(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Storage not initialized. Call init() first.")
        return self._conn

    def _manifest_path(self, namespace: str, name: str, version: str) -> Path:
        return self._artifacts_dir / namespace / name / version / "manifest.yaml"

    def save_manifest(self, manifest: Manifest) -> str:
        meta = manifest.metadata
        digest = compute_digest(manifest)

        # Check for duplicate version with different digest
        row = self._db.execute(
            "SELECT digest FROM artifacts WHERE namespace=? AND name=? AND version=?",
            (meta.namespace, meta.name, meta.version),
        ).fetchone()

        if row is not None:
            if row["digest"] == digest:
                return digest  # Idempotent
            raise DuplicateVersionError(
                f"{meta.namespace}/{meta.name}:{meta.version} already exists with a different digest"
            )

        # Work on a copy to avoid mutating the caller's object
        stored = manifest.model_copy(deep=True)
        stored.metadata.digest = digest
        path = self._manifest_path(meta.namespace, meta.name, meta.version)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(manifest_to_yaml(stored), encoding="utf-8")

        # Index in SQLite
        cursor = self._db.execute(
            "INSERT INTO artifacts (namespace, name, kind, version, digest, manifest_path) VALUES (?, ?, ?, ?, ?, ?)",
            (meta.namespace, meta.name, meta.kind.value, meta.version, digest, str(path)),
        )
        artifact_id = cursor.lastrowid

        for cap in manifest.provides:
            self._db.execute(
                "INSERT INTO capabilities (artifact_id, capability, contract, direction) VALUES (?, ?, ?, ?)",
                (artifact_id, cap.capability, cap.contract, "provides"),
            )
        for cap in manifest.requires:
            self._db.execute(
                "INSERT INTO capabilities (artifact_id, capability, contract, direction) VALUES (?, ?, ?, ?)",
                (artifact_id, cap.capability, cap.contract, "requires"),
            )

        import json
        self._db.execute(
            "INSERT INTO governance (artifact_id, visibility, status, owner, environment) VALUES (?, ?, ?, ?, ?)",
            (
                artifact_id,
                manifest.governance.visibility.value,
                manifest.governance.status.value,
                meta.owner,
                json.dumps(manifest.governance.environment),
            ),
        )

        self._db.commit()
        return digest

    def load_manifest(self, namespace: str, name: str, version: str) -> Manifest | None:
        path = self._manifest_path(namespace, name, version)
        if not path.exists():
            return None
        yaml_str = path.read_text(encoding="utf-8")
        manifest = manifest_from_yaml(yaml_str)

        # Load current governance status from DB (may have been soft-deleted)
        row = self._db.execute(
            "SELECT g.status FROM artifacts a JOIN governance g ON a.id = g.artifact_id "
            "WHERE a.namespace=? AND a.name=? AND a.version=?",
            (namespace, name, version),
        ).fetchone()
        if row is not None:
            manifest.governance.status = Status(row["status"])

        # Set digest
        manifest.metadata.digest = compute_digest(manifest)
        return manifest

    def find_providers(self, capability: str, contract: str) -> list[ArtifactRecord]:
        rows = self._db.execute(
            "SELECT a.*, g.status FROM artifacts a "
            "JOIN capabilities c ON a.id = c.artifact_id "
            "JOIN governance g ON a.id = g.artifact_id "
            "WHERE c.capability=? AND c.contract=? AND c.direction='provides' "
            "AND g.status != 'revoked'",
            (capability, contract),
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def search(self, query: str) -> list[ArtifactRecord]:
        pattern = f"%{query}%"
        rows = self._db.execute(
            "SELECT DISTINCT a.* FROM artifacts a "
            "LEFT JOIN capabilities c ON a.id = c.artifact_id "
            "LEFT JOIN governance g ON a.id = g.artifact_id "
            "WHERE (a.name LIKE ? OR a.namespace LIKE ? OR c.capability LIKE ?) "
            "AND (g.status IS NULL OR g.status != 'revoked')",
            (pattern, pattern, pattern),
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def list_artifacts(
        self, namespace: str | None = None, kind: Kind | None = None
    ) -> list[ArtifactRecord]:
        query = "SELECT a.* FROM artifacts a JOIN governance g ON a.id = g.artifact_id WHERE g.status != 'revoked'"
        params: list[str] = []
        if namespace is not None:
            query += " AND a.namespace=?"
            params.append(namespace)
        if kind is not None:
            query += " AND a.kind=?"
            params.append(kind.value)
        rows = self._db.execute(query, params).fetchall()
        return [self._row_to_record(r) for r in rows]

    def add_tag(self, namespace: str, name: str, version: str, tag: str) -> None:
        row = self._db.execute(
            "SELECT id FROM artifacts WHERE namespace=? AND name=? AND version=?",
            (namespace, name, version),
        ).fetchone()
        if row is None:
            raise ValueError(f"Artifact {namespace}/{name}:{version} not found")
        self._db.execute(
            "INSERT OR IGNORE INTO tags (artifact_id, tag) VALUES (?, ?)",
            (row["id"], tag),
        )
        self._db.commit()

    def delete_artifact(self, namespace: str, name: str, version: str) -> None:
        """Soft delete: mark as revoked in DB and update YAML."""
        row = self._db.execute(
            "SELECT id FROM artifacts WHERE namespace=? AND name=? AND version=?",
            (namespace, name, version),
        ).fetchone()
        if row is None:
            raise ValueError(f"Artifact {namespace}/{name}:{version} not found")
        self._db.execute(
            "UPDATE governance SET status='revoked' WHERE artifact_id=?",
            (row["id"],),
        )
        self._db.commit()

        # Update YAML file
        path = self._manifest_path(namespace, name, version)
        if path.exists():
            manifest = manifest_from_yaml(path.read_text(encoding="utf-8"))
            manifest.governance.status = Status.REVOKED
            path.write_text(manifest_to_yaml(manifest), encoding="utf-8")

    def rebuild_index(self) -> int:
        """Drop and rebuild SQLite index from YAML files."""
        self._db.executescript(
            "DELETE FROM capabilities; DELETE FROM tags; DELETE FROM governance; DELETE FROM artifacts;"
        )
        count = 0
        for manifest_path in self._artifacts_dir.rglob("manifest.yaml"):
            yaml_str = manifest_path.read_text(encoding="utf-8")
            manifest = manifest_from_yaml(yaml_str)
            self.save_manifest(manifest)
            count += 1
        return count

    def _row_to_record(self, row: sqlite3.Row) -> ArtifactRecord:
        artifact_id = row["id"]
        tag_rows = self._db.execute(
            "SELECT tag FROM tags WHERE artifact_id=?", (artifact_id,)
        ).fetchall()
        return ArtifactRecord(
            namespace=row["namespace"],
            name=row["name"],
            kind=Kind(row["kind"]),
            version=row["version"],
            digest=row["digest"],
            manifest_path=row["manifest_path"],
            created_at=row["created_at"],
            tags=[t["tag"] for t in tag_rows],
        )
