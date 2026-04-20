import pathlib
import re
import sys

import arviz as az
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ground_truth import detect_heel_strikes
from imu import detect_steps, load_trial

PROJECT = pathlib.Path(__file__).parent.parent
DATA_ROOT = PROJECT / "data"
KUOPIO_ROOT = DATA_ROOT / "kuopio"
INFO_XLSX = DATA_ROOT / "info_participants.xlsx"
IDATA_M3 = DATA_ROOT / "processed" / "idata_model_3.nc"
PROCESSED_PARQUET = DATA_ROOT / "processed" / "modeling_df.parquet"
REFERENCE_PARQUET = DATA_ROOT / "reference" / "modeling_df.parquet"
OUT_DIR = DATA_ROOT / "scout"

SKIP_SUBJECTS = {11, 14, 37, 49}
TRIAL_RE = re.compile(r"^([lr])_(slow|comf|fast)_(\d+)\.c3d$")
G_M_S2 = 9.80665


def _modeling_parquet():
    return PROCESSED_PARQUET if PROCESSED_PARQUET.exists() else REFERENCE_PARQUET


def section_a_detector_calibration():
    subject_01 = KUOPIO_ROOT / "01"
    c3d_trial = subject_01 / "mocap" / "l_comf_01.c3d"
    tolerance_pct = 10.0

    imu_arrays = load_trial(subject_01, "data_l_comf_01.mat")
    pelvis = imu_arrays["pelvis"]
    imu_result = detect_steps(pelvis["freeAcceleration"], pelvis["time"])
    plate_result = detect_heel_strikes(c3d_trial)

    n_imu = imu_result["n_peaks_imu"]
    n_plate = plate_result["n_detected"]
    cadence_imu = imu_result["cadence_imu"]
    cadence_plate = plate_result["cadence_steps_per_min"]

    pct_diff_count = (n_imu - n_plate) / n_plate * 100.0 if n_plate > 0 else float("nan")
    pct_diff_cadence = (
        (cadence_imu - cadence_plate) / cadence_plate * 100.0
        if cadence_imu is not None and cadence_plate
        else float("nan")
    )
    within = abs(pct_diff_cadence) <= tolerance_pct

    print("Subject 01, trial l_comf_01 (pelvis sensor)")
    print(f"  IMU peaks: {n_imu} (full trial)")
    print(f"  Plate strikes: {n_plate} (walkway crossing only)")
    print(f"  Step-count %diff: {pct_diff_count:+.1f}%")
    print(f"  IMU cadence: {cadence_imu} spm")
    print(f"  Plate cadence: {cadence_plate} spm")
    print(f"  Cadence %diff: {pct_diff_cadence:+.1f}% (target: ±{tolerance_pct:.0f}%)")
    print(f"  IMU trial dur: {imu_result['trial_duration_s']:.2f} s")
    print(
        f"  Plate window: {plate_result['plate_window_start_s']:.2f}–"
        f"{plate_result['plate_window_end_s']:.2f} s"
    )
    print(f"  Within ±{tolerance_pct:.0f}%? {'YES' if within else 'NO'}")

    time_s = pelvis["time"]
    magnitude_g = np.linalg.norm(pelvis["freeAcceleration"], axis=1) / G_M_S2
    peak_times = np.asarray(imu_result["peak_times_s"])
    peak_idx = np.searchsorted(time_s, peak_times)
    strike_times = np.asarray(plate_result["heel_strikes_s"])

    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(time_s, magnitude_g, color="C0", lw=0.8, label="|freeAcceleration| (g)")
    ax.plot(peak_times, magnitude_g[peak_idx], "o", color="C3", ms=5, label=f"IMU peaks (n={n_imu})")
    ax.axvspan(
        plate_result["plate_window_start_s"],
        plate_result["plate_window_end_s"],
        color="grey", alpha=0.15, label="plate window",
    )
    for t in strike_times:
        ax.axvline(t, color="black", ls=":", lw=1, alpha=0.7)
    ax.plot([], [], color="black", ls=":", label=f"plate heel strikes (n={n_plate})")
    ax.set_xlabel("time (s)")
    ax.set_ylabel("pelvis |freeAcceleration| (g)")
    ax.set_title("Subject 01, l_comf_01: IMU peaks vs force-plate heel strikes")
    ax.legend(loc="upper right", fontsize=9)
    plt.tight_layout()
    fig_path = OUT_DIR / "single_trial_detector.png"
    fig.savefig(fig_path, dpi=200, bbox_inches="tight")
    plt.close(fig)

    csv_path = OUT_DIR / "detector_subject01_calibration.csv"
    pd.Series(
        {
            "trial": "l_comf_01",
            "subject_id": "01",
            "n_imu_peaks": int(n_imu),
            "n_plate_strikes": int(n_plate),
            "cadence_imu_spm": float(cadence_imu),
            "cadence_plate_spm": float(cadence_plate),
            "pct_diff_count": float(pct_diff_count),
            "pct_diff_cadence": float(pct_diff_cadence),
            "tolerance_pct": float(tolerance_pct),
            "within_tolerance": bool(within),
        },
        name="value",
    ).rename_axis("metric").to_csv(csv_path)
    print(f"Wrote {fig_path}")
    print(f"Wrote {csv_path}")


