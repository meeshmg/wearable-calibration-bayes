#!/usr/bin/env bash
set -euo pipefail

# Fetches the Kuopio gait dataset from Zenodo (record 10559504) and extracts the
# imu_extracted/ and mocap/ subdirs per subject. Idempotent: subjects already on
# disk are skipped. Must be run from the project root.

mkdir -p logs
exec > >(tee logs/download.stdout.log) 2> >(tee logs/download.stderr.log >&2)

python src/download_kuopio.py "$@"
