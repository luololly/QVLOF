from __future__ import annotations

import numpy as np

from common.rdo_types import LayoutCandidate, LayoutFamily, ReplayPlan, ReplaySummary, SwitchEvent


def _score_candidate(
    candidate: LayoutCandidate,
    previous: LayoutCandidate | None,
    alpha: float,
    query_cost_source: str,
) -> float:
    movement = 0.0
    if previous is not None and previous.candidate_id != candidate.candidate_id:
        movement = candidate.estimated_movement_cost * alpha
    query_cost = candidate.estimated_query_cost
    if query_cost_source == "baseline":
        query_cost = float(candidate.metadata.get("baseline_query_cost", candidate.estimated_query_cost))
    return query_cost + movement


def _candidate_query_cost(candidate: LayoutCandidate, query_cost_source: str) -> float:
    if query_cost_source == "baseline":
        return float(candidate.metadata.get("baseline_query_cost", candidate.estimated_query_cost))
    return float(candidate.estimated_query_cost)


def _layout_state_key(candidate: LayoutCandidate) -> str:
    return str(candidate.metadata.get("layout_state_id", candidate.layout_label))


def _choose_by_qvlof_weights(
    candidates: list[LayoutCandidate],
    counters: dict[str, float],
    alpha: float,
    rng: np.random.Generator,
) -> LayoutCandidate:
    weights = np.asarray(
        [max(0.0, (alpha - counters.get(_layout_state_key(candidate), 0.0)) / alpha) for candidate in candidates],
        dtype=np.float64,
    )
    positive = float(weights.sum())
    if positive <= 0.0 or np.any(np.isnan(weights)):
        return min(candidates, key=lambda candidate: (counters.get(_layout_state_key(candidate), 0.0), candidate.candidate_id))
    probs = weights / positive
    return candidates[int(rng.choice(len(candidates), p=probs))]


def _choose_layouts_qvlof_counter(
    families: list[LayoutFamily],
    alpha: float,
    query_cost_source: str,
    random_state: int,
) -> ReplayPlan:
    if alpha <= 0.0:
        raise ValueError("alpha must be positive for qvlof-counter.")

    rng = np.random.default_rng(random_state)
    counters: dict[str, float] = {}
    current_state: str | None = None
    events: list[SwitchEvent] = []

    for family in families:
        if not family.candidates:
            raise ValueError(f"Layout family for window {family.window_id} has no candidates.")

        by_state = {_layout_state_key(candidate): candidate for candidate in family.candidates}
        for candidate in family.candidates:
            key = _layout_state_key(candidate)
            counters.setdefault(key, 0.0)
            counters[key] += _candidate_query_cost(candidate, query_cost_source)

        if current_state is None or current_state not in by_state:
            chosen = family.candidates[0]
            previous_state = None
            current_state = _layout_state_key(chosen)
        else:
            previous_state = current_state
            chosen = by_state[current_state]
            if counters[current_state] > alpha:
                chosen = _choose_by_qvlof_weights(family.candidates, counters, alpha, rng)
                current_state = _layout_state_key(chosen)
                if previous_state != current_state:
                    counters[previous_state] = 0.0

        switched = previous_state is not None and previous_state != current_state
        query_cost = _candidate_query_cost(chosen, query_cost_source)
        events.append(
            SwitchEvent(
                window_id=family.window_id,
                chosen_candidate_id=chosen.candidate_id,
                layout_label=chosen.layout_label,
                query_cost=query_cost,
                movement_cost=alpha if switched else 0.0,
                switched=switched,
            )
        )

    summary = ReplaySummary(
        total_query_cost=sum(event.query_cost for event in events),
        total_movement_cost=sum(event.movement_cost for event in events),
        total_cost=sum(event.query_cost + event.movement_cost for event in events),
        switch_count=sum(1 for event in events if event.switched),
        window_count=len(events),
        chosen_layouts=[event.chosen_candidate_id for event in events],
    )
    return ReplayPlan(events=events, summary=summary)