def section_b_n_strikes_scout():
    info = pd.read_excel(INFO_XLSX)
    invalid_by_subject = {}
    for _, row in info.iterrows():
        sid_padded = f"{int(row['ID']):02d}"
        raw = row["Invalid_trials"]
        if isinstance(raw, str) and raw.strip():
            invalid_by_subject[sid_padded] = {t.strip() for t in raw.split(",") if t.strip()}
        else:
            invalid_by_subject[sid_padded] = set()

    rows = []
    for sid_int in range(1, 52):
        if sid_int in SKIP_SUBJECTS:
            continue
        sid = f"{sid_int:02d}"
        mocap_dir = KUOPIO_ROOT / sid / "mocap"
        if not mocap_dir.is_dir():
            continue
        invalid = invalid_by_subject.get(sid, set())
        for c3d_path in sorted(mocap_dir.glob("*.c3d")):
            m = TRIAL_RE.match(c3d_path.name)
            if m is None:
                continue
            leg, speed, trial_num = m.group(1), m.group(2), m.group(3)
            if c3d_path.stem in invalid:
                continue
            try:
                result = detect_heel_strikes(c3d_path)
            except Exception as exc:
                print(f"ERROR {sid} {c3d_path.stem}: {exc!r}")
                continue
            rows.append({
                "subject_id": sid,
                "trial_name": c3d_path.stem,
                "leg": leg,
                "speed": speed,
                "trial_num": trial_num,
                "n_strikes_plate": int(result["n_detected"]),
                "qc_flags": ",".join(result["diagnostics"]["qc_flags"]),
            })

    scout_df = pd.DataFrame(rows)
    parquet_path = OUT_DIR / "n_strikes_distribution.parquet"
    scout_df.to_parquet(parquet_path, index=False)
    print(f"Wrote {parquet_path}: {len(scout_df)} rows")

    print("n_strikes_plate distribution:")
    print(scout_df["n_strikes_plate"].describe().to_string())
    print("\nCounts by n_strikes_plate:")
    print(scout_df["n_strikes_plate"].value_counts().sort_index().to_string())
    print("\nTrials with n_strikes_plate < 2 (too few to define cadence):")
    print(f"  {(scout_df['n_strikes_plate'] < 2).sum()} / {len(scout_df)}")

    headline_path = OUT_DIR / "scout_n_strikes_headline.csv"
    pd.Series(
        {
            "n_trials": len(scout_df),
            "n_lt_2_strikes": int((scout_df["n_strikes_plate"] < 2).sum()),
            **scout_df["n_strikes_plate"].describe().to_dict(),
        },
        name="value",
    ).rename_axis("metric").to_csv(headline_path)

    counts_path = OUT_DIR / "scout_n_strikes_counts.csv"
    (
        scout_df["n_strikes_plate"]
        .value_counts()
        .sort_index()
        .rename_axis("n_strikes_plate")
        .to_frame("n_trials")
        .to_csv(counts_path)
    )
    print(f"Wrote {headline_path}")
    print(f"Wrote {counts_path}")


