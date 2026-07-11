from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from algorithms import QsoAlgorithmConfig, build_qso_layout_order


@dataclass
class StaticLayout:
    pages: list[list[int]]
    id_to_page: list[int]
    permutation: list[int]
    access_score: list[float]


def _load_vector_features(path: str | Path) -> np.ndarray:
    source = Path(path)
    suffix = source.suffix.lower()
    if suffix == ".npy":
        data = np.load(source)
    elif suffix == ".csv":
        with source.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            rows = [[float(v) for v in row] for row in reader]
        data = np.asarray(rows, dtype=np.float32)
    else:
        raise ValueError(
            f"Unsupported vector feature format for {source}. Expected .npy or .csv."
        )
    if data.ndim != 2:
        raise ValueError(f"Vector feature matrix must be 2D, got shape {data.shape}.")
    return data.astype(np.float32, copy=False)


def _normalize_features(features: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(features, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return features / norms


def build_static_layout(
    events: object = None,
    num_vectors: int = 0,
    page_capacity: int = 0,
    vector_features_path: str | None = None,
    query_matrix: np.ndarray | None = None,
    lgpf_k: int = 3,
    transform_t: float = 0.3,
) -> StaticLayout:
    del events

    if num_vectors <= 0:
        raise ValueError("num_vectors must be positive.")
    if page_capacity <= 0:
        raise ValueError("page_capacity must be positive.")
    if not vector_features_path:
        raise ValueError("QSO layout generation requires vector_features_path.")
    if query_matrix is None:
        raise ValueError("QSO layout generation requires held-out training query_matrix.")

    features = _normalize_features(_load_vector_features(vector_features_path))
    if features.shape[0] != num_vectors:
        raise ValueError(
            "Vector feature row count does not match num_vectors: "
            f"{features.shape[0]} vs {num_vectors}."
        )

    normalized_query = np.asarray(query_matrix, dtype=np.float32)
    if normalized_query.ndim != 2:
        raise ValueError(
            f"Query feature matrix must be 2D, got shape {normalized_query.shape}."
        )
    if len(normalized_query) == 0:
        raise ValueError("Query feature matrix is empty.")
    if normalized_query.shape[1] != features.shape[1]:
        raise ValueError(
            "Query feature dimension does not match vector feature dimension: "
            f"{normalized_query.shape[1]} vs {features.shape[1]}."
        )
    normalized_query = _normalize_features(normalized_query)

    cluster_k = max(1, min(max(1, int(np.ceil(num_vectors / page_capacity))), 256))
    permutation = build_qso_layout_order(
        data=features,
        query=normalized_query,
        config=QsoAlgorithmConfig(
            lgpf_k=max(1, int(lgpf_k)),
            cluster_k=cluster_k,
            block_size=page_capacity,
            assignment_s_top=5,
            transform_t=float(transform_t),
            chunk_size=4096,
            use_query_transform=True,
            use_cov_transform=True,
            use_equal_size_clusters=False,
        ),
    ).tolist()

    pages = []
    for start in range(0, len(permutation), page_capacity):
        pages.append(permutation[start : start + page_capacity])

    id_to_page = [0] * num_vectors
    for page_id, page in enumerate(pages):
        for vid in page:
            id_to_page[vid] = page_id

    return StaticLayout(
        pages=pages,
        id_to_page=id_to_page,
        permutation=permutation,
        access_score=[0.0] * num_vectors,
    )
