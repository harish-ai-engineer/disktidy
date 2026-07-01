"""Basic smoke tests — no network, no destructive actions."""
import os
import tempfile

from disktidy import analyze, caches, consumers
from disktidy.util import dir_size, human_size, list_drives


def test_human_size():
    assert human_size(0) == "0 B"
    assert human_size(1024) == "1.0 KB"
    assert human_size(1024 ** 3).endswith("GB")


def test_dir_size_and_analyze(tmp_path):
    (tmp_path / "a.bin").write_bytes(b"x" * 2048)
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.bin").write_bytes(b"y" * 1024)

    assert dir_size(str(tmp_path)) == 3072

    result = analyze.analyze(str(tmp_path), top=5, want_files=True)
    assert result.folders and result.folders[0].path.endswith("sub")
    assert result.files and result.files[0].size == 2048


def test_list_drives_nonempty():
    assert len(list_drives()) >= 1


def test_detectors_do_not_raise():
    # These probe the real system; they must never throw, only return lists.
    assert isinstance(caches.detect(), list)
    assert isinstance(consumers.scan_consumers(git_roots=[tempfile.gettempdir()]), list)
