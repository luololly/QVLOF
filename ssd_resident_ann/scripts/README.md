# Disk-Resident Script Coupling

This directory contains the SSD-resident integration commands.

## Intended Use

The external baselines already provide their own build and benchmark scripts. This directory records the script-level coupling points where QSO/RDO layout artifacts enter those scripts.

It contains three script groups:

- `clac_block_py/`
- `static_disk_sh/`
- `dynamic_disk_sh/`

The three directories organize static QSO generation, dynamic RDO layout selection, and disk-access summaries.

## Main Script Anchors

- PageANN: page-graph generation and `create_disk_layout`
- SPANN: builder `.ini` files and `BuildSSDIndex`
- Starling: `scripts/run_benchmark.sh`
- MARGO: `scripts/run_benchmark.sh` plus `new_mincut`
- Gorgeous: `scripts/run_benchmark.sh`

## Directory Responsibilities

| Directory | Responsibility |
| --- | --- |
| `clac_block_py/` | disk-access and block-summary helpers |
| `static_disk_sh/` | QSO wrapper scripts for the five baselines |
| `dynamic_disk_sh/` | dynamic layout-family wrapper scripts |

## Static Script Binding Matrix

| System | Native script or entrypoint | QSO import moment | Unchanged execution stage |
| --- | --- | --- | --- |
| PageANN | page-graph generation plus disk layout materialization | before `create_disk_layout(...)` writes the final disk index | `PQFlashIndex` search |
| SPANN | `.ini` + `IndexBuilder/main.cpp` | before SSD posting pages are emitted by `BuildSSDIndex` | `SearchSSDIndex` serving |
| Starling | `scripts/run_benchmark.sh` | replace native partition generation before `index_relayout` | `page_search(...)` |
| MARGO | `new_mincut.cpp` / `run_benchmark.sh` | replace or bias partition generation before relayout | `page_search(...)` |
| Gorgeous | `scripts/run_benchmark.sh` | choose graph-only or graph-replica relayout input before runtime flags are applied | `PQFlashIndex` + `FileIOManager` |

## Dynamic Script Binding Matrix

| System | Layout family prepared offline | What the switching layer changes | What stays unchanged |
| --- | --- | --- | --- |
| PageANN | multiple page-layout builds | active page-layout directory or prefix | search binary |
| SPANN | multiple SSD posting builds | active index directory | serving binary and query path |
| Starling | multiple relaid partition/index pairs | active `INDEX_PREFIX_PATH` family | `page_search(...)` |
| MARGO | multiple partition/index families | active partition family and relaid index pair | `page_search(...)` |
| Gorgeous | multiple graph-aware artifact families | active graph file prefix and runtime mode toggles | async I/O runtime |

## Script-Level Coupling Rules

- replace a native partition-generation step with a precomputed QSO artifact
- add an optional input path such as `QSO_PART_FILE`
- select among multiple prebuilt layouts under RDO replay
- keep the original search binary unchanged

## What a Full Disk-Resident Run Looks Like

Across the five systems, the script-level execution pattern is always:

1. prepare base dataset and index metadata
2. run QSO or RDO layout generation
3. convert the layout artifact into the baseline-specific builder input
4. rebuild or relayout the on-disk artifact
5. invoke the original search binary on the selected artifact family

The concrete script names differ by baseline, but the coupling structure is shared.
