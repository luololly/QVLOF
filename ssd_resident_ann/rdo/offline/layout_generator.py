from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from common.rdo_types import LayoutCandidate, LayoutFamily, QsoWindowArtifact, WorkloadWindow
from offline.candidate_pool import CandidateLayoutPool
from offline.partial_layout import build_partial_layout
from offline.query_cost import estimate_layout_query_cost
from offline.qso_materializer import materialize_qso_window_artifacts
from offline.windowing import sample_query_windows_rtbs


def _query_cost_metadata(
    window: WorkloadWindow,
    layout_label: str,
    extra_metadata: dict[str, Any],
) -> tuple[float, dict[str, Any]]:
    estimated_query_cost, query_metadata = estimate_layout_query_cost(
        window,
        layout_label,
        return_metadata=True,
    )
    metadata = dict(extra_metadata)
    metadata.update(query_metadata)
    return estimated_query_cost, metadata


def generate_layout_families(windows: list[WorkloadWindow]) -> list[LayoutFamily]:
    families: list[LayoutFamily] = []
    previous_hot: set[int] = set()

    for window in windows:
        current_hot = set(window.hot_vector_ids)
        overlap = len(previous_hot.intersection(current_hot))
        base_query_cost, base_metadata = _query_cost_metadata(
            window,
            "base",
            {"hot_overlap": overlap, "hot_count": len(current_hot)},
        )
        hot_query_cost, hot_metadata = _query_cost_metadata(
            window,
            "hot",
            {"hot_overlap": overlap, "hot_count": len(current_hot)},
        )
        balanced_query_cost, balanced_metadata = _query_cost_metadata(
            window,
            "balanced",
            {"hot_overlap": overlap, "hot_count": len(current_hot)},
        )

        base = LayoutCandidate(
            candidate_id=f"window{window.window_id}_base",
            window_id=window.window_id,
            layout_label="base",
            artifact_hint=f"layout_window_{window.window_id}/base",
            estimated_query_cost=base_query_cost,
            estimated_movement_cost=0.0,
            metadata=base_metadata,
        )
        hot = LayoutCandidate(
            candidate_id=f"window{window.window_id}_hot",
            window_id=window.window_id,
            layout_label="hot",
            artifact_hint=f"layout_window_{window.window_id}/hot",
            estimated_query_cost=hot_query_cost,
            estimated_movement_cost=max(1.0, float(len(current_hot) - overlap)),
            metadata=hot_metadata,
        )
        balanced = LayoutCandidate(
            candidate_id=f"window{window.window_id}_balanced",
            window_id=window.window_id,
            layout_label="balanced",
            artifact_hint=f"layout_window_{window.window_id}/balanced",
            estimated_query_cost=balanced_query_cost,
            estimated_movement_cost=max(0.5, float(len(current_hot) - overlap) * 0.5),
            metadata=balanced_metadata,
        )
        families.append(LayoutFamily(window_id=window.window_id, candidates=[base, hot, balanced]))
        previous_hot = current_hot

    return families


