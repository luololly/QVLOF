# MARGO Grid-Search Tuning Note

## Scope and Evidence Boundary

This note supports the QVLOF rebuttal by documenting which MARGO parameters:

- align with the shared DiskANN-style build/search parameter axes,
- are MARGO-private layout or workflow controls and therefore only suitable for restricted local search,
- should stay fixed because they are structural or non-comparable, and
- already have direct local evidence versus still needing final Pareto-point backfill.

## Evidence Sources

| Source type | Path / anchor | Used for |
| --- | --- | --- |
| Code analysis | `Origin/MARGO/tests/search_disk_index.cpp` | online search parameters and defaults |
| Code analysis | `Origin/MARGO/tests/my_build_disk_index.cpp` | build-side defaults |
| Code analysis | `Origin/MARGO/scripts/config_local.sh` | local script defaults |
| Code analysis | `Origin/MARGO/README.md` | `nlist` ownership and workflow guidance |
| Code analysis | `Origin/MARGO/my_gp/new_mincut.cpp` | layout-specific `nlist` location |
| Local run evidence | `BenchResults/margo_meanios_1m_20260624/deep1m/build.log` | executed build configuration |
| Repository README | `Origin/MARGO/README.md` | project-level recommended workflow |

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
| `R` | build | disk-graph degree | code default `64`; script default `64`; local deep1m run `64` | workflow uses project-configured value per dataset | yes | yes, shared build axis | directly aligned with DiskANN-style family |
| `BUILD_L` | build | disk-graph build complexity | code default `100`; script default `125`; local deep1m run `125` | workflow uses configured per-dataset value | yes | yes, shared build axis | DiskANN-style build-complexity role |
| `LS` | search | online candidate depth | script default `150` | should follow shared search-depth grid | yes | yes, primary shared search axis | one of the main Recall-QPS knobs |
| `beamwidth` / `BM_LIST` | search | search frontier width | CLI default `2`; script default `5` | shared beam candidate set | yes | yes | distinguish CLI default from experiment script default |
| `MEM_R` | build (memory nav graph) | memory-navigation graph degree | script default `64` | workflow configured per dataset | partially | limited only | private memory-graph axis |
| `MEM_BUILD_L` | build (memory nav graph) | memory-nav build complexity | script default `125` | workflow configured per dataset | partially | limited only | not shared across all methods |
| `MEM_RAND_SAMPLING_RATE` | build (memory nav graph) | memory sample fraction | script default `0.1` | private memory-graph parameter | no | limited only | not semantically equivalent to generic cache knob |
| `MEM_L` | search | in-memory navigation search depth | CLI default `0`; script default `0` | separate family/intensity control | no | limited only | `0` disables memory-nav search |
| `USE_PAGE_SEARCH` | search family | page search vs non-page path | CLI default `1`; script default `1` | MARGO comparisons generally assume page-search family | no | family split only | should stay fixed within a family |
| `PS_USE_RATIO` / `use_ratio` | search | fraction of page contents used during page search | CLI default `1.0`; script default `1.0` | page-search-local tuning | no | limited only | private online ratio |
| `nlist` | layout | monotonic-path layout partition granularity | not in CLI; `README` says set in `new_mincut.cpp`; example `256`; `1` for greedy | README explicitly names it as the main layout parameter | no | limited only | method-defining private layout parameter |
| `GP_TIMES` | layout | partition iteration count in inherited Starling-style partition flow | script default `16` | can be fixed around method default unless layout sensitivity is studied | no | limited only | secondary layout-stage private parameter |
| `GP_CUT` | layout | partition graph cutoff | script default `4096` | treated as fixed in ordinary scripts | weakly | usually no | not worth inflating into a main scan axis |
| `USE_SQ` | search family | compressed-search branch | script default `0` | separate branch only if explicitly included | no | family split only | should not be mixed into main family |

## Shared Candidate Ranges

| Shared axis | MARGO parameter | Recommended harmonized candidate pool | Why shared |
| --- | --- | --- | --- |
| build graph degree | `R` | `{32, 48, 64, 128, 256}` | DiskANN-style graph-degree role |
| build complexity | `BUILD_L` | `{75, 100, 125, 150}` | Vamana-style build-width role |
| search depth | `LS` | `{10, 20, 30, 50, 100, 150, 300, 500, 1000}` | primary online Recall-QPS control |
| beam width | `beamwidth` / `BM_LIST` | `{4, 8, 16, 32}` | direct online frontier-width control |

## MARGO-Specific Limited Search

