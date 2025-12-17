![PyPI](https://img.shields.io/pypi/v/zenodozipdownloader)
![License](https://img.shields.io/github/license/thielec/zenodozipdownloader)
![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)

# ZenodoZipDownloader

A Python package to download and extract selected files from ZIP archives in Zenodo records, with pattern matching, CRC32 integrity checks, and robust retry logic.

## Features
- Download files from Zenodo records using DOI or record URL
- Filter ZIP files and inner files using glob patterns
- Download only a subset of files if desired
- CRC32 integrity check for downloaded files
- Retry logic for network and file operations
- Command-line interface (CLI)

## Installation

```sh
pip install zenodozipdownloader
```

Or from source:

```sh
git clone https://github.com/yourusername/zenodozipdownloader.git
cd zenodozipdownloader
pip install .
```

### Requirements

- Python 3.10 or newer
- Network access to `https://zenodo.org/`
- Optional: `tqdm` for download progress (see below)

### Optional progress bar

The package can show download progress if `tqdm` is available. Install it alongside the downloader with:

```sh
pip install zenodozipdownloader[tqdm]
```

## Usage

### As a Python module
```python
# [optional] set logging level to INFO for more verbose output
import logging
logging.basicConfig(level=logging.INFO)

from zenodozipdownloader import ZenodoZipDownloader

doi = "10.5281/zenodo.5423457"
downloader = ZenodoZipDownloader(doi, download_dir="zenodo_downloads")
downloaded_files = downloader.download(zip_pattern="*.zip", inner_pattern="*tubulin*.mat")

for path in downloaded_files:
    print(f"Saved: {path}")
```

By default:
- Extracted files stay inside the chosen `download_dir`; unsafe ZIP paths are skipped.
- All files are downloaded unless you provide `inner_pattern`.
- Downloads retry up to three times and validate CRC32 checksums.

### As a CLI tool
```sh
zenodozipdownloader 10.5281/zenodo.5423457 --download_dir zenodo_downloads --zip_pattern "*.zip" --inner_pattern "*tubulin*.mat"
```

Run `zenodozipdownloader --help` for the full CLI reference. It shares defaults with the Python API; omit `--first_n_zip` and `--first_n_inner` to process every match.

## Arguments
- `doi`: Zenodo DOI or record URL
- `--download_dir`: Directory to save downloaded files (default: current directory)
- `--zip_pattern`: Glob pattern for ZIP files in the record (default: `*.zip`)
- `--inner_pattern`: Glob pattern for files inside ZIPs (default: all)
- `--first_n_zip`: Only process the first N matching ZIP files (default: all)
- `--first_n_inner`: Only download the first N matching files within each ZIP (default: all)

## Testing

To run the integration tests and check code coverage:
```sh
pip install pytest pytest-cov
pytest --cov=zenodozipdownloader tests/
```

## License
MIT License
