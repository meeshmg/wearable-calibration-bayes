#!/usr/bin/env bash
set -euo pipefail

# Convenience entry point for a fresh clone: chains install → download → build.
# Each sub-step is independently runnable. Per-stage logs land in logs/ via
# each script's own tee plumbing — no top-level log capture here.
#
# Must be run from the project root WITH the wearable-calibration-bayes conda
# env already active (same assumption as bin/build.sh). On a truly fresh clone,
# the user runs bin/install.sh first, activates the env, then runs bin/setup.sh
# to do download + build.

bin/install.sh
bin/download_data.sh
bin/build.sh
