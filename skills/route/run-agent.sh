#!/usr/bin/env bash
# Run one route agent in foreground with progress and a bounded deadline.
set -euo pipefail
exec python3 "$(dirname "${BASH_SOURCE[0]}")/run-agent.py" "$@"
