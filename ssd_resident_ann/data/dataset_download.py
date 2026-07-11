#!/usr/bin/env python3
"""Download and prepare datasets for the disk-resident QVLOF package."""

from __future__ import annotations

import argparse
import os
import shutil
import struct
import tarfile
import urllib.request
from pathlib import Path
from typing import Any

import yaml


CONFIG_PATH = Path(__file__).with_name("config.yml")
CHUNK_SIZE = 1024 * 1024


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_args(config: dict[str, Any]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--datasets",
        nargs="+",
        default=config["dataset"]["prepare"],
        help="Datasets to prepare. Defaults to dataset.prepare in config.yml.",
    )
    parser.add_argument(
        "--root-dir",
        default=config["dataset"]["root_dir"],
        help="Dataset root directory. Defaults to dataset.root_dir in config.yml.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip files that already exist.",
    )
    return parser.parse_args()


def apply_proxy(config: dict[str, Any]) -> None:
    if config.get("proxy", {}).get("enabled"):
        os.environ["HTTP_PROXY"] = config["proxy"]["http"]
        os.environ["HTTPS_PROXY"] = config["proxy"]["https"]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def download_file(url: str, dst: Path, skip_existing: bool = False) -> None:
    if skip_existing and dst.exists():
        print(f"[skip] {dst}")
        return
    ensure_dir(dst.parent)
    print(f"[download] {url}")
    print(f"  -> {dst}")
    with urllib.request.urlopen(url) as response, dst.open("wb") as f:
        while True:
            chunk = response.read(CHUNK_SIZE)
            if not chunk:
                break
            f.write(chunk)


def download_stream_crop_xbin(
    url: str,
    dst: Path,
    num_vectors: int,
    dim: int,
    dtype_code: str,
    original_num_vectors: int,
    skip_existing: bool = False,
) -> None:
    if skip_existing and dst.exists():
        print(f"[skip] {dst}")
        return

    type_sizes = {
        "float32": 4,
        "uint8": 1,
        "int8": 1,
    }
    item_size = type_sizes[dtype_code]
    target_size = 8 + num_vectors * dim * item_size
    ensure_dir(dst.parent)

    print(f"[stream-crop] {url}")
    print(f"  -> {dst}")
    print(f"  vectors={num_vectors} dim={dim} dtype={dtype_code}")

    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response, dst.open("wb") as f:
        header = response.read(8)
        if len(header) != 8:
            raise RuntimeError(f"failed to read header from {url}")
        src_n, src_d = struct.unpack("<II", header)
        if src_n != original_num_vectors:
            raise RuntimeError(f"unexpected source size for {url}: {src_n} != {original_num_vectors}")
        if src_d != dim:
            raise RuntimeError(f"unexpected dim for {url}: {src_d} != {dim}")

        f.write(struct.pack("<II", num_vectors, dim))
        remaining = target_size - 8
        while remaining > 0:
            chunk = response.read(min(CHUNK_SIZE, remaining))
            if not chunk:
                raise RuntimeError(f"unexpected EOF while downloading {url}")
            f.write(chunk)
            remaining -= len(chunk)


def extract_tar_gz(src: Path, dst_dir: Path) -> None:
    ensure_dir(dst_dir)
    with tarfile.open(src, "r:gz") as tar:
        tar.extractall(dst_dir)


def copy_file(src: Path, dst: Path, skip_existing: bool = False) -> None:
    if skip_existing and dst.exists():
        print(f"[skip] {dst}")
        return
    ensure_dir(dst.parent)
    shutil.copyfile(src, dst)
    print(f"[copy] {src} -> {dst}")


def convert_fvecs_to_fbin(src: Path, dst: Path, skip_existing: bool = False) -> None:
    if skip_existing and dst.exists():
        print(f"[skip] {dst}")
        return
    ensure_dir(dst.parent)
    with src.open("rb") as f:
        dim_bytes = f.read(4)
        if len(dim_bytes) != 4:
            raise RuntimeError(f"invalid fvecs file: {src}")
        dim = struct.unpack("<I", dim_bytes)[0]
        raw = src.read()
    stride = 4 + dim * 4
    total = len(dim_bytes) + len(raw)
    if total % stride != 0:
        raise RuntimeError(f"unexpected fvecs size for {src}")
    num = total // stride
    with dst.open("wb") as out:
        out.write(struct.pack("<II", num, dim))
        view = memoryview(dim_bytes + raw)
        offset = 0
        for _ in range(num):
            vec_dim = struct.unpack("<I", view[offset:offset + 4])[0]
            if vec_dim != dim:
                raise RuntimeError(f"inconsistent dim in {src}")
            offset += 4
            out.write(view[offset:offset + dim * 4])
            offset += dim * 4
    print(f"[convert] {src} -> {dst}")


