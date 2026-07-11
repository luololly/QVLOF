from __future__ import annotations

import numpy as np

from common.rdo_types import LayoutFamily, PartialLayout, QuerySearchResult, ReplayPlan, ReplaySummary, WorkloadWindow
from online.query_runtime import search_with_fallback


def replay_switch_plan(plan: ReplayPlan) -> ReplaySummary:
    total_query_cost = sum(event.query_cost for event in plan.events)
    total_movement_cost = sum(event.movement_cost for event in plan.events)
    total_cost = total_query_cost + total_movement_cost
    switch_count = sum(1 for event in plan.events if event.switched)
    window_count = len(plan.events)
    chosen_layouts = [event.chosen_candidate_id for event in plan.events]

    summary = ReplaySummary(
        total_query_cost=total_query_cost,
        total_movement_cost=total_movement_cost,
        total_cost=total_cost,
        switch_count=switch_count,
        window_count=window_count,
        chosen_layouts=chosen_layouts,
    )
    plan.summary = summary
    return summary


def _partial_layout_from_candidate(window_id: int, layout_label: str, metadata: dict) -> PartialLayout:
    return PartialLayout(
        window_id=window_id,
        layout_label=layout_label,
        representative_query=np.asarray(metadata["representative_query"], dtype=np.float32),
        covered_vector_ids=[int(v) for v in metadata["covered_vector_ids"]],
        blocks=[],
        block_metas=list(metadata["block_metas"]),
        total_block_count=int(metadata.get("partial_layout_blocks", len(metadata["block_metas"]))),
        beta=float(metadata.get("partial_layout_beta", 1.0)),
        distance_values=[float(v) for v in metadata.get("distance_values", [])],
    )


def replay_online_switch_plan(
    plan: ReplayPlan,
    windows: list[WorkloadWindow],
    families: list[LayoutFamily],
    base_vectors: np.ndarray,
    k: int,
    a: float,
) -> tuple[ReplaySummary, list[dict]]:
    base_summary = replay_switch_plan(plan)
    window_by_id = {window.window_id: window for window in windows}
    family_by_id = {family.window_id: family for family in families}
    query_events: list[QuerySearchResult] = []

    for event in plan.events:
        if event.layout_label != "partial":
            continue
        window = window_by_id[event.window_id]
        family = family_by_id[event.window_id]
        candidate = next(
            (candidate for candidate in family.candidates if candidate.candidate_id == event.chosen_candidate_id),
            None,
        )
        if candidate is None:
            raise ValueError(
                f"Chosen candidate {event.chosen_candidate_id} is missing from layout family {event.window_id}."
            )
        partial_layout = _partial_layout_from_candidate(
            window_id=window.window_id,
            layout_label=candidate.layout_label,
            metadata=candidate.metadata,
        )
        for query_id, query in zip(window.query_ids, window.query_matrix, strict=True):
            query_events.append(
                search_with_fallback(
                    query=query,
                    base_vectors=base_vectors,
                    partial_layout=partial_layout,
                    k=k,
                    a=a,
                    query_id=query_id,
                    candidate_id=candidate.candidate_id,
                    window_id=window.window_id,
                    qso_full_layout_pages=candidate.metadata.get("qso_full_layout_pages"),
                )
            )

    fallback_query_count = sum(1 for item in query_events if item.fallback_used)
    partial_only_query_count = sum(1 for item in query_events if not item.fallback_used)
    mean_recall = float(np.mean([item.recall_at_k for item in query_events])) if query_events else 0.0
    summary = ReplaySummary(
        total_query_cost=base_summary.total_query_cost,
        total_movement_cost=base_summary.total_movement_cost,
        total_cost=base_summary.total_cost,
        switch_count=base_summary.switch_count,
        window_count=base_summary.window_count,
        chosen_layouts=list(base_summary.chosen_layouts),
        query_count=len(query_events),
        partial_only_query_count=partial_only_query_count,
        fallback_query_count=fallback_query_count,
        mean_recall_at_k=mean_recall,
    )
    return summary, [item.to_dict() for item in query_events]
