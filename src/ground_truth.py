import logging

import ezc3d
import numpy as np
from scipy.signal import butter, filtfilt

logger = logging.getLogger(__name__)

N_PLATES = 5
BASELINE_WINDOW_MS = 100
LOWPASS_CUTOFF_HZ = 20.0
BUTTER_ORDER = 4
THRESHOLD_N = 20.0
DEDUP_WINDOW_MS = 200
BASELINE_DRIFT_THRESHOLD_N = 20.0


def detect_heel_strikes(c3d_path):
    c = ezc3d.c3d(str(c3d_path))
    analog_rate = float(c['parameters']['ANALOG']['RATE']['value'][0])
    labels = c['parameters']['ANALOG']['LABELS']['value']
    analog = c['data']['analogs'][0]

    fz_indices = [labels.index(f'Force.Fz{k}') for k in range(1, N_PLATES + 1)]
    fz = analog[fz_indices]

    baseline_n = int(BASELINE_WINDOW_MS / 1000.0 * analog_rate)
    baseline_start = np.median(fz[:, :baseline_n], axis=1)
    baseline_end = np.median(fz[:, -baseline_n:], axis=1)

    fz_corr = fz - baseline_start[:, None]
    baseline_post = np.median(fz_corr[:, :baseline_n], axis=1)

    nyq = 0.5 * analog_rate
    b, a = butter(BUTTER_ORDER, LOWPASS_CUTOFF_HZ / nyq, btype='low')
    fz_filt = filtfilt(b, a, fz_corr, axis=1)

    loading = -fz_filt
    above = loading > THRESHOLD_N

    events = []
    per_plate_counts = [0] * N_PLATES
    for k in range(N_PLATES):
        rising = np.flatnonzero(np.diff(above[k].astype(np.int8)) == 1) + 1
        per_plate_counts[k] = int(rising.size)
        for idx in rising:
            events.append((idx / analog_rate, k))

    events.sort(key=lambda e: e[0])
    n_raw = len(events)

    dedup_window_s = DEDUP_WINDOW_MS / 1000.0
    deduped = []
    for t, k in events:
        if deduped and (t - deduped[-1][0]) < dedup_window_s:
            continue
        deduped.append((t, k))

    heel_strikes_s = [t for t, _ in deduped]
    n_detected = len(heel_strikes_s)
    trial_duration_s = fz.shape[1] / analog_rate

    if n_detected == 0:
        logger.warning('Zero heel strikes detected in %s', c3d_path)

    plate_window_start_s = heel_strikes_s[0] if n_detected > 0 else None
    plate_window_end_s = heel_strikes_s[-1] if n_detected > 0 else None
    if n_detected >= 2:
        cadence_steps_per_min = (n_detected - 1) / (plate_window_end_s - plate_window_start_s) * 60.0
    else:
        cadence_steps_per_min = None

    qc_flags = []
    baseline_drift = np.abs(baseline_end - baseline_start)
    for k in range(N_PLATES):
        if baseline_drift[k] > BASELINE_DRIFT_THRESHOLD_N:
            qc_flags.append(f'baseline_drift_plate_{k + 1}')
            logger.warning(
                'Baseline drift on plate %d: |end - start| = %.1f N in %s',
                k + 1, baseline_drift[k], c3d_path,
            )

    return {
        'heel_strikes_s': heel_strikes_s,
        'n_detected': n_detected,
        'cadence_steps_per_min': cadence_steps_per_min,
        'plate_window_start_s': plate_window_start_s,
        'plate_window_end_s': plate_window_end_s,
        'diagnostics': {
            'n_raw': n_raw,
            'n_deduped': n_detected,
            'dedup_count': n_raw - n_detected,
            'per_plate_counts': per_plate_counts,
            'baseline_start': baseline_start.tolist(),
            'baseline_end': baseline_end.tolist(),
            'baseline_post_correction': baseline_post.tolist(),
            'trial_duration_s': trial_duration_s,
            'analog_rate_hz': analog_rate,
            'qc_flags': qc_flags,
        },
    }
