from __future__ import annotations

import numpy as np
from scipy.spatial.distance import cdist
from sklearn.cluster import KMeans, MiniBatchKMeans

from algorithms import QsoAlgorithmConfig, build_qso_layout_order

try:
    from hilbertcurve.hilbertcurve import HilbertCurve
except ImportError:
    HilbertCurve = None


def sort_within_cluster(data: np.ndarray, idx: np.ndarray, center: np.ndarray):
    d = np.linalg.norm(data[idx] - center, axis=1)
    return idx[np.argsort(d)]


def f2_zorder(data: np.ndarray, bits: int = 16) -> np.ndarray:
    data_min = data.min(axis=0)
    data_max = data.max(axis=0)
    norm = (data - data_min) / (data_max - data_min + 1e-12)

    max_int = (1 << bits) - 1
    ints = (norm * max_int).astype(np.uint32)
    morton = np.zeros(data.shape[0], dtype=np.uint64)

    for b in range(bits):
        for d in range(data.shape[1]):
            morton |= ((ints[:, d] >> b) & 1) << (b * data.shape[1] + d)
    return np.argsort(morton)


def f3_hilbert(data: np.ndarray, p: int = 10) -> np.ndarray:
    if HilbertCurve is None:
        return f2_zorder(data, bits=min(16, max(4, p)))

    d = data.shape[1]
    hil = HilbertCurve(p, d)
    data_min = data.min(axis=0)
    data_max = data.max(axis=0) + 1e-9
    normalized = (data - data_min) / (data_max - data_min)
    coords = (normalized * (2**p - 1)).astype(np.int64)
    dist_vals = [hil.distance_from_point(coord.tolist()) for coord in coords]
    return np.argsort(np.asarray(dist_vals))


def f4_idistance(data: np.ndarray, k: int) -> np.ndarray:
    km = MiniBatchKMeans(n_clusters=min(k, len(data)), n_init=10)
    labels = km.fit_predict(data)
    centers = km.cluster_centers_
    center_norms = np.linalg.norm(centers, axis=1)
    order = np.argsort(center_norms)
    offsets = np.zeros_like(center_norms)
    for i, cid in enumerate(order):
        offsets[cid] = i * (np.ptp(data) + 1e-6)

    keyvals = np.zeros(data.shape[0], dtype=float)
    for i in range(data.shape[0]):
        cid = labels[i]
        dist = np.linalg.norm(data[i] - centers[cid])
        keyvals[i] = offsets[cid] + dist
    return np.argsort(keyvals)


def f5_kmeans(data: np.ndarray, k: int) -> np.ndarray:
    km = MiniBatchKMeans(n_clusters=min(k, len(data)), batch_size=min(1024, len(data)))
    labels = km.fit_predict(data)
    centers = km.cluster_centers_
    center_dists = np.sum(cdist(centers, centers), axis=1)
    ordered_clusters = np.argsort(center_dists)
    perm = []
    for cid in ordered_clusters:
        idx = np.where(labels == cid)[0]
        ordered_idx = sort_within_cluster(data, idx, centers[cid])
        perm.extend(ordered_idx.tolist())
    return np.asarray(perm)


def qso_access_order(
    data: np.ndarray,
    query_matrix: np.ndarray | None = None,
    cluster_k: int = 64,
    lgpf_k: int = 3,
    transform_t: float = 0.3,
) -> np.ndarray:
    if query_matrix is None or len(query_matrix) == 0:
        raise ValueError("qso_access_order requires non-empty query_matrix.")

    config = QsoAlgorithmConfig(
        lgpf_k=max(1, int(lgpf_k)),
        cluster_k=cluster_k,
        block_size=max(1, int(np.ceil(len(data) / max(1, cluster_k)))),
        assignment_s_top=5,
        transform_t=float(transform_t),
        chunk_size=4096,
        use_query_transform=True,
        use_cov_transform=True,
        use_equal_size_clusters=False,
    )
    return build_qso_layout_order(data=data, query=query_matrix, config=config)
