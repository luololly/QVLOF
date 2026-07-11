import json
import re
from pathlib import Path

import numpy as np
import pandas as pd


def normalize_table_name(name):
    stem = Path(str(name)).stem.lower()
    normalized = re.sub(r"[^a-z0-9_]+", "_", stem).strip("_")
    if not normalized:
        raise ValueError("layout_name must contain at least one letter or digit")
    if normalized[0].isdigit():
        normalized = f"layout_{normalized}"
    return normalized


def table_family(layout_name):
    base = normalize_table_name(layout_name)
    return {
        "base": base,
        "ivfflat": f"{base}_ivfflat",
        "hnsw": f"{base}_hnsw",
    }


def write_pgvector_layout(vectors, ids, layout_name, output_dir="result", source="qso"):
    vectors = np.asarray(vectors)
    ids = np.asarray(ids)
    if vectors.ndim != 2:
        raise ValueError("vectors must be a two-dimensional array")
    if ids.ndim != 1 or len(ids) != len(vectors):
        raise ValueError("ids must be one-dimensional and match vectors")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    family = table_family(layout_name)
    csv_path = output_path / f"{family['base']}.csv"
    manifest_path = output_path / f"{family['base']}.pgvector.json"

    data = np.hstack([ids.reshape(-1, 1), vectors])
    columns = ["id"] + [f"v{i}" for i in range(vectors.shape[1])]
    pd.DataFrame(data, columns=columns).to_csv(csv_path, index=False)

    manifest = {
        "system": "pgvector",
        "source": source,
        "layout_name": family["base"],
        "csv_path": str(csv_path),
        "vector_count": int(len(vectors)),
        "dimension": int(vectors.shape[1]),
        "table_family": family,
        "loader": "index/pg_vector/load_and_index.py",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    manifest["manifest_path"] = str(manifest_path)
    return manifest
