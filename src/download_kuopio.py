from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import sys
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ZENODO_RECORD_ID = "10559504"
ZENODO_DOI = "10.5281/zenodo.10559504"

ARCHIVES = [
    {
        "filename": "measurement_data_1_to_17.zip",
        "url": "https://zenodo.org/api/records/10559504/files/measurement_data_1_to_17.zip/content",
        "size_bytes": 7_259_126_563,
        "md5": "edab84684570169b3f0d239b2d9fa629",
        "subjects": [f"{i:02d}" for i in range(1, 18)],
    },
    {
        "filename": "measurement_data_18_to_34.zip",
        "url": "https://zenodo.org/api/records/10559504/files/measurement_data_18_to_34.zip/content",
        "size_bytes": 8_703_000_947,
        "md5": "8728c009f535d6198a03e853acc21d21",
        "subjects": [f"{i:02d}" for i in range(18, 35)],
    },
    {
        "filename": "measurement_data_35_to_51.zip",
        "url": "https://zenodo.org/api/records/10559504/files/measurement_data_35_to_51.zip/content",
        "size_bytes": 7_336_583_345,
        "md5": "200c10674354ce2d052b14816f93f408",
        "subjects": [f"{i:02d}" for i in range(35, 52)],
    },
]

XLSX = {
    "filename": "info_participants.xlsx",
    "url": "https://zenodo.org/api/records/10559504/files/info_participants.xlsx/content",
    "size_bytes": 19_644,
    "md5": "013c2dc43224098bdd9ed94885146e50",
    "dest": "data/info_participants.xlsx",
}

IMU_MISSING_SUBJECTS = {"11", "14", "37", "49"}

PIPELINE_SUBDIRS = ("imu_extracted", "mocap")

DATA_DIR = Path("data")
KUOPIO_DIR = DATA_DIR / "kuopio"
TMP_DIR = KUOPIO_DIR / "_tmp"

NORMALIZE_REMOVE = ("imu", "openpose")

ENTRY_PATTERN = re.compile(r"^(\d{2})/(imu_extracted|mocap)/")

CHUNK_SIZE = 8 * 1024 * 1024

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2


def expected_subdirs(subject):
    if subject in IMU_MISSING_SUBJECTS:
        return {"mocap"}
    return set(PIPELINE_SUBDIRS)


def normalize_subject_dirs():
    if not KUOPIO_DIR.is_dir():
        return
    removed = 0
    for subj_dir in sorted(KUOPIO_DIR.iterdir()):
        if not subj_dir.is_dir() or len(subj_dir.name) != 2 or not subj_dir.name.isdigit():
            continue
        for sub in NORMALIZE_REMOVE:
            target = subj_dir / sub
            if target.is_dir():
                shutil.rmtree(target)
                print(f"[normalize] removed {target}")
                removed += 1
    if removed == 0:
        print("[normalize] no stray imu/ or openpose/ subdirs found")


def md5_of_file(path):
    h = hashlib.md5()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(CHUNK_SIZE), b""):
            h.update(block)
    return h.hexdigest()


def subject_is_complete(subject):
    subj_dir = KUOPIO_DIR / subject
    if not subj_dir.is_dir():
        return False
    for subdir in expected_subdirs(subject):
        target = subj_dir / subdir
        if not target.is_dir():
            return False
        try:
            next(target.iterdir())
        except StopIteration:
            return False
    return True


def human_bytes(n):
    for unit in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024:
            return f"{int(n)} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def stream_download(url, dest, expected_size):
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    downloaded = 0
    with urllib.request.urlopen(url) as resp, part.open("wb") as out:
        while True:
            chunk = resp.read(CHUNK_SIZE)
            if not chunk:
                break
            out.write(chunk)
            downloaded += len(chunk)
    if downloaded != expected_size:
        raise RuntimeError(
            f"size mismatch for {url}: expected {expected_size}, got {downloaded}"
        )
    part.replace(dest)


