from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable


def count_blocks(indices: Iterable[int], block_size: int) -> int:
    if block_size <= 0:
        raise ValueError("block_size must be positive")
    blocks = {int(idx) // block_size for idx in indices}
    return len(blocks)


def parse_vector_ids(raw: str) -> list[int]:
    text = raw.strip()
    if not text:
        return []
    if text[0] == "[" and text[-1] == "]":
        text = text[1:-1].strip()
    if not text:
        return []
    parts = [part.strip() for part in text.replace(",", " ").split()]
    return [int(part) for part in parts if part]


def summarize_access_csv(input_csv: str | Path, output_csv: str | Path, block_size: int) -> Path:
    source = Path(input_csv)
    target = Path(output_csv)
    target.parent.mkdir(parents=True, exist_ok=True)

    with source.open("r", encoding="utf-8", newline="") as src, target.open(
        "w", encoding="utf-8", newline=""
    ) as dst:
        reader = csv.DictReader(src)
        if not reader.fieldnames or "vector_ids" not in reader.fieldnames:
            raise ValueError(f"{source} must contain a 'vector_ids' column.")

        writer = csv.DictWriter(dst, fieldnames=["row_id", "block_num"])
        writer.writeheader()

        for row_id, row in enumerate(reader):
            vector_ids = parse_vector_ids(row["vector_ids"])
            writer.writerow({"row_id": row_id, "block_num": count_blocks(vector_ids, block_size)})

    return target
