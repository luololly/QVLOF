# QSO for Disk-Resident ANN

This directory contains:

- runnable disk-resident QSO method code,
- baseline-specific static artifact generation.

The implementation is now split into:

- root-level entry and integration scripts
- an internal `algorithms/` subdirectory that holds the QSO algorithm stack

## Executable Entry Points

The directory now has two executable entry points:

- `static_layout_main.py`

Supporting modules:

- `vector_io.py`
- `methods.py`
- `layout_core.py`
- `artifact_writer.py`
- `spann_layout.py`

Algorithm layer:

- `algorithms/qso_pipeline.py`
- `algorithms/cov.py`
- `algorithms/lgpf.py`
- `algorithms/lgpf_q2d.py`
- `algorithms/equal_size_kmeans.py`

`static_layout_main.py` is the runnable QSO pipeline for disk-resident static artifacts. It consumes:

- base vector features,
- held-out training queries,
- one target disk-resident system,
- for SPANN only, a native posting-membership description,

and emits the corresponding static artifact family.

The current dependency direction is:

```text
static_layout_main.py
  -> layout_core.py / spann_layout.py / methods.py
  -> algorithms/*
  -> artifact_writer.py
```

## Purpose

The QSO implementation maps query-driven vector ordering into the artifact contracts of five SSD-resident ANN systems.

## QSO Role in the Disk-Resident Setting

In the disk-resident setting, QSO does not alter the online ANN traversal rule. Instead, it changes the physical unit order that will later be consumed by an existing builder, relayout utility, or disk-layout materializer.

That means QSO is always bound before the final on-disk artifact is emitted. The search executor remains the downstream consumer of a new physical layout, not a new search algorithm.

## Unified QSO Input Contract

Across the five baselines, QSO consumes three kinds of information:

1. **base vectors**
   - the original vector collection from which physical layout units are formed
2. **held-out training queries**
   - the workload-side signal used to score how base vectors should become more colocated under the QSO objective
3. **layout-unit definition**
   - the unit boundary imposed by the baseline builder:
     - page
     - posting page
     - partition
     - graph-aware sector group

For `SPANN`, the layout-unit definition is not derivable from vector features alone. QSO additionally needs the native
`posting_id -> vector_id` membership exported from the baseline build pipeline, because the QVLOF artifact must be
posting-level rather than vector-page-level.

QSO then emits a static ordering or grouping over that unit definition.

## Common QSO Output Types

Depending on the target baseline, QSO emits one of the following:

- a page-aligned vector permutation
- explicit page groups
- a posting-page organization
- a partition file
- a graph-aware placement plan

## Static Binding Matrix


| System   | QSO layout unit             | QSO output artifact                               | Import stage                                                            | Runtime consumer                 |
| -------- | --------------------------- | ------------------------------------------------- | ----------------------------------------------------------------------- | -------------------------------- |
| PageANN  | page-aligned vector group   | `_new_to_old_ids_map.bin` or `qso_pages.bin`      | `build_page_graph(...)` before `create_disk_layout(...)`                | `PQFlashIndex`                   |
| SPANN    | SSD posting page            | posting assignment or posting-page emission order | `ExtraStaticSearcher::BuildIndex(...)` before posting pages are emitted | `SearchSSDIndex`                 |
| Starling | partition page              | `_partition.bin`                                  | `tests/utils/index_relayout.cpp`                                        | `page_search(...)`               |
| MARGO    | partitioned graph sector    | `_partition.bin`                                  | `save_partition(...)` / `index_relayout.cpp`                            | `page_search(...)`               |
| Gorgeous | graph-aware partition group | graph-only or graph-replica partition artifact    | `index_relayout_free_mem` through `split_graph` / `gr_layout`           | `PQFlashIndex` + `FileIOManager` |

## Static Artifact Generator CLI

```bash
python qso/static_layout_main.py \
  --system starling \
  --train-queries /path/to/train_queries.npy \
  --vector-features /path/to/base.npy \
  --num-vectors 1000000 \
  --page-capacity 16 \
  --output-dir /path/to/output \
  --prefix sift1m_qso
```

SPANN requires one extra argument:

```bash
python qso/static_layout_main.py \
  --system spann \
  --train-queries /path/to/train_queries.npy \
  --vector-features /path/to/base.npy \
  --num-vectors 1000000 \
  --posting-membership /path/to/posting_membership.csv \
  --page-capacity 16 \
  --output-dir /path/to/output \
  --prefix sift1m_qso
```

Optional:

- `--cluster-k`
- `--lgpf-k`
- `--transform-t`

The index-oriented artifact entrypoint exposes `qso` as the supported method.
The repository still keeps some generic ordering helpers in `methods.py`, but they are not part of the
PageANN/SPANN/Starling/MARGO/Gorgeous index-oriented experiment entrypoint.
`static_layout_main.py` now uses the paper-aligned Algorithm 2 block-assignment path for the `S` stage:

