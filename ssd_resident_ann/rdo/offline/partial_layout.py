from __future__ import annotations

import math

import numpy as np

from common.rdo_types import PartialLayout, WorkloadWindow


def choose_representative_query(window: WorkloadWindow) -> np.ndarray:
    queries = np.asarray(window.query_matrix, dtype=np.float32)
    if queries.ndim != 2:
        raise ValueError(f"query_matrix must be 2D, got shape {queries.shape}.")
    if len(queries) == 0:
        raise ValueError("query_matrix must not be empty.")
    if len(queries) == 1:
        return queries[0].copy()

    bandwidth = max(1e-6, float(np.std(queries)))
    diff = queries[:, None, :] - queries[None, :, :]
    sq_dist = np.sum(diff * diff, axis=2)
    scores = np.exp(-sq_dist / (2.0 * bandwidth * bandwidth)).sum(axis=1)
    return queries[int(np.argmax(scores))].copy()


def _distance_radius(distances: np.ndarray) -> float:
    if len(distances) <= 1:
        return 1.0
    sorted_distances = np.sort(distances)
    deltas = np.diff(sorted_distances)
    positive = deltas[deltas > 0]
    if len(positive) == 0:
        return max(1e-6, float(sorted_distances[-1]))
    return max(1e-6, float(np.median(positive)))


def build_partial_layout(
    window: WorkloadWindow,
    base_vectors: np.ndarray,
    page_capacity: int,
    beta: float = 0.5,
) -> PartialLayout:
    if page_capacity <= 0:
        raise ValueError("page_capacity must be positive.")
    if not (0.0 < beta <= 1.0):
        raise ValueError("beta must be in (0, 1].")

    base = np.asarray(base_vectors, dtype=np.float32)
    if base.ndim != 2:
        raise ValueError(f"base_vectors must be 2D, got shape {base.shape}.")

    representative = choose_representative_query(window)
    distances = np.linalg.norm(base - representative[None, :], axis=1)
    ranked = np.argsort(distances).tolist()

    total_blocks = int(math.ceil(len(base) / page_capacity))
    partial_blocks = max(1, int(math.ceil(total_blocks * beta)))
    covered_count = min(len(base), partial_blocks * page_capacity)
    covered_vector_ids = ranked[:covered_count]

    blocks: list[list[int]] = []
    block_metas: list[dict[str, float | int]] = []
    for start in range(0, covered_count, page_capacity):
        block = covered_vector_ids[start : start + page_capacity]
        block_distances = distances[block]
        blocks.append(block)
        block_metas.append(
            {
                "distance_min": float(np.min(block_distances)),
                "distance_max": float(np.max(block_distances)),
                "size": len(block),
            }
        )

    return PartialLayout(
        window_id=window.window_id,
        layout_label="partial",
        representative_query=representative,
        covered_vector_ids=covered_vector_ids,
        blocks=blocks,
        block_metas=block_metas,
        total_block_count=len(blocks),
        beta=beta,
        distance_values=[float(distances[vid]) for vid in covered_vector_ids],
    )


def block_overlap_query_cost(query: np.ndarray, partial_layout: PartialLayout) -> float:
    q = np.asarray(query, dtype=np.float32)
    if q.shape != partial_layout.representative_query.shape:
        raise ValueError(
            "query dimension does not match representative_query dimension: "
            f"{q.shape} vs {partial_layout.representative_query.shape}."
        )

    representative_distance = float(np.linalg.norm(q - partial_layout.representative_query))
    covered_distances = np.asarray(
        [float(meta["distance_min"]) for meta in partial_layout.block_metas]
        + [float(meta["distance_max"]) for meta in partial_layout.block_metas],
        dtype=np.float32,
    )
    radius = _distance_radius(covered_distances) * 0.5

    overlap = 0
    lower = representative_distance - radius
    upper = representative_distance + radius
    for meta in partial_layout.block_metas:
        midpoint = 0.5 * (float(meta["distance_min"]) + float(meta["distance_max"]))
        if lower <= midpoint <= upper:
            overlap += 1

    if overlap == 0:
        return 1.0
    return float(overlap) / float(max(1, partial_layout.total_block_count))
