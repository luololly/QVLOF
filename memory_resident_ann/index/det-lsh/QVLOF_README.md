# QSO/RDO Adaptation Note for DET-LSH

## Public Upstream Source

The local implementation matches the DET-LSH method source published at:

`https://github.com/WeiJiuQi/DET-LSH`

## Verified Local Anchors

This note is grounded in the local DET-LSH implementation:

- `LSH.py`
- `det_lsh_re.py`
- `runLSH.py`
- `../../scripts/static_memory_sh/det_lsh.sh`

The critical verified local classes and functions are:

- `LSHProjector`
- `DynamicEncoder`
- `DETreeNode`
- `DETLSHIndex.build()`
- `DETLSHIndex.query()`

## What QSO Changes in DET-LSH

DET-LSH does not expose a separate page layout or partition file. Its build object is the tree family created from the input vector order and projected value distribution.

Therefore QSO should bind before `DETLSHIndex.build()`, by changing the base-vector order fed into the index.

The runtime query logic should remain unchanged.

## Exact Code Boundary

The local build path is explicit:

1. load CSV through `load_csv_with_id(...)`,
2. instantiate `DETLSHIndex(data, ...)`,
3. call `index.build()`,
4. query through `index.query(...)`.

Because the base matrix is stored as `self.data`, the most practical QSO contract is a reordered CSV or reordered in-memory matrix.

## Static QSO Binding

The practical DET-LSH+QSO path in this repository is:

1. generate a reordered CSV through QSO,
2. feed that CSV to `runLSH.py` or `det_lsh_re.py`,
3. rebuild the DET-LSH trees on that reordered matrix,
4. run the unmodified `query(...)` path.

The static batch driver `../../scripts/static_memory_sh/det_lsh.sh` already reflects this pattern by iterating over reordered CSV baselines.

## Dynamic RDO Binding

DET-LSH currently has no dedicated local dynamic wrapper under `../../scripts/dynamic_memory_sh/`.

Still, the feasible RDO boundary is clear:

1. build one DET-LSH tree family per window-specific reordered CSV,
2. save the candidate family metadata and evaluation outputs,
3. let an RDO controller switch the active family by workload window,
4. keep `query(...)` unchanged.

This dynamic path rebuilds and switches window-specific DET-LSH tree families.

## Current Boundary

What is already concrete locally:

- a working DET-LSH implementation,
- static evaluation over reordered data.

The dynamic DET-LSH boundary uses window-specific layout families. The shared `../../rdo/` pipeline maps candidate layouts to the corresponding DET-LSH tree families.
