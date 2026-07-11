# HDD-Resident Execution Commands

This directory records the command-level entrypoints for the SIFT1M, QSO, pgvector, and RDO workflow in this branch. The executable implementations remain in their owning modules so that data preparation, layout generation, database construction, and layout selection each have a single source entrypoint.

## Data Preparation

```bash
python data/dataset_download.py
```

This prepares the SIFT1M base vectors, query vectors, ground truth, and learning vectors under `dataset/sift/1m/sift/`.

## Static QSO Layout

```bash
python qso/static_layout_main.py \
  --dataset-dir dataset/sift/1m/sift \
  --output-dir results/qso/sift1m \
  --layout-name sift1m_qvlof
```

The QSO entrypoint generates a reordered CSV and a pgvector table-family manifest through `qso/pgvector_artifact.py`.

## pgvector Table Families

```bash
python index/pg_vector/load_and_index.py
```

Each reordered CSV is materialized as:

```text
<layout>
<layout>_ivfflat
<layout>_hnsw
```

## pgvector Query Evaluation

```bash
python index/pg_vector/run_experiment_ubuntu_final.py
```

The query entrypoint selects table names from `index/pg_vector/config.py` and executes the SQL KNN path for SIFT1M queries.

## Dynamic RDO Layout Selection

```bash
python rdo/sift1m_pgvector.py \
  --query-path dataset/sift/1m/sift/sift_query.fvecs \
  --window-size 200 \
  --layout-prefix sift1m_qvlof \
  --index-type hnsw \
  --output results/rdo/sift1m_pgvector_plan.json
```

RDO records window-specific layout choices. `rdo/pgvector_adapter.py` maps each selected layout to its base, IVFFlat, or HNSW table name.

## Entry Point Ownership

| Stage | Entry point |
| --- | --- |
| SIFT1M preparation | `data/dataset_download.py` |
| QSO layout generation | `qso/static_layout_main.py` |
| pgvector CSV import and index construction | `index/pg_vector/load_and_index.py` |
| pgvector query evaluation | `index/pg_vector/run_experiment_ubuntu_final.py` |
| RDO workload windows and layout selection | `rdo/sift1m_pgvector.py` |
| RDO-to-pgvector table mapping | `rdo/pgvector_adapter.py` |
