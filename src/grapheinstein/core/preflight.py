"""Large-repo preflight: scan-cost estimate and gate enforcement."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import networkx as nx

from grapheinstein.core.parsers.registry import EXTENSION_MAP
from grapheinstein.core.references import (
    is_reference_scan_eligible,
    unique_basename_targets,
)
from grapheinstein.utils import LargeRepoError

CODE_SUFFIXES = frozenset(EXTENSION_MAP.keys())


@dataclass(frozen=True)
class ScanCostEstimate:
    eligible_scan_files: int
    unique_basenames: int
    estimated_scan_ops: int
    non_code_share: float
    total_bytes: int
    file_count: int
    tripped_gates: tuple[str, ...] = field(default_factory=tuple)


def _file_size_bytes(attrs: dict) -> int:
    meta = attrs.get("metadata") or {}
    size = meta.get("size_bytes")
    if isinstance(size, int) and size >= 0:
        return size
    return 0


def _is_code_file(node_id: str) -> bool:
    return Path(node_id).suffix.lower() in CODE_SUFFIXES


def compute_scan_cost_estimate(
    graph: nx.DiGraph,
    *,
    code_only: bool = False,
    project_root: Path | None = None,
) -> ScanCostEstimate:
    """Compute inventory scan-cost metrics used by large-repo gates."""
    root = project_root
    total_bytes = 0
    file_count = 0
    non_code_bytes = 0
    eligible = 0

    for node_id, attrs in graph.nodes(data=True):
        if attrs.get("type") != "file" or node_id == ".":
            continue
        meta = dict(attrs.get("metadata") or {})
        if "size_bytes" not in meta and root is not None and not meta.get("symlink"):
            try:
                meta["size_bytes"] = (root / node_id).stat().st_size
            except OSError:
                pass
        size = int(meta.get("size_bytes") or 0)
        file_count += 1
        total_bytes += size
        if not _is_code_file(node_id):
            non_code_bytes += size
        # Build a temporary attrs view for eligibility
        probe = {"type": "file", "metadata": meta}
        if is_reference_scan_eligible(node_id, probe, code_only=code_only):
            eligible += 1

    unique_basenames = len(unique_basename_targets(graph))
    estimated_ops = eligible * unique_basenames
    non_code_share = (non_code_bytes / total_bytes) if total_bytes > 0 else 0.0
    return ScanCostEstimate(
        eligible_scan_files=eligible,
        unique_basenames=unique_basenames,
        estimated_scan_ops=estimated_ops,
        non_code_share=non_code_share,
        total_bytes=total_bytes,
        file_count=file_count,
    )


def enforce_large_repo_gates(
    estimate: ScanCostEstimate,
    *,
    code_only: bool,
    max_total_bytes: int,
    max_file_count: int,
    max_reference_scan_ops: int,
    max_non_code_share: float,
    large_repo_policy: str,
) -> ScanCostEstimate:
    """
    Raise LargeRepoError when hard or advisory gates trip.

    ``large_repo_policy=allow`` bypasses scan-ops and non-code-share only.
    Hard caps (bytes / file count) always apply.
    """
    tripped: list[str] = []
    if estimate.total_bytes > max_total_bytes:
        tripped.append(
            f"max_total_bytes ({estimate.total_bytes} > {max_total_bytes})"
        )
    if estimate.file_count > max_file_count:
        tripped.append(
            f"max_file_count ({estimate.file_count} > {max_file_count})"
        )

    advisory: list[str] = []
    if estimate.estimated_scan_ops > max_reference_scan_ops:
        advisory.append(
            f"max_reference_scan_ops "
            f"({estimate.estimated_scan_ops} > {max_reference_scan_ops})"
        )
    if code_only and estimate.non_code_share > max_non_code_share:
        advisory.append(
            f"max_non_code_share "
            f"({estimate.non_code_share:.3f} > {max_non_code_share})"
        )

    if large_repo_policy != "allow":
        tripped.extend(advisory)
    elif advisory:
        # Still record advisory trips for diagnostics even when allowed
        pass

    if not tripped:
        return ScanCostEstimate(
            eligible_scan_files=estimate.eligible_scan_files,
            unique_basenames=estimate.unique_basenames,
            estimated_scan_ops=estimate.estimated_scan_ops,
            non_code_share=estimate.non_code_share,
            total_bytes=estimate.total_bytes,
            file_count=estimate.file_count,
            tripped_gates=tuple(advisory) if large_repo_policy == "allow" else (),
        )

    remedies = (
        "Narrow the project path, use --code-only (excludes docs/ and discovery_cache/), "
        "add ignored_patterns, or pass --allow-large-repo to bypass advisory scan-cost "
        "gates (hard byte/file caps still apply)."
    )
    raise LargeRepoError(
        "Large-repo preflight rejected this index: "
        + "; ".join(tripped)
        + f". {remedies}",
        tripped_gates=tuple(tripped),
    )
