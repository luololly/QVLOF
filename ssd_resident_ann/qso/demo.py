#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from static_layout_main import SUPPORTED_SYSTEMS, emit_artifacts
from vector_io import read_feature_matrix


SUPPORTED_METHODS = {"qso"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Disk-resident QSO demo and artifact generator.")
    parser.add_argument("--system", required=True, choices=sorted(SUPPORTED_SYSTEMS))
    parser.add_argument("--method", default="qso", choices=sorted(SUPPORTED_METHODS))
    parser.add_argument(
        "--train-queries",
        required=True,
        help="Held-out training queries as .npy/.csv/.fvecs/.ivecs.",
    )
    parser.add_argument("--vector-features", required=True, help=".npy/.csv/.fvecs/.ivecs feature matrix")
    parser.add_argument("--page-capacity", required=True, type=int)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--cluster-k", type=int, default=64)
    parser.add_argument("--lgpf-k", type=int, default=3)
    parser.add_argument("--transform-t", type=float, default=0.3)
    parser.add_argument(
        "--posting-membership",
        help="SPANN only: CSV with columns posting_id,vector_id describing native posting membership.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    query_matrix = read_feature_matrix(args.train_queries)

    if args.method != "qso":
        raise ValueError(f"Unsupported method {args.method}")

    written = emit_artifacts(args)

    summary = {
        "method": args.method,
        "input_query_count": int(len(query_matrix)),
        "lgpf_k": int(args.lgpf_k),
        "transform_t": float(args.transform_t),
        "artifacts": [str(path) for path in written],
    }
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{args.prefix}_run_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print(f"Method: {args.method}")
    print(f"Input queries: {len(query_matrix)}")
    for path in written:
        print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