def appendix_per_subject_alpha():
    if not IDATA_M3.exists():
        print(
            f"Skipping per-subject alpha appendix — {IDATA_M3} not found. "
            f"Run notebooks/model_3.ipynb to produce it."
        )
        return

    idata_m3 = az.from_netcdf(IDATA_M3)
    summ = az.summary(idata_m3, var_names=["alpha_subject"], hdi_prob=0.95)
    summ = summ.reset_index().rename(columns={"index": "var_id"})
    summ["subject_id"] = summ["var_id"].str.extract(r"alpha_subject\[(.+?)\]")[0].astype(str)
    summ = summ[["subject_id", "mean", "hdi_2.5%", "hdi_97.5%"]].rename(
        columns={"mean": "alpha_mean", "hdi_2.5%": "hdi_lo", "hdi_97.5%": "hdi_hi"}
    )

    mdf_fit = pd.read_parquet(_modeling_parquet()).query("modeling_include")
    per_sub = (
        mdf_fit.groupby("subject_id")
        .agg(sex=("sex", "first"), n_trials=("subject_id", "size"))
        .reset_index()
    )
    appendix = (
        summ.merge(per_sub, on="subject_id", how="left")
        [["subject_id", "sex", "n_trials", "alpha_mean", "hdi_lo", "hdi_hi"]]
        .sort_values("alpha_mean", ascending=True)
        .reset_index(drop=True)
    )
    out = OUT_DIR / "appendix_per_subject_summary.csv"
    appendix.to_csv(out, index=False)
    print(f"Wrote {out}")


def appendix_cohort_demographics():
    raw = pd.read_excel(INFO_XLSX)
    df = raw[~raw["ID"].isin(SKIP_SUBJECTS)].copy()
    df["leg_length_mm"] = (
        df["Left_thigh_length"] + df["Left_shank_length"]
        + df["Right_thigh_length"] + df["Right_shank_length"]
    ) / 2.0
    df = df.rename(columns={
        "Age": "age_years",
        "Height": "height_cm",
        "Mass": "mass_kg",
        "IAD": "iad_mm",
        "Gender": "sex",
    })

    metrics = ["age_years", "height_cm", "mass_kg", "leg_length_mm", "iad_mm"]
    groups = [("F", df[df["sex"] == "F"]), ("M", df[df["sex"] == "M"]), ("All", df)]

    rows = []
    for sex_label, sub in groups:
        rows.append({
            "sex": sex_label,
            "metric": "n_subjects",
            "n": len(sub),
            "mean": np.nan,
            "sd": np.nan,
            "min": np.nan,
            "max": np.nan,
        })
        for m in metrics:
            v = sub[m].astype(float)
            rows.append({
                "sex": sex_label,
                "metric": m,
                "n": int(v.notna().sum()),
                "mean": float(v.mean()),
                "sd": float(v.std(ddof=1)),
                "min": float(v.min()),
                "max": float(v.max()),
            })
    cohort = pd.DataFrame(rows, columns=["sex", "metric", "n", "mean", "sd", "min", "max"])
    out = OUT_DIR / "cohort_demographics_summary.csv"
    cohort.to_csv(out, index=False)
    print(f"Wrote {out}")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=== §A Detector calibration ===")
    section_a_detector_calibration()
    print("\n=== §B n_strikes_plate scout ===")
    section_b_n_strikes_scout()
    print("\n=== Appendix: per-subject alpha (Model 3) ===")
    appendix_per_subject_alpha()
    print("\n=== Appendix: cohort demographics ===")
    appendix_cohort_demographics()
    return 0


if __name__ == "__main__":
    sys.exit(main())
