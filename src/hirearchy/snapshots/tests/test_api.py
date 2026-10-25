"""The public surface: ``__init__`` re-exports exactly ``api``; ``blob_id`` is git's own blob hash."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import hirearchy.snapshots as snapshots
from hirearchy.snapshots import api


def test_the_package_re_exports_exactly_the_api() -> None:
    assert snapshots.__all__ == api.__all__ == ["Change", "GitClient", "IgnoreList", "OrgHistory", "OrgSnapshotter", "RUNTIME_IGNORE_LINES", "blob_id"]
    assert all(getattr(snapshots, name) is getattr(api, name) for name in api.__all__)


def test_the_runtime_lines_are_the_four_files_that_change_constantly() -> None:
    assert api.RUNTIME_IGNORE_LINES == (".runtime/running.json", ".runtime/scheduler.log", ".runtime/scheduler.exit", ".runtime/events/")


SAMPLES = [b"", b"hello\n", b"no newline", b"\x00\x01\xff binary \x00", "z\u00e9\n".encode(), b"x" * 70_000]


def hash_object(root: Path, data: bytes) -> str:
    return subprocess.run(["git", "hash-object", "--stdin"], cwd=root, input=data, capture_output=True, check=True).stdout.decode().strip()


@pytest.mark.parametrize("data", SAMPLES)
def test_blob_id_equals_git_hash_object_sha1(tmp_path: Path, data: bytes) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    assert api.blob_id(data) == api.blob_id(data, 40) == hash_object(tmp_path, data)


@pytest.mark.parametrize("data", SAMPLES)
def test_blob_id_sha256_in_a_sha256_repository(tmp_path: Path, data: bytes) -> None:
    made = subprocess.run(["git", "init", "-q", "--object-format=sha256"], cwd=tmp_path, capture_output=True)
    if made.returncode != 0:  # a git too old for sha256 repositories
        pytest.skip("this git cannot make a sha256 repository")
    assert len(api.blob_id(data, 64)) == 64
    assert api.blob_id(data, 64) == hash_object(tmp_path, data)


@pytest.mark.parametrize("hexlen", [0, 20, 32, 41, 63, 65, 128, -40])
def test_blob_id_refuses_other_lengths(hexlen: int) -> None:
    with pytest.raises(ValueError):
        api.blob_id(b"x", hexlen)
