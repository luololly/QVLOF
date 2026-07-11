# Disk-Resident Index Integrations

This directory stores the QSO/RDO coupling notes for five SSD-resident ANN systems and records each baseline's artifact and runtime boundaries.

## Covered Systems

- `pageann/`
- `spann/`
- `starling/`
- `margo/`
- `gorgeous/`

## Integration Granularity

The disk-resident integration is documented at the granularity used by the baseline builders:


| System   | Static QSO binding                                                                                         | Dynamic RDO binding                                                          | Runtime path                                      |
| -------- | ---------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- | ------------------------------------------------- |
| PageANN  | `build_page_graph(...)` imports a QSO permutation or explicit page groups before `create_disk_layout(...)` | multiple page-layout builds selected by workload windows                     | `PQFlashIndex` search stays unchanged             |
| SPANN    | `BuildSSDIndex` imports QSO posting order before SSD posting pages are emitted                             | multiple SSD posting layouts selected by the controller                      | `SearchSSDIndex` serving stays unchanged          |
| Starling | `_partition.bin` is emitted with QSO page assignments and consumed by `index_relayout`                     | multiple partition/index pairs are selected by RDO                           | `page_search(...)` stays unchanged                |
| MARGO    | QSO replaces or biases partition generation before`save_partition(...)` / `index_relayout`                 | multiple partition families are selected by RDO                              | `page_search(...)` stays unchanged                |
| Gorgeous | QSO drives`split_graph` or `gr_layout` partition input before `index_relayout_free_mem`                    | multiple graph-aware layout families and runtime toggles are selected by RDO | `FileIOManager` and `PQFlashIndex` stay unchanged |
