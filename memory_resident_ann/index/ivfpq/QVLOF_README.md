# QSO/RDO Adaptation Note for IVF-PQ

## Public Upstream Source

`https://github.com/facebookresearch/faiss`

## Verified Local Anchors

This note is grounded in the local IVF-PQ evaluation path:

- `../../scripts/static_memory_sh/ivfpq_ids.sh`
- `../../scripts/dynamic_memory_sh/dynamic_query_ivfpq_benchmark.sh`
- `../hnsw/demos/replace_dynamic_cpp/ivfpq_dynamic_window_batch.cpp`
- `tutorial/cpp/3-IVFPQ.cpp`
- FAISS `IndexIVFPQ` code under `faiss/`

The most important verified local anchors are:

- `faiss::IndexIVFPQ`
- `nlist`
- `m`
- `nbits`
- `nprobe`
- `refine_r`

## What QSO Changes in IVF-PQ

In this repository, IVF-PQ is evaluated through a CSV-to-FAISS build path. QSO changes the order of the base vectors before training / add.

The runtime IVF-PQ search path should remain unchanged.

## Exact Code Boundary

The local dynamic binary builds IVF-PQ once and then evaluates per-window performance with variable `nprobe`.

The relevant constructor boundary is:

```cpp
auto* ivfpq = new faiss::IndexIVFPQ(quantizer, d, nlist, pq_m, pq_nbits, mt);
```

So the QSO binding belongs before that object is trained and populated, by changing the incoming base data order in `--base_csv`.

## Static QSO Binding

The static script `../../scripts/static_memory_sh/ivfpq_ids.sh` already uses multiple reordered base CSV layouts and runs the IVF-PQ harness over them.

This is the practical static contract:

1. QSO emits reordered CSVs,
2. IVF-PQ trains and adds on that order,
3. search remains ordinary IVF-PQ with configurable `nprobe`.

## Dynamic RDO Binding

The local dynamic script `../../scripts/dynamic_memory_sh/dynamic_query_ivfpq_benchmark.sh` already evaluates window-level behavior over:

- multiple reordered base layouts,
- multiple workload streams,
- one dynamic binary with:
  - `--window_size`
  - `--dynamic_k`
  - `--nprobe_list`
  - `--refine_r`
  - `--per_window_csv_path`

This means RDO binds at the layout-family level exactly as it does for HNSW:

1. candidate reordered layouts are built offline,
2. the dynamic binary measures per-window search behavior,
3. an external controller can choose the active layout by window.

## Current Boundary

What is already concrete locally:

- static layout replacement via reordered CSVs,
- dedicated dynamic window evaluation for IVF-PQ.

The generic `../../rdo/` output maps to IVF-PQ layout materialization through the reordered-CSV and window-batch adapter boundary.
