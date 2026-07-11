# QSO/RDO Adaptation Note for Annoy

## Public Upstream Source

`https://github.com/spotify/annoy`

## Verified Local Anchors

This note is grounded in the local QVLOF-side Annoy harness:

- `run_annoy_index_search.py`
- `run_annoy_window_batch.py`
- `config.py`
- `../../scripts/static_memory_sh/Annoy.sh`
- `../../scripts/dynamic_memory_sh/dynamic_query_annoy_benchmark.sh`

The most important verified local functions are:

- `load_csv_id_vec(...)`
- `build_annoy_index(...)`
- `run_experiment(...)`

## What QSO Changes in Annoy

Annoy is the cleanest in-memory baseline for QSO because its build pipeline is already:

1. load vectors,
2. `add_item(...)`,
3. `build(n_trees, n_jobs)`,
4. query through `get_nns_by_vector(...)`.

QSO should bind before step 2. The online search path should remain unchanged.

In the local harness, Annoy ids are assigned by row order:

```python
a.add_item(idx, base_vecs[idx])
```

So the physical layout contract is simply the row order of the input CSV.

## Exact Code Boundary

The local static builder in `run_annoy_index_search.py` uses:

- `load_csv_id_vec(...)` to load `id + vector`,
- `build_annoy_index(...)` to iterate rows in order,
- `AnnoyIndex.add_item(idx, base_vecs[idx])`.

That means a QSO layout does not need to patch Annoy internals. It only needs to provide a reordered base CSV.

## Static QSO Binding

The practical Annoy+QSO path in this repository is:

1. run QSO in `../../qso/demo.py`,
2. emit a reordered CSV such as `f1_AG5_sorted.csv`, `f2_zorder_sorted.csv`, or `f4_idistance_sorted.csv`,
3. point `run_annoy_index_search.py` or `../../scripts/static_memory_sh/Annoy.sh` to that CSV,
4. rebuild Annoy on the reordered row sequence,
5. run ordinary Annoy search.

This is already how the local scripts are organized.

## Builder-Side Import Hook

The import hook is not inside Annoy itself. It is the `--loadcsv` argument accepted by the local harness:

```text
python run_annoy_index_search.py --loadcsv <reordered_csv> --point_csv <queries>
```

So the QSO contract is:

- input: reordered base CSV,
- unchanged baseline: Annoy build/search APIs,
- changed object: the row order presented to `add_item(...)`.

## Dynamic RDO Binding

The local dynamic script `../../scripts/dynamic_memory_sh/dynamic_query_annoy_benchmark.sh` already evaluates multiple layouts across workload windows through:

- `run_annoy_window_batch.py`
- `--window_size`
- one output directory per base-layout / query-window combination.

RDO therefore binds as:

1. generate multiple window-specific reordered CSV layouts,
2. rebuild one Annoy index per layout candidate,
3. evaluate per-window recall / latency using `run_annoy_window_batch.py`,
4. let the controller choose which layout is active for each window.

The Annoy dynamic path uses a rebuild-and-switch model over window-specific index files.

## Current Boundary

What is already concrete locally:

- static QSO through reordered CSV inputs,
- dynamic window evaluation through the local batch runner.

The common `../../rdo/` output maps each selected layout family to the corresponding Annoy CSV/index set through the Annoy artifact adapter boundary.
