import argparse
from pathlib import Path

import numpy as np

from pgvector_artifact import write_pgvector_layout


DEFAULT_DATASET_DIR = Path(__file__).resolve().parents[1] / "dataset" / "sift" / "1m" / "sift"


def read_fvecs(path):
    data = np.fromfile(path, dtype=np.int32)
    if data.size == 0:
        raise ValueError(f"Empty fvecs file: {path}")
    dimension = int(data[0])
    records = data.reshape(-1, dimension + 1)
    if not np.all(records[:, 0] == dimension):
        raise ValueError(f"Inconsistent vector dimensions in {path}")
    return records[:, 1:].copy().view(np.float32)


def build_qso_layout(base_vectors, train_queries, cluster_count=100):
    from AG import f6_no_A6

    base_vectors = np.asarray(base_vectors, dtype=np.float32).copy()
    train_queries = np.asarray(train_queries, dtype=np.float32)
    permutation = np.asarray(
        f6_no_A6(base_vectors, train_queries, k=cluster_count),
        dtype=np.int64,
    )
    if len(permutation) != len(base_vectors) or len(np.unique(permutation)) != len(base_vectors):
        raise ValueError("QSO must return one permutation entry per base vector")
    return permutation


def emit_sift1m_pgvector_layout(
    dataset_dir=DEFAULT_DATASET_DIR,
    output_dir="results/qso/sift1m",
    layout_name="sift1m_qvlof",
    cluster_count=100,
):
    dataset_dir = Path(dataset_dir)
    base_vectors = read_fvecs(dataset_dir / "sift_base.fvecs")
    train_queries = read_fvecs(dataset_dir / "sift_query.fvecs")
    permutation = build_qso_layout(base_vectors, train_queries, cluster_count=cluster_count)
    return write_pgvector_layout(
        vectors=base_vectors[permutation],
        ids=permutation,
        layout_name=layout_name,
        output_dir=output_dir,
        source="qso/static_layout_main.py",
    )


def parse_args():
    parser = argparse.ArgumentParser(description="Generate a SIFT1M QSO layout for pgvector.")
    parser.add_argument("--dataset-dir", default=str(DEFAULT_DATASET_DIR))
    parser.add_argument("--output-dir", default="results/qso/sift1m")
    parser.add_argument("--layout-name", default="sift1m_qvlof")
    parser.add_argument("--cluster-count", type=int, default=100)
    return parser.parse_args()


def main():
    args = parse_args()
    artifact = emit_sift1m_pgvector_layout(
        dataset_dir=args.dataset_dir,
        output_dir=args.output_dir,
        layout_name=args.layout_name,
        cluster_count=args.cluster_count,
    )
    print(artifact["csv_path"])
    print(artifact["manifest_path"])


if __name__ == "__main__":
    main()
