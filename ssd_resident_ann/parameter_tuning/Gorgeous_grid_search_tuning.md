# Gorgeous Grid-Search Tuning Note

## Scope and Evidence Boundary

This note documents the Gorgeous tuning protocol for the QVLOF rebuttal. It separates:

- shared DiskANN-style build/search axes,
- Gorgeous-private graph-priority, graph-replication, and filtering/search-family controls,
- fixed page-size or substrate settings that should not be promoted into fake scan axes, and
- directly verified local settings versus still-pending final Pareto-point backfill.

## Evidence Sources


| Source type        | Path / anchor                                                                                            | Used for                                                          |
| ------------------ | -------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| Code analysis      | `Origin/Gorgeous/tests/search_disk_index.cpp`                                                            | search-time CLI parameters and defaults                           |
| Code analysis      | `Origin/Gorgeous/tests/build_disk_index.cpp`                                                             | build-side defaults                                               |
| Code analysis      | `Origin/Gorgeous/scripts/config_local.sh`                                                                | local script defaults                                             |
| Code analysis      | `Origin/Gorgeous/scripts/README.md`                                                                      | recommended parameter interpretations and representative defaults |
| Repository README  | `Origin/Gorgeous/README.md`                                                                              | paper-facing default descriptions                                 |
| Paper text         | `Doc and MD/Paper Library/Data Agents/future/papers/Gorgeous.pdf`                                        | paper terminology, sensitivity anchors, and evidence boundaries   |
| Local result table | `BenchResults/gorgeous_repro_sift1m_20260627/clean_tables/gorgeous_sift1m_full_sweep_clean.csv`          | executed sweep on one local setting family                        |
| Local result table | `BenchResults/gorgeous_repro_sift1m_20260627/clean_tables/gorgeous_sift1m_matched_clean.csv`             | one matched-recall adopted local point                            |
| Local result table | `BenchResults/gorgeous_meanios_1m_fullfeatures_20260629/gorgeous_fullfeatures_search_points_summary.csv` | executed full-features search points                              |
| Local result table | `BenchResults/gorgeous_meanios_1m_fullfeatures_20260629/gorgeous_fullfeatures_search_points_picks.csv`   | matched local picks on several 1M datasets                        |

## Shared Evaluation Constraints


| Item                                 | Status                             |
| ------------------------------------ | ---------------------------------- |
| dataset / query split / ground truth | shared across all compared methods |
| distance metric / data type          | shared across all compared methods |
| top-k target                         | shared across all compared methods |
| thread count                         | shared across all compared methods |
| total memory or cache budget         | shared across all compared methods |

## Parameter Layer Summary


