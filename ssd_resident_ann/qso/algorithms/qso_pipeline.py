from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans, MiniBatchKMeans

from .cov import covariance_eigen_decomposition, has_torch, transform_matrix, torch, torch_device
from .equal_size_kmeans import EqualSizeKMeans
from .lgpf import newdata as lgpf_newdata
from .lgpf_q2d import newdata as lgpf_q2d_newdata


def sort_within_cluster(data: np.ndarray, idx: np.ndarray, center: np.ndarray):
    d = np.linalg.norm(data[idx] - center, axis=1)
    return idx[np.argsort(d)]


@dataclass
class QsoAlgorithmConfig:
    lgpf_k: int = 3
    transform_t: float = 0.3
    cluster_k: int = 64
    block_size: int = 0
    assignment_s_top: int = 5
    chunk_size: int = 4096
    use_query_transform: bool = True
    use_cov_transform: bool = True
    use_equal_size_clusters: bool = False


def _normalize_rows(data: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(data, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return data / norms


def _mean_query_direction(query: np.ndarray) -> np.ndarray:
    q = np.asarray(query, dtype=np.float32)
    if q.ndim != 2 or len(q) == 0:
        raise ValueError("query must be a non-empty 2D matrix.")
    q_mean = q.mean(axis=0, keepdims=True)
    return _normalize_rows(q_mean)


def _build_equal_size_labels(data: np.ndarray, cluster_k: int):
    n = len(data)
    if cluster_k <= 1 or n <= 1:
        return np.zeros(n, dtype=np.int32), data.mean(axis=0, keepdims=True)

    cluster_k = min(cluster_k, n)
    base_size = max(1, n // cluster_k)
    remainder = n - base_size * cluster_k
    target_sizes = np.full(cluster_k, base_size, dtype=np.int32)
    if remainder > 0:
        target_sizes[:remainder] += 1

    eq = EqualSizeKMeans(
        n_clusters=cluster_k,
        sizes=target_sizes,
        n_init=10,
        random_state=42,
        batch_size=min(5000, n),
    )
    labels = eq.fit_predict(data)
    return labels, eq.cluster_centers_


def _build_block_assignment_labels(
    data: np.ndarray,
    block_size: int,
    assignment_s_top: int,
):
    n = len(data)
    if n <= 1:
        return np.zeros(n, dtype=np.int32), data.mean(axis=0, keepdims=True)
    if block_size <= 0:
        raise ValueError("block_size must be positive for Algorithm 2 block assignment.")

    block_size = max(1, int(block_size))
    cluster_k = max(1, int(np.ceil(n / block_size)))
    if cluster_k >= n and block_size == 1:
        return np.arange(n, dtype=np.int32), data.astype(np.float32, copy=True)

    km = MiniBatchKMeans(
        n_clusters=cluster_k,
        n_init=10,
        random_state=42,
        batch_size=min(1024, n),
    )
    seeded_centers = km.fit(data).cluster_centers_.astype(np.float32, copy=False)

    sq_dists = np.sum((data[:, None, :] - seeded_centers[None, :, :]) ** 2, axis=2)
    s_top = min(max(1, int(assignment_s_top)), cluster_k)
    nearest_center_ids = np.argpartition(sq_dists, kth=s_top - 1, axis=1)[:, :s_top]

    candidate_triplets: list[tuple[float, int, int]] = []
    for point_idx in range(n):
        for center_id in nearest_center_ids[point_idx]:
            candidate_triplets.append((float(sq_dists[point_idx, center_id]), point_idx, int(center_id)))
    candidate_triplets.sort(key=lambda item: item[0])

    labels = np.full(n, -1, dtype=np.int32)
    counts = np.zeros(cluster_k, dtype=np.int32)
    for _, point_idx, center_id in candidate_triplets:
        if labels[point_idx] >= 0 or counts[center_id] >= block_size:
            continue
        labels[point_idx] = center_id
        counts[center_id] += 1

    unassigned = np.flatnonzero(labels < 0)
    while len(unassigned) > 0:
        available_center_ids = np.flatnonzero(counts < block_size)
        if len(available_center_ids) == 0:
            raise RuntimeError("Algorithm 2 block assignment exhausted all cluster capacity.")

        available_dists = sq_dists[np.ix_(unassigned, available_center_ids)]
        local_best_center_offsets = np.argmin(available_dists, axis=1)
        local_best_dists = available_dists[np.arange(len(unassigned)), local_best_center_offsets]
        best_point_offset = int(np.argmin(local_best_dists))
        point_idx = int(unassigned[best_point_offset])
        center_id = int(available_center_ids[local_best_center_offsets[best_point_offset]])
        labels[point_idx] = center_id
        counts[center_id] += 1
        unassigned = np.flatnonzero(labels < 0)

    centers = seeded_centers.copy()
    for center_id in range(cluster_k):
        member_ids = np.flatnonzero(labels == center_id)
        if len(member_ids) > 0:
            centers[center_id] = data[member_ids].mean(axis=0)
    return labels, centers


def _cluster_and_sort(
    transformed_data: np.ndarray,
    cluster_k: int,
    use_equal_size_clusters: bool,
    query: np.ndarray,
    block_size: int = 0,
    assignment_s_top: int = 5,
    preset_labels: np.ndarray | None = None,
    preset_centers: np.ndarray | None = None,
):
    cluster_k = min(max(1, cluster_k), len(transformed_data))
    if preset_labels is not None or preset_centers is not None:
        if preset_labels is None or preset_centers is None:
            raise ValueError("preset_labels and preset_centers must be provided together.")
        labels = np.asarray(preset_labels, dtype=np.int32)
        centers = np.asarray(preset_centers, dtype=np.float32)
    elif use_equal_size_clusters:
        labels, centers = _build_equal_size_labels(transformed_data, cluster_k)
    else:
        effective_block_size = int(block_size)
        if effective_block_size <= 0:
            effective_block_size = max(1, int(np.ceil(len(transformed_data) / cluster_k)))
        labels, centers = _build_block_assignment_labels(
            transformed_data,
            block_size=effective_block_size,
            assignment_s_top=assignment_s_top,
        )

    normalized_query_mean = _mean_query_direction(query)
    block_scores = np.full(len(centers), np.inf, dtype=np.float32)
    for cid in range(len(centers)):
        idx = np.where(labels == cid)[0]
        if len(idx) == 0:
            continue
        x_cluster = transformed_data[idx]
        sim_q = cosine_similarity(x_cluster, normalized_query_mean).reshape(-1)
        block_scores[cid] = np.min(1.0 - sim_q)

    ordered_clusters = np.argsort(block_scores)

    perm = []
    for cid in ordered_clusters:
        idx = np.where(labels == cid)[0]
        if len(idx) == 0:
            continue
        ordered_idx = sort_within_cluster(transformed_data, idx, centers[cid])
        perm.extend(ordered_idx.tolist())
    return np.asarray(perm, dtype=np.int32)


def build_qso_layout_order(
    data: np.ndarray,
    query: np.ndarray,
    config: QsoAlgorithmConfig | None = None,
) -> np.ndarray:
    config = config or QsoAlgorithmConfig()

    if data.ndim != 2:
        raise ValueError(f"data must be 2D, got shape {data.shape}")
    if query.ndim != 2:
        raise ValueError(f"query must be 2D, got shape {query.shape}")
    if len(query) == 0:
        raise ValueError("query is empty")
    if data.shape[1] != query.shape[1]:
        raise ValueError("data and query must share the same feature dimension")
    if not has_torch():
        raise RuntimeError(
            "torch is required for QSO transform path. "
            "Install torch to match memory_resident_ann/qso semantics."
        )

    transformed_data = data.astype(np.float32, copy=False)
    transformed_query = query.astype(np.float32, copy=False)

    if config.use_cov_transform:
        cov, scale, rot = covariance_eigen_decomposition(transformed_query)
        a = transform_matrix(cov, scale, rot)
        a_torch = torch.from_numpy(a).float().to(torch_device())
        all_data = np.vstack([transformed_query, transformed_data]).astype(np.float32)
        all_torch = torch.from_numpy(all_data).float().to(torch_device())
        transformed_all = all_torch @ a_torch
        q_count = transformed_query.shape[0]
        transformed_query = transformed_all[:q_count].cpu().numpy()
        transformed_data = transformed_all[q_count:].cpu().numpy()

    if config.use_query_transform:
        transformed_data = lgpf_q2d_newdata(
            query=transformed_query,
            data=transformed_data,
            k=config.lgpf_k,
            t=config.transform_t,
            chunk_size=config.chunk_size,
        ).cpu().numpy()
    else:
        transformed_data = lgpf_newdata(
            transformed_data,
            size=transformed_data.shape[1],
            k=config.lgpf_k,
            t=config.transform_t,
        ).cpu().numpy()

    transformed_data = _normalize_rows(transformed_data)
    return _cluster_and_sort(
        transformed_data=transformed_data,
        cluster_k=config.cluster_k,
        use_equal_size_clusters=config.use_equal_size_clusters,
        query=transformed_query,
        block_size=config.block_size,
        assignment_s_top=config.assignment_s_top,
    )
