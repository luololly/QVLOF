# QSO/RDO Adaptation Note for Gorgeous

## Public Upstream Source

`https://github.com/JayLZhou/Gorgeous`

## Verified Local Anchors

This note is grounded in the public Gorgeous repository layout:

- `Gorgeous/scripts/run_benchmark.sh`
- `Gorgeous/tests/utils/index_relayout_free_mem.cpp`
- `Gorgeous/src/file_io_manager.cpp`
- `Gorgeous/include/file_io_manager.h`
- `Gorgeous/include/pq_flash_index.h`

The verified mode constants in `tests/utils/index_relayout_free_mem.cpp` are:

- `DEFAULT_MODE = 0`
- `GRAPH_ONLY = 1`
- `EMB_ONLY = 2`
- `GRAPH_REPLICA = 3`

## What QSO Changes in Gorgeous

Gorgeous is different from the other disk-resident baselines because it explicitly separates:

- the main disk index,
- graph-only split layout,
- graph-replicated layout,
- runtime search mode selection.

Therefore QSO should not be described as a single flat page reorder. The correct coupling is:

- QSO chooses graph-aware placement,
- Gorgeous materializes that placement through `split_graph` or `gr_layout`,
- the ordinary Gorgeous executor issues asynchronous reads over the new layout.

## Verified Script-Level Layout Modes

The current `scripts/run_benchmark.sh` already exposes the exact layout-generation stages.

### `gp`

Native page relayout through:

- `graph_partition/partitioner`
- `tests/utils/index_relayout`

### `split_graph`

Graph-only layout through:

- `partitioner --mode 1`
- `tests/utils/index_relayout_free_mem ... mode 1`
- output copied to `${GRAPH_PATH}_disk_graph.index`

### `gr_layout`

Graph-replicated layout through:

- `partitioner --mode 3`
- `tests/utils/index_relayout_free_mem ... mode 3`
- output copied to `${GRAPH_REP_INDEX_PATH}_graph_rep.index`

This is already the right abstraction for QSO and RDO.

## Exact Code Boundary for Relayout

`Gorgeous/tests/utils/index_relayout_free_mem.cpp` shows that `relayout(...)`:

1. reads the partition file header,
2. reads `layout[i]` for each partition,
3. validates index metadata,
4. rewrites sectors according to the chosen mode.

So the concrete QSO artifact is a partition-style grouping compatible with Gorgeous relayout.

For `GRAPH_ONLY` and `GRAPH_REPLICA`, the shared grouping contract is reused, but the relayout logic writes different physical artifacts.

## Exact Runtime Boundary

The runtime I/O substrate is `Gorgeous/src/file_io_manager.cpp`.

The verified entry points are:

- `FileIOManager::read(...)`
- `FileIOManager::submit_read_reqs(...)`
- internal `execute_io(...)`

That file does not decide layout. It receives aligned read requests and issues async I/O through `io_submit` / `io_getevents`.

So the correct causal chain is:

1. QSO changes where graph and embedding payloads are placed,
2. Gorgeous search still generates logical read requests,
3. `FileIOManager` serves the existing request API,
4. the request stream becomes more locality-friendly because the disk placement improved.

## Static QSO Binding Paths

There are two concrete ways to couple QSO to Gorgeous.

### Path A: graph-only QSO

Use the existing `split_graph` path:

1. QSO emits a partition file optimized for graph locality,
2. run `index_relayout_free_mem` with `mode 1`,
3. produce `${GRAPH_PATH}_disk_graph.index`,
4. keep the ordinary Gorgeous search path.

### Path B: graph-replica QSO

Use the existing `gr_layout` path:

1. QSO emits a partition file optimized for replicated hot graph regions,
2. run `index_relayout_free_mem` with `mode 3`,
3. produce `${GRAPH_REP_INDEX_PATH}_graph_rep.index`,
4. enable the standard Gorgeous runtime switches.

This second path is closer to the full Gorgeous design because it explicitly models graph replicas.

## Script-Level Import Hook

The native script already has the required branches. The import hook allows an externally generated QSO partition file to drive the existing relayout mode:

