## Dynamic Disk Script Wrappers

The disk-side scripts provide the dynamic-query and layout-family handoff for the corresponding disk-resident ANN systems.

Reason: the common disk-side RDO controller in this repository can already emit:

- layout manifests
- switch plans
- replay summaries

but the actual per-baseline dynamic runtime handoff still depends on external baseline-specific builders or
relayout tools. These wrapper scripts document the expected file-level entrypoints without claiming end-to-end
runtime integration is complete.
