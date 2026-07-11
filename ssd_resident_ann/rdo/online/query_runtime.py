from __future__ import annotations

import heapq

import numpy as np

from common.rdo_types import PartialLayout, QuerySearchResult


def _as_float32_matrix(arr: np.ndarray) -> np.ndarray:
    out = np.asarray(arr, dtype=np.float32)
    if out.ndim != 2:
        raise ValueError(f"expected 2D matrix, got shape {out.shape}.")
    return out


def _as_float32_vector(arr: np.ndarray) -> np.ndarray:
    out = np.asarray(arr, dtype=np.float32)
    if out.ndim != 1:
        raise ValueError(f"expected 1D vector, got shape {out.shape}.")
    return out


def _build_partial_distances(base_vectors: np.ndarray, partial_layout: PartialLayout) -> tuple[np.ndarray, np.ndarray]:
    base = _as_float32_matrix(base_vectors)
    rep = _as_float32_vector(partial_layout.representative_query)
    covered_ids = np.asarray(partial_layout.covered_vector_ids, dtype=np.int32)
    if len(covered_ids) == 0:
        raise ValueError("partial_layout.covered_vector_ids must not be empty.")
    covered = base[covered_ids]
    dis_values = np.linalg.norm(covered - rep[None, :], axis=1)
    order = np.argsort(dis_values, kind="stable")
    return covered_ids[order], dis_values[order]


def _full_knn(query: np.ndarray, base_vectors: np.ndarray, k: int) -> list[int]:
    q = _as_float32_vector(query)
    base = _as_float32_matrix(base_vectors)
    distances = np.linalg.norm(base - q[None, :], axis=1)
    order = np.argsort(distances, kind="stable")[:k]
    return [int(idx) for idx in order.tolist()]


def _qso_full_layout_knn(
    query: np.ndarray,
    base_vectors: np.ndarray,
    k: int,
    pages: list[list[int]] | None,
) -> tuple[list[int], list[int]]:
    if not pages:
        return _full_knn(query, base_vectors, k), []

    q = _as_float32_vector(query)
    base = _as_float32_matrix(base_vectors)
    candidates: list[tuple[float, int, int]] = []
    page_ids: list[int] = []
    for page_id, page in enumerate(pages):
        page_ids.append(page_id)
        for vid in page:
            idx = int(vid)
            candidates.append((float(np.linalg.norm(base[idx] - q)), page_id, idx))
    candidates.sort(key=lambda item: (item[0], item[1], item[2]))
    return [int(vid) for _, _, vid in candidates[:k]], page_ids


def _candidate_insert(
    heap: list[tuple[float, int]],
    vector_id: int,
    distance: float,
    limit: int,
) -> None:
    item = (-float(distance), int(vector_id))
    if len(heap) < limit:
        heapq.heappush(heap, item)
        return
    if distance < -heap[0][0]:
        heapq.heapreplace(heap, item)


def _sorted_neighbors_from_heap(heap: list[tuple[float, int]]) -> list[int]:
    rows = [(-dist, vid) for dist, vid in heap]
    rows.sort(key=lambda item: (item[0], item[1]))
    return [vid for _, vid in rows]


def _recall_at_k(found: list[int], truth: list[int], k: int) -> float:
    top_found = set(found[:k])
    top_truth = set(truth[:k])
    if not top_truth:
        return 1.0
    return float(len(top_found.intersection(top_truth))) / float(len(top_truth))


def _search_partial_candidate_ids(
    query: np.ndarray,
    base_vectors: np.ndarray,
    partial_layout: PartialLayout,
    k: int,
    a: float,
) -> tuple[list[int], bool]:
    if k <= 0:
        raise ValueError("k must be positive.")
    if a <= 0:
        raise ValueError("a must be positive.")

    q = _as_float32_vector(query)
    base = _as_float32_matrix(base_vectors)
    sorted_ids, sorted_dis = _build_partial_distances(base, partial_layout)
    query_dis = float(np.linalg.norm(q - partial_layout.representative_query))
    center_idx = int(np.searchsorted(sorted_dis, query_dis, side="left"))
    if center_idx >= len(sorted_ids):
        center_idx = len(sorted_ids) - 1

    limit = max(k, int(np.ceil(a * k)))
    heap: list[tuple[float, int]] = []

    def scan_from(pointer: int, step: int) -> bool:
        idx = pointer
        while 0 <= idx < len(sorted_ids):
            vid = int(sorted_ids[idx])
            vec_dist = float(np.linalg.norm(base[vid] - q))
            current_max = float("inf") if len(heap) < limit else -heap[0][0]
            if len(heap) < limit or vec_dist < current_max:
                _candidate_insert(heap, vid, vec_dist, limit)
                current_max = float("inf") if len(heap) < limit else -heap[0][0]
            dis_gap = abs(float(sorted_dis[idx]) - query_dis)
            if len(heap) >= limit and dis_gap >= current_max:
                break
            idx += step
        return idx < 0 or idx >= len(sorted_ids)

    seed_vid = int(sorted_ids[center_idx])
    seed_dist = float(np.linalg.norm(base[seed_vid] - q))
    _candidate_insert(heap, seed_vid, seed_dist, limit)

    left_boundary = scan_from(center_idx - 1, -1)
    right_boundary = scan_from(center_idx + 1, 1)
    return _sorted_neighbors_from_heap(heap), left_boundary or right_boundary


def search_with_fallback(
    query: np.ndarray,
    base_vectors: np.ndarray,
    partial_layout: PartialLayout,
    k: int,
    a: float,
    *,
    query_id: int = 0,
    candidate_id: str = "partial",
    window_id: int | None = None,
    qso_full_layout_pages: list[list[int]] | None = None,
) -> QuerySearchResult:
    partial_neighbor_ids, boundary_touched = _search_partial_candidate_ids(
        query=query,
        base_vectors=base_vectors,
        partial_layout=partial_layout,
        k=k,
        a=a,
    )
    fallback_used = boundary_touched or len(partial_neighbor_ids) < k
    full_neighbor_ids, fallback_page_ids = _qso_full_layout_knn(
        query=query,
        base_vectors=base_vectors,
        k=k,
        pages=qso_full_layout_pages,
    )
    neighbor_ids = full_neighbor_ids if fallback_used else partial_neighbor_ids[:k]
    if not fallback_used:
        search_mode = "partial-only"
    elif qso_full_layout_pages:
        search_mode = "partial+qso-full-layout"
    else:
        search_mode = "partial+fallback"
    return QuerySearchResult(
        query_id=int(query_id),
        window_id=int(partial_layout.window_id if window_id is None else window_id),
        candidate_id=candidate_id,
        layout_label=partial_layout.layout_label,
        neighbor_ids=[int(v) for v in neighbor_ids],
        partial_neighbor_ids=[int(v) for v in partial_neighbor_ids[:k]],
        full_neighbor_ids=[int(v) for v in full_neighbor_ids],
        fallback_used=bool(fallback_used),
        boundary_touched=bool(boundary_touched),
        candidate_count=len(partial_neighbor_ids),
        recall_at_k=_recall_at_k(neighbor_ids, full_neighbor_ids, k),
        search_mode=search_mode,
        fallback_page_ids=[int(v) for v in fallback_page_ids] if fallback_used else [],
        full_layout_accessed_pages=len(fallback_page_ids) if fallback_used else 0,
    )