| Parameter                    | Stage                         | Role                                    | Common/default value observed locally                                                                                                  | Paper / workflow recommendation                                                        | Semantically aligned across methods? | Worth scanning?                 | Notes                                                         |
| ---------------------------- | ----------------------------- | --------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- | ------------------------------------ | ------------------------------- | ------------------------------------------------------------- |
| `R`                          | build                         | disk-graph degree                       | code default`64`; script default `64`                                                                                                  | standard build-degree choice in local scripts                                          | yes                                  | yes, shared build axis          | aligned with DiskANN-style family                             |
| `BUILD_L`                    | build                         | disk-graph build complexity             | code default`100`; script default `128`                                                                                                | local script uses`128`                                                                 | yes                                  | yes, shared build axis          | aligned build complexity knob                                 |
| `LS`                         | search                        | online candidate depth                  | script default`"50 100"`; local sweeps include `50/100/150/...`                                                                        | should follow shared search-depth protocol                                             | yes                                  | yes, primary shared search axis | one of the main Recall-QPS knobs                              |
| `beamwidth` / `BM_LIST`      | search                        | search frontier width                   | CLI default`2`; script default `8`; local sweep tables show `5` in repro/full-feature runs                                             | shared beam candidate set                                                              | yes                                  | yes                             | distinguish code default from actual benchmark family         |
| `N_PQ_CODE`                  | build                         | PQ code compression ratio               | dataset config default`4` for single-modal; `2` for multi-modal                                                                        | scripts README explicitly recommends`4` single-modal, `2` multi-modal                  | no                                   | limited only                    | Gorgeous-private build/compression choice                     |
| `MEM_R`                      | build (memory nav graph)      | memory navigation graph degree          | script default`24`                                                                                                                     | part of Gorgeous memory-graph default family                                           | partially                            | limited only                    | private memory-graph parameter                                |
| `MEM_BUILD_L`                | build (memory nav graph)      | memory-nav build complexity             | script default`128`                                                                                                                    | local default family                                                                   | partially                            | limited only                    | private memory-graph parameter                                |
| `MEM_RAND_SAMPLING_RATE`     | build (memory nav graph)      | memory sample fraction                  | script default`0.005`; README says 0.5% is representative paper setting                                                                | README/paper-facing guidance recommends 0.5% representative setting                    | no                                   | limited only                    | Gorgeous-private memory-graph fraction                        |
| `MEM_L`                      | search                        | in-memory navigation depth              | script default`0`, but some local full-feature runs use `32`                                                                           | local families show both zero and non-zero memory-nav setups                           | no                                   | limited only                    | family-strength control                                       |
| `DECO_IMPL`                  | search family                 | enable Gorgeous search implementation   | script default`1`                                                                                                                      | Gorgeous main family uses`1`                                                           | no                                   | family split only               | determines whether search path is Gorgeous vs fallback family |
| `USE_DISK_GRAPH_CACHE_INDEX` | search family / layout family | graph-replicated layout switch          | script default`1`                                                                                                                      | main Gorgeous full mode uses`1`                                                        | no                                   | family split only               | search family and layout family selector                      |
| `USE_PAGE_SEARCH`            | search family                 | page-search fallback switch             | script default`1`                                                                                                                      | needed for Starling-like and Gorgeous modes                                            | no                                   | family split only               | should stay fixed within a family                             |
| `PQ_FILTER_RATIO`            | filtering                     | PQ-based early filtering ratio in `page_search(...)` | script default`0.9`                                                                                                                    | script family centers on `0.9`, but this knob is only effective on the non-graph-replicated Gorgeous search path | no                                   | limited only                    | private filtering axis; not evidenced by current graph-replicated full-feature runs |
| `PS_USE_RATIO`               | search                        | page-search usage ratio                 | script default`0.3`                                                                                                                    | local repro family uses`0.3`                                                           | no                                   | limited only                    | private online ratio                                          |
| `MEM_GRAPH_USE_RATIO`        | caching / search              | fraction of graph cached in memory      | script default`0.0`                                                                                                                    | README says set explicitly when reproducing graph-prioritized memory-cache experiments | no                                   | limited only                    | private memory-allocation axis                                |
| `MEM_EMB_USE_RATIO`          | caching / search              | fraction of embeddings cached in memory | script default`0.0`                                                                                                                    | README default`0.0`                                                                    | no                                   | limited only                    | private memory-allocation axis                                |
| `EMB_SEARCH_RATIO`           | search                        | embedding refinement ratio              | script config local`0.5`; scripts README text still mentions default `0.4`; full-feature local command families use their own settings | representative default around paper sigma                                              | no                                   | limited only                    | private search/refinement ratio                               |
| `SECTOR_LEN`                 | fixed                         | ordinary disk-page size                 | dataset config default`4096`                                                                                                           | fixed page alignment                                                                   | no                                   | no                              | physical page-size constant                                   |
| `GR_SECTOR_LEN`              | fixed                         | graph-replicated layout page size       | dataset config default`4096`                                                                                                           | fixed page alignment                                                                   | no                                   | no                              | physical page-size constant                                   |

## Paper-Term Mapping and Sensitivity Anchors


