"""Smoke tests for data/processed/modeling_df.parquet.

These tests require the parquet to already exist on disk; generate it
by running ``scripts/build_modeling_df.py``. Schema expectations track
``dev_docs/active/DATA_DICTIONARY.md`` (output table).
"""

import pathlib

import pandas as pd
import pytest

PARQUET = (
    pathlib.Path(__file__).parent.parent
    / "data" / "processed" / "modeling_df.parquet"
)

SENSITIVITY_LOCATIONS = [
    "right_femur", "left_femur",
    "right_tibia", "left_tibia",
    "right_foot", "left_foot",
]


@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    if not PARQUET.exists():
        pytest.skip(
            "modeling_df.parquet missing; run scripts/build_modeling_df.py"
        )
    return pd.read_parquet(PARQUET)


def test_parquet_exists():
    assert PARQUET.exists(), f"{PARQUET} not found"


def test_row_count_in_expected_range(df: pd.DataFrame):
    # 2818 processable trials per the 2026-04-18 scout; 15 at n=2, 0 at
    # n<2, so ~2803 modeling-eligible absent other failures.
    assert 2700 < len(df) < 2900, f"row count {len(df)} outside 2700-2900"
    eligible = int(df["modeling_include"].sum())
    assert 2700 < eligible < 2900, f"eligible {eligible} outside range"


def test_seven_cadence_error_columns_present(df: pd.DataFrame):
    assert "cadence_error" in df.columns
    for loc in SENSITIVITY_LOCATIONS:
        assert f"cadence_error_{loc}" in df.columns
    error_cols = [c for c in df.columns if c.startswith("cadence_error")]
    assert len(error_cols) == 7, f"expected 7 cadence_error cols, got {error_cols}"


def test_pelvis_cadence_error_no_nulls_when_eligible(df: pd.DataFrame):
    eligible = df[df["modeling_include"]]
    assert eligible["cadence_error"].notna().all(), (
        "cadence_error has nulls on modeling-eligible rows"
    )


def test_cadence_imu_non_negative_when_eligible(df: pd.DataFrame):
    # Regression guard for the 2026-04-18 uint16 tick-wrap bug: raw
    # sensor["time"] ticks wrap at 65535 → 0 within a trial, which
    # load_trial now unwraps before converting to seconds.
    eligible = df[df["modeling_include"]]
    neg = eligible[eligible["cadence_imu"] < 0]
    assert neg.empty, (
        f"{len(neg)} modeling-eligible trials have cadence_imu < 0; "
        f"subjects affected: {sorted(neg['subject_id'].unique())}"
    )


def test_leg_length_populated_for_all_47_subjects(df: pd.DataFrame):
    subjects = df["subject_id"].unique()
    assert len(subjects) == 47, f"expected 47 subjects, got {len(subjects)}"
    per_subject = df.groupby("subject_id")["leg_length_mm"].first()
    assert per_subject.notna().all(), (
        f"leg_length_mm null for: "
        f"{per_subject[per_subject.isna()].index.tolist()}"
    )


def test_subject_01_l_comf_01_spot_check(df: pd.DataFrame):
    # Calibration result 2026-04-18: pelvis cadence_imu 130.57 spm,
    # plate 137.30 spm, error −6.73.
    row = df[
        (df["subject_id"] == "01")
        & (df["leading_leg"] == "l")
        & (df["speed"] == "comf")
        & (df["trial_num"] == "01")
    ]
    assert len(row) == 1, f"expected 1 matching row, got {len(row)}"
    r = row.iloc[0]
    assert abs(r["cadence_plate"] - 137.30) < 0.5, (
        f"cadence_plate {r['cadence_plate']} != ~137.30"
    )
    assert abs(r["cadence_error"] - (-6.73)) < 0.5, (
        f"cadence_error {r['cadence_error']} != ~-6.73"
    )
