#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from artifact_writer import (
    write_manifest,
    write_pageann_map,
    write_pageann_pages,
    write_partition_bin,
    write_spann_posting_order,
    write_spann_posting_pages_v2,
    write_spann_vector_to_posting,
)
from layout_core import build_static_layout
from spann_layout import build_spann_posting_layout
from vector_io import read_feature_matrix


SUPPORTED_SYSTEMS = {"pageann", "spann", "starling", "margo", "gorgeous"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate static QSO artifacts consumable by disk-resident ANN baselines."
    )
    parser.add_argument("--system", required=True, choices=sorted(SUPPORTED_SYSTEMS))
    parser.add_argument(
        "--train-queries",
        required=True,
        help="Held-out training queries as .npy/.csv/.fvecs/.ivecs.",
    )
    parser.add_argument("--num-vectors", required=True, type=int)
    parser.add_argument("--page-capacity", required=True, type=int)
    parser.add_argument("--vector-features", required=True, help="Base vector feature matrix.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--prefix", required=True, help="Artifact file prefix inside output-dir.")
    parser.add_argument("--lgpf-k", type=int, default=3, help="Memory-aligned query-anchor neighbor count.")
    parser.add_argument("--transform-t", type=float, default=0.3, help="Memory-aligned LGPF transform strength T.")
    parser.add_argument(
        "--posting-membership",
        help="SPANN only: CSV with columns posting_id,vector_id describing native posting membership.",
    )
    return parser


def _load_query_mode_inputs(args: argparse.Namespace):
    train_queries = getattr(args, "train_queries", "")

    if not train_queries:
        raise ValueError("--train-queries is required.")
    if not getattr(args, "vector_features", None):
        raise ValueError("--train-queries requires --vector-features.")
    return [], read_feature_matrix(train_queries)


def emit_artifacts(args: argparse.Namespace) -> list[Path]:
    events, query_matrix = _load_query_mode_inputs(args)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = output_dir / args.prefix
    written: list[Path] = []

    if args.system == "pageann":
        layout = build_static_layout(
            events=events,
            num_vectors=args.num_vectors,
            page_capacity=args.page_capacity,
            vector_features_path=args.vector_features,
            query_matrix=query_matrix,
            lgpf_k=args.lgpf_k,
            transform_t=args.transform_t,
        )
        written.append(write_pageann_map(str(prefix) + "_new_to_old_ids_map.bin", layout))
        written.append(write_pageann_pages(str(prefix) + "_qso_pages.bin", layout, args.page_capacity))
    elif args.system == "spann":
        if not args.posting_membership:
            raise ValueError("--posting-membership is required when --system spann.")
        layout = build_spann_posting_layout(
            num_vectors=args.num_vectors,
            page_capacity=args.page_capacity,
            posting_membership_path=args.posting_membership,
            vector_features_path=args.vector_features,
            query_matrix=query_matrix,
            lgpf_k=args.lgpf_k,
            transform_t=args.transform_t,
        )
        written.append(write_spann_posting_order(str(prefix) + "_qso_posting_order.bin", layout))
        written.append(write_spann_posting_pages_v2(str(prefix) + "_qso_posting_pages.bin", layout))
        written.append(write_spann_vector_to_posting(str(prefix) + "_qso_vector_to_posting.bin", layout))
    elif args.system in {"starling", "margo", "gorgeous"}:
        layout = build_static_layout(
            events=events,
            num_vectors=args.num_vectors,
            page_capacity=args.page_capacity,
            vector_features_path=args.vector_features,
            query_matrix=query_matrix,
            lgpf_k=args.lgpf_k,
            transform_t=args.transform_t,
        )
        written.append(write_partition_bin(str(prefix) + "_partition.bin", layout, args.page_capacity))
    else:
        raise ValueError(f"Unsupported system {args.system}")

    written.append(
        write_manifest(
            str(prefix) + "_qso_manifest.json",
            system=args.system,
            layout=layout,
            page_capacity=args.page_capacity,
            vector_features_path=args.vector_features,
            train_queries_path=getattr(args, "train_queries", None),
        )
    )
    return written


def main() -> int:
    args = build_parser().parse_args()
    written = emit_artifacts(args)
    print(f"Generated {len(written)} artifact files for {args.system}:")
    for path in written:
        print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
