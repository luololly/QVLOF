from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from utils.config import RESOURCES_ROOT, RdoArgs, RdoDatasetConfig, load_dataset_config, load_run_params


@dataclass(frozen=True)
class RdoResourceBundle:
    dataset: RdoDatasetConfig
    params: RdoArgs
    resources_root: Path


def load_resource_bundle(
    dataset_config: str,
    run_params: str,
    resources_root: str | Path = RESOURCES_ROOT,
) -> RdoResourceBundle:
    root = Path(resources_root)
    dataset = load_dataset_config(dataset_config, root)
    params = load_run_params(run_params, root)
    if dataset.dataset_group != params.dataset_group:
        raise ValueError(
            "Dataset config and run params target different dataset groups: "
            f"{dataset.dataset_group} != {params.dataset_group}"
        )
    return RdoResourceBundle(dataset=dataset, params=params, resources_root=root)
