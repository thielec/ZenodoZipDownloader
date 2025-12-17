"""Zenodo ZIP Downloader Command-Line Interface"""

import sys
import logging
import argparse
from zenodozipdownloader import ZenodoZipDownloader


def main():
    """
    Main entry point for the Zenodo ZIP Downloader script.
    Parses command-line arguments and initiates the download for files
    from Zenodo ZIP records based on the provided options.
    Usage:
        python -m zenodozipdownloader "10.5281/zenodo.5423457" --download_dir "zenodo_downloads" --zip_pattern "*.zip" --inner_pattern "*tubulin*.mat"
    """

    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(
        description="Download files from Zenodo ZIP records."
    )
    parser.add_argument("doi", help="Zenodo DOI or Record URL")
    parser.add_argument(
        "--download_dir", default=".", help="Directory to save downloaded files"
    )
    parser.add_argument(
        "--zip_pattern",
        default="*.zip",
        help="Glob pattern for ZIP files in the record",
    )
    parser.add_argument(
        "--inner_pattern", default=None, help="Glob pattern for files inside ZIPs"
    )
    parser.add_argument(
        "--first_n_zip",
        type=int,
        default=0,
        help="Process only the first N matching ZIP files (0=all)",
    )
    parser.add_argument(
        "--first_n_inner",
        type=int,
        default=0,
        help="Download only the first N matching files within each ZIP (0=all)",
    )
    args = parser.parse_args()
    try:
        downloader = ZenodoZipDownloader(args.doi, download_dir=args.download_dir)
        downloader.download(
            zip_pattern=args.zip_pattern,
            inner_pattern=args.inner_pattern,
            first_n_zip=args.first_n_zip,
            first_n_inner=args.first_n_inner,
        )
    except KeyboardInterrupt:
        print("\nDownload interrupted by user.")
    except Exception as e:
        logging.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
