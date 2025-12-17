"""Integration tests for ZenodoZipDownloader functionality."""

import tempfile
from pathlib import Path
import pytest
from zenodozipdownloader.core import ZenodoZipDownloader


def test_download_single_file_variants():
    """Test downloading a single file using different DOI formats."""
    test_cases = [
        ("10.5281/zenodo.5423457", "DOI as canonical string"),
        ("https://zenodo.org/records/5423457", "DOI as Zenodo URL"),
        ("5423457", "DOI as Zenodo numeric ID"),
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        for identifier, description in test_cases:
            downloader = ZenodoZipDownloader(identifier, download_dir=tmpdir)
            files = downloader.download(
                zip_pattern="*.zip",
                inner_pattern="*.mat",
                first_n_zip=1,
                first_n_inner=1,
                retries=1,
                show_progress=False,
            )
            assert len(files) == 1, f"[{description}] Expected 1 file, got {len(files)}"
            file_path = files[0]
            assert Path(
                file_path
            ).exists(), f"[{description}] Downloaded file does not exist: {file_path}"


def test_download_pattern():
    """Test downloading files with specific patterns."""
    doi = "10.5281/zenodo.5423457"
    with tempfile.TemporaryDirectory() as tmpdir:
        downloader = ZenodoZipDownloader(doi, download_dir=tmpdir)
        files = downloader.download(
            zip_pattern="*.zip",
            inner_pattern="*patternMatching*.m",
            first_n_zip=0,
            first_n_inner=0,
            retries=1,
            show_progress=False,
        )
        assert len(files) == 2, f"Expected 2 files, got {len(files)}"
        for file_path in files:
            assert Path(
                file_path
            ).exists(), f"Downloaded file does not exist: {file_path}"


def test_download_corrupted_files():
    """Test downloading files with specific patterns."""
    doi = "10.5281/zenodo.5423457"
    with tempfile.TemporaryDirectory() as tmpdir:
        downloader = ZenodoZipDownloader(doi, download_dir=tmpdir)
        files = downloader.download(
            zip_pattern="*.zip/*patternMatching*.m",
            first_n_zip=0,
            first_n_inner=1,
            retries=1,
            show_progress=True,
        )
        assert Path(files[0]).exists()

        # Corrupt the file
        old_crc = downloader.file_crc32(files[0])
        with open(files[0], "ab") as f:
            f.write(b"corrupted data")
        new_crc = downloader.file_crc32(files[0])
        assert old_crc != new_crc, "File should be corrupted, CRC32 should differ"
        # Redownload the file
        files = downloader.download(
            zip_pattern="*.zip/*patternMatching*.m",
            first_n_zip=0,
            first_n_inner=1,
            retries=1,
            show_progress=True,
        )
        assert Path(files[0]).exists()
        new_crc = downloader.file_crc32(files[0])
        assert (
            old_crc == new_crc
        ), "File should be redownloaded, CRC32 should match original"


def test_invalid_doi():
    """Test that an invalid DOI raises a ValueError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(ValueError):
            ZenodoZipDownloader("invalid-doi", download_dir=tmpdir)


def test_no_matching_pattern():
    """Test that a valid DOI but a non-matching pattern returns an empty list."""
    doi = "10.5281/zenodo.5423457"
    with tempfile.TemporaryDirectory() as tmpdir:
        downloader = ZenodoZipDownloader(doi, download_dir=tmpdir)
        files = downloader.download(
            zip_pattern="*.zip",
            inner_pattern="no_such_file_pattern_*.xyz",
            first_n_zip=0,
            first_n_inner=0,
            retries=1,
            show_progress=False,
        )
        assert not files, "Expected no files to be downloaded for unmatched pattern"


if __name__ == "__main__":
    test_download_single_file_variants()
    test_download_pattern()
    test_invalid_doi()
    test_no_matching_pattern()
    print("All tests passed.")
