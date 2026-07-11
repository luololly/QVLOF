from __future__ import annotations

import json
import struct
from pathlib import Path

from layout_core import StaticLayout
from spann_layout import SpannPostingLayout


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_partition_bin(path: str | Path, layout: StaticLayout, page_capacity: int) -> Path:
    output = Path(path)
    _ensure_parent(output)
    with output.open("wb") as f:
        f.write(struct.pack("<Q", page_capacity))
        f.write(struct.pack("<Q", len(layout.pages)))
        f.write(struct.pack("<Q", len(layout.id_to_page)))
        for page in layout.pages:
            f.write(struct.pack("<I", len(page)))
            if page:
                f.write(struct.pack("<" + "I" * len(page), *page))
        if layout.id_to_page:
            f.write(struct.pack("<" + "I" * len(layout.id_to_page), *layout.id_to_page))
    return output


def write_pageann_map(path: str | Path, layout: StaticLayout) -> Path:
    output = Path(path)
    _ensure_parent(output)
    with output.open("wb") as f:
        f.write(struct.pack("<i", len(layout.permutation)))
        f.write(struct.pack("<i", 1))
        if layout.permutation:
            f.write(struct.pack("<" + "I" * len(layout.permutation), *layout.permutation))
    return output


def write_pageann_pages(path: str | Path, layout: StaticLayout, page_capacity: int) -> Path:
    output = Path(path)
    _ensure_parent(output)
    with output.open("wb") as f:
        f.write(struct.pack("<Q", len(layout.pages)))
        f.write(struct.pack("<Q", page_capacity))
        for page in layout.pages:
            f.write(struct.pack("<I", len(page)))
            if page:
                f.write(struct.pack("<" + "I" * len(page), *page))
        f.write(struct.pack("<Q", len(layout.id_to_page)))
        if layout.id_to_page:
            f.write(struct.pack("<" + "I" * len(layout.id_to_page), *layout.id_to_page))
    return output


def write_spann_bucket_assignment(path: str | Path, layout: StaticLayout) -> Path:
    output = Path(path)
    _ensure_parent(output)
    with output.open("wb") as f:
        f.write(struct.pack("<Q", len(layout.id_to_page)))
        f.write(struct.pack("<Q", len(layout.pages)))
        if layout.id_to_page:
            f.write(struct.pack("<" + "I" * len(layout.id_to_page), *layout.id_to_page))
    return output


def write_spann_posting_pages(path: str | Path, layout: StaticLayout) -> Path:
    output = Path(path)
    _ensure_parent(output)
    with output.open("wb") as f:
        f.write(struct.pack("<Q", len(layout.pages)))
        for page in layout.pages:
            f.write(struct.pack("<I", len(page)))
            if page:
                f.write(struct.pack("<" + "I" * len(page), *page))
    return output


def write_spann_posting_order(path: str | Path, layout: SpannPostingLayout) -> Path:
    output = Path(path)
    _ensure_parent(output)
    with output.open("wb") as f:
        f.write(struct.pack("<Q", len(layout.posting_order)))
        if layout.posting_order:
            f.write(struct.pack("<" + "I" * len(layout.posting_order), *layout.posting_order))
        for score in layout.posting_scores:
            f.write(struct.pack("<d", float(score)))
    return output


def write_spann_vector_to_posting(path: str | Path, layout: SpannPostingLayout) -> Path:
    output = Path(path)
    _ensure_parent(output)
    with output.open("wb") as f:
        f.write(struct.pack("<Q", len(layout.vector_to_posting)))
        if layout.vector_to_posting:
            f.write(struct.pack("<" + "I" * len(layout.vector_to_posting), *layout.vector_to_posting))
    return output


def write_spann_posting_pages_v2(path: str | Path, layout: SpannPostingLayout) -> Path:
    output = Path(path)
    _ensure_parent(output)
    with output.open("wb") as f:
        f.write(struct.pack("<Q", len(layout.posting_to_vectors)))
        f.write(struct.pack("<Q", layout.page_capacity))
        for vector_ids in layout.posting_to_vectors:
            f.write(struct.pack("<I", len(vector_ids)))
            if vector_ids:
                f.write(struct.pack("<" + "I" * len(vector_ids), *vector_ids))
    return output


def write_manifest(
    path: str | Path,
    system: str,
    layout: StaticLayout,
    page_capacity: int,
    vector_features_path: str | None,
    train_queries_path: str | None = None,
) -> Path:
    output = Path(path)
    _ensure_parent(output)
    payload = {
        "system": system,
        "num_vectors": len(layout.id_to_page),
        "page_capacity": page_capacity,
        "page_count": len(layout.pages),
        "train_queries": train_queries_path,
        "vector_features": vector_features_path,
        "permutation_prefix": layout.permutation[: min(32, len(layout.permutation))],
        "top_access_scores": sorted(
            (
                {"id": idx, "score": score}
                for idx, score in enumerate(layout.access_score)
                if score > 0
            ),
            key=lambda item: (-item["score"], item["id"]),
        )[:32],
    }
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output
