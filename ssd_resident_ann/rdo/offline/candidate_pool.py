from __future__ import annotations

import numpy as np

from common.rdo_types import PartialLayout, WorkloadWindow
from offline.query_cost import estimate_layout_query_cost


class CandidateLayoutPool:
    def __init__(self, epsilon: float = 0.08, sample_size: int = 32, random_state: int = 0):
        if epsilon < 0.0:
            raise ValueError("epsilon must be non-negative.")
        if sample_size <= 0:
            raise ValueError("sample_size must be positive.")
        self.epsilon = float(epsilon)
        self.sample_size = int(sample_size)
        self.random_state = int(random_state)
        self.layouts: list[PartialLayout] = []
        self.query_samples = np.empty((0, 0), dtype=np.float32)
        self.cost_profiles: list[np.ndarray] = []

    def reset_query_samples(self, queries: np.ndarray) -> None:
        arr = np.asarray(queries, dtype=np.float32)
        if arr.ndim != 2:
            raise ValueError(f"queries must be 2D, got shape {arr.shape}.")
        if len(arr) == 0:
            raise ValueError("queries must not be empty.")
        if len(arr) <= self.sample_size:
            self.query_samples = arr.copy()
            return
        rng = np.random.default_rng(self.random_state)
        indices = np.sort(rng.choice(len(arr), self.sample_size, replace=False))
        self.query_samples = arr[indices].copy()

    def _profile(self, layout: PartialLayout) -> np.ndarray:
        if self.query_samples.size == 0:
            raise ValueError("query_samples must be initialized before adding layouts.")
        dim = int(self.query_samples.shape[1])
        return np.asarray(
            [
                float(
                    estimate_layout_query_cost(
                        WorkloadWindow(
                            window_id=layout.window_id,
                            start_query_id=query_id,
                            end_query_id=query_id,
                            workload_label=f"sample{query_id}",
                            dataset_group="pool",
                            query_ids=[query_id],
                            query_matrix=np.asarray([query], dtype=np.float32).reshape(1, dim),
                            hot_vector_ids=[],
                        ),
                        "partial",
                        partial_layout=layout,
                        k=1,
                    )
                )
                for query_id, query in enumerate(self.query_samples.tolist())
            ],
            dtype=np.float32,
        )

    def try_add(self, layout: PartialLayout) -> bool:
        profile = self._profile(layout)
        if self.epsilon == 0.0 or not self.cost_profiles:
            self.layouts.append(layout)
            self.cost_profiles.append(profile)
            return True

        norm = float(len(profile))
        distances = [
            float(np.linalg.norm(profile - ref, ord=1) / max(1.0, norm))
            for ref in self.cost_profiles
        ]
        if min(distances) <= self.epsilon:
            return False

        self.layouts.append(layout)
        self.cost_profiles.append(profile)
        return True
