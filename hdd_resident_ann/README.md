# QVLOF for HDD-Resident ANN

This directory records the QVLOF integration boundary for PostgreSQL with pgvector:

- QSO emits a physical-layout artifact before index construction.
- The index builder consumes that artifact while keeping its query implementation unchanged.
- RDO treats multiple QSO layouts as a layout family and selects one family member for each workload window.

For pgvector, the physical-layout artifact is a reordered CSV and the dynamic layout family is represented by PostgreSQL table names.

## Integration Map

| Stage | HDD/pgvector artifact | Local implementation |
| --- | --- | --- |
| Static QSO layout | reordered `<layout>.csv` | `qso/static_layout_main.py`, `qso/pgvector_artifact.py` |
| pgvector import boundary | CSV rows inserted in physical order | `index/pg_vector/load_and_index.py::process_csv_file` |
| Built table family | `<layout>`, `<layout>_ivfflat`, `<layout>_hnsw` | `index/pg_vector/load_and_index.py` |
| Dynamic RDO layout | one table family per workload window | `rdo/sift1m_pgvector.py::build_window_plan` |
| RDO activation artifact | window-to-table switch list | `rdo/sift1m_pgvector.py::write_window_plan` |
| Runtime consumer | selected table name | `index/pg_vector/run_experiment_ubuntu_final.py::execute_query` |

Command-level entrypoints are listed in `scripts/README.md`.

The adapter files describe and materialize the coupling artifacts. They do not require QSO or RDO to modify pgvector's SQL KNN implementation.

## Static Binding

`qso/static_layout_main.py` computes a QSO permutation and writes the reordered vectors through `qso/pgvector_artifact.py`. For a layout named `window_0_qvlof`, the output is:

```text
window_0_qvlof.csv
window_0_qvlof.pgvector.json
```

The manifest names the table family that `load_and_index.py` derives from the CSV:

```text
window_0_qvlof
window_0_qvlof_ivfflat
window_0_qvlof_hnsw
```

## Dynamic Binding

The existing RDO implementation records layout changes in `schedule["move"]` as `(window, layout_path)` pairs. `rdo/pgvector_adapter.py` interprets each layout path as a pgvector base-table name and maps it to the requested table type.

For example, `results/window-0-qvlof.csv` maps to `window_0_qvlof_hnsw` when the selected index type is HNSW. Each workload window therefore selects one pgvector table family.

## Runtime Boundary

The query path remains:

```sql
SELECT id
FROM <selected_table>
ORDER BY embedding <-> '<query_vector>'
LIMIT <k>;
```

Only `<selected_table>` changes across RDO windows.
