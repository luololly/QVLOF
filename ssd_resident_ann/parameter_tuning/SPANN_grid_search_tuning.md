# SPANN Grid-Search Tuning Note

## Scope and Evidence Boundary

SPANN uses a parameter surface distinct from the DiskANN-style `R / L / beamwidth` surface. This note therefore treats SPANN separately and documents:

- which SPANN fields belong to head selection, head build, SSD posting build, and SSD search,
- which fields are appropriate online/search-side tuning axes,
- which structural fields should stay fixed within a comparison family,
- which values are directly verified from local `.ini` files or local runs, and
- which final adopted values still require real Pareto-point backfill.

## Evidence Sources

| Source type | Path / anchor | Used for |
| --- | --- | --- |
| Code / doc analysis | `Origin/SPTAG/docs/Parameters.md` | common defaults and parameter semantics |
| Code / config analysis | `Origin/SPTAG/Script_AE/iniFile/build_sift1m_local.ini` | local build family defaults |
| Code / config analysis | `Origin/SPTAG/Script_AE/iniFile/search_sift1m_local.ini` | local search family defaults |
| Local run evidence | `BenchResults/spann_text2image1m_metric_compare_20260705/build_ip.log` | executed text2image1m build configuration |
| Local run evidence | `BenchResults/spann_text2image1m_metric_compare_20260705/search_ip.log` | executed text2image1m search configuration and achieved QPS/recall |
| Local run evidence | `BenchResults/spann_text2image1m_metric_compare_20260705/summary.csv` | summarized search outcome |
| Local run evidence | `BenchResults/spann_meanios_20260625/deep1m/search2.log` | additional executed search configuration on deep1m-like setup |

## Shared Evaluation Constraints

| Item | Status |
| --- | --- |
| dataset / query split / ground truth | shared across all compared methods |
| distance metric / data type | shared across all compared methods |
| top-k target | shared across all compared methods |
| thread count | shared across all compared methods |
| total memory or cache budget | shared across all compared methods |

## Parameter Layer Summary

| Parameter | Stage | Role | Common/default value observed locally | Doc / config recommendation | Semantically aligned with other baselines? | Worth scanning? | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `SelectHead.Ratio` | head selection | head-point fraction | local config `0.16` | build config default example `0.16` | no | limited only | structural head-layer parameter |
| `SelectHead.SelectThreshold` | head selection | dynamic head-selection threshold | local config `50`; text2image run evidence `50` | config example `50` | no | limited only | not a generic search-depth knob |
| `BuildHead.NeighborhoodSize` | head build | head-graph degree | config example `32`; local run evidence `32` | docs default `32` | only loosely | limited only | closest SPANN-side analogue to graph degree, but still head-only |
| `BuildHead.MaxCheckForRefineGraph` | head build | head-graph refine effort | local config `8192`; run evidence `8192` | docs default `10000`, local config `8192` | no | limited only | structural build-quality control |
| `BuildHead.RNGFactor` | head build | RNG build behavior | local run evidence `1.0` | local config family keeps `1.0` | no | limited only | SPANN-specific build parameter |
| `BuildSSDIndex.InternalResultNum` | SSD build / serving coupling | internal candidate budget | local config `64`; run evidence `64` | local config example `64` | partially | yes, but within SPANN-only grid | closest SPANN-side online search-strength knob |
| `BuildSSDIndex.SearchInternalResultNum` | SSD build / serving coupling | synchronized search candidate budget | local config `64`; run evidence `64` | should stay synchronized with search family when used this way | partially | yes, synchronized with `InternalResultNum` | should not drift from the search-side setting in fair runs |
| `BuildSSDIndex.ReplicaCount` | SSD posting build | replica redundancy | local config `8`; run evidence `8` | local config example `8` | no | limited only | storage-structure parameter, not a shared online search knob |
| `BuildSSDIndex.PostingPageLimit` | SSD posting build | posting-page capacity / layout cap | local config `12`; run evidence `12` | local config example `12` | no | limited only | structural layout parameter |
| `SearchSSDIndex.InternalResultNum` | SSD search | internal search candidate budget | local config `64`; run evidence `64` | local config example `64` | partially | yes, main SPANN search axis | primary SPANN-side recall-latency knob |
| `SearchSSDIndex.MaxCheck` | SSD search | visited candidate / check budget | config example `1024` or `2048`; run evidence `1024` | docs identify `MaxCheck` as the main latency/recall parameter | partially | yes, main SPANN search axis | one of the most meaningful SPANN-side sweep axes |
| `SearchSSDIndex.SearchPostingPageLimit` | SSD search | posting-page access budget | local config `4`; run evidence `4` | local config example `4` | no | yes, but SPANN-only | closer to posting-access budget than beam width |
| `SearchSSDIndex.MaxDistRatio` | SSD search | distance-based pruning control | local config `8.0`; run evidence `8.0` | local config example `8.0` | no | limited only | private search pruning parameter |
| `HashTableExponent` | SSD search | internal hash-table sizing | local config `4` | config example `4` | no | usually no | structural search implementation detail |
| `UseDirectIO` / `Storage` / `SpdkBatchSize` | build/serve substrate | I/O backend configuration | local config `FILEIO`, `SpdkBatchSize=64`; run evidence consistent | environment/runtime substrate | no | no | should be held fixed within a comparison family |