| Code parameter | Paper term / mechanism | What the paper actually analyzes | Main anchor | Tuning implication |
| -------------- | ---------------------- | -------------------------------- | ----------- | ------------------ |
| `MEM_GRAPH_USE_RATIO` | graph cache / graph-prioritized memory cache | not scanned as an independent named ratio; the paper varies overall `memory ratio` and shows that more memory benefits the graph cache strongly | §3.3, Figure 6, §4.1 memory cache planning, Figure 12 | treat as a derived implementation knob under a fixed total memory budget; do not promote it to a fully free global axis |
| `MEM_EMB_USE_RATIO` | node cache / vector cache | not scanned as an independent named ratio; the paper states exact vectors are stored only if memory remains after compressed vectors, navigation index, and graph cache | Figure 9 memory layout, §4.1 memory cache planning, Figure 12 discussion | keep centered at `0.0` unless graph cache is already saturated under the target memory budget |
| `EMB_SEARCH_RATIO` | refinement ratio `sigma` | directly analyzed as a sensitivity axis together with queue size `D` | §3.2, Figure 5 | this is a real search-time tuning knob; bounded local search around `0.5` is paper-aligned |

Key paper reading:

- `EMB_SEARCH_RATIO` is the cleanest one: the paper defines refinement ratio `sigma`, uses `D_r = sigma D`, and reports Figure 5 showing that a moderate `sigma` such as `0.5` preserves recall at sufficiently large queue sizes.
- `MEM_GRAPH_USE_RATIO` and `MEM_EMB_USE_RATIO` are implementation-layer controls in the released code, but the paper narrative is not "scan two independent ratios." The paper instead varies the total memory budget and then prioritizes graph cache first, only using leftover memory for node/vector cache.
- Therefore, for rebuttal wording, it is safer to describe these as local realization knobs for Gorgeous's memory planner, not as paper-validated cross-method primary axes.

## Detailed Audit of the Seven Gorgeous-Specific Parameters


| Parameter | Stage | Actual role in code | Main code anchor | Paper term / paper-side interpretation | Default / common script value | Really worth scanning? | Recommended rebuttal treatment |
| --------- | ----- | ------------------- | ---------------- | -------------------------------------- | ----------------------------- | ---------------------- | ------------------------------ |
| `N_PQ_CODE` | build | controls PQ compression granularity for the in-memory compressed vectors; code converts it into `num_pq_chunks = ceil(dim / N_PQ_CODE)`, i.e. compressed bytes per vector | `scripts/config_dataset.sh`; `src/aux_utils.cpp` | compression ratio of the compressed vectors in §3.1 / Figure 4 | README recommends `4` for single-modal, `2` for multi-modal; local dataset configs default to `4` | yes, but only as a small build-side local axis | a real Gorgeous-private build parameter; use `{2,4}` or dataset-aware `{4}` single-modal / `{2}` multi-modal rather than a wide generic sweep |
| `PQ_FILTER_RATIO` | search / filtering | early page-level PQ pruning threshold inside `page_search(...)`: if a candidate's PQ distance is worse than the current tail times this ratio, it may be skipped | `src/gorgeous/index_search.cpp` | no clear paper-facing named axis; implementation-side heuristic | local script center `0.9`; repro script uses `0.9` | only conditionally | scan only on the non-graph-replicated Gorgeous path; current graph-replicated main path does not consume it in-body, so do not present it as a validated main-axis sweep |
| `MEM_GRAPH_USE_RATIO` | search / caching | loads a fraction of graph nodes / adjacency into memory; implemented as `n_cached_id = floor(num_points * ratio)` when `< 1` | `src/gorgeous/deco_index.cpp`; `tests/search_disk_index.cpp` | graph cache / graph-prioritized memory cache | local config default `0.0`; some full-feature scripts use `0.5` | limited only | implementation-level cache-loading ratio, not a paper-native independent axis; keep as a small local split knob under fixed family settings |
| `MEM_EMB_USE_RATIO` | search / caching | loads a fraction of exact embeddings into memory; implemented as `n_cached_nodes = floor(num_points * ratio)` when `< 1` | `src/gorgeous/deco_index.cpp`; `tests/search_disk_index.cpp` | node cache / vector cache | local config default `0.0`; some full-feature scripts use `0.5` | limited only | implementation-level vector-cache knob; not a paper-native independent axis; keep near `0.0` unless explicitly probing leftover-memory cases |
| `EMB_SEARCH_RATIO` | search / refinement | sets `embedding_search_L = max(k, floor(cur_list_size * ratio))`; this determines how many top approximate candidates are refined with exact vectors | `src/gorgeous/index_search.cpp`; `src/gorgeous/index_search_dup_graph.cpp` | refinement ratio `sigma` in §3.2 / Figure 5 | config local `0.5`; repro script `0.4`; some full-feature scripts `0.5` | yes, bounded local sweep | real search-time axis with direct paper support; use the paper-aligned set `{0.2,0.4,0.6,0.8,1.0}` |
| `DECO_IMPL` | search family switch | switches from Starling/DiskANN search implementation to Gorgeous search implementation | `tests/search_disk_index.cpp`; `scripts/README.md` | "Gorgeous search method" vs Starling search | local default `1` | no, not as a numeric tuning axis | family selector, not a normal scan axis; use it only to define comparison families |
| `USE_DISK_GRAPH_CACHE_INDEX` | layout family switch | switches whether `DecoIndex` loads and searches the graph-replicated disk layout or the Starling layout | `src/gorgeous/deco_index.cpp`; `tests/search_disk_index.cpp`; `scripts/README.md` | graph-replicated disk block vs Starling layout | local default `1` | no, not as a numeric tuning axis | family selector, not a normal scan axis; use it only to define layout families |

