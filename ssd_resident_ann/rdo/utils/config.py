from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


RDO_ROOT = Path(__file__).resolve().parents[1]
RESOURCES_ROOT = RDO_ROOT / "resources"


@dataclass(frozen=True)
class RdoDatasetConfig:
    dataset_group: str
    dataset: str
    vector_count: int
    dimension: int
    distance: str
    data_type: str
    base_vectors: str
    query_vectors: str
    ground_truth: str
    systems: list[str]


@dataclass(frozen=True)
class RdoArgs:
    dataset_group: str
    policy: str
    window_size: int
    hot_vector_topk: int
    alpha: float
    switch_threshold: float
    candidate_labels: list[str]
    target_systems: list[str]


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"RDO resource file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_dataset_config(name: str, resources_root: str | Path = RESOURCES_ROOT) -> RdoDatasetConfig:
    root = Path(resources_root)
    payload = _read_json(root / "config" / f"{name}.json")
    return RdoDatasetConfig(
        dataset_group=str(payload["dataset_group"]),
        dataset=str(payload["dataset"]),
        vector_count=int(payload["vector_count"]),
        dimension=int(payload["dimension"]),
        distance=str(payload["distance"]),
        data_type=str(payload["data_type"]),
        base_vectors=str(payload.get("base_vectors", "")),
        query_vectors=str(payload.get("query_vectors", "")),
        ground_truth=str(payload.get("ground_truth", "")),
        systems=[str(system) for system in payload.get("systems", [])],
    )


def load_run_params(name: str, resources_root: str | Path = RESOURCES_ROOT) -> RdoArgs:
    root = Path(resources_root)
    payload = _read_json(root / "params" / f"{name}.json")
    return RdoArgs(
        dataset_group=str(payload["dataset_group"]),
        policy=str(payload["policy"]),
        window_size=int(payload["window_size"]),
        hot_vector_topk=int(payload["hot_vector_topk"]),
        alpha=float(payload["alpha"]),
        switch_threshold=float(payload["switch_threshold"]),
        candidate_labels=[str(label) for label in payload.get("candidate_labels", [])],
        target_systems=[str(system) for system in payload.get("target_systems", [])],
    )
