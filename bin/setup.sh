#!/usr/bin/env bash
set -euo pipefail

# Convenience entry point for a fresh clone: chains install → download → build.
# Each sub-step is independently runnable. Per-stage logs land in logs/ via
# each script's own tee plumbing — no top-level log capture here.
#
# Must be run from the project root. The env does NOT need to be active: after
# install.sh creates it, this script sources conda's shell hook and activates
# the env in-process so subsequent scripts inherit it. Activating inline
# (rather than wrapping each child in `conda run`) keeps signal propagation
# intact — Ctrl+C in the parent shell cleanly terminates the whole chain.

ENV_NAME="wearable-calibration-bayes"

# WEARABLE_SETUP_CHAIN signals to install.sh that it's being chained, so it
# skips its "Run this next: conda activate ..." trailer (not relevant here).
WEARABLE_SETUP_CHAIN=1 bin/install.sh

# Activate the env in this shell so bin/download_data.sh and bin/build.sh
# inherit it. `conda info --base` finds the install regardless of how conda
# was installed (miniconda, anaconda, homebrew, etc.).
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "$ENV_NAME"

bin/download_data.sh
bin/build.sh
