from __future__ import annotations

import csv
from pathlib import Path

import numpy as np


def read_vecs(path: str | Path) -> np.ndarray:
    source = Path(path)
    data = np.fromfile(source, dtype="int32")
    if data.size == 0:
        raise ValueError(f"Empty vec file: {source}")
    dim = int(data[0])
    vectors = data.reshape(-1, dim + 1)[:, 1:].copy()
    if source.suffix.lower() == ".fvecs":
        vectors = vectors.view("float32")
    return vectors


def read_ivecs(path: str | Path) -> np.ndarray:
    source = Path(path)
    data = np.fromfile(source, dtype="int32")
    if data.size == 0:
        raise ValueError(f"Empty ivec file: {source}")
    dim = int(data[0])
    return data.reshape(-1, dim + 1)[:, 1:].copy()


def read_feature_matrix(path: str | Path) -> np.ndarray:
    source = Path(path)
    suffix = source.suffix.lower()
    if suffix == ".npy":
        matrix = np.load(source)
    elif suffix == ".csv":
        with source.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            rows = [[float(v) for v in row] for row in reader]
        matrix = np.asarray(rows, dtype=np.float32)
    elif suffix in {".fvecs", ".ivecs"}:
        matrix = read_vecs(source) if suffix == ".fvecs" else read_ivecs(source)
    else:
        raise ValueError(
            f"Unsupported vector feature format for {source}. "
            "Expected .npy, .csv, .fvecs, or .ivecs."
        )
    if matrix.ndim != 2:
        raise ValueError(f"Feature matrix must be 2D, got shape {matrix.shape}.")
    return matrix.astype(np.float32, copy=False)
