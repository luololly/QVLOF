from __future__ import annotations

import argparse
import csv
from pathlib import Path

from common_block_tools import count_blocks, parse_vector_ids


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate per-window block counts from a dynamic workload CSV.")
    parser.add_argument("--input", required=True, help="CSV containing window_id and vector_ids columns.")
    parser.add_argument("--output", required=True, help="Output CSV path.")
    parser.add_argument("--block-size", required=True, type=int, help="Block size for block counting.")
    args = parser.parse_args()

    source = Path(args.input)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)

    totals: dict[int, int] = {}
    rows: dict[int, int] = {}

    with source.open("r", encoding="utf-8", newline="") as src:
        reader = csv.DictReader(src)
        if not reader.fieldnames or "window_id" not in reader.fieldnames or "vector_ids" not in reader.fieldnames:
            raise ValueError(f"{source} must contain 'window_id' and 'vector_ids' columns.")
        for row in reader:
            window_id = int(row["window_id"])
            block_num = count_blocks(parse_vector_ids(row["vector_ids"]), args.block_size)
            totals[window_id] = totals.get(window_id, 0) + block_num
            rows[window_id] = rows.get(window_id, 0) + 1

    with target.open("w", encoding="utf-8", newline="") as dst:
        writer = csv.DictWriter(dst, fieldnames=["window_id", "rows_in_window", "avg_block", "total_block"])
        writer.writeheader()
        for window_id in sorted(totals):
            total = totals[window_id]
            row_count = rows[window_id]
            writer.writerow(
                {
                    "window_id": window_id,
                    "rows_in_window": row_count,
                    "avg_block": f"{total / row_count:.6f}",
                    "total_block": total,
                }
            )

    print(f"Wrote dynamic block summary to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