## Shared Candidate Ranges

SPANN intentionally does not inherit the DiskANN-style shared `R / build-L / search-L / beamwidth` pool. This section is kept explicitly so the cross-method protocol can show that the omission is deliberate rather than forgotten.

| Shared semantic axis from the DiskANN-style family | SPANN status | Why there is no shared pool here |
| --- | --- | --- |
| build graph degree | not applicable | SPANN uses head-graph and posting-structure parameters instead of a single DiskANN-style disk-graph `R` |
| build complexity | not applicable | SPANN build quality is distributed across head-build and SSD-build controls rather than one shared `BUILD_L` knob |
| search depth | not applicable | SPANN search strength is controlled mainly by `InternalResultNum`, `MaxCheck`, and posting-page budgets |
| beam width | not applicable | SPANN does not expose a DiskANN-style online `beamwidth` with equivalent semantics |

## SPANN-Only Candidate Ranges

These axes form the independent SPANN tuning surface required by the rebuttal protocol.

| SPANN-only axis | Parameter(s) | Candidate range rule | Why this is the right SPANN tuning surface |
| --- | --- | --- | --- |
| internal candidate budget | `SearchSSDIndex.InternalResultNum` plus synchronized `BuildSSDIndex.SearchInternalResultNum` when coupled | bounded stepped range around default config | closest SPANN-side equivalent of search-strength tuning |
| check budget | `SearchSSDIndex.MaxCheck` | bounded stepped range around default config | docs explicitly tie `MaxCheck` to latency/recall |
| posting-page search budget | `SearchSSDIndex.SearchPostingPageLimit` | small local range around current config | directly controls online posting access budget |
| optional search pruning | `SearchSSDIndex.MaxDistRatio` | narrow local range around default | SPANN-specific pruning control with direct online effect |

## SPANN Structural Parameters for Limited Search Only

| Parameter | Center value to start from | Suggested limited search | Why limited rather than part of main sweep |
| --- | --- | --- | --- |
| `SelectHead.Ratio` | local config `0.16` | small local neighborhood if head fraction sensitivity is needed | structural head-selection parameter |
| `SelectHead.SelectThreshold` | local config `50` | small local neighborhood only if head selection itself is under study | structural head-selection parameter |
| `BuildHead.NeighborhoodSize` | local config `32` | small local neighborhood | head-graph structure, not main online tuning axis |
| `BuildHead.MaxCheckForRefineGraph` | local config `8192` | fixed or very small local neighborhood | build-quality control, not online tuning |
| `BuildHead.RNGFactor` | local config/run evidence `1.0` | fixed or very small local neighborhood | build-structure parameter |
| `BuildSSDIndex.ReplicaCount` | local config `8` | small local neighborhood around default if storage-layout sensitivity is studied | replica redundancy changes SSD organization itself |
| `BuildSSDIndex.PostingPageLimit` | local config `12` | small local neighborhood around default | posting layout capacity parameter, not online beam analogue |