def convert_ivecs_to_ibin(src: Path, dst: Path, skip_existing: bool = False) -> None:
    if skip_existing and dst.exists():
        print(f"[skip] {dst}")
        return
    ensure_dir(dst.parent)
    with src.open("rb") as f:
        dim_bytes = f.read(4)
        if len(dim_bytes) != 4:
            raise RuntimeError(f"invalid ivecs file: {src}")
        dim = struct.unpack("<I", dim_bytes)[0]
        raw = src.read()
    stride = 4 + dim * 4
    total = len(dim_bytes) + len(raw)
    if total % stride != 0:
        raise RuntimeError(f"unexpected ivecs size for {src}")
    num = total // stride
    with dst.open("wb") as out:
        out.write(struct.pack("<II", num, dim))
        view = memoryview(dim_bytes + raw)
        offset = 0
        for _ in range(num):
            vec_dim = struct.unpack("<I", view[offset:offset + 4])[0]
            if vec_dim != dim:
                raise RuntimeError(f"inconsistent dim in {src}")
            offset += 4
            out.write(view[offset:offset + dim * 4])
            offset += dim * 4
    print(f"[convert] {src} -> {dst}")


def prepare_sift1m(root: Path, skip_existing: bool) -> None:
    dataset_dir = root / "sift1m"
    archive = dataset_dir / "sift.tar.gz"
    download_file("ftp://ftp.irisa.fr/local/texmex/corpus/sift.tar.gz", archive, skip_existing)
    extract_tar_gz(archive, dataset_dir)
    convert_fvecs_to_fbin(dataset_dir / "sift" / "sift_base.fvecs", dataset_dir / "sift_base.fbin", skip_existing)
    convert_fvecs_to_fbin(dataset_dir / "sift" / "sift_query.fvecs", dataset_dir / "sift_query.fbin", skip_existing)
    convert_ivecs_to_ibin(dataset_dir / "sift" / "sift_groundtruth.ivecs", dataset_dir / "sift_gt100.bin", skip_existing)


def prepare_gist1m(root: Path, skip_existing: bool) -> None:
    dataset_dir = root / "gist1m"
    archive = dataset_dir / "gist.tar.gz"
    download_file("ftp://ftp.irisa.fr/local/texmex/corpus/gist.tar.gz", archive, skip_existing)
    extract_tar_gz(archive, dataset_dir)
    convert_fvecs_to_fbin(dataset_dir / "gist" / "gist_base.fvecs", dataset_dir / "gist_base.fbin", skip_existing)
    convert_fvecs_to_fbin(dataset_dir / "gist" / "gist_query.fvecs", dataset_dir / "gist_query.fbin", skip_existing)
    convert_ivecs_to_ibin(dataset_dir / "gist" / "gist_groundtruth.ivecs", dataset_dir / "gist_gt100.bin", skip_existing)


def prepare_deep1m(root: Path, skip_existing: bool) -> None:
    dataset_dir = root / "deep1m"
    download_stream_crop_xbin(
        "https://storage.yandexcloud.net/yandex-research/ann-datasets/DEEP/base.1B.fbin",
        dataset_dir / "deep_base_1m.fbin",
        num_vectors=1_000_000,
        dim=96,
        dtype_code="float32",
        original_num_vectors=1_000_000_000,
        skip_existing=skip_existing,
    )
    download_file(
        "https://storage.yandexcloud.net/yandex-research/ann-datasets/DEEP/query.public.10K.fbin",
        dataset_dir / "query.public.10K.fbin",
        skip_existing,
    )
    download_file(
        "https://storage.yandexcloud.net/yandex-research/ann-datasets/deep_new_groundtruth.public.10K.bin",
        dataset_dir / "deep_gt100_1m.bin",
        skip_existing,
    )


def prepare_deep100m(root: Path, skip_existing: bool) -> None:
    dataset_dir = root / "deep100m"
    download_stream_crop_xbin(
        "https://storage.yandexcloud.net/yandex-research/ann-datasets/DEEP/base.1B.fbin",
        dataset_dir / "base.1B.fbin.crop_nb_100000000",
        num_vectors=100_000_000,
        dim=96,
        dtype_code="float32",
        original_num_vectors=1_000_000_000,
        skip_existing=skip_existing,
    )
    download_file(
        "https://storage.yandexcloud.net/yandex-research/ann-datasets/DEEP/query.public.10K.fbin",
        dataset_dir / "query.public.10K.fbin",
        skip_existing,
    )
    download_file(
        "https://dl.fbaipublicfiles.com/billion-scale-ann-benchmarks/GT_100M/deep-100M",
        dataset_dir / "gt100-public.10K.100m_crop.l2.fbin",
        skip_existing,
    )


