from __future__ import annotations

import argparse
from pathlib import Path

from common_block_tools import summarize_access_csv


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Write row-level block counts for a disk-side workload CSV without ef/k filtering."
    )
    parser.add_argument("--input", required=True, help="CSV containing a vector_ids column.")
    parser.add_argument("--output", required=True, help="Output CSV path.")
    parser.add_argument("--block-size", required=True, type=int, help="Block size for block counting.")
    args = parser.parse_args()

    result = summarize_access_csv(args.input, args.output, args.block_size)
    print(f"Wrote row-level block counts to {Path(result)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