```bash
QSO_PART_FILE=${QSO_PART_FILE:-}

if [ -n "${QSO_PART_FILE}" ] && [ -f "${QSO_PART_FILE}" ]; then
  GP_FILE_PATH=${QSO_PART_FILE}
else
  GP_FILE_PATH=${GRAPH_GP_PATH}_part.bin
  ${EXE_PATH}/graph_partition/partitioner ... --gp_file ${GP_FILE_PATH}
fi

${EXE_PATH}/tests/utils/index_relayout_free_mem \
  ${OLD_INDEX_FILE} ${GP_FILE_PATH} $GP_DATA_TYPE 1 ${SECTOR_LEN} 4096
```

and similarly for mode `3`:

```bash
${EXE_PATH}/tests/utils/index_relayout_free_mem \
  ${OLD_INDEX_FILE} ${GP_FILE_PATH} $GP_DATA_TYPE 3 ${SECTOR_LEN} ${GR_SECTOR_LEN}
```

This is a real code path already exposed by the repository.

## Exact Runtime Switches That Consume the Layout

In `scripts/run_benchmark.sh`, the `search` branch passes:

- `--disk_file_path`
- `--graph_rep_index_prefix`
- `--disk_graph_prefix`
- `--deco_impl`
- `--use_graph_rep_index`

and the local config exposes:

- `DECO_IMPL`
- `USE_DISK_GRAPH_CACHE_INDEX`

These switches are the concrete runtime boundary between “which physical graph-aware layout is active” and “how search is executed”.

RDO switches among prebuilt layout artifacts and runtime toggles; it does not rewrite `FileIOManager`.

## Function-Level Flow

The most concrete Gorgeous+QSO flow is:

```text
workload access profile
  -> QSO graph-aware grouping
  -> partition file
  -> index_relayout_free_mem(mode=1 or mode=3)
  -> disk_graph.index or graph_rep.index
  -> search_disk_index with DECO_IMPL / USE_DISK_GRAPH_CACHE_INDEX
  -> PQFlashIndex search
  -> FileIOManager async reads
```

The runtime executor remains unchanged. Only the persisted layout and chosen runtime mode change.

## How `FileIOManager` Fits Into the Story

It is useful to be explicit about what is and is not modified.

`src/file_io_manager.cpp`:

- registers thread-local I/O contexts,
- opens file descriptors,
- submits aligned reads,
- waits for async completions.

QSO does not modify any of those mechanics.

Instead, QSO changes the offsets requested by the upper search pipeline because nearby graph or embedding data has been packed into fewer sectors. That is exactly why `FileIOManager` is an important verified downstream anchor: it is where the layout benefit appears as fewer scattered reads.

## Concrete RDO Coupling

RDO is represented as a controller over multiple Gorgeous layout artifacts, for example:

```text
graph_layout_window0/
graph_layout_window1/
graph_layout_window2/
```

where each directory contains one or both of:

- a split-graph artifact,
- a graph-replica artifact.

Then:

1. `RDO_layout_main.py` builds candidate layout families,
2. `RDO_switch_main.py` selects which family is active,
3. `RDO_replay_main.py` evaluates the switch sequence,
4. Gorgeous search uses the standard runtime flags to open the selected files.

This matches the repository's current search configuration model.

## RDO Layout-Family Binding

The disk-side RDO code in `../../rdo/` emits dynamic manifests and switch plans. The Gorgeous layout-family adapter:

1. map each RDO candidate to a graph-aware layout family prefix,
2. generate the corresponding QSO partition file for the candidate's workload window,
3. materialize either a `split_graph` artifact, a `gr_layout` graph-replica artifact, or both,
4. store the runtime toggle metadata alongside the candidate artifact,
5. let the RDO switch plan select both the active graph artifact family and its runtime mode.

This keeps `FileIOManager` and `PQFlashIndex` unchanged while using `../../rdo/` as the common dynamic controller.

## What Remains Unchanged

A faithful adaptation keeps unchanged:

- the Gorgeous search executor,
- the asynchronous I/O substrate in `FileIOManager`,
- the runtime flags and search invocation shape,
- the online graph search logic exposed through `PQFlashIndex`.

Only graph-aware physical placement and active layout selection change.

The code-level coupling boundary is:

- QSO output enters through `split_graph` or `gr_layout`
- `index_relayout_free_mem` consumes the relayout artifact
- runtime activation depends on `DECO_IMPL` and `USE_DISK_GRAPH_CACHE_INDEX`
- the I/O effect materializes in `src/file_io_manager.cpp`
