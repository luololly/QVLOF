# QSO/RDO Adaptation Note for MARGO

## Public Upstream Source

`https://github.com/Zhang-Wenqi/MARGO`

## Verified Local Anchors

This note is grounded in the public MARGO repository layout:

- `MARGO/my_gp/new_mincut.cpp`
- `MARGO/graph_partition/include/partitioner.h`
- `MARGO/tests/utils/index_relayout.cpp`
- `MARGO/src/page_search.cpp`
- `MARGO/include/pq_flash_index.h`

The verified functions and methods used below are:

- `load_meta_data(...)`
- `load_index_graph(...)`
- `partition(base_path, 256)`
- `save_partition(...)`
- `load_partition_data(...)`
- `page_search(...)`

## What QSO Changes in MARGO

MARGO is already a disk-layout optimization system. Therefore QSO should not be described as replacing MARGO's search code. The correct interpretation is:

- keep MARGO's relayout and page-search pipeline,
- replace the partition-generation objective with a query-driven one.

In other words, QSO changes the partition file that MARGO later relayouts and serves.

## Exact Partition File Format

The partition format is directly verified in `graph_partition/include/partitioner.h::save_partition(...)`.

The binary layout is:

```text
uint64 C
uint64 partition_number
uint64 nd
for each partition:
    uint32 size
    uint32 ids[size]
uint32 id2pid[nd]
```

This is consistent with what `tests/utils/index_relayout.cpp` and `src/page_search.cpp::load_partition_data(...)` consume.

So a QSO-generated MARGO partition file must preserve this format exactly.

## Exact Native Pipeline

`MARGO/my_gp/new_mincut.cpp` shows the verified top-level flow:

```cpp
instance->load_meta_data(disk_path);
instance->load_index_graph(index_path);
instance->partition(base_path, 256);
instance->save_partition(partition_path);
```

That means there are two equally concrete integration paths.

## Path A: Direct artifact replacement

This is the simplest and safest coupling:

1. do not modify `new_mincut.cpp`,
2. run QSO externally,
3. emit a MARGO-compatible `_partition.bin`,
4. run `tests/utils/index_relayout.cpp`,
5. let `page_search(...)` consume the relaid index.

This path keeps every MARGO runtime component untouched.

## Path B: Inject QSO into the partitioner

If a deeper integration is desired, `graph_partition/include/partitioner.h` is the right file-level boundary.

The verified methods there include:

- `save_partition(...)`
- `load_partition(...)`
- `select_partition(unsigned i)`
- `graph_partition(...)`

The concrete idea is:

1. QSO produces access affinity or a target ordering over vector ids,
2. the partitioner reads that signal before `select_partition(...)` decides placement,
3. the result is still serialized by the existing `save_partition(...)`.

This keeps the MARGO output contract unchanged while replacing the placement objective.

## Minimal Direct-QSO Coupling

Writer contract for a standalone QSO partition emitter:

```cpp
std::vector<std::vector<unsigned>> pages = BuildQsoPages(access_profile, nd, C);
std::vector<unsigned> id2pid(nd);
for (unsigned pid = 0; pid < pages.size(); ++pid) {
    for (unsigned id : pages[pid]) id2pid[id] = pid;
}

write_u64(C);
write_u64(pages.size());
write_u64(nd);
for (auto& page : pages) {
    write_u32(page.size());
    write_u32_array(page);
}
write_u32_array(id2pid);
```

This produces the exact binary contract that MARGO already understands.

## How the Partition File Is Used

### Relayout stage

`MARGO/tests/utils/index_relayout.cpp`:

1. reads the partition header,
2. verifies `C` and `nd` against the disk index metadata,
3. loads `layout[i]` for each partition,
4. rewrites disk sectors in page order.

So the QSO artifact must already be page-bounded and metadata-consistent before relayout starts.

### Search stage

`MARGO/src/page_search.cpp` then:

1. loads `_partition.bin` through `load_partition_data(...)`,
2. reconstructs `gp_layout_` and `id2page_`,
3. runs `page_search(...)`.

This means the runtime search code is structurally identical to the Starling-style page-search path: better layout locality is automatically reflected in page accesses.

## Builder-Side Import Hook in `new_mincut.cpp`

For an in-tree builder binding, the import happens before `partition(base_path, 256)`.

For example:

```cpp
std::string qso_partition_path = base_path + "/qso_partition.bin";
if (std::filesystem::exists(qso_partition_path)) {
    instance->load_partition(qso_partition_path.c_str());
} else {
    instance->partition(base_path, 256);
}
instance->save_partition(partition_path);
```

This is concrete, small, and faithful to the current builder structure.

## Partition-Heuristic Binding

For tighter algorithmic coupling, the hook belongs in `partitioner.h` near the verified partition-selection methods:

```cpp
unsigned pid = select_partition(i);
// replace or bias pid using QSO co-access score
pid = SelectPartitionWithQsoBias(i, pid, qso_access_score, partition_load);
```

The point is not to invent a new file format. The point is to keep `save_partition(...)` unchanged so the rest of MARGO continues to work.

## Concrete RDO Coupling

RDO for MARGO is represented as a family of partition files or relaid indexes:

```text
layout_0_partition.bin
layout_1_partition.bin
layout_2_partition.bin
...
```

Each candidate goes through the ordinary MARGO relayout path. Then:

1. `RDO_layout_main.py` emits candidate partition layouts,
2. `RDO_switch_main.py` selects which layout is active for a workload window,
3. `RDO_replay_main.py` evaluates layout switching.

The serving code in `page_search(...)` remains unchanged.

## RDO Layout-Family Binding

The disk-side RDO code in `../../rdo/` produces candidate manifests and switch plans for MARGO layout families. The MARGO adapter:

1. map each RDO candidate to a window-specific partition prefix,
2. generate a QSO-compatible `_partition.bin` for the corresponding workload window,
3. run MARGO's relayout path to create the paired disk index,
4. register that partition/index pair as the candidate's concrete artifact,
5. let the switch plan select the active partition family per window.

This preserves the current MARGO search and relayout code while using `../../rdo/` as the common dynamic controller.

## Function-Level Flow

The code-level coupling is:

```text
workload access profile
  -> QSO partition pages
  -> MARGO-compatible _partition.bin
  -> tests/utils/index_relayout.cpp
  -> relaid _disk.index
  -> src/page_search.cpp::load_partition_data(...)
  -> src/page_search.cpp::page_search(...)
```

If deeper integration is used:

```text
workload access profile
  -> QSO affinity signal
  -> partitioner.h placement heuristic
  -> save_partition(...)
  -> index_relayout.cpp
  -> page_search(...)
```

Both versions are concrete and consistent with the verified repository structure.

## What Remains Unchanged

In a faithful adaptation, the following stay unchanged:

- MARGO disk index format,
- `tests/utils/index_relayout.cpp`,
- `load_partition_data(...)`,
- `page_search(...)`.

Only partition generation or partition ordering changes.
