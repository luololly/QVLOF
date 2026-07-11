# RDO for Disk-Resident ANN

This directory contains the RDO integration contracts for SSD-resident ANN systems.

It contains the disk-resident RDO control layer and the common contracts used by PageANN, SPANN, Starling, MARGO, and Gorgeous.

## Purpose

The RDO pipeline manages workload windows, candidate physical layouts, switching decisions, and replay summaries for the supported systems.

## RDO Role in the Disk-Resident Setting

RDO does not change how a baseline answers a single ANN query. It changes which prebuilt physical layout is active for the current workload phase.

For disk-resident systems, this means the RDO boundary always sits above:

- a page-layout family,
- an SSD posting-layout family,
- a partition/index family, or
- a graph-aware layout family.

The runtime search loop then consumes whichever family member has been selected.

## Common RDO Contract

RDO produces:

- candidate partial layouts
- a workload-window-specific switch policy
- replay records used to evaluate layout switching

In the disk-resident setting, the selected layout is then rebuilt or activated through the target baseline's existing import path.

## Executable Pipeline

The implementation provides three executable stages:

```text
RDO_layout_main.py
RDO_switch_main.py
RDO_replay_main.py
```

Supporting modules are now grouped by responsibility:

```text
common/
  rdo_types.py
offline/
  windowing.py
  layout_generator.py
  query_cost.py
online/
  switch_policy.py
evaluation/
  replay.py
resources/
  config/
  params/
utils/
  config.py
  setup.py
  io_utils.py
```

The modules are divided by responsibility:

- `offline/`: derive workload windows, estimate query-driven proxy costs, and emit candidate layout families
- `online/`: choose which candidate should be active
- `evaluation/`: aggregate the chosen sequence into replay summaries
- `common/`: shared dataclasses and contracts
- `resources/`: dataset descriptors and run-parameter snapshots
- `utils/`: file-format helpers and lightweight disk-side configuration/setup utilities

The `resources/` and `utils/` layers provide:

- resource files that describe dataset groups and run parameters,
- JSON/config loading helpers,
- setup glue for baseline adapters.

The disk-resident path uses query matrices, layout artifacts, and baseline-specific metadata as its control-plane inputs.

This code generates manifests, switch plans, replay summaries, and per-window QSO artifacts consumed by the five baseline integration boundaries.

## Three-Stage Pipeline

1. **layout stage**
   - produce multiple candidate physical layouts
   - current code can emit either proxy `base`, `hot`, and `balanced` candidates, or per-window QSO-materialized candidate families
   - in `partial` mode, each window family now contains the cold-start `qso_full` candidate plus the cumulative
     accepted partial-layout pool visible at that window
   - partial-layout `estimated_query_cost` is produced by `offline/query_cost.py` with an Algorithm 4 style histogram +
     spline-dequantization CDF + DIS block-range estimator
   - non-partial candidates still use a query-driven layout-level proxy for compatibility
2. **switch stage**
   - choose the active layout for each workload window
   - the default `qvlof-counter` policy follows the QVLOF/RDO switching rule: accumulate each layout's query cost,
     trigger switching when the active layout's cumulative cost exceeds `alpha`, then choose the next layout using
     weights proportional to `max(0, alpha - cumulative_cost) / alpha`
   - `cost-aware-greedy` and `sticky-best` remain available as engineering compatibility policies
3. **replay stage**
   - evaluate the switch sequence against the target baseline artifact family
   - current code aggregates estimated query cost, movement cost, and switch count
   - when given a layout manifest and base vectors, it can also run an Algorithm 5 style partial-layout-first query replay:
     search the selected partial layout first, then fall back to a QSO full-layout page simulator when the candidate
     metadata provides `qso_full_layout_pages`; if those pages are absent, the legacy full-vector fallback remains only
     as a compatibility path

## Current CLI Usage

Generate a layout-family manifest from held-out training queries:

```bash
python RDO_layout_main.py \
  --train-queries /path/to/train_queries.npy \
  --window-size 200 \
  --dataset-group sift100m \
  --output /path/to/layout_family.json
```

Generate a switch plan:

```bash
python RDO_switch_main.py \
  --layout-manifest /path/to/layout_family.json \
  --policy qvlof-counter \
  --alpha 1.0 \
  --query-cost-source estimated \
  --random-state 0 \
  --output /path/to/switch_plan.json
```

Generate a QSO-materialized candidate family instead of proxy `base/hot/balanced`:

```bash
python RDO_layout_main.py \
  --train-queries /path/to/train_queries.npy \
  --window-size 200 \
  --dataset-group sift100m \
  --materialize-qso-system starling \
  --qso-num-vectors 1000000 \
  --qso-page-capacity 64 \
  --qso-output-root /path/to/qso_windows \
  --qso-candidate-spec qso_all:3:0.3 \
  --qso-candidate-spec qso_focus:7:0.45 \
  --output /path/to/layout_family.json
```

Replay the plan:

```bash
python RDO_replay_main.py \
  --switch-plan /path/to/switch_plan.json \
  --summary-output /path/to/replay_summary.json \
  --events-output /path/to/replay_events.jsonl
```

Replay the selected partial layouts with Algorithm 5 style fallback semantics:

```bash
python RDO_replay_main.py \
  --switch-plan /path/to/switch_plan.json \
  --layout-manifest /path/to/layout_family.json \
  --base-vectors /path/to/base_vectors.npy \
  --k 100 \
  --a 2.0 \
  --summary-output /path/to/replay_summary.json \
  --query-events-output /path/to/query_events.jsonl
```

