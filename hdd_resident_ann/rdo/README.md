# RDO Binding for pgvector

RDO binds SIFT1M workload windows to pgvector table families.

The existing RDO controller records layout changes as `(window, layout_path)` entries in `schedule["move"]`. `pgvector_adapter.py` gives those paths pgvector semantics:

```text
<layout path> -> <base table> -> <base table>_ivfflat / <base table>_hnsw
```

For example:

```text
results/window-2-qvlof.csv
  -> window_2_qvlof
  -> window_2_qvlof_ivfflat
  -> window_2_qvlof_hnsw
```

`sift1m_pgvector.py` partitions `sift_query.fvecs` into workload windows and emits the table selected for each window. `pgvector_adapter.py` provides the table-family naming functions used by that plan.

Each workload window has a layout artifact, RDO selects among those artifacts, and the pgvector SQL query implementation remains unchanged.

## Entry Point

```bash
python rdo/sift1m_pgvector.py \
  --query-path dataset/sift/1m/sift/sift_query.fvecs \
  --window-size 200 \
  --layout-prefix sift1m_qvlof \
  --index-type hnsw \
  --output results/rdo/sift1m_pgvector_plan.json
```

The output contains query-window boundaries and the base, IVFFlat, or HNSW table selected for each window.