### Parameter-by-Parameter Notes

1. `N_PQ_CODE`

- This is the cleanest build-side private parameter.
- It is not a generic "more is better" knob. Larger `N_PQ_CODE` means fewer PQ bytes per vector are needed under the configured dimension-chunking rule, but the repo guidance is already dataset-typed:
  - single-modal: `4`
  - multi-modal: `2`
- The paper's matching concept is the compression ratio study in Figure 4, but the code exposes it through `N_PQ_CODE`, not through a direct byte-ratio parameter.

2. `PQ_FILTER_RATIO`

- This parameter is easy to over-claim.
- It is active in `page_search(...)`, where it prunes page-local candidates using PQ distances before they are inserted into the frontier.
- However, the current main Gorgeous family in our local full-feature scripts uses graph-replicated search, which routes to `page_search_dup_graph(...)`.
- In that graph-replicated function, `pq_filter_ratio` appears in the signature but has no in-body use site in the current code snapshot.
- Therefore this parameter is not a stable main-axis choice for the current Gorgeous full mode.

3. `MEM_GRAPH_USE_RATIO`

- In code, this is simply "what fraction of node IDs/adjacency structures to cache in memory".
- It is not tied to an explicit total-memory-budget checker in the search CLI.
- It also does not automatically consume "all remaining memory after compressed vectors and nav index" as the paper narrative suggests. That graph-first planning is a paper-level workflow, not a hard runtime constraint in the released search CLI.

4. `MEM_EMB_USE_RATIO`

- This is more restricted in practice than it first appears.
- It is only loaded inside the `if (mem_graph_use_ratio > 0)` branch, so `mem_graph_use_ratio=0, mem_emb_use_ratio>0` does not act like a fully independent "embedding-only cache" configuration in the current loading path.
- Also, the code does not enforce `MEM_GRAPH_USE_RATIO + MEM_EMB_USE_RATIO <= 1` or `== 1`.
- So these two are not complementary split ratios; they are separate loading ratios with asymmetric gating.

5. `EMB_SEARCH_RATIO`

