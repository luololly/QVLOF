# Parameter-Tuning Support Materials for QVLOF Rebuttal

This directory contains the method-level parameter-tuning notes prepared to support the QVLOF rebuttal for Comment 3 and Comment 6.

## Files

| File | Role |
| --- | --- |
| `PageANN_grid_search_tuning.md` | method-level tuning boundary for PageANN |
| `Starling_grid_search_tuning.md` | method-level tuning boundary for Starling |
| `MARGO_grid_search_tuning.md` | method-level tuning boundary for MARGO |
| `SPANN_grid_search_tuning.md` | method-level tuning boundary for SPANN |
| `Gorgeous_grid_search_tuning.md` | method-level tuning boundary for Gorgeous |

## How These Files Should Be Used

| Use case | Recommended file(s) |
| --- | --- |
| response-letter table source | `Doc and MD/Paper/QVLOF/Rebuttal/fair_comparison_parameter_summary.md` |
| response-letter final configuration appendix / cross-check | `Doc and MD/Paper/QVLOF/Rebuttal/final_adopted_configurations.md` |
| anonymous repository method-by-method support note | the five method-level files in this directory |
| internal verification of what is actually evidenced vs tracked in experiment records | the evidence tables inside each method-level file plus `final_adopted_configurations.md` |

## Protocol Boundary

These materials follow four rules:

1. Semantically aligned build/search parameters use shared candidate ranges across PageANN, Starling, MARGO, and Gorgeous where the role is genuinely aligned.
2. Method-private layout, routing, filtering, memory-navigation, or posting-organization parameters are tuned only in restricted local grids around documented defaults or recommended values.
3. SPANN is tuned separately under its own head/build/posting/search parameterization.
4. Fixed physical-page settings and auto-derived parameters are documented, but not presented as independent scan axes.

## Important Evidence Rule

These files are protocol-and-evidence notes, not proof that every listed combination has already been executed.

In particular:

- script defaults are not automatically final adopted configurations,
- paper or README recommended settings are not automatically final adopted configurations,
- any final adopted configuration must be copied from the actual Pareto-selected run used in the reported comparison,
- Pareto points are recorded in the corresponding result slot as experiment data becomes available.

## Relation to the Anonymous Repository

For the anonymous repository promised in Comment 6:

- this directory is the method-level support package,
- `fair_comparison_parameter_summary.md` is the response-letter-facing cross-method protocol summary,
- `final_adopted_configurations.md` is the final configuration ledger that should be updated once the actual reported Pareto points are fixed.
