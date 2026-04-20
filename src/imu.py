import pathlib

import numpy as np
import scipy.io
import scipy.signal
import yaml

_CONFIG_FILE = pathlib.Path(__file__).parent.parent / "config.yaml"
_TICKS_PER_SECOND = 100.1
_G_M_S2 = 9.80665

with open(_CONFIG_FILE) as _f:
    _CFG = yaml.safe_load(_f)
_DETECTOR_CFG = _CFG["detector_params"]
_SENSOR_MAP_CFG = _CFG["sensor_map"]


def _sensor_to_location(subject_id):
    mapping = dict(_SENSOR_MAP_CFG["default"])
    overrides = _SENSOR_MAP_CFG.get("subject_overrides", {}).get(subject_id, {})
    mapping.update(overrides)
    return {serial: loc for loc, serial in mapping.items()}


def load_trial(subject_dir, trial_filename):
    subject_id = subject_dir.name
    mat_path = subject_dir / "imu_extracted" / trial_filename

    mat = scipy.io.loadmat(mat_path, simplify_cells=True)
    sensors = mat["sensors"]

    serial_to_loc = _sensor_to_location(subject_id)

    result = {}
    for serial, sensor in sensors.items():
        location = serial_to_loc.get(serial)
        if location is None:
            continue

        # uint16 tick counter can wrap mid-trial (65535 -> 0); unwrap before
        # converting to seconds, else downstream cadence goes negative.
        raw_ticks = np.asarray(sensor["time"]).ravel().astype(np.int64)
        wraps = np.concatenate([[0], np.cumsum(np.diff(raw_ticks) < 0)])
        ticks_unwrapped = raw_ticks + wraps * (1 << 16)
        time_s = (ticks_unwrapped - ticks_unwrapped[0]).astype(np.float64) / _TICKS_PER_SECOND

        # accel arrays are length N, time is N-1; drop first accel sample to align.
        calib = np.asarray(sensor["calibratedAcceleration"], dtype=np.float64)[1:, :]
        free = np.asarray(sensor["freeAcceleration"], dtype=np.float64)[1:, :]

        result[location] = {
            "calibratedAcceleration": calib,
            "freeAcceleration": free,
            "time": time_s,
        }

    return result


def detect_steps(free_acceleration, time_s):
    if time_s.size < 2 or np.any(np.diff(time_s) < 0):
        raise ValueError("time_s must be monotonically non-decreasing")

    magnitude_g = np.linalg.norm(free_acceleration, axis=1) / _G_M_S2
    peaks, _ = scipy.signal.find_peaks(
        magnitude_g,
        prominence=_DETECTOR_CFG["prominence_g"],
        distance=_DETECTOR_CFG["min_distance_samples"],
    )
    n_peaks = int(peaks.size)
    peak_times_s = time_s[peaks].tolist()
    trial_duration_s = float(time_s[-1] - time_s[0])

    if n_peaks >= 2:
        cadence_imu = (n_peaks - 1) / (peak_times_s[-1] - peak_times_s[0]) * 60.0
    else:
        cadence_imu = None

    return {
        "n_peaks_imu": n_peaks,
        "peak_times_s": peak_times_s,
        "cadence_imu": cadence_imu,
        "trial_duration_s": trial_duration_s,
    }
