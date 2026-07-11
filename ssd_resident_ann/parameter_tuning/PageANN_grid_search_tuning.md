# PageANN Grid-Search Tuning Note

## Scope and Evidence Boundary

This file supports the QVLOF rebuttal for Comment 3 and Comment 6. It documents:

- which PageANN parameters are semantically aligned with other disk-resident baselines,
- which parameters are PageANN-specific and therefore only suitable for limited local search,
- which parameters should stay fixed or be treated as auto-derived,
- which entries already have direct local evidence, and
- which final adopted values must still be copied from the actual Pareto-selected run.

This note is a tuning protocol and evidence ledger, not a claim that every listed combination has already been executed.

## Evidence Sources

| Source type | Path / anchor | Used for |
| --- | --- | --- |
| Code analysis | `Origin/PageANN/apps/search_disk_index.cpp` | search-time CLI parameters and defaults |
| Code analysis | `Origin/PageANN/apps/generate_page_graph.cpp` | page-graph parameters |
| Code analysis | `Origin/PageANN/apps/recommend_vamana_graph_degree.cpp` | degree-recommendation stage |
| Code analysis | `Origin/PageANN/apps/utils/generate_hash_buckets.cpp` | hash-routing preprocessing parameters |
| Code analysis | `Origin/PageANN/workflows/scripts/run_pageann_sift100m_pipeline.sh` | workflow defaults and recommended pipeline values |
| Code analysis | `Origin/PageANN/include/defaults.h` | fixed sector length |
| Local paper copy | `Doc and MD/Projects/PageANN/papers/PageANN_Arxiv_2509.25487.pdf` | paper-level protocol statements and memory-ratio context |
| Local run evidence | `BenchResults/pageann_meanios_1m_20260625/pageann_text2image1m.nohup.log` | one executed PageANN build/search configuration |

## Shared Evaluation Constraints

The following are assumed to be controlled at the experiment level and therefore should not be repeated as PageANN-specific tuning axes:

| Item | Status |
| --- | --- |
| dataset / base vectors | shared across all compared methods |
| query set / held-out split | shared across all compared methods |
| ground truth | shared across all compared methods |
| distance metric and data type | shared across all compared methods |
| top-k target | shared across all compared methods |
| thread count | shared across all compared methods |
| total memory or cache budget | shared across all compared methods |

## Parameter Layer Summary

| Parameter | Stage | Role | Common/default value observed locally | Paper / workflow recommendation | Semantically aligned across methods? | Worth scanning? | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `R` | build | Vamana graph degree | code default `64`; 100M workflow `25`; local 1M run `18` | workflow chooses per dataset instead of a single fixed universal value | yes, with DiskANN-style family | yes, but only on shared build axis | should use the shared build-degree candidate set, not a PageANN-only sweep |
| `LBUILD` | build | Vamana build complexity | code default `100`; 100M workflow `150`; local 1M run `100` | workflow uses `150` on SIFT100M | yes | yes, shared build axis | DiskANN-style build-complexity semantics |
| `search_list` / `L` | search | online candidate depth | no CLI default; workflow `60 76 92`; local 1M run `50 70 90` | should be tuned on the shared search-depth grid | yes | yes, primary shared search axis | final choice must come from Pareto point |
| `beamwidth` | search | search beam width | CLI default `5`; workflow `5`; local 1M run `4` | workflow keeps `5` | yes | yes, shared search axis | local run shows evidence that non-default values were tried |
| `num_pages_to_cache` | search | page cache size | CLI default `0`; 100M workflow `10000`; local 1M run `0` | bounded by memory budget, not free extra resource | partially | limited only | cache unit is pages, not nodes |
| `min_degree_per_node` | layout | page-graph density target | required CLI arg; 100M workflow `23`; 1M local run `18` | chosen jointly with `R` and page capacity | no | limited only | should stay centered around recommended/default workflow value |
| `num_PQ_chunks` | layout | page-graph/PQ grouping granularity | required CLI arg; 100M workflow `20`; 1M local run `20` | workflow example uses `20` | no | limited only | distinct from DiskANN `QD` |
| `mem_budget_in_GB` | layout | page-graph construction memory budget | 100M workflow `3.6`; 1M local run `1.0` | tied to experiment budget | no | no, unless budget study | should be controlled globally, not presented as a free axis |
| `full_ooc` | layout | fully out-of-core page-graph build mode | workflow `false`; local 1M run `false` | workflow keeps `false` | no | usually no | binary mode, mainly implementation path selection |
| `use_hash_routing` | routing | enable hash-based routing | CLI default `false`; 100M workflow `true`; local 1M run `false` | workflow uses hash routing in official pipeline | no | limited only | should define comparison family, not be mixed into main Cartesian grid |
| `use_sampled_hash_routing` | routing | sampled-bucket routing | CLI default `false`; 100M workflow `false` | optional routing family | no | limited only | should not be mixed with ordinary layout-only comparison unless declared |
| `radius` | routing | hash routing Hamming radius | CLI default `0`; 100M workflow `1`; local 1M run `1` | workflow uses `1` with routing | no | limited only | only meaningful when routing family is active |
| `sample_ratio` in `generate_hash_buckets` | routing preprocessing | sampled routing bucket coverage | code default `1.0`; workflow subset example `0.5` | `1.0` for full buckets, subset uses workflow-defined ratio | no | limited only | preprocessing helper, not an online search knob |
| `SECTOR_LEN` | fixed | physical page size | `4096` | fixed disk-page alignment | no | no | do not present as an independent tuning axis |
| `QD=0` | auto | auto-derived memory PQ chunk coverage in build | code default `0` | auto behavior | no | no | should be documented as auto-derived, not scanned |

