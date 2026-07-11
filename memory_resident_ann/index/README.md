# Memory-Resident Index Integrations

This directory contains the QVLOF integration notes for the memory-resident ANN baselines in this branch.

The upstream projects are intentionally kept close to their original layouts. To avoid overwriting third-party `README.md` files, the QVLOF-specific notes live in per-method `QVLOF_README.md` files next to the original sources.

## Covered Systems

- `annoy/`
- `det-lsh/`
- `hnsw/`
- `ivfpq/`
- `lsh-apg/`
- `mirage/`
- `ogp/`
- `pg_vector/`

## QSO/RDO Integration Granularity

The integration boundary is not identical across methods. QSO is always a static layout binding. RDO is always a dynamic multi-layout or multi-window binding. The concrete attachment point depends on how each baseline consumes data.

| System | Upstream / reference repository | QVLOF note | Static QSO binding | Dynamic RDO binding | Runtime path kept unchanged |
| --- | --- | --- | --- | --- | --- |
| Annoy | `https://github.com/spotify/annoy` | `annoy/QVLOF_README.md` | reorder base CSV before `add_item()` / `build()` | rebuild one Annoy index per window-specific reordered CSV | `get_nns_by_vector()` / `get_nns_by_item()` |
| DET-LSH | `https://github.com/WeiJiuQi/DET-LSH` | `det-lsh/QVLOF_README.md` | reorder base CSV before `DETLSHIndex.build()` | rebuild window-specific DET-LSH trees for each layout candidate | `DETLSHIndex.query()` |
| HNSW | `https://github.com/nmslib/hnswlib` for the algorithm, with local FAISS-based harness on top of `https://github.com/facebookresearch/faiss` | `hnsw/QVLOF_README.md` | feed QSO-reordered CSV into the local `IndexHNSWFlat` build path | evaluate multiple reordered CSV layouts through `hnsw_dynamic_window_batch.cpp` | HNSW `search()` |
| IVF-PQ | `https://github.com/facebookresearch/faiss` | `ivfpq/QVLOF_README.md` | feed QSO-reordered CSV into the local `IndexIVFPQ` build path | evaluate multiple reordered CSV layouts through `ivfpq_dynamic_window_batch.cpp` | IVF-PQ `search()` / rerank path |
| LSH-APG | local code mirrors `https://github.com/Jacyhust/LSH-APG` | `lsh-apg/QVLOF_README.md` | replace the input `.data` file or dataset alias consumed by `divGraph` build | maintain one built graph/index folder per workload window | `graphSearch(...)` on `divGraph` / `fastGraph` |
| MIRAGE | local code mirrors `https://github.com/dsg-uwaterloo/mirage` | `mirage/QVLOF_README.md` | feed QSO-reordered CSV into the local `IndexMirage` build path | evaluate multiple reordered CSV layouts through `mirage_dyanmic_window_batch.cpp` | MIRAGE `search()` |
| OGP | `https://github.com/larsgottesbueren/gp-ann` | `ogp/QVLOF_README.md` | use QSO reorder as pre-partition data order or as routing/partition preprocessing | switch among multiple partition files / shard layouts per window | `QueryAttribution` / `SmallScaleQueries` |
| pgvector | `https://github.com/pgvector/pgvector` | `pg_vector/QVLOF_README.md` | load a QSO-reordered CSV as a new table and build pgvector indexes on top | switch among multiple reordered tables or table families across windows | SQL KNN query path |

## What Is Already Present Locally

The repository already contains two useful classes of evidence:

1. Static QSO evaluation scripts:
   - `memory_resident_ann/scripts/static_memory_sh/`
2. Dynamic / windowed evaluation scripts:
   - `memory_resident_ann/scripts/dynamic_memory_sh/`

Those scripts show that, for the memory-resident baselines, the practical QSO contract is usually:

- QSO emits a reordered base-vector file,
- the baseline rebuilds its index on that reordered file,
- the search path stays unchanged.

RDO extends this layout contract to a set of window-specific layouts and chooses among them over time.

## Naming Convention

Per-method notes use `QVLOF_README.md` instead of replacing the upstream `README.md`. This keeps:

- the original project documentation intact,
- the QVLOF adaptation guidance local and explicit,
- the ownership boundary clear between upstream code and this repository's integration logic.