def fetch_xlsx():
    dest = Path(XLSX["dest"])
    if dest.exists() and md5_of_file(dest) == XLSX["md5"]:
        print(f"[xlsx] {dest} already present with matching MD5 — skipping")
        return
    print(f"[xlsx] fetching {XLSX['filename']} ({human_bytes(XLSX['size_bytes'])})...")
    stream_download(XLSX["url"], dest, XLSX["size_bytes"])
    actual = md5_of_file(dest)
    if actual != XLSX["md5"]:
        raise RuntimeError(f"md5 mismatch for {dest}: expected {XLSX['md5']}, got {actual}")
    print("[xlsx] md5 OK")


def process_archive(idx, total, archive, force):
    subjects = archive["subjects"]
    complete = [s for s in subjects if subject_is_complete(s)]
    print(
        f"[{idx}/{total}] {archive['filename']} "
        f"({len(subjects)} subjects: {subjects[0]}–{subjects[-1]})"
    )

    if not force and len(complete) == len(subjects):
        print(
            f"      idempotency: {len(complete)}/{len(subjects)} subjects complete on disk — skipping"
        )
        return

    print(
        f"      idempotency: {len(complete)}/{len(subjects)} subjects complete on disk — fetching"
    )
    zip_path = TMP_DIR / archive["filename"]
    print(f"      downloading {human_bytes(archive['size_bytes'])} to {zip_path}...")
    stream_download(archive["url"], zip_path, archive["size_bytes"])

    actual = md5_of_file(zip_path)
    if actual != archive["md5"]:
        raise RuntimeError(
            f"md5 mismatch for {zip_path}: expected {archive['md5']}, got {actual}"
        )
    print(f"      md5 OK ({archive['md5'][:12]}...)")

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        found_subjects = {m.group(1) for m in (ENTRY_PATTERN.match(n) for n in names) if m}
        missing = [s for s in subjects if s not in found_subjects]
        if missing:
            print(
                f"      WARNING: expected subjects {missing} not found in archive — "
                "continuing with what is present",
                file=sys.stderr,
            )
        to_extract = [n for n in names if ENTRY_PATTERN.match(n)]
        for name in to_extract:
            zf.extract(name, KUOPIO_DIR)
        extracted_subjects = sorted({ENTRY_PATTERN.match(n).group(1) for n in to_extract})
        print(f"      extracted imu_extracted + mocap for {len(extracted_subjects)} subjects")

    zip_path.unlink()
    print("      removed ZIP")


def final_tally():
    if not KUOPIO_DIR.is_dir():
        print("done: no subjects extracted (data/kuopio/ missing)")
        return
    with_imu = 0
    mocap_only = 0
    for subj_dir in sorted(KUOPIO_DIR.iterdir()):
        if not subj_dir.is_dir() or not subj_dir.name.isdigit():
            continue
        subject = subj_dir.name
        if not subject_is_complete(subject):
            continue
        if subject in IMU_MISSING_SUBJECTS:
            mocap_only += 1
        else:
            with_imu += 1
    n = with_imu + mocap_only
    print(f"done: {n} subjects extracted ({with_imu} with IMU, {mocap_only} mocap-only)")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Kuopio gait dataset from Zenodo record 10559504."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download and re-extract even if subject dirs appear complete.",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=3,
        help="Number of archives to download concurrently (default: 3).",
    )
    args = parser.parse_args()

    KUOPIO_DIR.mkdir(parents=True, exist_ok=True)

    print("Fetching ~23 GB from Zenodo — this may take a while.")

    try:
        normalize_subject_dirs()
        fetch_xlsx()
        indexed = list(enumerate(ARCHIVES, start=1))
        if args.jobs > 1:
            with ThreadPoolExecutor(max_workers=args.jobs) as ex:
                list(ex.map(
                    lambda pair: process_archive(pair[0], len(ARCHIVES), pair[1], args.force),
                    indexed,
                ))
        else:
            for i, archive in indexed:
                process_archive(i, len(ARCHIVES), archive, args.force)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return EXIT_FAIL

    final_tally()

    try:
        TMP_DIR.rmdir()
    except OSError:
        pass

    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
