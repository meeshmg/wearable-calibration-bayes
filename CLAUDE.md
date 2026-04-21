# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## This Directory's Role

This is the **public-facing repository** for the Wearable Calibration Bayes project — the cleaned, publishable version. It does not contain dev docs, generated model assets, or LaTeX build artifacts. The sibling directory `../wearable-calibration-bayes-dev/` is the private development workspace where all work happens first.

**Do not develop here directly.** Changes should be made in the dev copy and synced to this directory when ready to publish. This copy should only contain what belongs in the public repo.

## Project Overview

Hierarchical Bayesian audit of whether a generic step-counting algorithm produces systematically biased cadence estimates across demographic groups, using the Kuopio Gait Dataset (47 subjects, 17F/30M). ISyE 6420 (Bayesian Statistics) Spring 2026 final project.

Four nested hierarchical Bayesian models — fully pooled, subject-level partial pooling, sex as group-level predictor, sex + measured anthropometrics — compared on LOO-CV. Outcome: `cadence_error = cadence_imu − cadence_plate` (steps per minute).

## Environment

```bash
conda env create -f environment.yaml
conda activate wearable-calibration-bayes
```

Key deps: Python 3.11, PyMC 5.28, ArviZ 0.23, ezc3d (C3D parsing), scipy, pandas.

## Common Commands

```bash
# Run notebooks against committed frozen reference (no raw data needed)
bin/install.sh
conda activate wearable-calibration-bayes
# open notebooks/ and run top-to-bottom; see notebooks/README.md for order

# Full pipeline: download ~23GB raw data and rebuild from source
bin/setup.sh              # end-to-end from fresh clone
bin/download_data.sh      # fetch Zenodo archives
bin/build.sh              # write data/processed/modeling_df.parquet

# Tests
python -m pytest tests/
python -m pytest tests/test_imu.py
python -m pytest tests/test_imu.py::test_name
```

## Architecture

### Data Pipeline (`src/`)

1. `download_kuopio.py` — fetches three Zenodo archives
2. `imu.py` — loads IMU `.mat` files, resolves sensor serial→body location via `config.yaml`, runs fixed-threshold peak detection on all 7 body locations
3. `ground_truth.py` — loads Vicon C3D via `ezc3d`, extracts force-plate Fz, detects heel strikes
4. `build_modeling_df.py` — orchestrates pipeline, joins demographics, computes cadence error (pelvis primary + 6 sensitivity locations)
5. `build_scout_assets.py` — lightweight pre-modeling data exploration

`config.yaml` is the single source for detector parameters and sensor mapping.

### Notebooks (`notebooks/`)

Execution order — see `notebooks/README.md` for full asset manifest:

1. `audit.ipynb` — exclusions investigation
2. `eda.ipynb` — outcome, demographics, detector-quality figures
3. `model_1.ipynb` — fully pooled (Normal → Student-t)
4. `model_2.ipynb` — subject-level partial pooling (M2, M2a, M2b)
5. `model_3.ipynb` — sex as group-level predictor
6. `model_4.ipynb` — sex + standardized anthropometrics
7. `model_comparison.ipynb` — LOO-CV, cross-model summary (requires all `idata_*.nc` from prior notebooks)

Notebooks prefer `data/processed/modeling_df.parquet` and fall back to `data/reference/modeling_df.parquet` (committed frozen reference).

## What's Not in This Repo

Development docs (`dev_docs/`), generated model assets (`notebooks/model_assets/`), serialized InferenceData (`data/processed/idata_*.nc`), and LaTeX build artifacts live in the private dev workspace only.

## Coding Conventions

- **PyMC/ArviZ first** — use built-in methods, not NumPy/SciPy equivalents
- **No hand-coded MCMC** — use PyMC samplers
- **Model blocks annotated** — inline `# prior`, `# hyperprior`, `# likelihood`, `# deterministic` labels, plus header comment block
- **`RANDOM_SEED = 42`** per notebook, passed to all stochastic calls
- **`config.yaml`** for detector params — never hardcode thresholds in Python
- **No silent drops** — every trial in parquet with `qc_flags` and `modeling_include` for auditable exclusions
