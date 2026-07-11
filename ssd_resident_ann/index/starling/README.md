# QSO/RDO Adaptation Note for Starling

## Public Upstream Source

`https://github.com/zilliztech/starling`

## Verified Local Anchors

This note is grounded in the public Starling repository layout:

- `Starling/scripts/run_benchmark.sh`
- `Starling/src/page_search.cpp`
- `Starling/tests/utils/index_relayout.cpp`
- `Starling/include/pq_flash_index.h`

The most important verified functions are:

- `load_partition_data(...)`
- `page_search(...)`

## What QSO Changes in Starling

Starling already exposes the exact artifact boundary that QSO wants:

1. build the disk index,
2. generate a partition file,
3. relayout the disk index,
4. run page-based search.

Therefore the clean QSO artifact is not a patch inside the search loop. It is a replacement for the partition file consumed by relayout and later loaded by search.

## Exact Artifact Format of `_partition.bin`

The format is fully verified from `src/page_search.cpp` and `tests/utils/index_relayout.cpp`.

`load_partition_data(...)` reads:

```text
uint64 C
uint64 partition_nums
uint64 nd
for each partition:
    uint32 size
    uint32 ids[size]
uint32 id2page[nd]
```

This last `id2page` tail is important. A QSO-generated Starling partition file must include it, otherwise `load_partition_data(...)` will read invalid page mappings.

## Static QSO Binding

The Starling+QSO integration is bound at the partition-file boundary and does not modify the online search loop:

1. run QSO on the workload access profile,
2. emit a Starling-compatible `_partition.bin`,
3. run `tests/utils/index_relayout` with that file,
4. copy the produced `_part_tmp.index` to the final `_disk.index`,
5. run the normal `page_search(...)` path.

This is already how the native Starling script is structured.

## Verified Script Boundary

In `Starling/scripts/run_benchmark.sh`, the `gp` branch does:

1. call `graph_partition/partitioner --gp_file $GP_FILE_PATH`,
2. call `tests/utils/index_relayout ${OLD_INDEX_FILE} ${GP_FILE_PATH}`,
3. copy `${GP_PATH}_part_tmp.index` to `${INDEX_PREFIX_PATH}_disk.index`,
4. copy `${GP_FILE_PATH}` to `${INDEX_PREFIX_PATH}_partition.bin`.

That means the minimal QSO adaptation is simply to replace step 1 with an externally generated QSO partition file and keep steps 2-4 unchanged.

## Script-Level Import Hook

The concrete import hook is in `run_benchmark.sh`:

```bash
QSO_PART_FILE=${QSO_PART_FILE:-}

if [ -n "${QSO_PART_FILE}" ] && [ -f "${QSO_PART_FILE}" ]; then
  GP_FILE_PATH=${QSO_PART_FILE}
else
  GP_FILE_PATH=${GP_PATH}_part.bin
  ${EXE_PATH}/graph_partition/partitioner ... --gp_file ${GP_FILE_PATH}
fi

${EXE_PATH}/tests/utils/index_relayout ${OLD_INDEX_FILE} ${GP_FILE_PATH}
cp ${GP_PATH}_part_tmp.index ${INDEX_PREFIX_PATH}_disk.index
cp ${GP_FILE_PATH} ${INDEX_PREFIX_PATH}_partition.bin
```

This is enough to make Starling consume a QSO layout without touching `page_search(...)`.

## What `index_relayout.cpp` Actually Consumes

`Starling/tests/utils/index_relayout.cpp` verifies several invariants before relayout:

1. `_partition.bin` header matches the disk index metadata,
2. `C` matches the sector capacity,
3. `nd` matches the point count,
4. `layout[i]` is read for every partition,
5. sectors are rewritten page by page using the ids in `layout[i]`.

This means a valid QSO artifact must satisfy:

- every vector id appears exactly once in the page lists,
- each page size is at most `C`,
- `id2page[id]` matches the page that actually contains `id`.

## Concrete QSO Writer Contract

A correct Starling QSO writer follows this contract:

```text
Input:
  - workload access profile
  - vector count nd
  - page capacity C
  - optional graph neighbors

Output:
  - partition pages P[0..partition_nums-1], each |P[i]| <= C
  - id2page[id]
  - binary file with Starling header/layout/tail format
```

Writer contract:

```cpp
write_u64(C);
write_u64(partition_nums);
write_u64(nd);
for page in pages:
    write_u32(page.size());
    write_u32_array(page.ids);
write_u32_array(id2page);
```

This is the exact runtime contract consumed by `load_partition_data(...)`.

## End-to-End Function-Level Flow

The fully concrete path is:

```text
workload access profile
  -> QSO page assignment
  -> Starling-format _partition.bin
  -> tests/utils/index_relayout
  -> *_part_tmp.index
  -> *_disk.index
  -> src/page_search.cpp::load_partition_data(...)
  -> src/page_search.cpp::page_search(...)
```

This is already the natural shape of Starling, so QSO only changes the partition-generation policy.

## Why `page_search(...)` Can Stay Unchanged

The verified runtime path in `src/page_search.cpp` is:

1. `load_partition_data(...)` loads `gp_layout_` and `id2page_`,
2. `page_search(...)` uses those structures to control page visits during search.

So if QSO makes query-related vectors share a page more often, the online traversal automatically becomes less scattered. There is no need to redesign the search executor.

## RDO Coupling

RDO is represented as multiple partition files:

```text
window0_partition.bin
window1_partition.bin
window2_partition.bin
...
```

Each one is relaid through the `index_relayout` binary. Then:

1. `RDO_layout_main.py` generates candidate partition files,
2. `RDO_switch_main.py` chooses which partition file is active,
3. `RDO_replay_main.py` evaluates the switch sequence.

Again, Starling search remains unchanged. Only the active relaid layout changes.

## RDO Layout-Family Binding

The disk-side RDO code in `../../rdo/` generates the dynamic control manifests. For Starling, the layout-family adapter:

1. take each RDO candidate's `artifact_hint` as the target prefix for a window-specific layout,
2. run the QSO partition writer for that window's access profile,
3. emit `window<i>_partition.bin`,
4. run Starling `tests/utils/index_relayout` to produce the paired relaid disk index,
5. let `RDO_switch_main.py` select the active partition/index pair for each workload window.

The common RDO code supplies switching decisions for the Starling partition and relayout artifacts.

The code-level coupling boundary is:

- partition file format consumed by `tests/utils/index_relayout.cpp`
- runtime partition loading in `load_partition_data(...)`
- downstream search path in `page_search(...)`
