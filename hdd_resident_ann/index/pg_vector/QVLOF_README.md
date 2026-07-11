# QSO/RDO Adaptation Note for pgvector

## Public Upstream Source

`https://github.com/pgvector/pgvector`

## Verified Local Anchors

This note is grounded in the local pgvector integration:

- `load_and_index.py`
- `run_experiment_ubuntu_final.py`
- `config.py`
- `conda_env/pg_vector_env.yml`

The most important verified local anchors are:

- table creation from reordered CSV files,
- IVFFlat index creation,
- HNSW index creation,
- SQL KNN evaluation through `ORDER BY embedding <-> ... LIMIT k`.

## What QSO Changes in pgvector

The pgvector layout boundary is a PostgreSQL table and its associated vector indexes.

QSO should bind before table loading:

1. QSO emits a reordered CSV,
2. `load_and_index.py` loads that CSV into a new table,
3. pgvector builds IVFFlat / HNSW indexes on that table,
4. SQL search remains unchanged.

## Exact Code Boundary

The local loader does:

1. read each CSV under `fanncsv_dir`,
2. create a base table,
3. `COPY` vectors into that table,
4. clone the table into `<table>_ivfflat` and `<table>_hnsw`,
5. build the corresponding pgvector indexes.

This means the QSO artifact is simply the reordered CSV file name and its resulting table family.

The local QSO-side binding is implemented by:

- `../../qso/static_layout_main.py`, which reads SIFT1M and computes the QSO permutation,
- `../../qso/pgvector_artifact.py`, which writes a loader-compatible CSV and a pgvector table-family manifest.

For an artifact named `window_0_qvlof.csv`, the manifest records:

- base table: `window_0_qvlof`,
- IVFFlat table: `window_0_qvlof_ivfflat`,
- HNSW table: `window_0_qvlof_hnsw`.

## Static QSO Binding

The practical pgvector+QSO path in this repository is:

1. generate reordered CSVs through QSO,
2. place them under the configured `fanncsv_dir`,
3. run `load_and_index.py`,
4. run `run_experiment_ubuntu_final.py` to evaluate the derived `_ivfflat` / `_hnsw` tables.

The search contract is fully SQL-based and remains unchanged.

## Dynamic RDO Binding

The RDO command sequence and pgvector table-family boundary are recorded in `../../scripts/README.md`:

1. materialize one table family per window-specific reordered CSV,
2. build pgvector indexes for each family,
3. let the controller switch the queried table name by workload window,
4. keep the SQL KNN path unchanged.

The pgvector switching path is defined by database-side table materialization, vector-index construction, and active table selection.

The local RDO-side binding is represented by `../../rdo/sift1m_pgvector.py` and `../../rdo/pgvector_adapter.py`. SIFT1M queries are divided into workload windows, and each window is assigned the base, IVFFlat, or HNSW table name derived from its QSO layout.

This establishes the following artifact contract without changing SQL search:

| QVLOF stage | pgvector representation | Local boundary |
| --- | --- | --- |
| QSO static layout | reordered CSV | `qso/pgvector_artifact.py` |
| Index materialization | base + IVFFlat + HNSW table family | `load_and_index.py::process_csv_file` |
| RDO layout candidate | one table family per workload window | `rdo/sift1m_pgvector.py::build_window_plan` |
| RDO switch decision | selected table name per window | `rdo/sift1m_pgvector.py::write_window_plan` |
| Runtime search | SQL KNN over the selected table | `run_experiment_ubuntu_final.py::execute_query` |

## Current Boundary

What is already concrete locally:

- static CSV-to-table loading,
- IVFFlat and HNSW index creation,
- query-time logging for pgvector-backed tables.

The adapter materializes the table-selection artifact consumed by the pgvector runtime boundary.
