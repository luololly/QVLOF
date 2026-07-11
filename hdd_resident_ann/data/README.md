# SIFT1M Data

This directory prepares the SIFT1M inputs used by the pgvector, QSO, and RDO components in this branch.

## Download

```bash
python data/dataset_download.py
```

The archive is extracted under:

```text
dataset/sift/1m/sift/
├── sift_base.fvecs
├── sift_query.fvecs
├── sift_groundtruth.ivecs
└── sift_learn.fvecs
```

## Data Roles

| File | Role |
| --- | --- |
| `sift_base.fvecs` | base vectors reordered by QSO and loaded into pgvector |
| `sift_query.fvecs` | query vectors used for QSO training and RDO workload windows |
| `sift_groundtruth.ivecs` | exact neighbors used for Recall evaluation |
| `sift_learn.fvecs` | optional training vectors for index-specific preparation |

## pgvector Layout Artifacts

QSO writes reordered CSV files with the following schema:

```text
id,v0,v1,...,v127
```

`index/pg_vector/load_and_index.py` loads each CSV into a table family:

```text
<layout>
<layout>_ivfflat
<layout>_hnsw
```

RDO associates workload windows with these table families through `rdo/pgvector_adapter.py`.
