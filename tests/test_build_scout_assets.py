"""Smoke tests for data/scout/ outputs.

These tests require ``src/build_scout_assets.py`` to have been run
against real downloaded data; they skip otherwise. Schema expectations
track the audit notebook cells that the script replaces.
"""

import pathlib

import pandas as pd
import pytest

SCOUT_DIR = pathlib.Path(__file__).parent.parent / "data" / "scout"

PARQUET = SCOUT_DIR / "n_strikes_distribution.parquet"
SCOUT_HEADLINE_CSV = SCOUT_DIR / "scout_n_strikes_headline.csv"
SCOUT_COUNTS_CSV = SCOUT_DIR / "scout_n_strikes_counts.csv"
CALIB_CSV = SCOUT_DIR / "detector_subject01_calibration.csv"
CALIB_PNG = SCOUT_DIR / "single_trial_detector.png"
COHORT_CSV = SCOUT_DIR / "cohort_demographics_summary.csv"
APPENDIX_ALPHA_CSV = SCOUT_DIR / "appendix_per_subject_summary.csv"


def _require(path: pathlib.Path) -> None:
    if not path.exists():
        pytest.skip(f"{path} missing; run src/build_scout_assets.py")


def test_module_imports():
    import build_scout_assets  # noqa: F401


def test_n_strikes_parquet_schema():
    _require(PARQUET)
    df = pd.read_parquet(PARQUET)
    expected = {
        "subject_id", "trial_name", "leg", "speed", "trial_num",
        "n_strikes_plate", "qc_flags",
    }
    assert expected <= set(df.columns), f"missing cols: {expected - set(df.columns)}"
    # 2818 processable trials per the 2026-04-18 scout; allow a little slack.
    assert 2700 < len(df) < 2900, f"row count {len(df)} outside 2700-2900"
    assert df["n_strikes_plate"].ge(0).all()


def test_scout_headline_and_counts_csvs():
    _require(SCOUT_HEADLINE_CSV)
    _require(SCOUT_COUNTS_CSV)
    headline = pd.read_csv(SCOUT_HEADLINE_CSV)
    assert {"metric", "value"} <= set(headline.columns)
    assert (headline["metric"] == "n_trials").any()
    counts = pd.read_csv(SCOUT_COUNTS_CSV)
    assert {"n_strikes_plate", "n_trials"} <= set(counts.columns)


def test_detector_calibration_outputs():
    _require(CALIB_CSV)
    _require(CALIB_PNG)
    calib = pd.read_csv(CALIB_CSV).set_index("metric")["value"]
    for key in ("cadence_imu_spm", "cadence_plate_spm", "pct_diff_cadence", "within_tolerance"):
        assert key in calib.index, f"missing metric: {key}"
    assert CALIB_PNG.stat().st_size > 0


def test_cohort_demographics_summary():
    _require(COHORT_CSV)
    df = pd.read_csv(COHORT_CSV)
    expected = {"sex", "metric", "n", "mean", "sd", "min", "max"}
    assert expected <= set(df.columns)
    assert set(df["sex"].unique()) == {"F", "M", "All"}
    for metric in ("age_years", "height_cm", "mass_kg", "leg_length_mm", "iad_mm"):
        assert (df["metric"] == metric).any(), f"missing metric: {metric}"


def test_appendix_per_subject_summary():
    _require(APPENDIX_ALPHA_CSV)
    df = pd.read_csv(APPENDIX_ALPHA_CSV)
    expected = {"subject_id", "sex", "n_trials", "alpha_mean", "hdi_lo", "hdi_hi"}
    assert expected <= set(df.columns)
    assert df["alpha_mean"].is_monotonic_increasing
