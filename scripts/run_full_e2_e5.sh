#!/usr/bin/env bash
# Full-N (10,000-frame) E2 + E5 judge run -- the real H1/H1b/H3 measurement (docs/DECISIONS.md
# D054). Replaces the ad-hoc background command whose crash mid-P0b prompted this script.
#
# Safe to re-run: both steps take --resume, so a second invocation after a crash continues from
# the per-variant checkpoints rather than re-spending judge calls already paid for.
#
#   QWEN3VL_BASE_URL=https://... scripts/run_full_e2_e5.sh
#
# If QWEN3VL_BASE_URL is unset it is read from .env. The Modal server cold-starts on the first
# request (~11 min after a preemption for the 8B model); the retry/backoff in _call_qwen3vl
# (D054/D055) rides that out.
#
# RUN IT DETACHED. This is a ~10h job. A plain `&` or an agent's background shell gets reaped
# when its parent exits -- observed, twice. Use a detached tmux session so it outlives the
# launching shell:
#     tmux new-session -d -s vernier_run "./scripts/run_full_e2_e5.sh > data/run_full_e2_e5.tmux.log 2>&1"
#     tmux attach -t vernier_run     # to watch;  Ctrl-b d  to detach again
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ -z "${QWEN3VL_BASE_URL:-}" ]]; then
  QWEN3VL_BASE_URL="$(grep -E '^QWEN3VL_BASE_URL=' .env | cut -d= -f2-)"
fi
if [[ -z "${QWEN3VL_BASE_URL:-}" ]]; then
  echo "QWEN3VL_BASE_URL is not set and not in .env -- recover it with:" >&2
  echo "    modal run cloud/modal_qwen3vl.py   # prints the deployed server URL" >&2
  exit 1
fi
export QWEN3VL_BASE_URL
echo "judge server: ${QWEN3VL_BASE_URL}"

mkdir -p data
ts="$(date +%Y%m%dT%H%M%S)"

# The Modal L4 runs on preemptible capacity -- "Container terminated due to preemption" was the
# real cause of the frame-3,000 death (D055). `_call_qwen3vl` now retries ~19 min (past a full
# ~11 min cold start), but if a preemption lands during an unusually slow restart and the
# retries still exhaust, the cheapest recovery is to just re-invoke with --resume: every step
# below continues from its own checkpoints, so a re-run costs only the frames since the last
# checkpoint write, not the whole pass.
_ATTEMPTS=6

run_step() {
  local name="$1"; shift
  local i
  for i in $(seq 1 "$_ATTEMPTS"); do
    echo "=== ${name} (attempt ${i}/${_ATTEMPTS}) ==="
    if "$@"; then
      return 0
    fi
    echo "=== ${name} exited nonzero; re-resuming in 30s (attempt ${i}/${_ATTEMPTS}) ==="
    sleep 30
  done
  echo "=== ${name} still failing after ${_ATTEMPTS} attempts -- giving up ===" >&2
  return 1
}

run_step "E2 (H1/H1b) N=10000" \
  python3 scripts/e2_replication.py --n 10000 --out data/e2_full_n10000.json --resume \
  2>&1 | tee -a "data/e2_full_n10000.${ts}.log"

run_step "E5 (H3 prompt sweep) N=2000" \
  python3 scripts/e5_prompt_sweep.py --n 2000 --out data/e5_full_n2000.json --resume \
  2>&1 | tee -a "data/e5_full_n2000.${ts}.log"

echo "=== done -- regenerate the card ==="
echo "    make card"
