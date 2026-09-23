from __future__ import annotations

from typing import Protocol

from capmesh.models.manifest import Manifest
from capmesh.models.resolution import Binding


class BindingAdapter(Protocol):
    def supports(self, manifest: Manifest) -> bool: ...
    def bind(self, manifest: Manifest, trace_id: str) -> Binding: ...
