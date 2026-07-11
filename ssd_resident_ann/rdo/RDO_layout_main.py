#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
QSO_DIR = ROOT_DIR / "qso"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(QSO_DIR) not in sys.path:
    sys.path.insert(0, str(QSO_DIR))

from offline.layout_generator import (
    apply_materialized_artifact_hints,
    generate_layout_families,
    generate_partial_layout_families,
    generate_qso_layout_families,
)
from offline.qso_materializer import materialize_qso_window_artifacts
from offline.windowing import build_windows_from_queries
from utils.io_utils import write_json
from vector_io import read_feature_matrix


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate disk-resident RDO layout-family manifests.")
    parser.add_argument(
        "--train-queries",
        help="Held-out training queries / workload query stream as .npy/.csv/.fvecs/.ivecs.",
    )
    parser.add_argument(
        "--base-vectors",
        help="Optional base vectors used to derive hot_vector_ids from query windows.",
    )
    parser.add_argument("--window-size", required=True, type=int)
    parser.add_argument("--dataset-group", required=True)
    parser.add_argument("--output", required=True, help="Output JSON manifest path.")
    parser.add_argument("--workload-label-prefix", default="window")
    parser.add_argument("--hot-vector-topk", type=int, default=32)
    parser.add_argument("--hot-neighbor-k", type=int, default=8)
    parser.add_argument(
        "--layout-mode",
        choices=["proxy", "partial"],
        default="proxy",
        help="Choose between simple proxy candidates or representative-query partial-layout candidates.",
    )
    parser.add_argument("--partial-page-capacity", type=int, help="Required when --layout-mode partial.")
    parser.add_argument("--partial-beta", type=float, default=0.5)
    parser.add_argument("--pool-epsilon", type=float, default=0.08)
    parser.add_argument("--pool-sample-size", type=int, default=32)
    parser.add_argument(
        "--materialize-qso-system",
        choices=["pageann", "spann", "starling", "margo", "gorgeous"],
        help="Optionally materialize per-window QSO artifacts for one target system.",
    )
    parser.add_argument("--qso-num-vectors", type=int, help="Required when materializing QSO artifacts.")
    parser.add_argument("--qso-page-capacity", type=int, help="Required when materializing QSO artifacts.")
    parser.add_argument("--qso-output-root", help="Required when materializing QSO artifacts.")
    parser.add_argument("--qso-vector-features", help="Optional feature matrix passed to QSO.")
    parser.add_argument("--qso-lgpf-k", type=int, default=3)
    parser.add_argument("--qso-transform-t", type=float, default=0.3)
    parser.add_argument("--qso-posting-membership", help="SPANN only: posting membership CSV.")
    parser.add_argument(
        "--qso-candidate-spec",
        action="append",
        help=(
            "Optional repeated spec formatted as "
            "label:lgpf_k:transform_t. "
            "When provided with --materialize-qso-system, layout families are generated "
            "from per-window QSO candidates instead of heuristic base/hot/balanced."
        ),
    )
    return parser


def _load_workload_windows(args: argparse.Namespace):
    train_queries = getattr(args, "train_queries", None)

    if not train_queries:
        raise ValueError("--train-queries is required.")

    queries = read_feature_matrix(train_queries)
    base_vectors = read_feature_matrix(args.base_vectors) if args.base_vectors else None
    return build_windows_from_queries(
        query_matrix=queries,
        window_size=args.window_size,
        dataset_group=args.dataset_group,
        workload_label_prefix=args.workload_label_prefix,
        hot_vector_topk=args.hot_vector_topk,
        base_vectors=base_vectors,
        hot_neighbor_k=args.hot_neighbor_k,
    )


def _parse_qso_candidate_specs(raw_specs: list[str] | None) -> list[dict]:
    if not raw_specs:
        return []
    specs: list[dict] = []
    for raw in raw_specs:
        parts = raw.split(":")
        if len(parts) != 3:
            raise ValueError(
                f"Invalid --qso-candidate-spec '{raw}'. Expected label:lgpf_k:transform_t."
            )
        label, lgpf_k, transform_t = parts
        specs.append(
            {
                "layout_label": label,
                "lgpf_k": int(lgpf_k),
                "transform_t": float(transform_t),
            }
        )
    return specs


def main() -> int:
    args = build_parser().parse_args()
    windows = _load_workload_windows(args)
    if args.layout_mode == "partial":
        if not args.base_vectors:
            raise ValueError("--base-vectors is required when --layout-mode partial.")
        if args.partial_page_capacity is None:
            raise ValueError("--partial-page-capacity is required when --layout-mode partial.")
        base_vectors = read_feature_matrix(args.base_vectors)
        families = generate_partial_layout_families(
            windows=windows,
            base_vectors=base_vectors,
            page_capacity=args.partial_page_capacity,
            beta=args.partial_beta,
            epsilon=args.pool_epsilon,
            sample_size=args.pool_sample_size,
            random_state=0,
        )
    else:
        families = generate_layout_families(windows)
    qso_window_artifacts = []
    qso_candidate_specs = _parse_qso_candidate_specs(args.qso_candidate_spec)
    if args.materialize_qso_system:
        if args.qso_num_vectors is None or args.qso_page_capacity is None or not args.qso_output_root:
            raise ValueError(
                "--qso-num-vectors, --qso-page-capacity, and --qso-output-root are required "
                "when --materialize-qso-system is set."
            )
        if args.materialize_qso_system == "spann" and not args.qso_posting_membership:
            raise ValueError("--qso-posting-membership is required when materializing SPANN artifacts.")
        if qso_candidate_specs:
            families = generate_qso_layout_families(
                windows=windows,
                system=args.materialize_qso_system,
                num_vectors=args.qso_num_vectors,
                page_capacity=args.qso_page_capacity,
                output_root=args.qso_output_root,
                candidate_specs=qso_candidate_specs,
                vector_features_path=args.qso_vector_features,
                posting_membership=args.qso_posting_membership,
            )
        else:
            qso_window_artifacts = materialize_qso_window_artifacts(
                windows=windows,
                system=args.materialize_qso_system,
                num_vectors=args.qso_num_vectors,
                page_capacity=args.qso_page_capacity,
                output_root=args.qso_output_root,
                vector_features_path=args.qso_vector_features,
                lgpf_k=args.qso_lgpf_k,
                transform_t=args.qso_transform_t,
                posting_membership=args.qso_posting_membership,
            )
            families = apply_materialized_artifact_hints(families, qso_window_artifacts)
    payload = {
        "windows": [window.to_dict() for window in windows],
        "layout_families": [family.to_dict() for family in families],
        "qso_window_artifacts": [artifact.to_dict() for artifact in qso_window_artifacts],
    }
    output = write_json(args.output, payload)
    print(f"Wrote layout-family manifest to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
