# QSO/RDO Adaptation Note for PageANN

## Public Upstream Source

`https://github.com/dingyikang/PageANN`

## Verified Local Anchors

This note is grounded in the public PageANN repository layout:

- `PageANN/apps/generate_page_graph.cpp`
- `PageANN/apps/utils/create_disk_layout.cpp`
- `PageANN/include/disk_utils.h`
- `PageANN/src/disk_utils.cpp`
- `PageANN/src/pq_flash_index.cpp`

The critical verified functions are:

- `build_page_graph(...)`
- `mergeNodesIntoPage(...)`
- `create_disk_layout(...)`
- `diskann_create_disk_layout(...)`

## What QSO Changes in PageANN

PageANN already separates:

1. vector-level graph construction,
2. page grouping,
3. disk layout materialization,
4. search execution.

QSO should be attached to step 2 or step 3. The online executor in `src/pq_flash_index.cpp` should remain unchanged.

The physical layout unit is a page-aligned vector group:

- `mergedNodes[page_id] = list of vector ids in that page`
- `nodeToPageMap[vector_id] = page_id`

That pair is the exact contract QSO should produce.

## Exact Code Boundary

The most important code block is in `PageANN/src/disk_utils.cpp` inside `build_page_graph(...)`. Around the verified block near lines 1695-1744, PageANN constructs:

```cpp
std::vector<std::vector<uint32_t>> mergedNodes;
std::vector<uint32_t> nodeToPageMap;
std::vector<uint32_t> new_to_original_map;
```

Then it chooses one of two paths:

1. call `mergeNodesIntoPage(...)` for the native PageANN grouping, or
2. decode a precomputed sequential ordering from `<prefix>_new_to_old_ids_map.bin`.

Finally it calls:

```cpp
create_disk_layout(..., mergedNodes, nodeToPageMap);
```

This is the cleanest QSO insertion point. The searcher should not be patched first.

## Static QSO Binding

The PageANN+QSO integration is bound at the page-layout construction stage:

1. run the normal vector-level index build,
2. run QSO on the workload access profile and base vectors,
3. convert the QSO output into `new_to_original_map`, or directly into `mergedNodes` plus `nodeToPageMap`,
4. let the existing `create_disk_layout(...)` code write the final `.index`.

In practice there are two concrete ways to do this.

### Path A: Reuse the existing sequential reorder branch

`build_page_graph(...)` already contains a branch that reconstructs `mergedNodes` from a file named:

- `<final_index_prefix_path>_new_to_old_ids_map.bin`

The verified writer for that file is in `PageANN/src/disk_utils.cpp` around lines 1106-1115. The binary format is:

```text
int32 npts
int32 dim (=1)
uint32 new_to_old[npts]
```

So the simplest QSO coupling is:

1. let QSO emit one global permutation of vector ids,
2. write it in this exact binary format,
3. force `build_page_graph(...)` to enter the sequential decode path,
4. let the existing loop rebuild pages as contiguous chunks of `nnodes_per_page`.

This path uses the existing PageANN reorder branch and keeps the search executor unchanged.

### Path B: Inject full page groups

If QSO already produces page-sized groups, the better adaptation is to bypass both native grouping and sequential chunking, and directly load:

- `mergedNodes`
- `nodeToPageMap`

That matches the real input consumed by `create_disk_layout(...)`.

## Builder-Side Import Hook

The code block around `mergeClosesNodes` in `PageANN/src/disk_utils.cpp` is the natural place for a small optional import:

```cpp
std::string qso_map_file = final_index_prefix_path + "_new_to_old_ids_map.bin";
std::string qso_group_file = final_index_prefix_path + "_qso_pages.bin";

if (std::filesystem::exists(qso_group_file)) {
    load_qso_pages(qso_group_file, nnodes_per_page, points_num,
                   mergedNodes, nodeToPageMap, new_to_original_map);
} else if (std::filesystem::exists(qso_map_file)) {
    load_qso_permutation(qso_map_file, points_num, nnodes_per_page,
                         mergedNodes, nodeToPageMap, new_to_original_map);
} else {
    mergeNodesIntoPage(..., mergedNodes, nodeToPageMap, new_to_original_map);
}

create_disk_layout(..., mergedNodes, nodeToPageMap);
```

This is the correct level of integration because the native search path is left untouched.

## QSO Artifact Formats That Match the Existing Code

### Option 1: permutation file

Reusing the verified `_new_to_old_ids_map.bin` format:

