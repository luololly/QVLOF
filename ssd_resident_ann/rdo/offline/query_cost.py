from __future__ import annotations

from typing import Any

import numpy as np
from scipy.interpolate import PchipInterpolator

from common.rdo_types import PartialLayout, WorkloadWindow


LAYOUT_PROXY_FACTORS = {
    "hot": 0.72,
    "qso": 0.78,
    "qso_all": 0.76,
    "qso_focus": 0.68,
    "balanced": 0.88,
    "base": 1.0,
}


def _query_matrix(window: WorkloadWindow) -> np.ndarray:
    queries = np.asarray(window.query_matrix, dtype=np.float32)
    if queries.ndim != 2:
        raise ValueError(f"query_matrix must be 2D, got shape {queries.shape}.")
    if len(window.query_ids) != len(queries):
        raise ValueError(
            "query_ids and query_matrix must describe the same number of queries: "
            f"{len(window.query_ids)} vs {len(queries)}."
        )
    return queries


def _query_dispersion(query_matrix: np.ndarray) -> float:
    queries = np.asarray(query_matrix, dtype=np.float32)
    if len(queries) == 0:
        return 0.0
    centroid = queries.mean(axis=0, keepdims=True)
    distances = np.linalg.norm(queries - centroid, axis=1)
    return float(distances.mean())


def _layout_factor(layout_label: str) -> float:
    if layout_label in LAYOUT_PROXY_FACTORS:
        return LAYOUT_PROXY_FACTORS[layout_label]
    if layout_label.startswith("qso"):
        return LAYOUT_PROXY_FACTORS["qso"]
    return LAYOUT_PROXY_FACTORS["base"]


def _partial_layout_dis_values(partial_layout: PartialLayout) -> np.ndarray:
    values = np.asarray(partial_layout.distance_values, dtype=np.float32)
    if len(values) > 0:
        return values

    approximated: list[float] = []
    for meta in partial_layout.block_metas:
        size = int(meta.get("size", 1))
        lo = float(meta["distance_min"])
        hi = float(meta["distance_max"])
        if size <= 1:
            approximated.append(0.5 * (lo + hi))
        else:
            approximated.extend(np.linspace(lo, hi, size).tolist())
    if not approximated:
        raise ValueError("partial_layout requires distance_values or block_metas.")
    return np.asarray(approximated, dtype=np.float32)


def _build_histogram_cdf(dis_values: np.ndarray) -> tuple[np.ndarray, np.ndarray, int]:
    values = np.sort(np.asarray(dis_values, dtype=np.float32))
    if len(values) == 0:
        raise ValueError("dis_values must not be empty.")
    if len(values) == 1:
        x = np.asarray([float(values[0]), float(values[0]) + 1e-6], dtype=np.float32)
        y = np.asarray([1.0, 1.0], dtype=np.float32)
        return x, y, 1

    bin_count = max(1, min(32, int(np.ceil(np.sqrt(len(values))))))
    hist, edges = np.histogram(values, bins=bin_count)
    cumulative = np.cumsum(hist, dtype=np.float64) / float(len(values))
    x = edges[1:].astype(np.float32)
    y = cumulative.astype(np.float32)
    if float(x[0]) > float(values[0]):
        x = np.concatenate(([float(values[0])], x))
        y = np.concatenate(([0.0], y))
    if float(x[-1]) < float(values[-1]):
        x = np.concatenate((x, [float(values[-1])]))
        y = np.concatenate((y, [1.0]))
    return x, y, bin_count