- This is the most paper-grounded private search knob.
- It is exactly the refinement ratio idea in Figure 5: refine only the top `sigma * D` approximate candidates.
- The local script discrepancy (`0.4` in one repro script vs `0.5` in config/full-feature scripts) should be described as workflow variation, not as a contradiction in the algorithm.

6. `DECO_IMPL`

- This is not a "tunable hyperparameter" in the ordinary sense.
- It selects whether the repo uses Gorgeous search code or falls back to the inherited Starling/DiskANN family.
- Treating `{0,1}` as an ordinary scan axis would incorrectly mix method identity with within-method tuning.

7. `USE_DISK_GRAPH_CACHE_INDEX`

- This is also not a normal tuning axis.
- It changes the layout family from Starling-style page layout to Gorgeous graph-replicated layout.
- In practice, this means changing both the on-disk artifact loaded and the search path used.
- It should therefore be treated as a family definition switch, not an online hyperparameter.

### Bottom-Line Classification


| Class | Parameters | Why |
| ----- | ---------- | --- |
| real Gorgeous-private build/search knobs worth bounded tuning | `N_PQ_CODE`, `EMB_SEARCH_RATIO` | both have clear algorithmic meaning and real code effect; `EMB_SEARCH_RATIO` also has direct paper sensitivity evidence |
| implementation-level cache loading knobs, worth only restricted local probing | `MEM_GRAPH_USE_RATIO`, `MEM_EMB_USE_RATIO` | real code effect, but not paper-native independent axes and not tied to an explicit unified search-memory-budget parameter |
| heuristic knob with path-dependent validity | `PQ_FILTER_RATIO` | real effect only on the non-graph-replicated path in the current code snapshot |
| family selectors, not ordinary scan axes | `DECO_IMPL`, `USE_DISK_GRAPH_CACHE_INDEX` | define method/layout/search family identity rather than within-family tuning |

## Shared Candidate Ranges


| Shared axis        | Gorgeous parameter      | Recommended harmonized candidate pool | Why shared                                              |
| ------------------ | ----------------------- | ------------------------------------- | ------------------------------------------------------- |
| build graph degree | `R`                     | `{32, 48, 64, 128, 256}`              | DiskANN-style graph-degree role |
| build complexity   | `BUILD_L`               | `{75, 100, 125, 150}`                 | Vamana-style build-width role                   |
| search depth       | `LS`                    | `{10, 20, 30, 50, 100, 150, 300, 500, 1000}` | primary online Recall-QPS control                 |
| beam width         | `beamwidth` / `BM_LIST` | `{4, 8, 16, 32}`                     | direct online frontier-width control                    |

## Gorgeous-Specific Limited Search


| Parameter                | Center value to start from                                                                | Suggested limited search                     | Why limited rather than shared                |
| ------------------------ | ----------------------------------------------------------------------------------------- | -------------------------------------------- | --------------------------------------------- |
| `N_PQ_CODE`              | `4` for single-modal, `2` for multi-modal                                                 | very small set around README recommendations | Gorgeous-private build/compression choice     |
| `MEM_R`                  | script default`24`                                                                        | narrow local neighborhood                    | private memory-navigation graph structure     |
| `MEM_BUILD_L`            | script default`128`                                                                       | narrow local neighborhood                    | private memory-navigation graph build quality |
| `MEM_RAND_SAMPLING_RATE` | script default and paper-facing representative setting`0.005`                             | restricted local values around this center   | private memory sample fraction                |
| `MEM_L`                  | family center depends on run family (`0` in repro family, `32` in some full-feature runs) | small local set within chosen family         | memory-navigation strength control            |
| `PQ_FILTER_RATIO`        | script default`0.9`                                                                       | `{0.8, 0.9, 1.0}` around the script center, but only on the non-graph-replicated Gorgeous path where `page_search(...)` actually consumes it | private online filtering ratio                |
| `PS_USE_RATIO`           | script default`0.3`                                                                       | bounded local neighborhood                   | private page-search ratio                     |
| `MEM_GRAPH_USE_RATIO`    | script default`0.0`; paper conceptually prioritizes graph cache under a fixed memory budget | restricted implementation-level set `{0.0, 0.5, 1.0}` | implementation-level graph-cache allocation knob |
| `MEM_EMB_USE_RATIO`      | script default`0.0`; paper uses vector/node cache only after graph cache planning         | restricted implementation-level set `{0.0, 0.5, 1.0}` | implementation-level vector-cache allocation knob |
| `EMB_SEARCH_RATIO`       | center near paper `sigma = 0.5` with config-local`0.5` / README text `0.4`               | paper-aligned candidate set `{0.2, 0.4, 0.6, 0.8, 1.0}` | private refinement ratio with direct paper sensitivity evidence |

