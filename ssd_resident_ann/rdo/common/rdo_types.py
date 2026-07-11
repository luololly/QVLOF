from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np


@dataclass
class WorkloadWindow:
    window_id: int
    start_query_id: int
    end_query_id: int
    workload_label: str
    dataset_group: str
    query_ids: list[int]
    query_matrix: np.ndarray
    hot_vector_ids: list[int]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["query_ids"] = list(self.query_ids)
        payload["query_matrix"] = self.query_matrix.tolist()
        return payload


@dataclass
class LayoutCandidate:
    candidate_id: str
    window_id: int
    layout_label: str
    artifact_hint: str
    estimated_query_cost: float
    estimated_movement_cost: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LayoutFamily:
    window_id: int
    candidates: list[LayoutCandidate]

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_id": self.window_id,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
        }


@dataclass
class QsoWindowArtifact:
    window_id: int
    system: str
    output_dir: str
    prefix: str
    artifact_prefix: str
    files: list[str]
    train_queries: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PartialLayout:
    window_id: int
    layout_label: str
    representative_query: np.ndarray
    covered_vector_ids: list[int]
    blocks: list[list[int]]
    block_metas: list[dict[str, float | int]]
    total_block_count: int
    beta: float
    distance_values: list[float] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["representative_query"] = self.representative_query.tolist()
        return payload


@dataclass
class ReplaySummary:
    total_query_cost: float
    total_movement_cost: float
    total_cost: float
    switch_count: int
    window_count: int
    chosen_layouts: list[str]
    query_count: int = 0
    partial_only_query_count: int = 0
    fallback_query_count: int = 0
    mean_recall_at_k: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QuerySearchResult:
    query_id: int
    window_id: int
    candidate_id: str
    layout_label: str
    neighbor_ids: list[int]
    partial_neighbor_ids: list[int]
    full_neighbor_ids: list[int]
    fallback_used: bool
    boundary_touched: bool
    candidate_count: int
    recall_at_k: float
    search_mode: str
    fallback_page_ids: list[int] = field(default_factory=list)
    full_layout_accessed_pages: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SwitchEvent:
    window_id: int
    chosen_candidate_id: str
    layout_label: str
    query_cost: float
    movement_cost: float
    switched: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReplayPlan:
    events: list[SwitchEvent]
    summary: ReplaySummary

    def to_dict(self) -> dict[str, Any]:
        return {
            "events": [event.to_dict() for event in self.events],
            "summary": self.summary.to_dict(),
        }
