#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from common.rdo_types import LayoutCandidate, LayoutFamily
from online.switch_policy import choose_layouts
from utils.io_utils import read_json, write_json


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
    parser = argparse.ArgumentParser(description="Generate disk-resident RDO switch plans.")
    parser.add_argument("--layout-manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--policy",
        default="qvlof-counter",
        choices=["qvlof-counter", "cost-aware-greedy", "sticky-best"],
    )
    parser.add_argument("--alpha", type=float, default=1.0)
    parser.add_argument("--switch-threshold", type=float, default=0.0)
    parser.add_argument("--query-cost-source", default="estimated", choices=["estimated", "baseline"])
    parser.add_argument("--random-state", type=int, default=0)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = read_json(args.layout_manifest)
    families = _load_families(payload)
    plan = choose_layouts(
        families=families,
        policy=args.policy,
        alpha=args.alpha,
        switch_threshold=args.switch_threshold,
        query_cost_source=args.query_cost_source,
        random_state=args.random_state,
    )
    output = write_json(args.output, plan.to_dict())
    print(f"Wrote switch plan to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