## Search Family Split

These switches define comparison families and should not be mixed into one exhaustive Cartesian grid.


| Family                                         | `DECO_IMPL` | `USE_DISK_GRAPH_CACHE_INDEX` | `USE_PAGE_SEARCH` | Meaning                                                 |
| ---------------------------------------------- | ----------- | ---------------------------- | ----------------- | ------------------------------------------------------- |
| DiskANN-like fallback                          | `0`         | `0`                          | `0`               | fallback family, not main Gorgeous mode                 |
| Starling-like fallback                         | `0`         | `0`                          | `1`               | Starling-style layout/search family                     |
| Gorgeous search on non-replicated graph layout | `1`         | `0`                          | `1`               | Gorgeous search family without graph-replicated storage |
| Gorgeous full mode                             | `1`         | `1`                          | `1`               | main Gorgeous family                                    |

`PQ_FILTER_RATIO` evidence boundary: current local `fullfeatures` 1M runs use `DECO_IMPL=1` and `USE_DISK_GRAPH_CACHE_INDEX=1`, which routes execution to `page_search_dup_graph(...)`. The current code path does not consume `pq_filter_ratio` inside that function body, so local `pq08/pq09` graph-replicated probe logs should not be treated as valid parameter-effect evidence for this knob.

## Fixed or Auto-Derived Parameters


| Parameter                                                      | Value / behavior                                               | Reason not to scan                                       |
| -------------------------------------------------------------- | -------------------------------------------------------------- | -------------------------------------------------------- |
| `SECTOR_LEN`                                                   | `4096`                                                         | physical page-size alignment constant                    |
| `GR_SECTOR_LEN`                                                | `4096`                                                         | physical page-size alignment constant                    |
| `CACHE` / node-cache count when fixed to zero in main families | fixed by family/budget                                         | do not inflate into an extra unconstrained resource axis |
| relayout`mode` values                                          | determined by chosen family (`gp`, `split_graph`, `gr_layout`) | family definition, not online tuning                     |

## Final Adopted Configuration Backfill Slot