| Parameter | Center value to start from | Suggested limited search | Why limited rather than shared |
| --- | --- | --- | --- |
| `nlist` | README example `256`; greedy baseline `1` | `{1, 32, 64, 128, 256}` as a restricted protocol grid around documented anchors | MARGO-defining layout parameter, not a shared ANN knob |
| `MEM_R` | script default `64` | narrow local neighborhood | private memory-navigation graph structure |
| `MEM_BUILD_L` | script default `125` | narrow local neighborhood | memory-navigation graph build quality control |
| `MEM_RAND_SAMPLING_RATE` | script default `0.1` | restricted local set around workflow value | private sample-fraction axis |
| `MEM_L` | script default `0` | small local set | toggles/strengthens memory-navigation family |
| `USE_PAGE_SEARCH` | script family `1` | keep fixed within family | family selector, not a main sweep axis |
| `PS_USE_RATIO` | script default `1.0` | bounded local search around current family center | page-search-private ratio |
| `GP_TIMES` | script default `16` | limited local search only if layout sensitivity is studied | layout-stage parameter |
| `USE_SQ` | script default `0` | separate branch only when explicitly evaluated | compressed-search family, not main fairness sweep |

## Fixed or Auto-Derived Parameters

| Parameter | Value / behavior | Reason not to scan |
| --- | --- | --- |
| `GP_CUT` | script default `4096` | structural partition cap, usually fixed |
| `GP_LOCK_NUMS` | script default `0` | implementation detail |
| streaming / insert-delete scenario controls | separate workflow family | outside the static disk-resident top-k rebuttal comparison |
| range-search-only parameters | separate query family | outside the current comparison |
| `SECTOR_LEN` / 4KB page assumptions | fixed physical layout regime | not a meaningful independent rebuttal scan axis |

## Final Adopted Configuration Backfill Slot

| Field | Status | Value | Evidence |
| --- | --- | --- | --- |
| dataset | experiment record |  | must come from actual reported baseline run |
| metric / dtype | experiment record |  | must match reported setting |
| `R` | verified for one local run, pending final backfill | local deep1m run `64` | `BenchResults/margo_meanios_1m_20260624/deep1m/build.log` |
| `BUILD_L` | verified for one local run, pending final backfill | local deep1m run `125` | recorded in the preceding row |
| `LS` | experiment record |  | no final Pareto-selected value yet |
| `beamwidth` | experiment record |  | script default `5` is not enough to claim final adoption |
| `MEM_R` | partially verified | script default `64` | `scripts/config_local.sh` |
| `MEM_BUILD_L` | partially verified | script default `125` | `scripts/config_local.sh` |
| `MEM_RAND_SAMPLING_RATE` | partially verified | script default `0.1` | `scripts/config_local.sh` |
| `MEM_L` | partially verified | script default `0` | `scripts/config_local.sh` |
| `USE_PAGE_SEARCH` | partially verified | script default `1` | `scripts/config_local.sh` |
| `PS_USE_RATIO` | partially verified | script default `1.0` | `scripts/config_local.sh` |
| `nlist` | partially verified | README example `256`; `1` means greedy | `Origin/MARGO/README.md` |
| comparison family | experiment record |  | must state whether the final reported run used ordinary page-search family, SQ family, or another branch |

## Direct Local Evidence Already Available

| Evidence type | Confirmed value(s) | Source |
| --- | --- | --- |
| project guidance | `nlist` is the main graph-layout-optimization parameter, set in `my_gp/new_mincut.cpp`; `nlist=1` gives greedy | `Origin/MARGO/README.md` |
| script default | `R=64`, `BUILD_L=125`, `USE_SQ=0`, `MEM_R=64`, `MEM_BUILD_L=125`, `MEM_RAND_SAMPLING_RATE=0.1`, `GP_TIMES=16`, `GP_CUT=4096`, `BM_LIST=(5)`, `MEM_L=0`, `USE_PAGE_SEARCH=1`, `PS_USE_RATIO=1.0`, `LS=150` | `Origin/MARGO/scripts/config_local.sh` |
| executed local build | `R=64`, `L=125`, `T=16` | `BenchResults/margo_meanios_1m_20260624/deep1m/build.log` |

## Protocol Summary

1. Put `R`, `BUILD_L`, `LS`, and `beamwidth` on the shared candidate ranges used for the semantically aligned baselines.
2. Keep `nlist`, page-search ratio, memory-navigation settings, and inherited partition settings in a restricted local grid centered on method defaults or documented recommended values.
3. Do not pretend that `nlist`, streaming controls, or range-search controls belong in the exhaustive `LS` sweep.
4. Do not promote the README example or script defaults into the final adopted configuration until the actual Pareto-selected baseline run is identified.
