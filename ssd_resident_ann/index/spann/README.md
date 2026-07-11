# QSO/RDO Adaptation Note for SPTAG/SPANN

## Public Upstream Source

`https://github.com/microsoft/SPTAG`

## Verified Local Anchors

This note is based on the public SPTAG repository layout:

- `SPTAG/AnnService/src/IndexBuilder/main.cpp`
- `SPTAG/AnnService/src/Core/SPANN/SPANNIndex.cpp`
- `SPTAG/AnnService/inc/Core/SPANN/ExtraStaticSearcher.h`
- `SPTAG/AnnService/inc/Core/SPANN/Options.h`
- `SPTAG/AnnService/inc/Core/SPANN/ParameterDefinitionList.h`
- `SPTAG/AnnService/src/SSDServing/main.cpp`
- `SPTAG/Test/src/SPFreshTest.cpp`
- `SPTAG/Script_AE/iniFile/build_sift1m_local.ini`

## What QSO Changes in SPANN

SPANN is not a page-graph relayout system in the PageANN sense. Its disk-resident unit is an SSD posting-page organization built during `BuildSSDIndex`.

So the correct QSO contract is:

- input: workload access profile + vectors + native posting membership + SPANN posting capacity constraints,
- output: a posting-oriented physical organization,
- unchanged executor: the ordinary SPANN SSD serving path.

The most important capacity controls are already exposed in the SPANN code:

- `PostingPageLimit`
- `SearchPostingPageLimit`
- `InternalResultNum`
- `SearchInternalResultNum`

## Exact Builder Boundary

The builder entrypoint is `SPTAG/AnnService/src/IndexBuilder/main.cpp`.

Its verified sequence is:

1. load `.ini`,
2. collect sections `Base`, `SelectHead`, `BuildHead`, `BuildSSDIndex`, `Index`,
3. call `indexBuilder->SetParameter(...)`,
4. call `BuildIndex(...)`.

This is the top-level place where a QSO artifact should be declared and handed into the SPANN build.

Inside the SPANN implementation, `SPANNIndex.cpp` reaches the SSD builder through the verified call:

```cpp
m_extraSearcher->BuildIndex(p_reader, m_index, m_options, m_versionMap, m_vectorTranslateMap)
```

around the SSD-build branch in the repository layout.

That call is the concrete handoff from generic builder logic to SSD posting construction.

## Where the Posting Layout Is Actually Formed

The best verified code hook is `SPTAG/AnnService/inc/Core/SPANN/ExtraStaticSearcher.h`.

Inside `ExtraStaticSearcher::BuildIndex(...)`, the code:

1. finishes selection sorting,
2. computes `postingSizeLimit`,
3. derives page capacity from `m_postingPageLimit`,
4. launches the thread pool that writes posting structures.

The key verified logic is around lines 781-787:

```cpp
if (p_opt.m_postingPageLimit > 0) {
    p_opt.m_postingPageLimit = max(...);
    p_opt.m_searchPostingPageLimit = p_opt.m_postingPageLimit;
    postingSizeLimit = ...
}
```

This is the right place to apply a QSO ordering, because the code is already turning candidate lists into page-bounded SSD postings.

## Builder / Posting / Serve Split

SPANN has a stronger separation between build time and serve time than the page-partition-based baselines. The integration boundary is easiest to understand as three layers:

1. **builder layer**
   - `IndexBuilder/main.cpp`
   - parses `.ini`
   - forwards `BuildSSDIndex` parameters into SPANN

2. **posting-layout layer**
   - `SPANNIndex.cpp`
   - `ExtraStaticSearcher::BuildIndex(...)`
   - converts selections into SSD posting pages under `PostingPageLimit`

3. **serve layer**
   - `SSDServing/main.cpp`
   - `SearchSSDIndex`
   - consumes an already built SSD posting layout

QSO binds at layer 2. RDO binds above layer 3 by selecting which built layout directory is active. The serve layer consumes the selected posting layout.

## Static QSO Binding

The SPANN+QSO binding is applied inside the SSD posting build:

1. add an optional file path parameter such as `QsoPostingOrderFile` under `BuildSSDIndex`,
2. parse it through the existing builder path used for SPANN options,
3. in `ExtraStaticSearcher::BuildIndex(...)`, load the QSO artifact after replica/search selection is available but before posting pages are finalized,
4. reorder posting membership or posting write order under the existing `PostingPageLimit`.

Posting-layout import contract:

```cpp
// after selections are sorted, before posting pages are emitted
QsoPostingLayout qso;
if (!m_opt->m_qsoPostingOrderFile.empty()) {
    qso = LoadQsoPostingLayout(m_opt->m_qsoPostingOrderFile);
    ReorderPostingAssignments(selections, replicaCount, qso, postingSizeLimit);
}

EmitPostingPages(selections, postingSizeLimit, ...);
```

The important point is that `EmitPostingPages(...)` is still the original SPANN path. QSO only changes who is colocated before those pages are persisted.

The physical change therefore happens in two substeps:

1. membership or order inside a posting page is changed by QSO,
2. the baseline SSD emitter persists those modified posting pages through the original build path.

The serving stage only sees a different SSD posting organization.

## Concrete Artifact Shapes

There are two realistic QSO artifact designs for SPANN.

### Option 1: posting-order plus reverse mapping

```text
uint64 posting_count
uint32 posting_id_order[posting_count]
float64 posting_score[posting_count]
```