- `B = page_capacity` is the layout block size,
- `m = ceil(|D_adj| / B)` is the cluster count,
- `MiniBatchKMeans` seeds the provisional centers,
- each vector considers its nearest `s_top` centers,
- assignment is filled greedily under per-block capacity,
- leftover vectors are assigned to the nearest non-full block,
- final block centers are recomputed from assigned members.

The older balanced / equal-size clustering path is retained only as a legacy internal option and is no longer the main
QSO path.

The current pipeline still does not patch any external baseline repository. It produces the static artifact family that those repositories consume in their existing relayout or build path.

## Current Executable Coverage

### Method layer

The runnable method layer now includes:

- vector loading
- direct use of held-out training queries as QSO input
- QSO incremental layout generation for disk-resident static artifacts
- direct artifact emission for each target system

### PageANN

Emits:

- `<prefix>_new_to_old_ids_map.bin`
- `<prefix>_qso_pages.bin`

### SPANN

Emits:

- `<prefix>_qso_posting_order.bin`
- `<prefix>_qso_posting_pages.bin`
- `<prefix>_qso_vector_to_posting.bin`

These files are now posting-level artifacts:

- `qso_posting_order.bin`: physical order over native posting ids
- `qso_posting_pages.bin`: ordered posting contents, each posting as a vector-id list
- `qso_vector_to_posting.bin`: reverse map from vector id to native posting id

SPANN uses a posting-aware input because its disk layout is organized through posting lists,
so QSO must be given native posting membership before it can emit the correct artifact family.

### Starling / MARGO / Gorgeous

Emits:

- `<prefix>_partition.bin`

For Starling and MARGO this file is already in the exact binary contract consumed by `index_relayout` and `load_partition_data(...)`.

For Gorgeous, this partition-style artifact is consumed by `index_relayout_free_mem` in graph-only or graph-replica mode.

## Implementation Scope

The QSO implementation is scoped to SSD-resident artifact generation:

- workload-driven ordering,
- disk layout grouping,
- baseline artifact generation,
- method comparison for static layout runs.

That is the right shape for a disk-resident release package because the key runnable output is the artifact consumed by PageANN, SPANN, Starling, MARGO, or Gorgeous.

## Dependencies

The basic CLI path depends on:

- `numpy`
- `scipy`
- `scikit-learn`

The QSO transform path requires:

- `torch`

The QSO transform code uses the torch implementation of covariance and LGPF-style
updates. If `torch` is unavailable, the QSO transform path fails explicitly instead of using a lighter approximation.

## What QSO Replaces and What It Leaves Intact

QSO replaces:

- native page grouping
- native posting colocation order
- native partition objective
- native graph-aware disk placement order

QSO leaves intact:

- the baseline search loop
- the runtime query scheduling policy
- the existing page/posting/graph readers
- the final search executor

This separation is the key reason the QSO abstraction applies across all five systems.

## System Mapping

- PageANN: see `../index/pageann/README.md`
- SPANN: see `../index/spann/README.md`
- Starling: see `../index/starling/README.md`
- MARGO: see `../index/margo/README.md`
- Gorgeous: see `../index/gorgeous/README.md`

## Per-System Artifact Boundaries

### PageANN

QSO binds to page construction. The emitted artifact is either:

- a global permutation that PageANN repacks into contiguous pages, or
- an explicit page-group description consumed before `create_disk_layout(...)`.

### SPANN

QSO binds to SSD posting construction. The emitted artifact is a posting-oriented grouping that is imported before
page-bounded SSD postings are persisted. Unlike the other four systems, this requires a native posting-membership input
so that QSO can lift workload signals from vectors to posting lists.

### Starling

QSO binds to `_partition.bin`. The emitted artifact is already in the exact format consumed by `index_relayout` and later by `load_partition_data(...)`.

### MARGO

QSO binds either:

- outside the partitioner through a fully formed partition artifact, or
- inside the partitioner through a query-driven placement bias before `save_partition(...)`.

### Gorgeous

QSO binds to graph-aware relayout input. The emitted artifact is consumed by `split_graph` or `gr_layout`, after which the ordinary runtime opens the resulting graph-oriented index files.

## End-to-End Static Flow

The common disk-resident static flow is:

```text
base vectors + held-out training queries
  -> QSO ordering/grouping
  -> baseline-specific layout artifact
  -> builder or relayout import
  -> final on-disk index artifact
  -> unchanged online ANN search path
```

The QSO path is query-driven: it consumes held-out training queries directly and derives its layout signal from those queries rather than an access-profile
compatibility mode.
The only thing that changes from one system to another is the layout unit and the exact import function.
