# QSO/RDO Adaptation Note for MIRAGE

## Public Upstream Source

The local code mirrors:

`https://github.com/dsg-uwaterloo/mirage`

## Verified Local Anchors

This note is grounded in the local MIRAGE build/evaluation path:

- `README.md`
- `demos/demo_mirage.cpp`
- `../hnsw/demos/demo_sift1M.cpp`
- `../hnsw/demos/replace_dynamic_cpp/mirage_dyanmic_window_batch.cpp`
- `../../scripts/static_memory_sh/mirage_ids.sh`
- `../../scripts/dynamic_memory_sh/dynamic_query_mirage_benchmark.sh`

The most important verified local anchors are:

- `faiss::IndexMirage`
- `index.mirage.S`
- `index.mirage.R`
- `index.mirage.iter`

## What QSO Changes in MIRAGE

As integrated here, MIRAGE behaves like the other FAISS-based memory-resident baselines: QSO should change the base-vector order before the MIRAGE index is built.

The search executor should remain unchanged.

## Exact Code Boundary

The local MIRAGE demos create:

```cpp
faiss::IndexMirage index(d);
```

and then add base vectors to that object.

The local CSV harnesses also consume `--base_csv` and `--query_csv`, so the static QSO boundary changes the base CSV order before rebuilding the MIRAGE index.

## Static QSO Binding

The static script `../../scripts/static_memory_sh/mirage_ids.sh` already runs the MIRAGE binary over:

- baseline layout,
- QSO layout,
- z-order / hilbert / idistance layouts.

So the static contract is already concrete:

1. QSO emits reordered CSVs,
2. MIRAGE rebuilds on each layout,
3. search remains native MIRAGE search.

## Dynamic RDO Binding

The local dynamic script `../../scripts/dynamic_memory_sh/dynamic_query_mirage_benchmark.sh` and the dynamic MIRAGE binary establish the RDO boundary:

- `--dynamic 1`
- `--window_size`
- `--dynamic_k`
- `--per_window_csv_path`

This means:

1. prepare multiple reordered base layouts offline,
2. evaluate window-level behavior for each layout family,
3. let a controller choose the active layout by workload window.

## Current Boundary

What is already concrete locally:

- static QSO through reordered base CSVs,
- dynamic window-level MIRAGE evaluation.

The shared `../../rdo/` output maps to MIRAGE-ready layout families through the reordered-CSV window adapter.