def _estimate_query_radius(
    query_dis: float,
    dis_values: np.ndarray,
    k: int,
    extra_candidates: int,
) -> tuple[float, float, int]:
    if k <= 0:
        raise ValueError("k must be positive.")
    if extra_candidates < 0:
        raise ValueError("extra_candidates must be non-negative.")

    target_count = min(len(dis_values), max(1, int(k) + int(extra_candidates)))
    target_probability = float(target_count) / float(max(1, len(dis_values)))
    x, y, bin_count = _build_histogram_cdf(dis_values)
    cdf = PchipInterpolator(x, y, extrapolate=True)

    max_radius = float(np.max(np.abs(dis_values - float(query_dis))))
    lo = 0.0
    hi = max(1e-6, max_radius)
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        lower = float(query_dis) - mid
        upper = float(query_dis) + mid
        covered = float(cdf(upper) - cdf(lower))
        covered = min(1.0, max(0.0, covered))
        if covered >= target_probability:
            hi = mid
        else:
            lo = mid
    return max(hi, 1e-6), target_probability, int(bin_count)


def _algorithm4_query_cost(
    query: np.ndarray,
    partial_layout: PartialLayout,
    k: int,
    extra_candidates: int,
) -> tuple[float, dict[str, Any]]:
    q = np.asarray(query, dtype=np.float32)
    if q.shape != partial_layout.representative_query.shape:
        raise ValueError(
            "query dimension does not match representative_query dimension: "
            f"{q.shape} vs {partial_layout.representative_query.shape}."
        )

    dis_values = _partial_layout_dis_values(partial_layout)
    query_dis = float(np.linalg.norm(q - partial_layout.representative_query))
    radius, target_probability, histogram_bin_count = _estimate_query_radius(
        query_dis=query_dis,
        dis_values=dis_values,
        k=k,
        extra_candidates=extra_candidates,
    )

    lower = query_dis - radius
    upper = query_dis + radius
    accessed = 0
    accessed_block_ids: list[int] = []
    for block_id, meta in enumerate(partial_layout.block_metas):
        block_min = float(meta["distance_min"])
        block_max = float(meta["distance_max"])
        if block_max >= lower and block_min <= upper:
            accessed += 1
            accessed_block_ids.append(block_id)

    if accessed == 0:
        cost = 1.0
    else:
        cost = float(accessed) / float(max(1, partial_layout.total_block_count))
    return cost, {
        "query_distance": query_dis,
        "query_radius": radius,
        "distribution_target_probability": target_probability,
        "accessed_blocks": accessed,
        "accessed_block_ids": accessed_block_ids,
        "distribution_sample_count": int(len(dis_values)),
        "distribution_method": "spline-dequantization-cdf",
        "cdf_method": "pchip",
        "histogram_bin_count": histogram_bin_count,
    }


def estimate_layout_query_cost(
    window: WorkloadWindow,
    layout_label: str,
    partial_layout: PartialLayout | None = None,
    *,
    k: int = 10,
    extra_candidates: int = 0,
    return_metadata: bool = False,
) -> float | tuple[float, dict[str, Any]]:
    queries = _query_matrix(window)
    query_count = max(1, len(queries))

    if partial_layout is not None:
        per_query = [
            _algorithm4_query_cost(
                query=query,
                partial_layout=partial_layout,
                k=k,
                extra_candidates=extra_candidates,
            )
            for query in queries
        ]
        per_query_costs = [item[0] for item in per_query]
        cost = float(np.mean(per_query_costs))
        first_query_metadata = per_query[0][1] if per_query else {}
        metadata = {
            "query_cost_model": "algorithm4-distribution",
            "layout_proxy": layout_label,
            "query_count": query_count,
            "partial_layout_blocks": partial_layout.total_block_count,
            "partial_layout_beta": partial_layout.beta,
            "representative_query": partial_layout.representative_query.tolist(),
            "algorithm4_k": int(k),
            "algorithm4_extra_candidates": int(extra_candidates),
            **first_query_metadata,
        }
    else:
        dispersion = _query_dispersion(queries)
        factor = _layout_factor(layout_label)
        base_cost = float(query_count) * (1.0 + dispersion)
        cost = max(1.0, base_cost * factor)
        metadata = {
            "query_cost_model": "layout-level-proxy",
            "layout_proxy": layout_label,
            "query_count": query_count,
            "query_dispersion": dispersion,
            "layout_proxy_factor": factor,
        }
    if return_metadata:
        return cost, metadata
    return cost
