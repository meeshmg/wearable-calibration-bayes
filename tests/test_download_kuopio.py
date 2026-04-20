"""Unit tests for src/download_kuopio.py.

Covers the gap table recorded in dev_docs/active/PACKAGING_PLAN.md
under the "Validation status" subsection of the downloader spec:
``stream_download`` chunked HTTP + size check + atomic rename, archive
MD5 verification on downloaded ZIPs, ``zipfile`` namelist inspection +
ENTRY_PATTERN filter, selective extraction + ZIP cleanup, the
``--force`` bypass branch, and the error paths (size mismatch, MD5
mismatch, missing subject warning). Also regression-covers the paths
already exercised by the one-shot idempotent run: ``expected_subdirs``,
``subject_is_complete``, ``final_tally``, and ``md5_of_file``.

Tests mock ``urllib.request.urlopen`` and monkeypatch the module-level
path constants onto ``tmp_path``-derived directories so no real HTTP
traffic occurs and no real ``data/`` files are touched.
"""

import hashlib
import io
import zipfile
from pathlib import Path

import pytest

import download_kuopio as dk


# ---------------------------------------------------------------------------
# Small helpers shared across tests
# ---------------------------------------------------------------------------


class FakeResponse:
    """Context-manager-compatible stand-in for ``urllib.request.urlopen``.

    Serves ``payload`` in chunks via ``.read(n)`` so the downloader's
    streaming loop is exercised with multiple iterations.
    """

    def __init__(self, payload: bytes) -> None:
        self._buf = io.BytesIO(payload)

    def read(self, n: int) -> bytes:
        return self._buf.read(n)

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: D401 - short ctx-mgr
        return None