This artifact controls the physical posting write order while keeping the native posting identities intact.
In practice it is paired with a reverse membership map:

```text
uint64 npts
uint32 vector_to_posting[npts]
```

### Option 2: explicit page emission order

```text
uint64 posting_count
uint64 posting_page_limit
for each posting:
    uint32 size
    uint32 ids[size]
```

This is closer to the final SSD page layout and is more direct when QSO already outputs native posting contents in the target order.

## Why `.ini` and `SPFreshTest.cpp` Matter

The local `SPFreshTest.cpp` builds SPANN through a string config and shows the exact `BuildSSDIndex` parameters that matter:

```ini
[BuildSSDIndex]
isExecute=true
BuildSsdIndex=true
InternalResultNum=64
SearchInternalResultNum=64
PostingPageLimit=...
SearchPostingPageLimit=...
```

This parameter-propagation pattern is already used in `SPFreshTest.cpp` with repeated `SetParameter(...)` calls.

An implementation-complete `.ini` view therefore has three parts:

- dataset fields such as `VectorPath`, `QueryPath`, and `TruthPath`,
- SSD layout capacity fields such as `PostingPageLimit`,
- one QSO-specific artifact path consumed before posting emission.

## Exact Build/Serve Split

There are two distinct places to keep in mind:

### Build time

- `IndexBuilder/main.cpp`
- `SPANNIndex.cpp`
- `ExtraStaticSearcher::BuildIndex(...)`

This is where QSO must intervene.

### Search time

- normal SPANN SSD serving path,
- `SearchSSDIndex` settings,
- `SSDServing/main.cpp` parameter translation.

`SSDServing/main.cpp` already maps `PostingPageLimit` to `SearchPostingPageLimit` and `InternalResultNum` to `SearchInternalResultNum` when serving. That is strong evidence that the online code expects a built SSD layout, not a new online relocation algorithm.

## Concrete RDO Coupling

RDO for SPANN is represented as a controller over several built SSD layouts.

A practical structure is:

```text
layout_window_0/
layout_window_1/
layout_window_2/
...
```

where each directory contains a full SPANN SSD build generated from a different QSO/RDO layout artifact.

Then:

1. `RDO_layout_main.py` emits candidate posting organizations,
2. each organization triggers one `BuildSSDIndex`,
3. `RDO_switch_main.py` chooses which directory is active,
4. `RDO_replay_main.py` evaluates the sequence of switches.

The online query loop still uses the normal SPANN serving binary against the selected layout directory.

In that dynamic setting, the layout family is concrete:

- one head-index-compatible SSD posting build per workload phase,
- one `IndexDirectory` per build,
- one switch decision per workload window.

The head index and serve-side query loop remain structurally identical; only the active SSD posting organization changes.

## RDO Layout-Family Binding

The disk-side RDO code in `../../rdo/` emits workload windows, candidate layout-family manifests,
switch plans, and replay summaries. For SPANN, the layout-family adapter:

1. export native posting membership for the target build,
2. for each RDO candidate window, run the QSO SPANN posting generator with that window's access profile,
3. convert the generated posting-level artifact into the optional `BuildSSDIndex` import file,
4. build one SPANN `IndexDirectory` per candidate layout,
5. let the RDO switch plan choose the active `IndexDirectory` for each workload window.

`../../rdo/` supplies the common windowing and switching control layer consumed by the SPANN adapter.

## SPANN Artifact Contract

The SPANN QSO path uses:

1. `qso/static_layout_main.py` emits posting-level QSO artifacts for SPANN:
   - `<prefix>_qso_posting_order.bin`
   - `<prefix>_qso_posting_pages.bin`
   - `<prefix>_qso_vector_to_posting.bin`
2. the builder-side import boundary reads the posting-level QSO artifact inside `BuildSSDIndex(...)`, before
   `SelectPostingOffset(...)` / `OutputSSDIndexFile(...)`,
3. the native SPTAG/SPANN serving path consumes the resulting SSD index directory.

## About `ExtraFullGraphSearcher`

The repository metadata references `ExtraFullGraphSearcher`, while the code path used by this integration note is:

- `m_extraSearcher->BuildIndex(...)` in `SPANNIndex.cpp`,
- `ExtraStaticSearcher::BuildIndex(...)` in `inc/Core/SPANN/ExtraStaticSearcher.h`.

Therefore this document uses the verified local implementation anchors instead of claiming a patch against a missing local header.

## Function-Level Flow

The code-level coupling is:

```text
workload access profile
  -> QSO posting layout
  -> IndexBuilder/main.cpp
  -> SPANNIndex.cpp::BuildIndex SSD branch
  -> ExtraStaticSearcher::BuildIndex(...)
  -> posting pages under PostingPageLimit
  -> normal SearchSSDIndex serving
```

More concretely:

1. `IndexBuilder/main.cpp` loads the config and forwards it into SPANN.
2. `SPANNIndex.cpp` enters the SSD builder path.
3. `ExtraStaticSearcher::BuildIndex(...)` computes the page-bounded posting limit.
4. A small import helper injects the QSO ordering before postings are written.
5. The built SSD postings are served by the unmodified SPANN search path.

## What Remains Unchanged

The following should remain unchanged in a faithful adaptation:

- SPANN head index construction,
- SPANN SSD serving logic,
- `SearchSSDIndex` query execution,
- search-time buffer and posting-page traversal logic.

Only the build-time posting-page organization changes.
