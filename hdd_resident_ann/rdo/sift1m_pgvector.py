import argparse
import json
from pathlib import Path

import numpy as np

from pgvector_adapter import INDEX_TYPES, table_family


DEFAULT_QUERY_PATH = Path(__file__).resolve().parents[1] / "dataset" / "sift" / "1m" / "sift" / "sift_query.fvecs"


def read_fvecs(path):
    data = np.fromfile(path, dtype=np.int32)
    if data.size == 0:
        raise ValueError(f"Empty fvecs file: {path}")
    dimension = int(data[0])
    records = data.reshape(-1, dimension + 1)
    if not np.all(records[:, 0] == dimension):
        raise ValueError(f"Inconsistent vector dimensions in {path}")
    return records[:, 1:].copy().view(np.float32)


def split_query_windows(query_vectors, window_size):
    if window_size <= 0:
        raise ValueError("window_size must be positive")
    query_vectors = np.asarray(query_vectors, dtype=np.float32)
    return [
        {
            "window": window_id,
            "query_start": start,
            "query_end": min(start + window_size, len(query_vectors)),
            "query_count": min(window_size, len(query_vectors) - start),
        }
        for window_id, start in enumerate(range(0, len(query_vectors), window_size))
    ]


def build_window_plan(windows, layout_prefix="sift1m_qvlof", index_type="hnsw"):
    if index_type not in INDEX_TYPES:
        raise ValueError(f"index_type must be one of {sorted(INDEX_TYPES)}")
    switches = []
    for window in windows:
        family = table_family(f"{layout_prefix}_window_{window['window']}")
        switches.append(
            {
                "window": int(window["window"]),
                "layout": family["base"],
                "table": family[index_type],
            }
        )
    return {
        "system": "pgvector",
        "dataset": "sift1m",
        "index_type": index_type,
        "windows": windows,
        "switches": switches,
        "runtime_consumer": "index/pg_vector/run_experiment_ubuntu_final.py",
    }


def write_window_plan(query_path, output_path, window_size=200, layout_prefix="sift1m_qvlof", index_type="hnsw"):
    query_vectors = read_fvecs(query_path)
    plan = build_window_plan(
        split_query_windows(query_vectors, window_size),
        layout_prefix=layout_prefix,
        index_type=index_type,
    )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return plan


def parse_args():
    parser = argparse.ArgumentParser(description="Generate a SIFT1M RDO table-family plan for pgvector.")
    parser.add_argument("--query-path", default=str(DEFAULT_QUERY_PATH))
    parser.add_argument("--output", default="results/rdo/sift1m_pgvector_plan.json")
    parser.add_argument("--window-size", type=int, default=200)
    parser.add_argument("--layout-prefix", default="sift1m_qvlof")
    parser.add_argument("--index-type", choices=sorted(INDEX_TYPES), default="hnsw")
    return parser.parse_args()


def main():
    args = parse_args()
    plan = write_window_plan(
        query_path=args.query_path,
        output_path=args.output,
        window_size=args.window_size,
        layout_prefix=args.layout_prefix,
        index_type=args.index_type,
    )
    print(args.output)
    print(f"windows={len(plan['windows'])}")


if __name__ == "__main__":
    main()
