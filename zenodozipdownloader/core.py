"""
Main module for Zenodo ZIP Downloader.
Provides the ZenodoZipDownloader class to download and extract files
from ZIP archives in Zenodo records.
"""

import os
from pathlib import Path
import time
import re
import logging
import binascii
import fnmatch
import requests
from remotezip import RemoteZip

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None


class ZenodoZipDownloader:
    """
    A class to download and extract files from ZIP archives in Zenodo records.

    doi = "10.5281/zenodo.5423457"
    downloader = ZenodoZipDownloader(doi, download_dir="zenodo_downloads")
    downloader.download(zip_pattern="*.zip", inner_pattern="*.mat")
    """

    def __init__(self, doi: str, download_dir: str | os.PathLike = "."):
        self.logger = logging.getLogger(__name__)
        self.doi, self.record_id = self._parse_doi_input(doi)
        self.download_dir = Path(download_dir).resolve()
        self.api_url = f"https://zenodo.org/api/records/{self.record_id}"
        self.record = self._get_record_metadata()
        self.files = self.record.get("files", [])

    def _parse_doi_input(self, doi_input: str) -> tuple[str, str]:
        doi_input = doi_input.strip().rstrip("/")
        if doi_input.isdigit():
            zenodo_doi = f"10.5281/zenodo.{doi_input}"
            record_id = doi_input
            return zenodo_doi, record_id
        zenodo_url_match = re.match(r"https?://zenodo\.org/records?/(\d+)", doi_input)
        if zenodo_url_match:
            record_id = zenodo_url_match.group(1)
            return f"10.5281/zenodo.{record_id}", record_id
        zenodo_doi_match = re.search(r"(10\.5281/zenodo\.\d+)", doi_input)
        if zenodo_doi_match:
            zenodo_doi = zenodo_doi_match.group(1)
            record_id = zenodo_doi.split(".")[-1]
            return zenodo_doi, record_id
        raise ValueError(f"Unsupported DOI format: {doi_input}")

    def _get_record_metadata(self) -> dict:
        try:
            response = requests.get(self.api_url, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(
                f"Failed to fetch Zenodo record {self.record_id} from {self.api_url}"
            ) from e
        try:
            return response.json()
        except ValueError as e:
            raise RuntimeError(f"Invalid JSON from {self.api_url}") from e

    @staticmethod
    def file_crc32(filename: str | Path) -> int:
        prev = 0
        with open(filename, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                prev = binascii.crc32(chunk, prev)
        return prev & 0xFFFFFFFF

    def _open_zip_with_retry(self, zip_url: str, retries: int = 3) -> RemoteZip:
        last_exception = None
        for attempt in range(retries):
            try:
                return RemoteZip(zip_url)
            except Exception as e:
                last_exception = e
                if attempt == retries - 1:
                    raise RuntimeError(
                        f"Failed to open ZIP '{zip_url}' after {retries} attempts"
                    ) from e
                self.logger.warning(
                    "Attempt %d failed, retrying in %ds: %s", attempt + 1, 2**attempt, e
                )
                time.sleep(2**attempt)
        raise RuntimeError("Failed to open ZIP") from (
            last_exception or Exception("Unknown")
        )

    def _download_file_with_retry(
        self,
        zipf: RemoteZip,
        info,
        output_path: str | os.PathLike,
        retries: int = 3,
        show_progress: bool = True,
        zip_url: str | None = None,
    ) -> None:
        last_exception = None
        for attempt in range(retries):
            try:
                with (
                    zipf.open(info.filename) as source,
                    open(output_path, "wb") as target,
                ):
                    crc = 0
                    total_written = 0
                    chunk_size = 8192
                    pbar = None
                    if show_progress and tqdm is not None:
                        pbar = tqdm(
                            total=info.file_size,
                            unit="B",
                            unit_scale=True,
                            desc=Path(output_path).name,
                            leave=False,
                        )
                    while True:
                        chunk = source.read(chunk_size)
                        if not chunk:
                            break
                        target.write(chunk)
                        crc = binascii.crc32(chunk, crc)
                        total_written += len(chunk)
                        if pbar:
                            pbar.update(len(chunk))
                    if pbar:
                        pbar.close()
                    crc &= 0xFFFFFFFF
                if total_written == info.file_size and crc == info.CRC:
                    return
                if attempt == retries - 1:
                    raise RuntimeError(
                        f"Integrity check failed for '{output_path}' (expected size {info.file_size}, got {total_written}; expected CRC {info.CRC}, got {crc})"
                    )
            except Exception as e:
                last_exception = e
                if attempt == retries - 1:
                    raise RuntimeError(
                        f"Failed to download '{info.filename}' from '{zip_url or 'unknown'}' to '{output_path}'"
                    ) from e
            time.sleep(2**attempt)
        raise RuntimeError("Failed to download file after retries") from (
            last_exception or Exception("unknown")
        )

    def _resolve_output_path(self, filename: str) -> Path:
        """Resolve a ZIP member path and make sure it stays within download_dir. Error when unsafe."""
        try:
            candidate = (self.download_dir / filename).resolve()
            candidate.relative_to(self.download_dir)
        except (OSError, RuntimeError, ValueError) as exc:
            raise ValueError(
                f"Invalid ZIP entry '{filename}' for download_dir '{self.download_dir}'."
            ) from exc
        return candidate

    def download(
        self,
        zip_pattern: str = "*.zip",
        inner_pattern: str | None = None,
        first_n_zip: int = 0,
        first_n_inner: int = 0,
        retries: int = 3,
        show_progress: bool = True,
    ) -> list[Path]:
        """
        Download and extract files from ZIP archives in the Zenodo record.

        Args:
            zip_pattern (str): Pattern to match ZIP files in the record (default: "*.zip").
            inner_pattern (str | None): Pattern to match files inside ZIPs (default: None, matches all).
            first_n_zip (int): If >0, only process the first N ZIP files (default: 0, all).
            first_n_inner (int): If >0, only extract the first N matching files per ZIP (default: 0, all).
            retries (int): Number of retries for downloads (default: 3).
            show_progress (bool): Show progress bar if tqdm is available (default: True).

        Returns:
            list[Path]: List of downloaded file paths as Path objects.
        """

        if not inner_pattern:
            if not zip_pattern.lower().endswith(".zip") and ".zip/" in zip_pattern:
                zip_split = zip_pattern.split(".zip/")
                zip_pattern = zip_split[0] + ".zip"
                inner_pattern = zip_split[1] if len(zip_split) > 1 else "*.*"
            else:
                inner_pattern = "*.*"
        downloaded = []
        zip_files = [f for f in self.files if fnmatch.fnmatch(f["key"], zip_pattern)]
        if not zip_files:
            self.logger.info(
                "No ZIP files matching '%s' found in this Zenodo record.", zip_pattern
            )
            return []
        if first_n_zip > 0:
            zip_files = zip_files[:first_n_zip]
        for zip_file in zip_files:
            zip_url = zip_file["links"]["self"]
            self.logger.info("Processing ZIP: %s", zip_file["key"])
            with self._open_zip_with_retry(zip_url, retries) as zipf:
                matched_files = [
                    info
                    for info in zipf.infolist()
                    if fnmatch.fnmatch(info.filename, inner_pattern)
                ]
                if not matched_files:
                    self.logger.info(
                        "No files matching '%s' found in ZIP '%s'.",
                        inner_pattern,
                        zip_file["key"],
                    )
                    continue
                if first_n_inner > 0:
                    matched_files = matched_files[:first_n_inner]
                for info in matched_files:
                    try:
                        output_path = self._resolve_output_path(info.filename)
                    except ValueError as exc:
                        self.logger.warning("%s", exc)
                        continue
                    needs_download = True
                    if output_path.exists():
                        local_size = output_path.stat().st_size
                        if local_size == info.file_size:
                            local_crc = self.file_crc32(output_path)
                            if local_crc == info.CRC:
                                self.logger.info(
                                    "'%s' already exists, size and CRC32 match. Skipping.",
                                    output_path,
                                )
                                needs_download = False
                            else:
                                self.logger.info(
                                    "'%s' exists but CRC32 does not match. Re-downloading.",
                                    output_path,
                                )
                        else:
                            self.logger.info(
                                "'%s' exists but size does not match. Re-downloading.",
                                output_path,
                            )
                    if needs_download:
                        if output_path.parent:
                            output_path.parent.mkdir(parents=True, exist_ok=True)
                        self._download_file_with_retry(
                            zipf,
                            info,
                            output_path,
                            retries,
                            show_progress,
                            zip_url=zip_url,
                        )
                        self.logger.info(
                            "Downloaded '%s' with its original filename and path.",
                            output_path,
                        )
                    downloaded.append(output_path)
        return downloaded