def choose_layouts(
    families: list[LayoutFamily],
    policy: str = "qvlof-counter",
    alpha: float = 1.0,
    switch_threshold: float = 0.0,
    query_cost_source: str = "estimated",
    random_state: int = 0,
) -> ReplayPlan:
    if policy not in {"qvlof-counter", "cost-aware-greedy", "sticky-best"}:
        raise ValueError(f"Unsupported switch policy: {policy}")
    if query_cost_source not in {"estimated", "baseline"}:
        raise ValueError(f"Unsupported query cost source: {query_cost_source}")
    if policy == "qvlof-counter":
        return _choose_layouts_qvlof_counter(
            families=families,
            alpha=alpha,
            query_cost_source=query_cost_source,
            random_state=random_state,
        )

    previous: LayoutCandidate | None = None
    events: list[SwitchEvent] = []

    for family in families:
        if not family.candidates:
            raise ValueError(f"Layout family for window {family.window_id} has no candidates.")

        if previous is None:
            base_candidate = next(
                (candidate for candidate in family.candidates if candidate.layout_label == "base"),
                None,
            )
            chosen = (
                base_candidate
                if query_cost_source == "estimated" and base_candidate is not None
                else min(
                    family.candidates,
                    key=lambda candidate: (
                        float(candidate.metadata.get("baseline_query_cost", candidate.estimated_query_cost))
                        if query_cost_source == "baseline"
                        else candidate.estimated_query_cost,
                        candidate.candidate_id,
                    ),
                )
            )
        else:
            stay = min(
                family.candidates,
                key=lambda candidate: (
                    0 if candidate.layout_label == previous.layout_label else 1,
                    float(candidate.metadata.get("baseline_query_cost", candidate.estimated_query_cost))
                    if query_cost_source == "baseline"
                    else candidate.estimated_query_cost,
                    candidate.candidate_id,
                ),
            )
            best = min(
                family.candidates,
                key=lambda candidate: (
                    _score_candidate(candidate, previous, alpha, query_cost_source),
                    candidate.candidate_id,
                ),
            )

            if policy == "sticky-best":
                stay_query_cost = (
                    float(stay.metadata.get("baseline_query_cost", stay.estimated_query_cost))
                    if query_cost_source == "baseline"
                    else stay.estimated_query_cost
                )
                best_query_cost = (
                    float(best.metadata.get("baseline_query_cost", best.estimated_query_cost))
                    if query_cost_source == "baseline"
                    else best.estimated_query_cost
                )
                improvement = stay_query_cost - best_query_cost
                if best.layout_label != stay.layout_label and improvement > switch_threshold:
                    chosen = best
                else:
                    chosen = stay
            else:
                stay_score = _score_candidate(stay, previous, alpha, query_cost_source)
                best_score = _score_candidate(best, previous, alpha, query_cost_source)
                if best_score + switch_threshold < stay_score:
                    chosen = best
                else:
                    chosen = stay

        switched = previous is not None and previous.layout_label != chosen.layout_label
        movement_cost = chosen.estimated_movement_cost if switched else 0.0
        query_cost = (
            float(chosen.metadata.get("baseline_query_cost", chosen.estimated_query_cost))
            if query_cost_source == "baseline"
            else chosen.estimated_query_cost
        )
        events.append(
            SwitchEvent(
                window_id=family.window_id,
                chosen_candidate_id=chosen.candidate_id,
                layout_label=chosen.layout_label,
                query_cost=query_cost,
                movement_cost=movement_cost,
                switched=switched,
            )
        )
        previous = chosen

    summary = ReplaySummary(
        total_query_cost=sum(event.query_cost for event in events),
        total_movement_cost=sum(event.movement_cost for event in events),
        total_cost=sum(event.query_cost + event.movement_cost for event in events),
        switch_count=sum(1 for event in events if event.switched),
        window_count=len(events),
        chosen_layouts=[event.chosen_candidate_id for event in events],
    )
    return ReplayPlan(events=events, summary=summary)