def generate_partial_layout_families(
    windows: list[WorkloadWindow],
    base_vectors: np.ndarray,
    page_capacity: int,
    beta: float = 0.5,
    epsilon: float = 0.08,
    sample_size: int = 32,
    random_state: int = 0,
) -> list[LayoutFamily]:
    query_samples = sample_query_windows_rtbs(
        windows=windows,
        sample_size=sample_size,
        random_state=random_state,
        time_bias=2.0,
    )
    pool = CandidateLayoutPool(
        epsilon=epsilon,
        sample_size=sample_size,
        random_state=random_state,
    )
    pool.reset_query_samples(query_samples)

    families: list[LayoutFamily] = []
    pooled_partials: list[tuple[str, PartialLayout]] = []
    for window in windows:
        family_candidates: list[LayoutCandidate] = []

        qso_full_cost, qso_full_metadata = estimate_layout_query_cost(
            window,
            "qso_full",
            return_metadata=True,
        )
        family_candidates.append(
            LayoutCandidate(
                candidate_id=f"window{window.window_id}_qso_full",
                window_id=window.window_id,
                layout_label="qso_full",
                artifact_hint="qso_full_layout",
                estimated_query_cost=qso_full_cost,
                estimated_movement_cost=0.0,
                metadata={
                    "layout_state_id": "qso_full",
                    **qso_full_metadata,
                },
            )
        )

        partial_layout = build_partial_layout(
            window=window,
            base_vectors=base_vectors,
            page_capacity=page_capacity,
            beta=beta,
        )
        accepted = pool.try_add(partial_layout)
        layout_state_id = f"partial_window{window.window_id}"
        if accepted:
            pooled_partials.append((layout_state_id, partial_layout))

        for state_id, pooled_layout in pooled_partials:
            estimated_query_cost, query_cost_metadata = estimate_layout_query_cost(
                window,
                "partial",
                partial_layout=pooled_layout,
                return_metadata=True,
            )
            family_candidates.append(
                LayoutCandidate(
                    candidate_id=f"window{window.window_id}_{state_id}",
                    window_id=window.window_id,
                    layout_label="partial",
                    artifact_hint=f"partial_window_{pooled_layout.window_id}",
                    estimated_query_cost=estimated_query_cost,
                    estimated_movement_cost=float(len(pooled_layout.covered_vector_ids)),
                    metadata={
                        "layout_state_id": state_id,
                        "pool_accepted": bool(accepted) if state_id == layout_state_id else False,
                        "covered_vector_ids": list(pooled_layout.covered_vector_ids),
                        "representative_query": pooled_layout.representative_query.tolist(),
                        "block_metas": list(pooled_layout.block_metas),
                        "distance_values": list(pooled_layout.distance_values),
                        "partial_layout_beta": pooled_layout.beta,
                        "pool_size_after_insert": len(pool.layouts),
                        "source_window_id": pooled_layout.window_id,
                        **query_cost_metadata,
                    },
                )
            )
        families.append(LayoutFamily(window_id=window.window_id, candidates=family_candidates))
    return families


def apply_materialized_artifact_hints(
    families: list[LayoutFamily],
    artifacts: list[QsoWindowArtifact],
) -> list[LayoutFamily]:
    artifact_by_window = {artifact.window_id: artifact for artifact in artifacts}
    for family in families:
        artifact = artifact_by_window.get(family.window_id)
        if artifact is None:
            continue
        for candidate in family.candidates:
            candidate.artifact_hint = artifact.artifact_prefix
            candidate.metadata["materialized_system"] = artifact.system
            candidate.metadata["materialized_files"] = list(artifact.files)
    return families


def generate_qso_layout_families(
    windows: list[WorkloadWindow],
    system: str,
    num_vectors: int,
    page_capacity: int,
    output_root: str | Path,
    candidate_specs: list[dict],
    vector_features_path: str | None = None,
    posting_membership: str | None = None,
) -> list[LayoutFamily]:
    root = Path(output_root)
    per_window: dict[int, list[LayoutCandidate]] = {window.window_id: [] for window in windows}

    for spec in candidate_specs:
        label = spec["layout_label"]
        lgpf_k = int(spec.get("lgpf_k", 3))
        transform_t = float(spec.get("transform_t", 0.3))
        candidate_root = root / label
        artifacts = materialize_qso_window_artifacts(
            windows=windows,
            system=system,
            num_vectors=num_vectors,
            page_capacity=page_capacity,
            output_root=candidate_root,
            vector_features_path=vector_features_path,
            lgpf_k=lgpf_k,
            transform_t=transform_t,
            posting_membership=posting_membership,
        )
        artifact_by_window = {artifact.window_id: artifact for artifact in artifacts}
        for window in windows:
            artifact = artifact_by_window[window.window_id]
            hot_count = max(1, len(window.hot_vector_ids))
            estimated_query_cost, query_cost_metadata = estimate_layout_query_cost(
                window,
                label,
                return_metadata=True,
            )
            estimated_movement_cost = float(hot_count * max(transform_t, 0.25))
            per_window[window.window_id].append(
                LayoutCandidate(
                    candidate_id=f"window{window.window_id}_{label}",
                    window_id=window.window_id,
                    layout_label=label,
                    artifact_hint=artifact.artifact_prefix,
                    estimated_query_cost=estimated_query_cost,
                    estimated_movement_cost=estimated_movement_cost,
                    metadata={
                        "materialized_system": artifact.system,
                        "materialized_files": list(artifact.files),
                        "qso_lgpf_k": lgpf_k,
                        "qso_transform_t": transform_t,
                        **query_cost_metadata,
                    },
                )
            )

    return [
        LayoutFamily(window_id=window.window_id, candidates=per_window[window.window_id])
        for window in windows
    ]
