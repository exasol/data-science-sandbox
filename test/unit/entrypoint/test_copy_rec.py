import contextlib
import pytest

from exasol.ds.sandbox.runtime.ansible.roles.entrypoint.files import entrypoint
from pathlib import Path


@contextlib.contextmanager
def directory(dir: Path):
    dir.mkdir()
    dir.chmod(0o700)
    yield dir


def create_file(file: Path):
    file.write_text(f"content of file {file}")
    file.chmod(0o600)
    return file


def test_missing_src(caplog, tmp_path):
    root = tmp_path
    dst = root / "dst"
    entrypoint.copy_rec(root / "src", dst)
    assert not dst.exists()
    assert "Source directory not found" in caplog.text


def test_warning_as_error(tmp_path):
    root = tmp_path
    dst = root / "dst"
    with pytest.raises(RuntimeError, match='Source directory not found: .*'):
        entrypoint.copy_rec(root / "src", dst, warning_as_error=True)


def test_empty_src(tmp_path):
    root = tmp_path
    with directory(root / "src") as src:
        dst = root / "dst"
        entrypoint.copy_rec(src, dst)
    assert dst.exists()
    assert oct(dst.stat().st_mode).endswith("777")


def test_file(tmp_path):
    root = tmp_path
    with directory(root / "src") as src:
        testee = create_file(src / "file.txt")
        dst = root / "dst"
        entrypoint.copy_rec(src, dst)
    copy = dst / testee.name
    assert copy.exists()
    assert copy.read_text() == testee.read_text()
    assert oct(copy.stat().st_mode).endswith("666")


def test_dir(tmp_path):
    root = tmp_path
    with directory(root / "src") as src:
        with directory(src / "sub") as sub:
            testee = create_file(sub / "file.txt")
        dst = root / "dst"
        entrypoint.copy_rec(src, dst)
    copy = dst / "sub" / testee.name
    assert copy.exists()
    assert copy.read_text() == testee.read_text()
    assert oct(copy.stat().st_mode).endswith("666")