This replay evaluates the selected layout sequence inside the common RDO control layer before the baseline runtime consumes the active artifact.

## Current Artifact Semantics

`RDO_layout_main.py` writes:

- `windows`: workload-window metadata derived from held-out training queries
- `layout_families`: candidate manifests for each window

When `--qso-candidate-spec` is provided together with `--materialize-qso-system`, `layout_families` contains one
candidate per QSO spec for each window, and each candidate points at the per-window QSO artifact prefix.

When `--layout-mode partial` is used, `layout_families` no longer contains only the newly generated partial layout of
that window. Instead, each window receives a cumulative candidate family composed of:

- a cold-start `qso_full` candidate,
- all accepted partial layouts currently retained in the candidate pool,
- per-candidate `layout_state_id` metadata so the switch stage can track a persistent layout state across windows.

Each workload window is query-primary:

- `query_ids`
- `query_matrix`
- `hot_vector_ids`, preferably derived from query-to-base nearest-neighbor voting when base vectors are provided

Each candidate has:

- `candidate_id`
- `layout_label`
- `artifact_hint`
- `estimated_query_cost`
- `estimated_movement_cost`
- `metadata`

For partial candidates, `estimated_query_cost` is an Algorithm 4 style estimator, not a runtime benchmark. It computes
each query's distance to the representative query, builds a DIS histogram over the partial layout, applies a spline-based
dequantization / monotone CDF approximation, estimates the query radius from that CDF, counts overlapping DIS block
ranges, and averages the accessed-block fraction over the query window. For non-partial compatibility candidates,
`offline/query_cost.py` still uses the older query-driven layout-level proxy based on
`query_matrix` and `layout_label`. QSO parameters such as `lgpf_k` and `transform_t` stay in candidate metadata and QSO
artifact generation; they no longer directly define the switch-stage query-cost estimate.

`artifact_hint` records the path or prefix associated with each candidate. With `--materialize-qso-system`, it points to
the per-window QSO artifact prefix under `--qso-output-root`. The baseline adapters map that prefix to a PageANN layout
directory, a SPANN index directory, a Starling/MARGO partition-index pair, or a Gorgeous graph-layout family.

## Baseline Runtime Boundary

Disk-index construction, baseline relayout, runtime search, and performance measurement follow the per-system import and execution boundaries documented under `../index/` and `../scripts/`.

It does include an independent Algorithm 5 style partial-layout replay path. That path uses the selected partial layout's
representative query and DIS-ordered vector ids, performs a bidirectional candidate scan, and falls back to a QSO
full-layout page simulator when the partial scan touches a boundary or returns fewer than `k` candidates and
`qso_full_layout_pages` is available in candidate metadata. If those pages are not available, the replay keeps a legacy
full-vector top-k fallback as a compatibility path. This is a control-layer semantic replay, not a replacement for
baseline-integrated runtime search or a baseline artifact adapter.

The layout stage calls `qso/static_layout_main.py` per window and passes each query window as a per-window
`train_queries` file. The resulting QSO artifacts enter the baseline-specific build, relayout, and search chain through the adapters layered after the common RDO control plane.

## Dynamic Layout Family by Baseline


| System   | Candidate family emitted by layout stage       | What switch stage selects                      | What replay stage evaluates                        |
| -------- | ---------------------------------------------- | ---------------------------------------------- | -------------------------------------------------- |
| PageANN  | multiple page-group or permutation builds      | active page-based disk layout                  | page-layout sequence over workload windows         |
| SPANN    | multiple SSD posting organizations             | active SSD index directory                     | posting-layout sequence and its online search cost |
| Starling | multiple`_partition.bin` + `_disk.index` pairs | active partition/index pair                    | relaid layout sequence                             |
| MARGO    | multiple partition families + relaid indexes   | active partition family                        | partition/index sequence                           |
| Gorgeous | multiple split-graph or graph-replica families | active graph-aware artifact family and toggles | graph-layout sequence and active runtime mode      |

## What Changes Across Windows

RDO may change:

- page composition
- posting colocation
- partition assignment
- graph-aware placement family

RDO does not change:

- the ANN search kernel
- the low-level disk I/O API
- the query evaluator itself

That separation is what allows one switching policy abstraction to cover all five systems.

## System Mapping

- PageANN: repeated page-layout builds selected by workload windows
- SPANN: multiple SSD posting organizations
- Starling: multiple `_partition.bin` plus relaid `_disk.index` variants
- MARGO: multiple partition families plus relayout outputs
- Gorgeous: multiple split-graph or graph-replica layout families

## Dynamic Activation Boundaries

### PageANN

The active unit is a rebuilt page-based disk layout. The switch stage chooses among several page-group families produced from different workload windows.

### SPANN

The active unit is a built SSD posting layout. The switch stage selects which posting-layout directory is searched while keeping the serving binary unchanged.

### Starling

The active unit is a relaid `_disk.index` paired with its `_partition.bin`. The switch stage selects among multiple relaid pairs.

### MARGO

The active unit is a partition/index family generated from one workload phase. The switch stage chooses which family is visible to the runtime.

### Gorgeous

The active unit is a graph-aware layout family together with the runtime toggle set that opens it. The switch stage selects both the artifact family and the corresponding runtime mode.

## End-to-End Dynamic Flow

The common disk-resident dynamic flow is:

```text
workload windows
  -> candidate layout family generation
  -> switching policy
  -> active artifact family per window
  -> unchanged baseline runtime
  -> replay-time evaluation of the sequence
```

The replay target differs by system, but the control logic remains shared.