## Shared Candidate Ranges

These are the PageANN parameters that should follow the candidate ranges defined by the rebuttal protocol in the rebuttal protocol.

| Shared axis | PageANN parameter | Recommended harmonized candidate pool | Why shared |
| --- | --- | --- | --- |
| build graph degree | `R` | `{32, 48, 64, 128, 256}` | Vamana-style graph-degree semantics |
| build complexity | `LBUILD` | `{75, 100, 125, 150}` | build-search-width semantics |
| search depth | `search_list` / `L` | `{10, 20, 30, 50, 100, 150, 300, 500, 1000}` | primary Recall-QPS control knob |
| beam width | `beamwidth` | `{4, 8, 16, 32}` | directly controls search frontier width |

## PageANN-Specific Limited Search

These parameters should be explored only in small local neighborhoods around documented workflow values or defaults.

| Parameter | Center value to start from | Suggested limited search | Why limited rather than shared |
| --- | --- | --- | --- |
| `min_degree_per_node` | workflow `23` on SIFT100M; local evidence `18` on 1M run | small neighborhood around the workflow-appropriate value | page-graph density target is PageANN-specific |
| `num_PQ_chunks` | workflow `20`; local evidence `20` | narrow set around current workflow value | PageANN page-graph/PQ organization is not semantically identical to other methods |
| `use_hash_routing` | workflow family `true`; local evidence run `false` | compare fixed families instead of mixing in one grid | routing changes the search family itself |
| `use_sampled_hash_routing` | default/workflow `false` unless sampled routing is explicitly studied | only enable in a separate routing family | preprocessing and online semantics are PageANN-specific |
| `radius` | workflow `1`; code default `0` | small local set around chosen routing family center | only meaningful when routing is active |
| `generate_hash_buckets --sample_ratio` | `1.0` for full buckets, `0.5` for sampled subset in workflow | restricted values around workflow examples | preprocessing parameter, not a main online ANN knob |
| `num_pages_to_cache` | shared memory-budget-constrained center | limited values within the configured cache budget | page cache unit is pages, so it should be budget-normalized |

## Fixed or Auto-Derived Parameters

| Parameter | Value / behavior | Reason not to scan |
| --- | --- | --- |
| `SECTOR_LEN` | `4096` | physical page-size alignment constant |
| `QD` in `build_vamana_disk_index` | `0` auto-derived default | auto-derived build behavior, not a real independent rebuttal axis |
| `build_PQ_bytes` | code default `0` unless explicitly changing build compression path | not part of the main fair-comparison tuning protocol here |
| `use_opq` | default `false` | separate compression family, not part of the main protocol |
| `label_*` / filtered search parameters | default off | outside the non-filtered baseline comparison |
| `stitched_R` and stitched workflow | separate stitched build path | not part of the main PageANN disk-resident comparison family |

## Final Adopted Configuration Backfill Slot

Copy the final reported PageANN configuration here only after the actual Pareto point is selected from the real QVLOF baseline evaluation.

| Field | Status | Value | Evidence |
| --- | --- | --- | --- |
| dataset | experiment record |  | must come from actual reported baseline run |
| metric / dtype | experiment record |  | must match reported setting |
| `R` | experiment record |  | do not infer from workflow default alone |
| `LBUILD` | experiment record |  | do not infer from workflow default alone |
| `min_degree_per_node` | experiment record |  | do not infer from local 1M test alone |
| `num_PQ_chunks` | partially verified | workflow/local evidence `20` exists, but final adopted value still pending | `run_pageann_sift100m_pipeline.sh`; `pageann_text2image1m.nohup.log` |
| `search_list` | experiment record |  | final point must come from Pareto-selected run |
| `beamwidth` | experiment record |  | local run shows `4`, workflow shows `5`; neither should be auto-promoted |
| `num_pages_to_cache` | experiment record |  | must respect the actual comparison budget |
| routing family | experiment record |  | must state whether final result used no routing / hash routing / sampled routing |
| selected-by-Pareto rule | fixed protocol | highest-QPS point near target `Recall@10` | rebuttal protocol rule |

## Direct Local Evidence Already Available

| Evidence type | Confirmed value(s) | Source |
| --- | --- | --- |
| workflow default | `R=25`, `LBUILD=150`, `MIN_DEGREE_PER_NODE=23`, `PQ_CHUNKS=20`, `SEARCH_LS=60 76 92`, `BEAMWIDTH=5`, `NUM_PAGES_TO_CACHE=10000`, `USE_HASH_ROUTING=true`, `RADIUS=1` | `Origin/PageANN/workflows/scripts/run_pageann_sift100m_pipeline.sh` |
| executed local run | `R=18`, `LBUILD=100`, `min_degree_per_node=18`, `num_PQ_chunks=20`, `L in {50,70,90}`, `beamwidth=4`, `num_pages_to_cache=0`, `use_hash_routing=false`, `radius=1` | `BenchResults/pageann_meanios_1m_20260625/pageann_text2image1m.nohup.log` |
| fixed constant | `SECTOR_LEN=4096` | `Origin/PageANN/include/defaults.h` |

## Protocol Summary

For rebuttal use, PageANN should be tuned as follows:

1. Put `R`, `LBUILD`, `search_list`, and `beamwidth` on the shared candidate ranges used by the semantically aligned baselines.
2. Keep page-graph and routing parameters in restricted local search around documented workflow values.
3. Do not pretend that `SECTOR_LEN`, `QD=0`, or other auto-derived/fixed settings are meaningful independent scan axes.
4. Do not copy workflow defaults into the final adopted configuration table unless the selected Pareto point actually used them.
