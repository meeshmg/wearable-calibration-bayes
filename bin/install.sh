#!/usr/bin/env bash
set -euo pipefail

# Creates (or updates) the project conda env from environment.yaml.
# Must be run from the project root — the directory containing environment.yaml.

ENV_NAME="wearable-calibration-bayes"
YAML="environment.yaml"

mkdir -p logs
exec > >(tee logs/install.stdout.log) 2> >(tee logs/install.stderr.log >&2)

if ! command -v conda >/dev/null 2>&1; then
    echo "error: conda not on PATH" >&2
    exit 1
fi

if [[ ! -f "$YAML" ]]; then
    echo "error: $YAML not found in $(pwd); run from the project root" >&2
    exit 1
fi

if conda env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
    echo "Env '$ENV_NAME' already exists; updating with --prune."
    conda env update -f "$YAML" --prune
else
    echo "Creating env '$ENV_NAME' from $YAML."
    conda env create -f "$YAML"
fi

PY_VERSION="$(conda run -n "$ENV_NAME" python --version 2>&1 || echo 'python: unavailable')"
PIP_VERSION="$(conda run -n "$ENV_NAME" pip --version 2>&1 || echo 'pip: unavailable')"

cat <<EOF

Env provides:
  $PY_VERSION
  $PIP_VERSION

Environment built successfully.
EOF

if [[ "${WEARABLE_SETUP_CHAIN:-}" != "1" ]]; then
    cat <<EOF
>>> Run this next: conda activate $ENV_NAME
Then continue with:   bin/download_data.sh  (or)  bin/setup.sh
EOF
fi
