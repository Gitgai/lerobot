#!/usr/bin/env bash
# Phase 0: measure the SUCCESS RATE of a policy in LeIsaac PickOrange.
#
# WHY
# ---
# Two 3,000-step runs of 12e21/gr00t_n1d6_leisaac_pick_orange disagreed:
#     run2  3/3 oranges placed, lifts 0.187/0.190/0.162, 33 place-steps
#     run3  2/3 placed, orange002 never lifted (0.003 m), 3 place-steps
# Identical settings. The policy samples stochastically (flow matching draws its
# noise in the SERVER process, which no client-side seed can bind), so a single
# run is an anecdote. Everything we might fine-tune later has to be measured
# against a RATE, or improvement cannot be told apart from variance.
#
# 3,000 STEPS IS THE MINIMUM. Three pick-and-place cycles need ~2,500; the
# earlier 900-step verdicts in this project describe the first third of an
# episode and cannot support "never does X".
#
# Runs are SEQUENTIAL on purpose - concurrent Isaac Sim instances contend for
# the GPU and each one alone already drives it hard.
#
# Usage:
#   scripts/phase0_reliability_sweep.sh [N_RUNS] [MAX_STEPS] [PORT] [POLICY_TYPE]
# Defaults: 5 runs, 3000 steps, port 5556, gr00t-n16
#
# Score the result with:
#   python3 scripts/phase0_score_sweep.py

set -uo pipefail

N_RUNS="${1:-5}"
MAX_STEPS="${2:-3000}"
PORT="${3:-5556}"
POLICY_TYPE="${4:-gr00t-n16}"

PROJ="/home/kiran/projects/git/nvidia/lerobot/projects/testproject"
EVAL="$PROJ/scripts/sim_policy_eval_instrumented.py"
OUTDIR="$PROJ/logs/phase0"
mkdir -p "$OUTDIR"

echo "[phase0] $N_RUNS runs x $MAX_STEPS steps, policy=$POLICY_TYPE port=$PORT"

for i in $(seq 1 "$N_RUNS"); do
    seed=$((1000 + i))
    out="$OUTDIR/run${i}_seed${seed}.csv"
    log="$OUTDIR/run${i}_seed${seed}.log"

    if [ -s "$out" ]; then
        echo "[phase0] run $i already present, skipping"
        continue
    fi

    # Kill any straggler sim. Match the INTERPRETER PATH, and filter on
    # /proc/PID/comm == python: a bare pgrep -f also matches this script and the
    # nohup wrapper, whose command lines contain the same string.
    for p in $(pgrep -f "leisaac-venv/bin/python" 2>/dev/null); do
        [ "$(cat /proc/"$p"/comm 2>/dev/null)" = python ] && kill -9 "$p" 2>/dev/null
    done
    sleep 3

    echo "[phase0] === run $i/$N_RUNS (seed $seed) ==="
    (cd ~/sim/leisaac-src && \
        LEISAAC_ASSETS_ROOT=$HOME/sim/leisaac-src/assets ACCEPT_EULA=Y \
        PRIVACY_CONSENT=Y OMNI_KIT_ACCEPT_EULA=YES DISPLAY=:0 \
        ~/sim/leisaac-venv/bin/python -u "$EVAL" \
            --policy_type="$POLICY_TYPE" --policy_port="$PORT" \
            --max_steps="$MAX_STEPS" --seed="$seed" --out="$out") > "$log" 2>&1

    if grep -q "wrote" "$log"; then
        echo "[phase0] run $i OK -> $(basename "$out")"
    else
        echo "[phase0] run $i FAILED - see $log"
        tail -3 "$log" | cut -c1-120
    fi
done

for p in $(pgrep -f "leisaac-venv/bin/python" 2>/dev/null); do
    [ "$(cat /proc/"$p"/comm 2>/dev/null)" = python ] && kill -9 "$p" 2>/dev/null
done

echo "[phase0] sweep complete. Score it: python3 scripts/phase0_score_sweep.py"
