# Starling Grid-Search Tuning Note

## Scope and Evidence Boundary

This note documents the Starling tuning protocol for the QVLOF rebuttal. It separates:

- shared build/search knobs that can be aligned with the other DiskANN-style baselines,
- Starling-private page-search, navigation-graph, and partition parameters,
- fixed or auto-derived settings that should not be promoted into fake scan axes, and
- the gap between script defaults, paper defaults, and final Pareto-selected adopted values.

## Evidence Sources

| Source type | Path / anchor | Used for |
| --- | --- | --- |
| Code analysis | `Origin/Starling/tests/search_disk_index.cpp` | online search parameters and defaults |
| Code analysis | `Origin/Starling/tests/build_disk_index.cpp` | build-side defaults |
| Code analysis | `Origin/Starling/scripts/config_local.sh` | commonly used local script defaults |
| Code analysis | `Origin/Starling/scripts/run_benchmark.sh` | stage wiring and benchmark-time variable flow |
| Local paper copy | `Doc and MD/Projects/Starling/papers/Starling_Arxiv_2401.02116.pdf` | paper-level default protocol and parameter tables |
| Local run evidence | `BenchResults/starling_meanios_1m_20260624/deep1m/build.log` | executed build configuration |
| Local run evidence | `BenchResults/starling_meanios_1m_20260624/deep1m/gp_partition.log` | executed graph-partition configuration |
| Local run evidence | `BenchResults/starling_meanios_1m_20260624/deep1m/relayout.log` | executed relayout configuration |

## Shared Evaluation Constraints

| Item | Status |
| --- | --- |
| dataset / query split / ground truth | shared across all compared methods |
| distance metric / data type | shared across all compared methods |
| top-k target | shared across all compared methods |
| thread count | shared across all compared methods |
| total memory or cache budget | shared across all compared methods |

## Parameter Layer Summary

| Parameter | Stage | Role | Common/default value observed locally | Paper / workflow recommendation | Semantically aligned across methods? | Worth scanning? | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `R` | build | disk-graph degree | code default `64`; local build evidence `32`; script default `64` | paper appendix gives method-specific values per dataset | yes | yes, shared build axis | use shared build-degree range for fair tuning |
| `BUILD_L` | build | disk-graph build complexity | code default `100`; script default `125`; local build evidence `70` | paper tables report per-dataset chosen values | yes | yes, shared build axis | do not force one global fixed value across all datasets |
| `LS` | search | online candidate depth | no CLI default; script default `"150"` | shared search-depth sweep should be used | yes | yes, primary shared search axis | one of the main Recall-QPS knobs |
| `beamwidth` / `BM_LIST` | search | search frontier width | CLI default `2`; script default `5`; paper experiments use tuned settings | shared beam set | yes | yes | distinguish CLI validation default from experiment script default |
| `MEM_R` | build (memory nav graph) | memory navigation graph degree | script default `64` | paper uses a smaller in-memory graph than full disk graph | partially | limited only | private memory-graph parameter |
| `MEM_BUILD_L` | build (memory nav graph) | memory nav graph build complexity | script default `125` | paper appendix gives memory-graph parameter values | partially | limited only | should stay in local search around method defaults |
| `MEM_RAND_SAMPLING_RATE` / sample ratio `mu` | build (memory nav graph) | controls memory-graph sample fraction | script default `0.1`; paper discusses sample-ratio sensitivity and reports default sample-ratio protocol | no | limited only | key Starling-private axis; should not be collapsed into generic cache knob |
| `MEM_L` | search | depth of in-memory navigation search | CLI default `0`; script default `0` | paper evaluates navigation graph as a separate mechanism | no | limited only | defines search family; `0` disables memory nav |
| `USE_PAGE_SEARCH` | search family | page search vs beam search | CLI default `1`; script default `1` | paper centers Starling on page search | no | family split, not main sweep | should be fixed within a comparison family |
| `PS_USE_RATIO` / `use_ratio` | search | fraction of page contents used during page search | CLI default `1.0`; script default `1.0` | page-search-specific local tuning | no | limited only | not semantically equivalent to generic `L` |
| `GP_TIMES` | layout | partition iteration count | script default `16`; local run evidence `8` | paper says BNF/block shuffling default uses `beta=8` | no | limited only | layout/private parameter |
| `GP_CUT` | layout | graph-degree cutoff during partitioning | script default `4096` | script and local practice treat it as fixed | weakly, but practically fixed | usually no | not worth presenting as an active scan axis unless layout sensitivity is explicitly studied |
| `USE_SQ` | search family | compressed-search branch | CLI default `0`; script default `0` | separate optional branch | no | family split only | should not be mixed into main Starling family without explicit declaration |
| `SECTOR_LEN` | fixed | physical page size | inherited 4KB disk-page regime | fixed | no | no | not a meaningful tuning axis here |

## Shared Candidate Ranges

| Shared axis | Starling parameter | Recommended harmonized candidate pool | Why shared |
| --- | --- | --- | --- |
| build graph degree | `R` | `{32, 48, 64, 128, 256}` | DiskANN-style graph-degree role |
| build complexity | `BUILD_L` | `{75, 100, 125, 150}` | Vamana-style build-width role |
| search depth | `LS` | `{10, 20, 30, 50, 100, 150, 300, 500, 1000}` | main online Recall-QPS knob |
| beam width | `beamwidth` / `BM_LIST` | `{4, 8, 16, 32}` | direct online frontier-width control |

