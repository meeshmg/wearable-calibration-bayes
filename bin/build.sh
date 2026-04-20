#!/usr/bin/env bash
set -euo pipefail

# Rebuilds data/processed/modeling_df.parquet from raw Kuopio data.
# Must be run from the project root with the 'wearable-calibration-bayes' conda env active.

mkdir -p logs
exec > >(tee logs/build.stdout.log) 2> >(tee logs/build.stderr.log >&2)

python -u src/build_modeling_df.py
python -u src/build_scout_assets.py
