from __future__ import annotations

import numpy as np
from sklearn.cluster import MiniBatchKMeans
from sklearn.metrics import pairwise_distances


class EqualSizeKMeans:
    def __init__(
        self,
        n_clusters: int,
        size: int | None = None,
        sizes: list[int] | np.ndarray | None = None,
        n_init: int = 10,
        random_state: int | None = None,
        batch_size: int = 5000,
    ):
        self.n_clusters = n_clusters
        self.size = size
        self.sizes = None if sizes is None else np.asarray(sizes, dtype=np.int32)
        self.n_init = n_init
        self.random_state = random_state
        self.batch_size = batch_size
        self.cluster_centers_ = None
        self.labels_ = None

    def _target_sizes(self, n: int) -> np.ndarray:
        if self.sizes is not None:
            if len(self.sizes) != self.n_clusters:
                raise ValueError("sizes length must equal n_clusters")
            if int(self.sizes.sum()) != n:
                raise ValueError("sizes must sum to N")
            if np.any(self.sizes < 0):
                raise ValueError("sizes must be non-negative")
            return self.sizes.astype(np.int32, copy=True)
        if self.size is None:
            raise ValueError("Either size or sizes must be provided")
        target_sizes = np.full(self.n_clusters, int(self.size), dtype=np.int32)
        if int(target_sizes.sum()) != n:
            raise ValueError("EqualSizeKMeans requires N == n_clusters * size")
        return target_sizes

    def fit_predict(self, x: np.ndarray):
        n = x.shape[0]
        target_sizes = self._target_sizes(n)

        kmeans = MiniBatchKMeans(
            n_clusters=self.n_clusters,
            n_init=self.n_init,
            batch_size=self.batch_size,
            random_state=self.random_state,
        )
        kmeans.fit(x)
        centers = kmeans.cluster_centers_
        self.cluster_centers_ = centers

        labels = -np.ones(n, dtype=np.int32)
        cluster_sizes = np.zeros(self.n_clusters, dtype=np.int32)
        order = np.arange(n)
        np.random.shuffle(order)

        for start in range(0, n, self.batch_size):
            end = min(start + self.batch_size, n)
            idx = order[start:end]
            xb = x[idx]
            dists = pairwise_distances(xb, centers)
            pref = np.argsort(dists, axis=1)
            for i, prefs in zip(idx, pref):
                for cid in prefs:
                    if cluster_sizes[cid] < target_sizes[cid]:
                        labels[i] = cid
                        cluster_sizes[cid] += 1
                        break

        unassigned = np.where(labels < 0)[0]
        if len(unassigned) > 0:
            free_clusters = []
            for cid in range(self.n_clusters):
                free_clusters.extend([cid] * int(target_sizes[cid] - cluster_sizes[cid]))
            free_clusters = np.asarray(free_clusters)
            dists = pairwise_distances(x[unassigned], centers[free_clusters])
            best = np.argmin(dists, axis=1)
            for i, k_idx in enumerate(best):
                cid = int(free_clusters[k_idx])
                labels[unassigned[i]] = cid
                cluster_sizes[cid] += 1

        if not np.all(cluster_sizes == target_sizes):
            raise RuntimeError("EqualSizeKMeans failed to produce balanced clusters")

        self.labels_ = labels
        return labels
