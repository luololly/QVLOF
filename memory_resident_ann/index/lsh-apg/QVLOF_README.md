# QSO/RDO Adaptation Note for LSH-APG

## Public Upstream Source

The local code layout mirrors:

`https://github.com/Jacyhust/LSH-APG`

## Verified Local Anchors

This note is grounded in the local LSH-APG code and wrappers:

- `cppCode/LSH-APG/src/main.cpp`
- `cppCode/LSH-APG-window_batch/src/main.cpp`
- `../../scripts/static_memory_sh/apg_lsh.sh`
- `../../scripts/dynamic_memory_sh/dynamic_query_LSH_APG_benchmark.sh`

The most important verified local anchors are:

- `divGraph`
- `fastGraph`
- `Preprocess`
- `graphSearch(...)`
- the persistent `./indexes/` folder

## What QSO Changes in LSH-APG

LSH-APG is graph-based, but in this repository the practical build boundary is still the dataset alias and the data file consumed by:

```cpp
Preprocess prep(data_fold + datasetName + ".data", ...);
```

QSO therefore binds before graph construction by changing the underlying base data file or dataset alias that `Preprocess` loads.

The search path through `graphSearch(...)` should remain unchanged.

## Exact Code Boundary

The local static and dynamic mains both:

1. choose `datasetName`,
2. load `datasetName.data`,
3. build or reuse `path + "_divGraph"` under `./indexes/`,
4. run search over `divGraph` or `fastGraph`.

So the clean QSO contract is a dataset file that already reflects the desired reordered vector layout.

## Static QSO Binding

The static wrapper `../../scripts/static_memory_sh/apg_lsh.sh` already iterates over multiple dataset aliases such as reordered QSO outputs.

That means the practical static path is:

1. QSO emits a reordered dataset file,
2. LSH-APG builds `divGraph` on that file,
3. the existing `graphSearch(...)` runtime is reused.

## Dynamic RDO Binding

The dynamic wrapper `../../scripts/dynamic_memory_sh/dynamic_query_LSH_APG_benchmark.sh` already establishes the window-level integration shape:

1. keep one `work_dir` per dataset / layout family,
2. optionally reuse built indexes via `isbuilt`,
3. run window-batch evaluation through `LSH-APG-window_batch`,
4. keep per-window outputs separated by workload stream.

RDO therefore binds as a set of window-specific LSH-APG index folders rather than as one mutable index.

## Current Boundary

What is already concrete locally:

- static and dynamic wrappers,
- an explicit persistent `indexes/` boundary suitable for multi-layout evaluation.

The shared RDO layout families map to LSH-APG-ready dataset aliases and persistent index directories.
