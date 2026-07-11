# QSO/RDO Adaptation Note for HNSW

## Public Upstream Sources

Algorithm reference:

- `https://github.com/nmslib/hnswlib`

Local build/evaluation harness base:

- `https://github.com/facebookresearch/faiss`

## Verified Local Anchors

This note is grounded in the local HNSW evaluation path:

- `demos/replace_cpp/hnsw_query_csv_gt_universal_nohdf5_no_nq_with_ids.cpp`
- `demos/replace_dynamic_cpp/hnsw_dynamic_window_batch.cpp`
- `demos/demo_sift1M.cpp`
- `../../scripts/static_memory_sh/hnsw_ids.sh`
- `../../scripts/dynamic_memory_sh/dynamic_query_hnsw_benchmark.sh`

The most important verified local HNSW anchors are:

- `faiss::IndexHNSWFlat`
- `hnsw->hnsw.efConstruction`
- per-query ids dump through `ids_csv_path`
- per-window evaluation through `per_window_csv_path`

## What QSO Changes in HNSW

In this repository, HNSW is integrated through a FAISS-based CSV benchmark harness. The static layout unit is again the row order of the base CSV.

QSO should therefore bind before the HNSW build:

1. reorder the base vectors,
2. rebuild `IndexHNSWFlat`,
3. keep HNSW search unchanged.

## Exact Code Boundary

The local HNSW build path in `hnsw_query_csv_gt_universal_nohdf5_no_nq_with_ids.cpp` and the dynamic counterpart is:

1. load `--base_csv`,
2. construct `faiss::IndexHNSWFlat(d, hnsw_M, mt)`,
3. set `hnsw->hnsw.efConstruction = hnsw_efC`,
4. add vectors in CSV order,
5. search with HNSW `efSearch` at evaluation time.

That makes `--base_csv` the correct QSO injection point.

## Static QSO Binding

The local static script `../../scripts/static_memory_sh/hnsw_ids.sh` already runs:

- `base_vectors.csv`
- `f1_AG4` / `f1_AG5`
- `f2_zorder_sorted.csv`
- `f3_hilbert_sorted.csv`
- `f4_idistance_sorted.csv`

through the selected HNSW binary.

So the static contract is:

1. QSO emits reordered CSV layouts,
2. HNSW rebuilds on each layout,
3. search remains the native HNSW path.

## Dynamic RDO Binding

The local dynamic script `../../scripts/dynamic_memory_sh/dynamic_query_hnsw_benchmark.sh` binds RDO at the layout-family level:

1. one reordered base CSV per layout candidate,
2. one workload query CSV per window stream,
3. `hnsw_dynamic_window_batch.cpp` computes per-window recall / latency,
4. a higher-level controller can choose which reordered layout to activate for each window.

The runtime contract is explicit in the dynamic binary arguments:

- `--dynamic 1`
- `--window_size`
- `--dynamic_k`
- `--per_window_csv_path`

This is the concrete HNSW evaluation boundary consumed by the `../../rdo/RDO_*` layout-family workflow.

## Current Boundary

What is already concrete locally:

- static QSO through reordered CSVs,
- dynamic window-level evaluation through a dedicated HNSW batch binary.

What remains separate:

- the shared RDO controller produces generic candidate schedules,
- the HNSW harness still expects concrete reordered CSV files prepared outside that controller.
