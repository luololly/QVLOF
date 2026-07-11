import os
import tarfile
import urllib.request
from pathlib import Path

import yaml
from tqdm import tqdm


DATA_DIR = Path(__file__).resolve().parent
CONFIG_PATH = DATA_DIR / "config.yml"


def load_config():
    with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
        return yaml.safe_load(config_file)


def configure_proxy(proxy_config):
    if proxy_config.get("enabled", False):
        os.environ["HTTP_PROXY"] = proxy_config["http"]
        os.environ["HTTPS_PROXY"] = proxy_config["https"]


def download(url, output_path):
    if output_path.exists():
        print(f"{output_path.name} already exists, skipping download.")
        return

    print(f"Downloading {url} to {output_path}...")
    with urllib.request.urlopen(url) as response, output_path.open("wb") as output_file:
        progress = tqdm(unit="B", unit_scale=True, desc=output_path.name)
        while chunk := response.read(1024 * 1024):
            output_file.write(chunk)
            progress.update(len(chunk))
        progress.close()


def extract_sift(archive_path, dataset_dir):
    sift_dir = dataset_dir / "sift"
    if sift_dir.exists():
        print(f"{sift_dir} already exists, skipping extraction.")
        return

    print(f"Extracting {archive_path}...")
    with tarfile.open(archive_path, "r:gz") as archive:
        archive.extractall(dataset_dir)


def main():
    config = load_config()
    dataset_config = config["dataset"]
    if dataset_config["name"] != "sift-1m":
        raise ValueError("This branch supports the SIFT1M dataset.")

    configure_proxy(config.get("proxy", {}))
    dataset_root = (DATA_DIR / dataset_config["root_dir"]).resolve()
    dataset_dir = dataset_root / "sift" / "1m"
    dataset_dir.mkdir(parents=True, exist_ok=True)

    archive_path = dataset_dir / "sift.tar.gz"
    download(dataset_config["archive_url"], archive_path)
    extract_sift(archive_path, dataset_dir)
    print(f"SIFT1M is available under {dataset_dir / 'sift'}")


if __name__ == "__main__":
    main()
