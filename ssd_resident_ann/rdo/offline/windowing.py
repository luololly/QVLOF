from __future__ import annotations

from collections import defaultdict

import numpy as np

from common.rdo_types import WorkloadWindow
from offline.partial_layout import choose_representative_query


def _compute_hot_vector_ids_from_queries(
    query_matrix: np.ndarray,
    base_vectors: np.ndarray,
    topk: int,
    hot_neighbor_k: int,
) -> list[int]:
    if topk <= 0:
        return []
    if hot_neighbor_k <= 0:
        raise ValueError("hot_neighbor_k must be positive.")

    queries = np.asarray(query_matrix, dtype=np.float32)
    base = np.asarray(base_vectors, dtype=np.float32)
    if queries.ndim != 2 or base.ndim != 2:
        raise ValueError("query_matrix and base_vectors must both be 2D.")
    if len(queries) == 0 or len(base) == 0:
        return []
    if queries.shape[1] != base.shape[1]:
        raise ValueError(
            "Query/base dimension mismatch: "
            f"{queries.shape[1]} vs {base.shape[1]}."
        )

    neighbor_k = min(hot_neighbor_k, len(base))
    diff = queries[:, None, :] - base[None, :, :]
    dists = np.sum(diff * diff, axis=2)
    nn_indices = np.argpartition(dists, kth=neighbor_k - 1, axis=1)[:, :neighbor_k]

    scores: dict[int, float] = defaultdict(float)
    for row_indices in nn_indices:
        ordered = sorted(row_indices.tolist(), key=lambda vid: float(dists[0, vid]) if len(queries) == 1 else vid)
        for rank, vid in enumerate(ordered):
            scores[int(vid)] += 1.0 / float(rank + 1)
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return [vid for vid, _ in ranked[:topk]]


def build_windows_from_queries(
    query_matrix: np.ndarray,
    window_size: int,
    dataset_group: str,
    workload_label_prefix: str = "window",
    hot_vector_topk: int = 32,
    base_vectors: np.ndarray | None = None,
    hot_neighbor_k: int = 8,
) -> list[WorkloadWindow]:
    if window_size <= 0:
        raise ValueError("window_size must be positive.")
    if hot_vector_topk <= 0:
        raise ValueError("hot_vector_topk must be positive.")

    queries = np.asarray(query_matrix, dtype=np.float32)
    if queries.ndim != 2:
        raise ValueError(f"Query matrix must be 2D, got shape {queries.shape}.")

    windows: list[WorkloadWindow] = []
    for start in range(0, len(queries), window_size):
        query_chunk = queries[start : start + window_size]
        if len(query_chunk) == 0:
            continue
        window_id = len(windows)
        hot_vector_ids = (
            _compute_hot_vector_ids_from_queries(
                query_matrix=query_chunk,
                base_vectors=base_vectors,
                topk=hot_vector_topk,
                hot_neighbor_k=hot_neighbor_k,
            )
            if base_vectors is not None
            else []
        )
        windows.append(
            WorkloadWindow(
                window_id=window_id,
                start_query_id=start,
                end_query_id=start + len(query_chunk) - 1,
                workload_label=f"{workload_label_prefix}{window_id}",
                dataset_group=dataset_group,
                query_ids=list(range(start, start + len(query_chunk))),
                query_matrix=query_chunk.copy(),
                hot_vector_ids=hot_vector_ids,
            )
        )
    return windows


def sample_query_windows(
    windows: list[WorkloadWindow],
    sample_size: int,
    random_state: int = 0,
) -> np.ndarray:
    if sample_size <= 0:
        raise ValueError("sample_size must be positive.")

    all_queries = []
    for window in windows:
        queries = np.asarray(window.query_matrix, dtype=np.float32)
        if queries.ndim != 2:
            raise ValueError(f"query_matrix must be 2D, got shape {queries.shape}.")
        if len(queries) == 0:
            continue
        representative = choose_representative_query(window)
        all_queries.append(representative)
        all_queries.extend(list(queries))

    if not all_queries:
        raise ValueError("windows do not contain usable queries.")

    stacked = np.asarray(all_queries, dtype=np.float32)
    if len(stacked) <= sample_size:
        return stacked

    rng = np.random.default_rng(random_state)
    indices = np.sort(rng.choice(len(stacked), sample_size, replace=False))
    return stacked[indices]


def sample_query_windows_rtbs(
    windows: list[WorkloadWindow],
    sample_size: int,
    random_state: int = 0,
    time_bias: float = 2.0,
) -> np.ndarray:
    if sample_size <= 0:
        raise ValueError("sample_size must be positive.")
    if time_bias <= 0.0:
        raise ValueError("time_bias must be positive.")

    weighted_queries: list[tuple[np.ndarray, float]] = []
    total_windows = max(1, len(windows))
    for idx, window in enumerate(windows):
        queries = np.asarray(window.query_matrix, dtype=np.float32)
        if queries.ndim != 2:
            raise ValueError(f"query_matrix must be 2D, got shape {queries.shape}.")
        if len(queries) == 0:
            continue
        representative = choose_representative_query(window)
        recency = float(idx + 1) / float(total_windows)
        weight = float(np.exp(time_bias * recency))
        weighted_queries.append((representative, weight))
        for query in queries:
            weighted_queries.append((np.asarray(query, dtype=np.float32), weight))

    if not weighted_queries:
        raise ValueError("windows do not contain usable queries.")

    matrix = np.asarray([row for row, _ in weighted_queries], dtype=np.float32)
    if len(matrix) <= sample_size:
        return matrix

    weights = np.asarray([weight for _, weight in weighted_queries], dtype=np.float64)
    weights = weights / weights.sum()
    rng = np.random.default_rng(random_state)
    indices = np.sort(rng.choice(len(matrix), sample_size, replace=False, p=weights))
    return matrix[indices]
