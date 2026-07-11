from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from layout_core import StaticLayout, build_static_layout


@dataclass
class SpannPostingLayout:
    posting_to_vectors: list[list[int]]
    posting_order: list[int]
    vector_to_posting: list[int]
    posting_scores: list[float]
    page_capacity: int
    permutation: list[int]
    access_score: list[float]

    @property
    def pages(self) -> list[list[int]]:
        return self.posting_to_vectors

    @property
    def id_to_page(self) -> list[int]:
        return self.vector_to_posting


def _load_posting_membership_csv(path: Path, num_vectors: int) -> tuple[list[list[int]], list[int]]:
    posting_to_vectors: list[list[int]] = []
    vector_to_posting = [-1] * num_vectors

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        required = {"posting_id", "vector_id"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError(
                f"Posting membership CSV {path} must contain columns: {sorted(required)}."
            )
        for row in reader:
            posting_id = int(row["posting_id"])
            vector_id = int(row["vector_id"])
            if not (0 <= vector_id < num_vectors):
                raise ValueError(
                    f"vector_id {vector_id} out of range for num_vectors={num_vectors}."
                )
            while len(posting_to_vectors) <= posting_id:
                posting_to_vectors.append([])
            posting_to_vectors[posting_id].append(vector_id)

    for posting_id, vector_ids in enumerate(posting_to_vectors):
        deduped = sorted(set(vector_ids))
        posting_to_vectors[posting_id] = deduped
        for vector_id in deduped:
            prev = vector_to_posting[vector_id]
            if prev != -1 and prev != posting_id:
                raise ValueError(
                    f"vector_id {vector_id} appears in multiple postings: {prev} and {posting_id}."
                )
            vector_to_posting[vector_id] = posting_id

    missing = [vid for vid, pid in enumerate(vector_to_posting) if pid < 0]
    if missing:
        preview = missing[: min(16, len(missing))]
        raise ValueError(
            f"Posting membership missing {len(missing)} vectors; first ids: {preview}."
        )

    return posting_to_vectors, vector_to_posting


def _load_posting_membership(path: str | Path, num_vectors: int) -> tuple[list[list[int]], list[int]]:
    source = Path(path)
    if source.suffix.lower() != ".csv":
        raise ValueError(
            f"Unsupported posting membership format for {source}. Expected .csv."
        )
    return _load_posting_membership_csv(source, num_vectors)


def _rank_postings(
    posting_to_vectors: list[list[int]],
    vector_to_posting: list[int],
    access_score: list[float],
    layout: StaticLayout,
) -> tuple[list[int], list[float]]:
    num_postings = len(posting_to_vectors)
    posting_scores = np.zeros(num_postings, dtype=np.float64)
    posting_first_pos = [len(layout.permutation)] * num_postings

    for vector_id, score in enumerate(access_score):
        posting_id = vector_to_posting[vector_id]
        if posting_id >= 0:
            posting_scores[posting_id] += float(score)

    for position, vector_id in enumerate(layout.permutation):
        posting_id = vector_to_posting[vector_id]
        if posting_first_pos[posting_id] > position:
            posting_first_pos[posting_id] = position

    ranked = sorted(
        range(num_postings),
        key=lambda pid: (
            -posting_scores[pid],
            posting_first_pos[pid],
            pid,
        ),
    )
    return ranked, posting_scores.tolist()


def build_spann_posting_layout(
    num_vectors: int,
    page_capacity: int,
    posting_membership_path: str | Path,
    vector_features_path: str | None = None,
    query_matrix: np.ndarray | None = None,
    lgpf_k: int = 3,
    transform_t: float = 0.3,
) -> SpannPostingLayout:
    if page_capacity <= 0:
        raise ValueError("page_capacity must be positive for SPANN artifact generation.")

    layout = build_static_layout(
        num_vectors=num_vectors,
        page_capacity=page_capacity,
        vector_features_path=vector_features_path,
        query_matrix=query_matrix,
        lgpf_k=lgpf_k,
        transform_t=transform_t,
    )
    posting_to_vectors, vector_to_posting = _load_posting_membership(
        posting_membership_path, num_vectors
    )
    access_score = [0.0] * num_vectors
    posting_order, posting_scores = _rank_postings(
        posting_to_vectors=posting_to_vectors,
        vector_to_posting=vector_to_posting,
        access_score=access_score,
        layout=layout,
    )
    ordered_postings = [posting_to_vectors[pid] for pid in posting_order]

    return SpannPostingLayout(
        posting_to_vectors=ordered_postings,
        posting_order=posting_order,
        vector_to_posting=vector_to_posting,
        posting_scores=[posting_scores[pid] for pid in posting_order],
        page_capacity=page_capacity,
        permutation=layout.permutation,
        access_score=access_score,
    )