```text
int32 npts
int32 dim (=1)
uint32 new_to_old[npts]
```

The downstream logic in `build_page_graph(...)` will pack:

```text
page 0 = new_to_old[0 : nnodes_per_page-1]
page 1 = new_to_old[nnodes_per_page : 2*nnodes_per_page-1]
...
```

### Option 2: explicit page-group file

If a custom helper is added, the most natural explicit format is:

```text
uint64 page_count
uint64 nnodes_per_page
for each page:
    uint32 ids[nnodes_per_page]
uint64 npts
uint32 node_to_page[npts]
```

This mirrors the temporary debug dump already written by PageANN around lines 1119-1133 in `temp_mergedNodes_and_map.bin`.

## How the Existing Search Code Consumes the Result

After layout construction, the PageANN executor in `src/pq_flash_index.cpp` reads the resulting disk index and performs ordinary page-based search.

The coupling logic is:

1. QSO changes `mergedNodes` and `nodeToPageMap`,
2. `create_disk_layout(...)` rewrites physical pages and page-neighbor metadata,
3. `PQFlashIndex` executes the original ANN search over the new page locality.

The key point is that PageANN search semantics are preserved. Only page composition changes.

## Using `apps/utils/create_disk_layout.cpp`

`PageANN/apps/utils/create_disk_layout.cpp` exposes a verified CLI:

```text
create_disk_layout <data_type> <base_file.bin> <mem_index_file> <output_disk_index_file> [reorder_data_file.bin]
```

This utility supports the raw-vector QSO artifact path. In that case:

1. QSO produces `reorder_data_file.bin`,
2. `diskann_create_disk_layout(...)` writes a raw reordered disk layout,
3. no page-graph-specific grouping logic is imported.

That path is weaker than the full page-aware integration above, but it is still a concrete coupling route already exposed by the codebase.

## Function-Level Data Flow

The most faithful PageANN+QSO flow is:

```text
workload access profile
  -> QSO permutation or page groups
  -> build_page_graph(...)
  -> mergedNodes / nodeToPageMap / new_to_original_map
  -> create_disk_layout(...)
  -> page-based disk index
  -> src/pq_flash_index.cpp search
```

More concretely:

1. QSO ranks or groups vector ids according to query co-access.
2. The import helper converts that output into page-bounded groups.
3. `nodeToPageMap` is filled for every original vector id.
4. `create_disk_layout(...)` writes sectors according to those page groups.
5. The original PageANN search executor benefits from denser page-local accesses.

## RDO Coupling

RDO is bound above this layout boundary:

1. `RDO_layout_main.py` emits several candidate permutations or page-group files,
2. each candidate becomes one PageANN layout build,
3. `RDO_switch_main.py` selects the active layout for a workload window,
4. `RDO_replay_main.py` evaluates the layout-switch sequence.

The important constraint is that RDO still selects layouts, not search algorithms.

## RDO Layout-Family Binding

The disk-side RDO code in `../../rdo/` provides candidate manifests and switch plans. For PageANN, the layout-family adapter:

1. read each `layout_families[*].candidates[*].artifact_hint`,
2. invoke the QSO page-group generator for that window,
3. materialize either `<prefix>_new_to_old_ids_map.bin` or `<prefix>_qso_pages.bin`,
4. run the PageANN page-graph build path to produce one page-layout directory per candidate,
5. let the switch plan select the active directory or prefix per workload window.

`../../rdo/` supplies the dynamic control logic used to select the PageANN artifacts generated for each candidate.

## Current Measurable Status

Under the current repository state, PageANN is already close to being measurable with QSO artifacts, but not in a
strictly zero-patch way.

The current practical status is:

1. `../../qso/static_layout_main.py` emits the required PageANN-side static artifacts:
   - `<prefix>_new_to_old_ids_map.bin`
   - `<prefix>_qso_pages.bin`
2. the original PageANN build flow can be reused after a very small builder-side import patch in
   `src/disk_utils.cpp::build_page_graph(...)`,
3. after that patch, the generated PageANN disk index can be searched through the ordinary runtime path.

That means QSO performance gain for PageANN is already testable in practice if one accepts a minimal builder-side
adapter. The current blocker is not the QSO artifact itself, but the absence of an upstream-native import hook for
those artifacts.

## Code-Level Coupling Boundary

- QSO output is imported in `build_page_graph(...)`
- the required in-memory structures are `mergedNodes` and `nodeToPageMap`
- `create_disk_layout(...)` writes the physical layout
- `src/pq_flash_index.cpp` remains unchanged
