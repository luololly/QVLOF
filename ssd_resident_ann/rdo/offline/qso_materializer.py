from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import numpy as np

from common.rdo_types import QsoWindowArtifact, WorkloadWindow
from static_layout_main import emit_artifacts


def _write_window_train_queries(path: Path, query_matrix: np.ndarray) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(path, np.asarray(query_matrix, dtype=np.float32))
    return path


def materialize_qso_window_artifacts(
    windows: list[WorkloadWindow],
    system: str,
    num_vectors: int,
    page_capacity: int,
    output_root: str | Path,
    vector_features_path: str | None = None,
    lgpf_k: int = 3,
    transform_t: float = 0.3,
    posting_membership: str | None = None,
) -> list[QsoWindowArtifact]:
    root = Path(output_root)
    artifacts: list[QsoWindowArtifact] = []

    for window in windows:
        output_dir = root / f"window_{window.window_id}"
        prefix = f"window_{window.window_id}"
        if window.query_matrix.ndim != 2 or window.query_matrix.shape[1] <= 0:
            raise ValueError(f"Window {window.window_id} requires a usable query_matrix.")

        train_queries = str(
            _write_window_train_queries(
                output_dir / f"window_{window.window_id}_train_queries.npy",
                window.query_matrix,
            )
        )
        written = emit_artifacts(
            Namespace(
                system=system,
                train_queries=train_queries,
                num_vectors=num_vectors,
                page_capacity=page_capacity,
                vector_features=vector_features_path,
                output_dir=str(output_dir),
                prefix=prefix,
                lgpf_k=lgpf_k,
                transform_t=transform_t,
                posting_membership=posting_membership,
            )
        )
        artifacts.append(
            QsoWindowArtifact(
                window_id=window.window_id,
                system=system,
                output_dir=str(output_dir),
                prefix=prefix,
                artifact_prefix=str(output_dir / prefix),
                train_queries=train_queries,
                files=[str(path) for path in written],
            )
        )

    return artifacts
