import pathlib
import re
import sys
import traceback

import pandas as pd

from ground_truth import detect_heel_strikes
from imu import detect_steps, load_trial

PROJECT = pathlib.Path(__file__).parent.parent
DATA_ROOT = PROJECT / "data" / "kuopio"
INFO_XLSX = PROJECT / "data" / "info_participants.xlsx"
OUT_DIR = PROJECT / "data" / "processed"
OUT_PATH = OUT_DIR / "modeling_df.parquet"

SKIP_SUBJECTS = {11, 14, 37, 49}
TRIAL_RE = re.compile(r"^([lr])_(slow|comf|fast)_(\d+)\.c3d$")

SENSITIVITY_LOCATIONS = [
    "right_femur",
    "left_femur",
    "right_tibia",
    "left_tibia",
    "right_foot",
    "left_foot",
]
FOOT_LOCATIONS = {"left_foot", "right_foot"}


def _location_factor(loc):
    return 0.5 if loc in FOOT_LOCATIONS else 1.0


def _subject_info():
    df = pd.read_excel(INFO_XLSX)
    df["subject_id"] = df["ID"].apply(lambda x: f"{int(x):02d}")
    df["leg_length_mm"] = (
        df["Left_thigh_length"]
        + df["Left_shank_length"]
        + df["Right_thigh_length"]
        + df["Right_shank_length"]
    ) / 2
    df["invalid_trials_set"] = df["Invalid_trials"].apply(
        lambda raw: {t.strip() for t in raw.split(",") if t.strip()}
        if isinstance(raw, str) and raw.strip()
        else set()
    )
    return df.set_index("subject_id")


def _demographic_fields(sid, subject_row):
    return {
        "subject_id": sid,
        "sex": subject_row["Gender"],
        "age": int(subject_row["Age"]),
        "height_cm": float(subject_row["Height"]),
        "mass_kg": float(subject_row["Mass"]),
        "iad_mm": float(subject_row["IAD"]),
        "leg_length_mm": float(subject_row["leg_length_mm"]),
    }


def _process_trial(subject_dir, c3d_path, leg, speed, trial_num, sid, subject_row):
    trial_basename = c3d_path.stem
    mat_filename = f"data_{trial_basename}.mat"

    row = _demographic_fields(sid, subject_row)
    row.update({"speed": speed, "leading_leg": leg, "trial_num": trial_num})

    imu = load_trial(subject_dir, mat_filename)
    if "pelvis" not in imu:
        raise ValueError("pelvis sensor missing from IMU file")
    pelvis = detect_steps(imu["pelvis"]["freeAcceleration"], imu["pelvis"]["time"])
    row["cadence_imu"] = pelvis["cadence_imu"]
    row["trial_duration_s"] = pelvis["trial_duration_s"]

    for loc in SENSITIVITY_LOCATIONS:
        if loc in imu:
            steps = detect_steps(imu[loc]["freeAcceleration"], imu[loc]["time"])
            row[f"cadence_imu_{loc}"] = steps["cadence_imu"]
        else:
            row[f"cadence_imu_{loc}"] = None

    gt = detect_heel_strikes(c3d_path)
    plate = gt["cadence_steps_per_min"]
    row["cadence_plate"] = plate
    row["n_strikes_plate"] = int(gt["n_detected"])
    start, end = gt["plate_window_start_s"], gt["plate_window_end_s"]
    row["plate_window_duration_s"] = (
        end - start if start is not None and end is not None else None
    )
    per_plate = gt["diagnostics"]["per_plate_counts"]
    for k in range(1, 6):
        row[f"plate_{k}_strikes"] = int(per_plate[k - 1])

    if plate is not None and row["cadence_imu"] is not None:
        row["cadence_error"] = row["cadence_imu"] - plate
    else:
        row["cadence_error"] = None
    for loc in SENSITIVITY_LOCATIONS:
        imu_loc = row[f"cadence_imu_{loc}"]
        if plate is not None and imu_loc is not None:
            row[f"cadence_error_{loc}"] = imu_loc - _location_factor(loc) * plate
        else:
            row[f"cadence_error_{loc}"] = None

    flags = list(gt["diagnostics"]["qc_flags"])
    if row["n_strikes_plate"] < 3:
        flags.append("n_strikes_below_3")
    if row["cadence_imu"] is None:
        flags.append("imu_pelvis_no_cadence")
    row["qc_flags"] = ",".join(flags)
    row["modeling_include"] = (
        row["n_strikes_plate"] >= 3
        and row["cadence_imu"] is not None
        and row["cadence_plate"] is not None
    )

    return row


def _error_row(sid, subject_row, leg, speed, trial_num, exc):
    row = _demographic_fields(sid, subject_row)
    row.update({"speed": speed, "leading_leg": leg, "trial_num": trial_num})
    row["qc_flags"] = f"pipeline_error:{type(exc).__name__}"
    row["modeling_include"] = False
    return row


def main():
    info = _subject_info()
    rows = []
    errors = []
    zero_usable_subjects = []

    for sid_int in range(1, 52):
        if sid_int in SKIP_SUBJECTS:
            continue
        sid = f"{sid_int:02d}"
        subject_dir = DATA_ROOT / sid
        mocap_dir = subject_dir / "mocap"
        if not mocap_dir.is_dir():
            print(f"ERROR: subject {sid} missing mocap/ dir", file=sys.stderr)
            zero_usable_subjects.append(sid)
            continue
        if sid not in info.index:
            print(f"ERROR: subject {sid} missing from info_participants.xlsx", file=sys.stderr)
            zero_usable_subjects.append(sid)
            continue

        subject_row = info.loc[sid]
        invalid = subject_row["invalid_trials_set"]

        n_total = 0
        n_err = 0
        for c3d_path in sorted(mocap_dir.glob("*.c3d")):
            m = TRIAL_RE.match(c3d_path.name)
            if m is None:
                continue
            leg, speed, trial_num = m.group(1), m.group(2), m.group(3)
            if c3d_path.stem in invalid:
                continue

            n_total += 1
            try:
                rows.append(
                    _process_trial(subject_dir, c3d_path, leg, speed, trial_num, sid, subject_row)
                )
            except Exception as exc:
                rows.append(_error_row(sid, subject_row, leg, speed, trial_num, exc))
                errors.append((sid, c3d_path.stem, repr(exc)))
                n_err += 1
                traceback.print_exc()

        if n_total > 0 and n_err == n_total:
            zero_usable_subjects.append(sid)

        print(f"subject {sid}: {n_total} trials, {n_err} errors", file=sys.stderr)

    if zero_usable_subjects:
        print(
            f"\nSTOPPING: subjects with 0 usable trials: {zero_usable_subjects}",
            file=sys.stderr,
        )
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_parquet(OUT_PATH, index=False)

    n_total = len(df)
    n_eligible = int(df["modeling_include"].sum())
    print("\n=== SUMMARY ===")
    print(f"Total trials written: {n_total}")
    print(f"Modeling-eligible rows: {n_eligible}")
    print(f"Excluded (n<3 or error): {n_total - n_eligible}")
    print("\nPer speed:")
    print(df.groupby("speed")["modeling_include"].agg(total="count", eligible="sum").to_string())
    print("\nPer sex:")
    print(df.groupby("sex")["modeling_include"].agg(total="count", eligible="sum").to_string())
    if errors:
        print(f"\nPipeline errors: {len(errors)}")
        err_df = pd.DataFrame(errors, columns=["subject_id", "trial", "err"])
        print("Top subjects by error count:")
        print(err_df["subject_id"].value_counts().head().to_string())
    print(f"\nWrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