## Starling-Specific Limited Search

| Parameter | Center value to start from | Suggested limited search | Why limited rather than shared |
| --- | --- | --- | --- |
| `MEM_R` | script default `64` | narrow local neighborhood | private memory-navigation graph structure |
| `MEM_BUILD_L` | script default `125` | narrow local neighborhood | memory-navigation graph build quality control |
| `MEM_RAND_SAMPLING_RATE` / `mu` | script default `0.1`; paper treats sample ratio as a key sensitivity parameter | bounded local grid around recommended sample ratios | Starling-private memory-graph fraction |
| `MEM_L` | default `0` within baseline family | small local set such as off / moderate / stronger nav | changes whether memory navigation is active |
| `USE_PAGE_SEARCH` | paper/main family `1` | compare fixed families, not mixed grid | defines beam-search vs page-search family |
| `PS_USE_RATIO` | script default `1.0` | restricted local search around current family center | page-search-private ratio |
| `GP_TIMES` | paper default `8`; script often `16`; local run evidence `8` | limited search around documented centers | layout-stage parameter, not main online ANN knob |
| `USE_SQ` | default `0` | separate branch only if explicitly included | compressed-search family, not main fairness sweep |

## Fixed or Auto-Derived Parameters

| Parameter | Value / behavior | Reason not to scan |
| --- | --- | --- |
| `GP_CUT` | script default `4096` | treated as a structural layout cap, not a practical rebuttal-stage scan axis |
| `GP_LOCK_NUMS` | script default `0` | implementation/partition initialization detail |
| `FREQ_*` parameters in ordinary static baseline comparison | kept fixed unless explicitly running frequency-driven layout family | otherwise mixes another workflow layer into the main search sweep |
| `SECTOR_LEN` / 4KB page regime | fixed physical page size | not a meaningful independent tuning axis |
| range-search-only parameters (`kicked_size`, `custom_round_num`, `radius_file`) | irrelevant to top-k KNN comparison | outside the current rebuttal comparison family |

## Final Adopted Configuration Backfill Slot

| Field | Status | Value | Evidence |
| --- | --- | --- | --- |
| dataset | experiment record |  | must come from actual reported baseline run |
| metric / dtype | experiment record |  | must match reported setting |
| `R` | partially verified | local deep1m build used `32`; script default `64` | `BenchResults/starling_meanios_1m_20260624/deep1m/build.log`; `scripts/config_local.sh` |
| `BUILD_L` | partially verified | local deep1m build used `70`; script default `125` | recorded in the preceding row |
| `LS` | experiment record |  | no final Pareto-selected value yet in local evidence |
| `beamwidth` | experiment record |  | script default `5`, but final adopted value must come from real baseline run |
| `MEM_R` | partially verified | script default `64` | `scripts/config_local.sh` |
| `MEM_BUILD_L` | partially verified | script default `125` | `scripts/config_local.sh` |
| `MEM_RAND_SAMPLING_RATE` | partially verified | script default `0.1` | `scripts/config_local.sh` |
| `MEM_L` | partially verified | script default `0` | `scripts/config_local.sh` |
| `USE_PAGE_SEARCH` | partially verified | script default `1` | `scripts/config_local.sh` |
| `PS_USE_RATIO` | partially verified | script default `1.0` | `scripts/config_local.sh` |
| `GP_TIMES` | partially verified | local deep1m run `8`; script default `16`; paper default BNF iteration `8` | build logs and paper text |
| comparison family | experiment record |  | must state whether final reported result is page-search family, SQ family, etc. |

## Direct Local Evidence Already Available

| Evidence type | Confirmed value(s) | Source |
| --- | --- | --- |
| paper-level default statement | default eight serving threads; BNF/block shuffling uses `beta=8` by default; Starling uses tuned hyper-parameters under fixed memory budget | `Starling_Arxiv_2401.02116.pdf` |
| paper appendix tables | paper reports disk-graph, memory-graph, pruning, and comparator parameter tables | `Starling_Arxiv_2401.02116.pdf`, tables around the parameter appendix |
| script default | `R=64`, `BUILD_L=125`, `USE_SQ=0`, `MEM_R=64`, `MEM_BUILD_L=125`, `MEM_RAND_SAMPLING_RATE=0.1`, `GP_TIMES=16`, `GP_CUT=4096`, `BM_LIST=(5)`, `MEM_L=0`, `USE_PAGE_SEARCH=1`, `PS_USE_RATIO=1.0`, `LS=150` | `Origin/Starling/scripts/config_local.sh` |
| executed local build | `R=32`, `L=70`, `T=16` | `BenchResults/starling_meanios_1m_20260624/deep1m/build.log` |
| executed local partition | `GP_TIMES=8`, `-T 16` | `BenchResults/starling_meanios_1m_20260624/deep1m/gp_partition.log` |

## Protocol Summary

1. Put `R`, `BUILD_L`, `LS`, and `beamwidth` on the shared candidate ranges.
2. Treat memory-navigation, page-search ratio, and partition parameters as Starling-private limited-search parameters.
3. Keep `USE_PAGE_SEARCH` and `USE_SQ` as comparison-family selectors rather than mixing them into one exhaustive grid.
4. Do not promote script defaults or appendix values into final adopted settings until the actual Pareto-selected run is identified.