def prepare_sift100m(root: Path, skip_existing: bool) -> None:
    dataset_dir = root / "sift100m"
    download_stream_crop_xbin(
        "https://dl.fbaipublicfiles.com/billion-scale-ann-benchmarks/bigann/base.1B.u8bin",
        dataset_dir / "learn.100M.u8bin",
        num_vectors=100_000_000,
        dim=128,
        dtype_code="uint8",
        original_num_vectors=1_000_000_000,
        skip_existing=skip_existing,
    )
    download_file(
        "https://dl.fbaipublicfiles.com/billion-scale-ann-benchmarks/bigann/query.public.10K.u8bin",
        dataset_dir / "query.public.10K.u8bin",
        skip_existing,
    )
    download_file(
        "https://comp21storage.z5.web.core.windows.net/comp21/bigann/public_query_gt100.bin",
        dataset_dir / "gt_DiskANN_K100",
        skip_existing,
    )
    print("[note] gt_PageANN_K100 is generated by the PageANN ground-truth step from gt_DiskANN_K100 or from scratch.")


def prepare_text2image100m(root: Path, skip_existing: bool) -> None:
    dataset_dir = root / "text2image100m_ip"
    download_stream_crop_xbin(
        "https://storage.yandexcloud.net/yandex-research/ann-datasets/T2I/base.1B.fbin",
        dataset_dir / "base.1B.fbin.crop_nb_100000000",
        num_vectors=100_000_000,
        dim=200,
        dtype_code="float32",
        original_num_vectors=1_000_000_000,
        skip_existing=skip_existing,
    )
    download_file(
        "https://storage.yandexcloud.net/yandex-research/ann-datasets/T2I/query.heldout.30K.fbin",
        dataset_dir / "query.heldout.30K.fbin",
        skip_existing,
    )
    download_file(
        "https://storage.yandexcloud.net/yandex-research/ann-datasets/T2I/gt100-heldout.30K.fbin",
        dataset_dir / "gt100-heldout.30K.100m_crop.mips.fbin",
        skip_existing,
    )


def prepare_spacev100m(root: Path, skip_existing: bool) -> None:
    dataset_dir = root / "spacev100m"
    download_stream_crop_xbin(
        "https://comp21storage.z5.web.core.windows.net/comp21/spacev1b/spacev1b_base.i8bin",
        dataset_dir / "spacev1b_base.i8bin.crop_nb_100000000",
        num_vectors=100_000_000,
        dim=100,
        dtype_code="int8",
        original_num_vectors=1_000_000_000,
        skip_existing=skip_existing,
    )
    download_file(
        "https://comp21storage.z5.web.core.windows.net/comp21/spacev1b/query.i8bin",
        dataset_dir / "query.i8bin",
        skip_existing,
    )
    download_file(
        "https://comp21storage.z5.web.core.windows.net/comp21/spacev1b/msspacev-gt-100M",
        dataset_dir / "msspacev-gt-100M",
        skip_existing,
    )


def prepare_glove(root: Path, skip_existing: bool) -> None:
    dataset_dir = root / "glove"
    ensure_dir(dataset_dir)
    print("[manual-step] glove")
    print("  public file expected: glove-100-angular.hdf5")
    print(f"  place it under: {dataset_dir}")
    print("  current public host ann-benchmarks.com may reject direct scripted download from this environment.")
    print("  once available locally, convert it to glove_base.fbin / glove_query.fbin / glove_gt100.bin.")


PREPARE_FUNCS = {
    "sift1m": prepare_sift1m,
    "gist1m": prepare_gist1m,
    "deep1m": prepare_deep1m,
    "sift100m": prepare_sift100m,
    "deep100m": prepare_deep100m,
    "text2image100m_ip": prepare_text2image100m,
    "spacev100m": prepare_spacev100m,
    "glove": prepare_glove,
}


def main() -> int:
    config = load_config()
    args = parse_args(config)
    apply_proxy(config)

    root = (CONFIG_PATH.parent / args.root_dir).resolve()
    ensure_dir(root)
    print(f"Dataset root: {root}")

    unknown = sorted(set(args.datasets) - set(PREPARE_FUNCS))
    if unknown:
        raise SystemExit(f"Unsupported datasets: {', '.join(unknown)}")

    for dataset in args.datasets:
        print()
        print(f"=== Preparing {dataset} ===")
        PREPARE_FUNCS[dataset](root, args.skip_existing)

    print()
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
