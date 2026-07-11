# QSO Binding for pgvector

QSO binds to pgvector before table loading and index construction.

`static_layout_main.py` reads SIFT1M base and query vectors, produces the QVLOF permutation, reorders the base vectors, and passes the result to `pgvector_artifact.py`. The artifact writer emits:

- a CSV with columns `id, v0, v1, ...`, compatible with `index/pg_vector/load_and_index.py`;
- a `.pgvector.json` manifest describing the base, IVFFlat, and HNSW table names derived from that CSV.

The artifact naming follows PostgreSQL table-identifier rules and preserves the reordered CSV as the index-construction input.

The pgvector query implementation is not changed by QSO. QSO only changes the row insertion order used before pgvector builds IVFFlat or HNSW indexes.

## Entry Point

```bash
python qso/static_layout_main.py \
  --dataset-dir dataset/sift/1m/sift \
  --output-dir results/qso/sift1m \
  --layout-name sift1m_qvlof
```

`AG.py`, `COV.py`, `LGPF.py`, `LGPF_q2d.py`, and `k_means.py` contain the QVLOF algorithm components used by the entrypoint. The other Python files retain method-development and analysis utilities.
