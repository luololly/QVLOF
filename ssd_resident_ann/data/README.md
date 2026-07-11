# Disk-Resident Data Layout

This directory defines the data contracts used by the SSD-resident integration layer.

Its purpose is not to store raw access records or ready-made layout files. Its purpose is to define the dataset registry, workload-side field contracts, and the static/dynamic artifact boundaries consumed by the five disk-resident baselines.

## Directory Contents

```text
data/
├── README.md
├── config.yml
├── dataset_download.py
├── dataset_overview.ipynb
└── dataset_analysis.ipynb
```

## What This Directory Controls

This directory serves three roles:

1. **dataset registry**
   - which datasets belong to the QVLOF paper core set
   - which datasets belong to the additional 100M disk-resident extension

2. **workload-side contracts**
   - which fields define a static QSO access profile
   - which fields define a dynamic RDO workload window

3. **artifact layering**
   - which artifacts belong to `static_qso`
   - which artifacts belong to `dynamic_rdo`
   - which builder or relayout stage consumes them

## Dataset Scope

The dataset scope follows two groups:

| Group | Datasets |
| --- | --- |
| `qvlof_paper_1m` | `DEEP1M`, `SIFT1M`, `GLOVE`, `GIST1M` |
| `disk_100m_extension` | `SIFT100M`, `DEEP100M`, `Text2Image (IP)`, `SPACEV100M` |

Each dataset entry in `config.yml` records:

- `paper_label`
- `group`
- `value_type`
- `distance`
- `scale`
- `base_file`
- `query_file`
- `groundtruth_file`

## QSO Data Boundary

For the disk-resident systems, QSO consumes:

- base vectors
- query vectors
- workload access profile fields
- a baseline-specific layout unit definition

The access-profile fields are defined inline in `config.yml` under:

- `access_profile.columns`
- `access_profile.semantics`

These fields are shared across the five systems, but the emitted artifact differs by layout unit.

### Static QSO Artifact Layer

The static layer is described under:

- `baselines.<system>.static_qso.artifact_names`
- `baselines.<system>.static_qso.import_stage`
- `baselines.<system>.static_qso.rebuild_output`

That section answers three questions for each baseline:

1. what file or artifact QSO emits,
2. where the artifact is imported,
3. what rebuilt disk artifact is produced.

## RDO Data Boundary

For dynamic workloads, RDO consumes:

- workload-window metadata
- candidate layout identifiers
- one candidate layout family per workload phase

The workload-window fields are defined inline in `config.yml` under:

- `workload_windows.fields`

### Dynamic RDO Artifact Layer

The dynamic layer is described under:

- `baselines.<system>.dynamic_rdo.layout_family`
- `baselines.<system>.dynamic_rdo.switch_unit`
- `baselines.<system>.dynamic_rdo.replay_target`

That section answers:

1. what counts as one dynamic layout family member,
2. what the switching stage selects,
3. what the replay stage evaluates.

## Baseline-Specific Data Wiring

| System | Required dataset-side fields | Static QSO output | Dynamic RDO family |
| --- | --- | --- | --- |
| PageANN | `base_file`, `query_file`, `groundtruth_file`, `index_prefix` | page permutation or `qso_pages.bin` | page-layout build family |
| SPANN | `VectorPath`, `QueryPath`, `WarmupPath`, `TruthPath`, `IndexDirectory` | posting order or posting-page family | SSD posting-layout family |
| Starling | `BASE_PATH`, `QUERY_FILE`, `GT_FILE`, `INDEX_PREFIX_PATH` | `_partition.bin` + `_disk.index` | relaid partition/index family |
| MARGO | `BASE_PATH`, `QUERY_FILE`, `GT_FILE`, `INDEX_PREFIX_PATH` | `_partition.bin` + `_disk.index` | partition/index family |
| Gorgeous | `BASE_PATH`, `QUERY_FILE`, `GT_FILE`, `GRAPH_PATH`, `GRAPH_REP_INDEX_PATH` | graph-only or graph-replica layout artifacts | graph-aware layout family |

## `dataset_download.py`

`dataset_download.py` is the dataset preparation entrypoint for this directory.

It now performs real preparation work instead of only printing metadata:

- downloads small public dataset packages directly
- downloads query and ground-truth files directly when public URLs exist
- streams large `1B` base files and writes cropped `100M` or `1M` `.fbin/.i8bin` outputs without first storing the full `1B` file
- writes the resulting files using the names recorded in `config.yml`

Current preparation modes are:

- `sift1m`: download `sift.tar.gz` from TexMex and unpack the dataset files
- `gist1m`: download `gist.tar.gz` from TexMex and unpack the dataset files
- `deep1m`: stream-crop `DEEP/base.1B.fbin` directly to `deep_base_1m.fbin`, then download `query.public.10K.fbin` and the public 10K ground truth
- `sift100m`: stream-crop `bigann/base.1B.u8bin` directly to `learn.100M.u8bin`, then download `query.public.10K.u8bin`; the PageANN-specific ground truth file is produced in the PageANN ground-truth step
- `deep100m`: stream-crop `DEEP/base.1B.fbin` to `base.1B.fbin.crop_nb_100000000`, then download the public 100M ground truth
- `text2image100m_ip`: stream-crop `T2I/base.1B.fbin` to `base.1B.fbin.crop_nb_100000000`, then download the held-out 30K queries and ground truth
- `spacev100m`: stream-crop `spacev1b_base.i8bin` to `spacev1b_base.i8bin.crop_nb_100000000`, then download `query.i8bin` and `msspacev-gt-100M`

`glove` is kept as a real but environment-sensitive case: the public `glove-100-angular.hdf5` host may reject scripted downloads from some environments, so the script currently exposes the exact expected local handoff path instead of pretending that the download is universally reliable.

Typical usage:

```bash
python dataset_download.py
python dataset_download.py --datasets deep100m text2image100m_ip spacev100m
python dataset_download.py --skip-existing
```

## Notebooks

### `dataset_overview.ipynb`

Summarizes:

- dataset-level metadata
- dataset groups
- manifest file names

### `dataset_analysis.ipynb`

Checks:

- required dataset manifest fields
- dataset group completeness
- registry summary counts

## Reproduction Rule

Read `config.yml` in the following order:

1. `dataset`
2. `access_profile`
3. `workload_windows`
4. `baselines.<system>.static_qso`
5. `baselines.<system>.dynamic_rdo`

That order mirrors the actual coupling order used by the five disk-resident baselines.
