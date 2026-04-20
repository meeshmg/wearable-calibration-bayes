import pathlib

import numpy as np
import pytest

from imu import load_trial

DATA_ROOT = pathlib.Path(__file__).parent.parent / "data" / "kuopio"
SUBJECT_01 = DATA_ROOT / "01"
TRIAL = "data_l_comf_01.mat"

SUBJECT_33 = DATA_ROOT / "33"
WRAP_TRIAL = "data_r_fast_06.mat"  # uint16 tick counter wraps at idx 236

EXPECTED_LOCATIONS = {
    "pelvis",
    "left_foot", "right_foot",
    "left_femur", "right_femur",
    "left_tibia", "right_tibia",
}


def test_load_trial_subject01_structure():
    result = load_trial(SUBJECT_01, TRIAL)

    assert set(result.keys()) == EXPECTED_LOCATIONS, (
        f"Got locations: {sorted(result.keys())}"
    )

    for loc, arrays in result.items():
        t = arrays["time"]
        calib = arrays["calibratedAcceleration"]
        free = arrays["freeAcceleration"]
        N = len(t)

        assert N > 0, f"{loc}: time array is empty"
        assert np.all(np.diff(t) > 0), f"{loc}: time not strictly increasing"
        assert calib.shape == (N, 3), (
            f"{loc}: calibratedAcceleration shape {calib.shape} != ({N}, 3)"
        )
        assert free.shape == (N, 3), (
            f"{loc}: freeAcceleration shape {free.shape} != ({N}, 3)"
        )


def test_load_trial_handles_uint16_tick_wrap():
    # Regression guard for the 2026-04-18 uint16 tick-wrap bug. Pre-fix,
    # subject 33 r_fast_06 had time_s jump from ~2.36 s to ~-652 s at
    # sample index 236, producing cadence_imu ~ -0.737 spm downstream.
    result = load_trial(SUBJECT_33, WRAP_TRIAL)
    for loc, arrays in result.items():
        t = arrays["time"]
        assert np.all(np.diff(t) >= 0), (
            f"{loc}: time not monotonic — uint16 unwrap regression"
        )
        assert t[-1] > t[0], f"{loc}: trial duration non-positive"
