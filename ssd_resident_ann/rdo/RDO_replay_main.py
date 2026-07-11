#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np


THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from common.rdo_types import LayoutCandidate, LayoutFamily, ReplayPlan, ReplaySummary, SwitchEvent, WorkloadWindow
from evaluation.replay import replay_online_switch_plan, replay_switch_plan
from utils.io_utils import read_json, write_json, write_jsonl


def _load_plan(payload: dict) -> ReplayPlan:
    events = [
        SwitchEvent(
            window_id=int(item["window_id"]),
            chosen_candidate_id=item["chosen_candidate_id"],
            layout_label=item["layout_label"],
            query_cost=float(item["query_cost"]),
            movement_cost=float(item["movement_cost"]),
            switched=bool(item["switched"]),
        )
        for item in payload.get("events", [])
    ]
    summary_payload = payload.get("summary", {})
    summary = ReplaySummary(
        total_query_cost=float(summary_payload.get("total_query_cost", 0.0)),
        total_movement_cost=float(summary_payload.get("total_movement_cost", 0.0)),
        total_cost=float(summary_payload.get("total_cost", 0.0)),
        switch_count=int(summary_payload.get("switch_count", 0)),
        window_count=int(summary_payload.get("window_count", 0)),
        chosen_layouts=list(summary_payload.get("chosen_layouts", [])),
    )
    return ReplayPlan(events=events, summary=summary)


def _load_windows(payload: dict) -> list[WorkloadWindow]:
    return [
        WorkloadWindow(
            window_id=int(item["window_id"]),
            start_query_id=int(item["start_query_id"]),
            end_query_id=int(item["end_query_id"]),
            workload_label=item["workload_label"],
            dataset_group=item["dataset_group"],
            query_ids=[int(v) for v in item.get("query_ids", [])],
            query_matrix=np.asarray(item["query_matrix"], dtype=np.float32),
            hot_vector_ids=[int(v) for v in item.get("hot_vector_ids", [])],
        )
        for item in payload.get("windows", [])
    ]


def _load_families(payload: dict) -> list[LayoutFamily]:
    families: list[LayoutFamily] = []
    for row in payload.get("layout_families", []):
        candidates = [
            LayoutCandidate(
                candidate_id=item["candidate_id"],
                window_id=int(item["window_id"]),
                layout_label=item["layout_label"],
                artifact_hint=item["artifact_hint"],
                estimated_query_cost=float(item["estimated_query_cost"]),
                estimated_movement_cost=float(item["estimated_movement_cost"]),
                metadata=dict(item.get("metadata", {})),
            )
            for item in row.get("candidates", [])
        ]
        families.append(LayoutFamily(window_id=int(row["window_id"]), candidates=candidates))
    return families


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Replay a disk-resident RDO switch plan.")
    parser.add_argument("--switch-plan", required=True)
    parser.add_argument("--summary-output", required=True)
    parser.add_argument("--events-output", help="Optional JSONL output for per-window replay events.")
    parser.add_argument("--layout-manifest", help="Required for Algorithm 5 style partial-layout replay.")
    parser.add_argument("--base-vectors", help="Required for Algorithm 5 style partial-layout replay.")
    parser.add_argument("--k", type=int, default=10, help="Query top-k used during partial-layout replay.")
    parser.add_argument("--a", type=float, default=2.0, help="Partial-search candidate multiplier from Algorithm 5.")
    parser.add_argument("--query-events-output", help="Optional JSONL output for per-query replay events.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = read_json(args.switch_plan)
    plan = _load_plan(payload)
    if args.layout_manifest and args.base_vectors:
        manifest = read_json(args.layout_manifest)
        windows = _load_windows(manifest)
        families = _load_families(manifest)
        base_vectors = np.load(args.base_vectors)
        summary, query_events = replay_online_switch_plan(
            plan=plan,
            windows=windows,
            families=families,
            base_vectors=base_vectors,
            k=args.k,
            a=args.a,
        )
        if args.query_events_output:
            write_jsonl(args.query_events_output, query_events)
    else:
        summary = replay_switch_plan(plan)
    write_json(args.summary_output, summary.to_dict())
    if args.events_output:
        write_jsonl(args.events_output, [event.to_dict() for event in plan.events])
    print(f"Wrote replay summary to {args.summary_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