| Field                        | Status             | Value                                                                                     | Evidence                                                |
| ---------------------------- | ------------------ | ----------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| dataset                      | experiment record   |                                                                                           | must come from actual reported baseline run             |
| metric / dtype               | experiment record   |                                                                                           | must match reported setting                             |
| `R`                          | partially verified | `64` in local script/result families                                                      | config and local result paths                           |
| `BUILD_L`                    | partially verified | `128` in local script/result families                                                     | config and local result paths                           |
| `LS`                         | partially verified | local evidence includes`50/100/150/...`; specific selected value depends on target recall | local result tables                                     |
| `beamwidth`                  | partially verified | local repro/full-feature tables show`5`; script default file shows `8`                    | local result tables and config file                     |
| `N_PQ_CODE`                  | partially verified | `4` recommended for single-modal; `2` for multi-modal                                     | `scripts/README.md`                                     |
| `MEM_R`                      | partially verified | `24`                                                                                      | `scripts/config_local.sh`                               |
| `MEM_BUILD_L`                | partially verified | `128`                                                                                     | `scripts/config_local.sh`                               |
| `MEM_RAND_SAMPLING_RATE`     | partially verified | `0.005`                                                                                   | `scripts/config_local.sh`; README                       |
| `MEM_L`                      | partially verified | `0` in repro family; `32` in some full-feature points                                     | local result tables                                     |
| `DECO_IMPL`                  | partially verified | `1` for main Gorgeous family                                                              | `scripts/config_local.sh`                               |
| `USE_DISK_GRAPH_CACHE_INDEX` | partially verified | `1` for main Gorgeous family                                                              | `scripts/config_local.sh`                               |
| `PQ_FILTER_RATIO`            | partially verified | script center `0.9`; parameter-effect evidence still pending on the non-graph-replicated path | `scripts/config_local.sh`; `tests/search_disk_index.cpp`; `src/gorgeous/index_search.cpp`; `src/gorgeous/index_search_dup_graph.cpp` |
| `PS_USE_RATIO`               | partially verified | `0.3`                                                                                     | `scripts/config_local.sh`; repro result log naming      |
| `MEM_GRAPH_USE_RATIO`        | partially verified | `0.0` in local config                                                                     | `scripts/config_local.sh`                               |
| `MEM_EMB_USE_RATIO`          | partially verified | `0.0` in local config                                                                     | `scripts/config_local.sh`                               |
| `EMB_SEARCH_RATIO`           | partially verified | config-local`0.5`, README text references `0.4` representative default                    | config + README                                         |
| final Pareto-selected tuple  | experiment record   |                                                                                           | must come from the actual reported baseline curve/point |

## Direct Local Evidence Already Available


| Evidence type                | Confirmed value(s)                                                                                                                                                                                                                                                                                                       | Source                                                                      |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------- |
| repository guidance          | `N_PQ_CODE=4` for single-modal, `2` for multi-modal; `MEM_GRAPH_USE_RATIO` and `MEM_EMB_USE_RATIO` default `0.0`; `USE_DISK_GRAPH_CACHE_INDEX=1`; `DECO_IMPL=1`                                                                                                                                                          | `Origin/Gorgeous/scripts/README.md`                                         |
| script default               | `R=64`, `BUILD_L=128`, `MEM_R=24`, `MEM_BUILD_L=128`, `MEM_RAND_SAMPLING_RATE=0.005`, `BM_LIST=(8)`, `MEM_L=0`, `DECO_IMPL=1`, `MEM_GRAPH_USE_RATIO=0.0`, `MEM_EMB_USE_RATIO=0.0`, `EMB_SEARCH_RATIO=0.5`, `USE_DISK_GRAPH_CACHE_INDEX=1`, `PQ_FILTER_RATIO=0.9`, `USE_PAGE_SEARCH=1`, `PS_USE_RATIO=0.3`, `LS="50 100"` | `Origin/Gorgeous/scripts/config_local.sh`                                   |
| executed repro sweep         | on one local SIFT1M family,`beamwidth=5`, `L in {50,100,150}`, `PS_USE_RATIO=0.3`, matched local point at `L=100`, `Recall@10=99.8`                                                                                                                                                                                      | `gorgeous_sift1m_full_sweep_clean.csv`, `gorgeous_sift1m_matched_clean.csv` |
| executed full-features picks | local matched points exist for several 1M datasets, e.g. text2image1m matched at`L=250`, `BW=5`, `Recall@10=99.0` in one full-features family                                                                                                                                                                            | `gorgeous_fullfeatures_search_points_picks.csv`                             |
| code-path audit              | `PQ_FILTER_RATIO` is applied in `page_search(...)`, but current full-feature graph-replicated runs route to `page_search_dup_graph(...)`, where the parameter currently has no in-body use site | `Origin/Gorgeous/tests/search_disk_index.cpp`, `Origin/Gorgeous/src/gorgeous/index_search.cpp`, `Origin/Gorgeous/src/gorgeous/index_search_dup_graph.cpp` |
