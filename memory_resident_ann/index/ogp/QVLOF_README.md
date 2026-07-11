# QSO/RDO Adaptation Note for OGP

## Public Upstream Source

`https://github.com/larsgottesbueren/gp-ann`

## Verified Local Anchors

This note is grounded in the local OGP code:

- `README.md`
- `experiments.py`
- `partition.cpp`
- `run_query_attribution.cpp`
- `small_scale_queries.cpp`
- `data/csv2Bin_noId.py`
- `data/csv2Bin_withId.py`
- `../../scripts/dynamic_memory_sh/dynamic_query_OGP_benchmark.sh`

The most important verified local anchors are:

- `Partition`
- `QueryAttribution`
- `SmallScaleQueries`
- `WriteClusters(...)`
- `ReadClusters(...)`

## What QSO Changes in OGP

OGP is already a partition-and-routing baseline, so QSO should not be described as changing its online search loop.

The correct binding is:

- QSO changes the input point order or preprocessing before partitioning,
- OGP builds its partition / routing artifacts on top of that reordered point set,
- query attribution and shard search remain unchanged.

## Exact Code Boundary

The builder entrypoint in `partition.cpp` is:

1. read point file,
2. compute a partition or overlapping partition,
3. write clusters to `<prefix>.k=<...>.<method>[.o=...]`.

The query path in `run_query_attribution.cpp` is:

1. load points and queries,
2. read clusters from the partition file,
3. build routing configs,
4. run shard searches,
5. serialize results.

That makes the partition file the clean artifact boundary.

## Static QSO Binding

The most faithful OGP+QSO path is:

1. convert a QSO-reordered CSV to `.fbin` through `data/csv2Bin_*.py`,
2. run `Partition` on that reordered point set,
3. run `QueryAttribution` or `SmallScaleQueries` on the resulting partition artifact,
4. keep the OGP query path unchanged.

## Dynamic RDO Binding

The local wrapper `../../scripts/dynamic_memory_sh/dynamic_query_OGP_benchmark.sh` already shows the dynamic shape:

1. build one partition artifact,
2. run one evaluation for `q250`,
3. run one evaluation for `q500`,
4. store outputs separately.

For a fuller RDO integration, the correct extension is:

1. generate multiple window-specific partition files,
2. build paired query-attribution / shard-search artifacts for each window,
3. let the controller switch the active partition family by window.

This is more naturally aligned with OGP than with the CSV-rebuild methods because OGP already externalizes partitions as first-class artifacts.

## Current Boundary

What is already concrete locally:

- point-file to partition-file build,
- explicit query attribution and small-scale query binaries,
- a dynamic wrapper for multiple workload streams.

The `../../rdo/` candidate layouts map to OGP partition artifacts and workload-window switch schedules through the partition-family boundary.