## Fixed or Auto-Derived Parameters

| Parameter | Value / behavior | Reason not to scan |
| --- | --- | --- |
| update / steady-state / stress-test controls | fixed `false` in ordinary static comparison family unless explicitly evaluating SPFresh-style update scenarios | outside the current static rebuttal comparison |
| `Storage=FILEIO` / backend details | fixed per environment | runtime substrate, not algorithmic fairness axis |
| `SpdkBatchSize` | environment/backend setting | not part of main static comparison |
| `UseDirectIO` | environment/backend setting | keep fixed within a comparison family |
| `HashTableExponent` | local config `4` | implementation-level setting, not a main search trade-off axis |

## Final Adopted Configuration Backfill Slot

| Field | Status | Value | Evidence |
| --- | --- | --- | --- |
| dataset | experiment record |  | must come from actual reported baseline run |
| metric / dtype | experiment record |  | must match reported setting |
| `SelectHead.Ratio` | partially verified | `0.16` in local configs/runs | `build_sift1m_local.ini`; text2image logs |
| `SelectHead.SelectThreshold` | partially verified | `50` | recorded in the preceding row |
| `BuildHead.NeighborhoodSize` | partially verified | `32` | recorded in the preceding row |
| `BuildHead.MaxCheckForRefineGraph` | partially verified | `8192` | recorded in the preceding row |
| `BuildHead.RNGFactor` | partially verified | `1.0` | text2image logs |
| `InternalResultNum` | partially verified | `64` in local configs/runs | configs and search logs |
| `MaxCheck` | partially verified | `1024` in text2image/deep1m-like runs | search logs |
| `SearchPostingPageLimit` | partially verified | `4` | search logs |
| `ReplicaCount` | partially verified | `8` | build/search logs |
| `PostingPageLimit` | partially verified | `12` | build/search logs |
| `MaxDistRatio` | partially verified | `8.0` | search logs |
| final Pareto-selected tuple | experiment record |  | must come from the actual reported SPANN curve/point |

## Direct Local Evidence Already Available

| Evidence type | Confirmed value(s) | Source |
| --- | --- | --- |
| docs default / semantics | `NeighborhoodSize=32`, `MaxCheck` controls search latency/recall, `NumberOfThreads` common default is documented, etc. | `Origin/SPTAG/docs/Parameters.md` |
| local `.ini` baseline | `Ratio=0.16`, `SelectThreshold=50`, `NeighborhoodSize=32`, `InternalResultNum=64`, `ReplicaCount=8`, `PostingPageLimit=12`, `MaxCheck=1024 or 2048`, `SearchPostingPageLimit=4`, `MaxDistRatio=8.0` | `build_sift1m_local.ini`, `search_sift1m_local.ini` |
| executed text2image1m-like run | `InternalResultNum=64`, `ReplicaCount=8`, `PostingPageLimit=12`, `SearchPostingPageLimit=4`, `MaxCheck=1024`, `Ratio=0.16`, `SelectThreshold=50`, `NeighborhoodSize=32`, `RNGFactor=1.0`, achieved `QPS=162.54`, `Recall@10=0.917994` in one IP-like run | `build_ip.log`, `search_ip.log`, `summary.csv` |
| executed deep1m-like run | the parameter family configured with `InternalResultNum=64`, `SearchPostingPageLimit=4`, `MaxCheck=1024`, etc. | `spann_meanios_20260625/deep1m/search2.log` |

## Protocol Summary

1. SPANN must be tuned under its own head/build/posting/search parameterization, not coerced into a DiskANN-style `R/L/W` table.
2. The main rebuttal-stage SPANN sweep should center on `InternalResultNum`, `MaxCheck`, and `SearchPostingPageLimit`, with `MaxDistRatio` as an optional restricted local axis.
3. Head-selection, head-build, and posting-layout structure parameters should remain fixed or only be explored in a small local neighborhood around documented defaults.
4. Do not convert local `.ini` defaults into final adopted settings unless the actual reported Pareto point used them.
