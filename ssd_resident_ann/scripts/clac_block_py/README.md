## Block Helpers for Disk-Resident ANN

This directory computes block-level access summaries for SSD-resident ANN baselines. The accounting semantics follow each system's physical layout unit:

- PageANN: page-graph or page-layout access
- SPANN: posting-level or posting-page access
- Starling: partition-page access
- MARGO: partitioned graph-sector access
- Gorgeous: graph-aware partition access

These files provide disk-side access and block-accounting utilities for baseline runtime traces and CSV summaries.
