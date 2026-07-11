import json
import re
from pathlib import Path


INDEX_TYPES = {"base", "ivfflat", "hnsw"}


def normalize_layout_name(layout_path):
    stem = Path(str(layout_path)).stem.lower()
    normalized = re.sub(r"[^a-z0-9_]+", "_", stem).strip("_")
    if not normalized:
        raise ValueError("layout path must contain at least one letter or digit")
    if normalized[0].isdigit():
        normalized = f"layout_{normalized}"
    return normalized


def table_family(layout_path):
    base = normalize_layout_name(layout_path)
    return {
        "base": base,
        "ivfflat": f"{base}_ivfflat",
        "hnsw": f"{base}_hnsw",
    }


def materialize_pgvector_schedule(schedule, index_type="hnsw"):
    if index_type not in INDEX_TYPES:
        raise ValueError(f"index_type must be one of {sorted(INDEX_TYPES)}")

    mapped = []
    for window, layout_path in schedule.get("move", []):
        family = table_family(layout_path)
        mapped.append(
            {
                "window": int(window),
                "layout": family["base"],
                "table": family[index_type],
            }
        )
    return mapped


def write_pgvector_schedule(schedule, output_path, index_type="hnsw"):
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "system": "pgvector",
        "index_type": index_type,
        "switches": materialize_pgvector_schedule(schedule, index_type=index_type),
        "runtime_consumer": "index/pg_vector/run_experiment_ubuntu_final.py",
    }
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload
