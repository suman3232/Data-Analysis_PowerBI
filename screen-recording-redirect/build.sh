#!/usr/bin/env bash
# Builds output/amazon-review-redirect.mp4 (see MASTER_PROMPT.md). Needs ffmpeg, python3, numpy, Pillow.
set -euo pipefail
cd "$(dirname "$0")"
python3 build.py "$@"