def _make_synthetic_zip(path: Path, entries: dict[str, bytes]) -> None:
    """Write a ZIP_STORED archive at ``path`` with the given entries."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)


def _populate_subject(
    kuopio_dir: Path, subject: str, subdirs: tuple[str, ...], empty: bool = False
) -> Path:
    """Create ``kuopio_dir/<subject>/<subdir>/`` with optional dummy files."""
    subj_dir = kuopio_dir / subject
    subj_dir.mkdir(parents=True, exist_ok=True)
    for sub in subdirs:
        target = subj_dir / sub
        target.mkdir(parents=True, exist_ok=True)
        if not empty:
            (target / "placeholder.txt").write_text("x")
    return subj_dir


@pytest.fixture
def fake_paths(tmp_path, monkeypatch):
    """Point DATA_DIR / KUOPIO_DIR / TMP_DIR into ``tmp_path``.

    Yields the ``kuopio`` directory for convenience.
    """
    data = tmp_path / "data"
    kuopio = data / "kuopio"
    tmp_ = kuopio / "_tmp"
    kuopio.mkdir(parents=True)
    tmp_.mkdir(parents=True)
    monkeypatch.setattr(dk, "DATA_DIR", data)
    monkeypatch.setattr(dk, "KUOPIO_DIR", kuopio)
    monkeypatch.setattr(dk, "TMP_DIR", tmp_)
    return kuopio


# ---------------------------------------------------------------------------
# md5_of_file (regression)
# ---------------------------------------------------------------------------


def test_md5_of_file_matches_known_digest(tmp_path):
    content = b"the quick brown fox jumps over the lazy dog"
    path = tmp_path / "sample.bin"
    path.write_bytes(content)
    expected = hashlib.md5(content).hexdigest()
    assert dk.md5_of_file(path) == expected


# ---------------------------------------------------------------------------
# expected_subdirs (regression)
# ---------------------------------------------------------------------------


def test_expected_subdirs_regular_subject():
    assert dk.expected_subdirs("01") == {"imu_extracted", "mocap"}


@pytest.mark.parametrize("subject", sorted(dk.IMU_MISSING_SUBJECTS))
def test_expected_subdirs_imu_missing_subject(subject):
    assert dk.expected_subdirs(subject) == {"mocap"}


# ---------------------------------------------------------------------------
# subject_is_complete (regression)
# ---------------------------------------------------------------------------


def test_subject_is_complete_missing_dir(fake_paths):
    assert dk.subject_is_complete("01") is False


def test_subject_is_complete_empty_dir(fake_paths):
    (fake_paths / "01").mkdir()
    assert dk.subject_is_complete("01") is False


def test_subject_is_complete_missing_one_subdir(fake_paths):
    _populate_subject(fake_paths, "01", ("mocap",))  # missing imu_extracted
    assert dk.subject_is_complete("01") is False


def test_subject_is_complete_empty_subdirs(fake_paths):
    _populate_subject(fake_paths, "01", ("imu_extracted", "mocap"), empty=True)
    assert dk.subject_is_complete("01") is False


def test_subject_is_complete_full_regular_subject(fake_paths):
    _populate_subject(fake_paths, "01", ("imu_extracted", "mocap"))
    assert dk.subject_is_complete("01") is True


def test_subject_is_complete_imu_missing_subject_mocap_only(fake_paths):
    # Subject 11 is in IMU_MISSING_SUBJECTS; only mocap is expected.
    _populate_subject(fake_paths, "11", ("mocap",))
    assert dk.subject_is_complete("11") is True


def test_subject_is_complete_imu_missing_subject_empty_mocap(fake_paths):
    _populate_subject(fake_paths, "11", ("mocap",), empty=True)
    assert dk.subject_is_complete("11") is False


# ---------------------------------------------------------------------------
# final_tally (regression)
# ---------------------------------------------------------------------------


def test_final_tally_classifies_regular_and_mocap_only(fake_paths, capsys):
    # 3 regular complete + 2 IMU-missing complete + 1 regular incomplete.
    _populate_subject(fake_paths, "01", ("imu_extracted", "mocap"))
    _populate_subject(fake_paths, "02", ("imu_extracted", "mocap"))
    _populate_subject(fake_paths, "03", ("imu_extracted", "mocap"))
    _populate_subject(fake_paths, "11", ("mocap",))
    _populate_subject(fake_paths, "14", ("mocap",))
    _populate_subject(fake_paths, "04", ("mocap",))  # regular, missing imu_extracted
    # Non-subject directory should be ignored.
    (fake_paths / "_tmp").mkdir(exist_ok=True)

    dk.final_tally()
    out = capsys.readouterr().out
    assert "5 subjects extracted" in out
    assert "3 with IMU" in out
    assert "2 mocap-only" in out


def test_final_tally_missing_kuopio_dir(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(dk, "KUOPIO_DIR", tmp_path / "does_not_exist")
    dk.final_tally()
    assert "no subjects extracted" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# stream_download
# ---------------------------------------------------------------------------


def test_stream_download_writes_file_and_renames_atomically(tmp_path, monkeypatch):
    payload = b"A" * (dk.CHUNK_SIZE + 1024)  # force more than one chunk
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda url: FakeResponse(payload)
    )
    dest = tmp_path / "out" / "archive.zip"
    dk.stream_download("https://example.test/file", dest, len(payload))
    assert dest.read_bytes() == payload
    # .part file should be renamed away.
    assert not dest.with_suffix(dest.suffix + ".part").exists()


def test_stream_download_size_mismatch_raises(tmp_path, monkeypatch):
    payload = b"only-eleven"  # 11 bytes
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda url: FakeResponse(payload)
    )
    dest = tmp_path / "out" / "archive.zip"
    with pytest.raises(RuntimeError, match="size mismatch"):
        dk.stream_download("https://example.test/file", dest, expected_size=999)
    # Final dest should not be created; the .part file is left in place by design.
    assert not dest.exists()


# ---------------------------------------------------------------------------
# process_archive — happy path and error branches
# ---------------------------------------------------------------------------


def _archive_with_real_zip(tmp_path: Path, filename: str, subjects: list[str]):
    """Build a synthetic ZIP on disk and return a matching archive dict.

    The ZIP includes ``imu_extracted/`` and ``mocap/`` entries (which
    should be extracted) plus ``imu/`` and ``openpose/`` entries (which
    must be skipped). Payload bytes are served by the urlopen mock.
    """
    zip_path = tmp_path / filename
    entries: dict[str, bytes] = {}
    for s in subjects:
        entries[f"{s}/imu_extracted/data_l_comf_01.mat"] = b"imu-extracted-bytes"
        entries[f"{s}/mocap/trial_01.c3d"] = b"mocap-bytes"
        entries[f"{s}/imu/raw_stream.bin"] = b"raw-imu-should-skip"
        entries[f"{s}/openpose/frame_0001.json"] = b"openpose-should-skip"
    _make_synthetic_zip(zip_path, entries)
    payload = zip_path.read_bytes()
    md5 = hashlib.md5(payload).hexdigest()
    archive = {
        "filename": filename,
        "url": f"https://example.test/{filename}",
        "size_bytes": len(payload),
        "md5": md5,
        "subjects": subjects,
    }
    return archive, payload


def test_process_archive_extracts_only_pipeline_subdirs_and_removes_zip(
    tmp_path, fake_paths, monkeypatch
):
    archive, payload = _archive_with_real_zip(
        tmp_path, "measurement_data_small.zip", ["01", "02"]
    )
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda url: FakeResponse(payload)
    )

    dk.process_archive(1, 1, archive, force=False)

    # Extracted entries for both subjects in the two pipeline subdirs.
    for subject in ["01", "02"]:
        assert (fake_paths / subject / "imu_extracted" / "data_l_comf_01.mat").exists()
        assert (fake_paths / subject / "mocap" / "trial_01.c3d").exists()
        # Skipped subdirs must NOT land on disk.
        assert not (fake_paths / subject / "imu").exists()
        assert not (fake_paths / subject / "openpose").exists()

    # ZIP is cleaned up.
    assert not (dk.TMP_DIR / archive["filename"]).exists()


def test_process_archive_md5_mismatch_raises(tmp_path, fake_paths, monkeypatch):
    archive, payload = _archive_with_real_zip(
        tmp_path, "measurement_data_badmd5.zip", ["01"]
    )
    archive = {**archive, "md5": "0" * 32}  # force mismatch
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda url: FakeResponse(payload)
    )

    with pytest.raises(RuntimeError, match="md5 mismatch"):
        dk.process_archive(1, 1, archive, force=False)

    # ZIP should be left in place for diagnosis (per spec).
    assert (dk.TMP_DIR / archive["filename"]).exists()


def test_process_archive_missing_subject_warns_and_continues(
    tmp_path, fake_paths, monkeypatch, capsys
):
    # Archive claims subjects 01 & 02 but ZIP only contains 01.
    archive, payload = _archive_with_real_zip(
        tmp_path, "measurement_data_missing.zip", ["01"]
    )
    archive = {**archive, "subjects": ["01", "02"]}
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda url: FakeResponse(payload)
    )

    # Should NOT raise — just warn to stderr.
    dk.process_archive(1, 1, archive, force=False)

    err = capsys.readouterr().err
    assert "WARNING" in err
    assert "02" in err
    # Subject 01 still extracted successfully.
    assert (fake_paths / "01" / "imu_extracted" / "data_l_comf_01.mat").exists()


def test_process_archive_idempotent_skip_when_all_complete(
    fake_paths, monkeypatch, capsys
):
    # Pre-populate both subjects so the idempotency branch is taken.
    _populate_subject(fake_paths, "01", ("imu_extracted", "mocap"))
    _populate_subject(fake_paths, "02", ("imu_extracted", "mocap"))

    def _fail_urlopen(url):  # pragma: no cover - must not be called
        raise AssertionError(
            "urlopen should not be called when all subjects are complete"
        )

    monkeypatch.setattr("urllib.request.urlopen", _fail_urlopen)
    archive = {
        "filename": "should_be_skipped.zip",
        "url": "https://example.test/should_be_skipped.zip",
        "size_bytes": 0,
        "md5": "0" * 32,
        "subjects": ["01", "02"],
    }

    dk.process_archive(1, 1, archive, force=False)

    out = capsys.readouterr().out
    assert "skipping" in out


def test_process_archive_force_bypasses_idempotency(
    tmp_path, fake_paths, monkeypatch
):
    # Pre-populate so the NON-forced branch would skip. With force=True
    # the downloader should proceed to stream_download and extraction.
    _populate_subject(fake_paths, "01", ("imu_extracted", "mocap"))
    archive, payload = _archive_with_real_zip(
        tmp_path, "measurement_data_force.zip", ["01"]
    )

    calls = {"urlopen": 0}

    def _count_urlopen(url):
        calls["urlopen"] += 1
        return FakeResponse(payload)

    monkeypatch.setattr("urllib.request.urlopen", _count_urlopen)

    dk.process_archive(1, 1, archive, force=True)

    assert calls["urlopen"] == 1, "force=True should trigger a download"
    # Extraction landed the synthetic entry on disk.
    assert (fake_paths / "01" / "imu_extracted" / "data_l_comf_01.mat").exists()
    assert not (dk.TMP_DIR / archive["filename"]).exists()


# ---------------------------------------------------------------------------
# normalize_subject_dirs — always-normalize (option c)
# ---------------------------------------------------------------------------


def test_normalize_removes_imu_and_openpose_but_preserves_pipeline_subdirs(
    fake_paths, capsys
):
    # Subject 18 mirrors the real on-disk inconsistency: has all 4 subdirs.
    _populate_subject(fake_paths, "18", ("imu_extracted", "mocap", "imu", "openpose"))
    # Subject 01 is already clean — must be left alone.
    _populate_subject(fake_paths, "01", ("imu_extracted", "mocap"))
    # Subject 11 is mocap-only (IMU-missing) — must also be left alone.
    _populate_subject(fake_paths, "11", ("mocap",))
    # A non-subject directory (e.g. _tmp) must be ignored by the 2-digit filter.
    (fake_paths / "_tmp").mkdir(exist_ok=True)
    (fake_paths / "_tmp" / "imu").mkdir()

    dk.normalize_subject_dirs()

    # Stray subdirs gone from subject 18.
    assert not (fake_paths / "18" / "imu").exists()
    assert not (fake_paths / "18" / "openpose").exists()
    # Pipeline subdirs preserved on subject 18.
    assert (fake_paths / "18" / "imu_extracted" / "placeholder.txt").exists()
    assert (fake_paths / "18" / "mocap" / "placeholder.txt").exists()
    # Clean subjects untouched.
    assert (fake_paths / "01" / "imu_extracted" / "placeholder.txt").exists()
    assert (fake_paths / "01" / "mocap" / "placeholder.txt").exists()
    assert (fake_paths / "11" / "mocap" / "placeholder.txt").exists()
    # Non-subject dirs untouched (filter rejects non-2-digit names).
    assert (fake_paths / "_tmp" / "imu").exists()

    out = capsys.readouterr().out
    assert "removed" in out
    assert "18/imu" in out
    assert "18/openpose" in out


def test_normalize_no_strays_prints_clean_message(fake_paths, capsys):
    _populate_subject(fake_paths, "01", ("imu_extracted", "mocap"))
    _populate_subject(fake_paths, "11", ("mocap",))

    dk.normalize_subject_dirs()

    out = capsys.readouterr().out
    assert "no stray" in out


def test_normalize_missing_kuopio_dir_is_noop(tmp_path, monkeypatch):
    monkeypatch.setattr(dk, "KUOPIO_DIR", tmp_path / "does_not_exist")
    dk.normalize_subject_dirs()  # must not raise


# ---------------------------------------------------------------------------
# ENTRY_PATTERN regex (regression — core filter used by process_archive)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name,should_match",
    [
        ("01/imu_extracted/data.mat", True),
        ("01/mocap/trial.c3d", True),
        ("17/imu_extracted/deep/nested/path.mat", True),
        ("01/imu/raw.bin", False),
        ("01/openpose/frame.json", False),
        ("1/imu_extracted/data.mat", False),  # single-digit ID — rejected
        ("01/other/x", False),
        ("imu_extracted/x", False),
    ],
)
def test_entry_pattern_matches_only_pipeline_subdirs(name, should_match):
    assert bool(dk.ENTRY_PATTERN.match(name)) is should_match
