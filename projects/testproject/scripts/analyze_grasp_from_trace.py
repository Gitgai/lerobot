#!/usr/bin/env python3
"""Score a live run from its trace: did the gripper ever actually hold something?

The physical test
-----------------
Fingers cannot pass through an object. So whenever the policy COMMANDS a hard
squeeze, exactly one of two things happens:

  STALL   measured width stays well above the commanded width
          -> something is between the fingers = REAL GRASP
  FOLLOW  measured width tracks the command all the way down
          -> the fingers closed on air = EMPTY

This distinguishes a real carry from an empty-handed lift, which the joint
trajectory alone cannot do (2026-08-02: two 10-minute runs looked like carries
in the command stream and were 100% empty by this test).

Health check
------------
Also reports observation/action rates. A run below ~0.8 obs/s is effectively
blind (the policy is steering on seconds-old images) and its behavioral result
must not be trusted - see the 2026-08-02 evening runs.

Usage
-----
    python analyze_grasp_from_trace.py TRACE_DIR [TRACE_DIR ...]
    python analyze_grasp_from_trace.py ../artifacts/traces/*/
"""

import argparse
import bisect
import json
import os

# Calibrated on the 2026-08-02 probe session (small orange / onion / tomato).
SQUEEZE_CMD_MAX = 22.0  # a command below this is a "hard squeeze" attempt
STALL_MARGIN = 10.0  # measured must exceed command by this to count as blocked
RAISED_LIFT = -40.0  # shoulder_lift below this = arm is up (carry height)
HEALTHY_OBS_RATE = 0.8  # obs/s below this = run was effectively blind


def _load(trace_dir):
    obs_path = os.path.join(trace_dir, "observations.jsonl")
    act_path = os.path.join(trace_dir, "executed_actions.jsonl")
    if not (os.path.exists(obs_path) and os.path.exists(act_path)):
        return None, None

    obs = []
    with open(obs_path) as f:
        for line in f:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            state = rec.get("state") or {}
            if "gripper.pos" not in state:
                continue
            obs.append(
                (
                    rec.get("client_timestamp") or rec.get("recorded_at_unix"),
                    state.get("shoulder_lift.pos", 0.0),
                    state["gripper.pos"],
                )
            )

    cmds = []
    with open(act_path) as f:
        for line in f:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            action = rec.get("performed_action") or {}
            if "gripper.pos" not in action:
                continue
            cmds.append((rec.get("recorded_at_unix"), action["gripper.pos"]))

    return obs, cmds


def analyze(trace_dir):
    obs, cmds = _load(trace_dir)
    if not obs or not cmds or len(obs) < 10:
        return None

    cmd_times = [c[0] for c in cmds]

    def cmd_at(t):
        i = min(max(bisect.bisect_left(cmd_times, t), 0), len(cmds) - 1)
        return cmds[i][1]

    duration = obs[-1][0] - obs[0][0]
    if duration <= 0:
        return None

    stalled = followed = carrying = 0
    hold_widths = []
    for t, lift, measured in obs:
        commanded = cmd_at(t)
        blocked = measured > commanded + STALL_MARGIN
        if commanded < SQUEEZE_CMD_MAX:
            if blocked:
                stalled += 1
                hold_widths.append(measured)
            else:
                followed += 1
        if lift < RAISED_LIFT and commanded < 25 and blocked:
            carrying += 1

    return {
        "duration_s": duration,
        "obs_rate": len(obs) / duration,
        "action_rate": len(cmds) / duration,
        "stalled": stalled,
        "followed": followed,
        "carry_samples": carrying,
        "hold_widths": (min(hold_widths), max(hold_widths)) if hold_widths else None,
    }


def verdict(r):
    if r["obs_rate"] < HEALTHY_OBS_RATE:
        return "UNTRUSTWORTHY (starved observations - infrastructure, not behavior)"
    if r["carry_samples"] > 0:
        return "REAL GRASP + CARRY"
    if r["stalled"] >= 5:
        return "grasped but never carried"
    if r["followed"] > 0:
        return "EMPTY - fingers closed on air"
    return "no squeeze attempted"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace_dirs", nargs="+")
    args = parser.parse_args()

    for trace_dir in args.trace_dirs:
        trace_dir = trace_dir.rstrip("/")
        name = os.path.basename(trace_dir)
        r = analyze(trace_dir)
        if r is None:
            print(f"{name}: no usable trace data")
            continue
        widths = (
            f"{r['hold_widths'][0]:.0f}-{r['hold_widths'][1]:.0f}" if r["hold_widths"] else "-"
        )
        print(
            f"{name}\n"
            f"  {r['duration_s']:.0f}s | {r['obs_rate']:.2f} obs/s | {r['action_rate']:.1f} act/s\n"
            f"  squeezes: STALLED={r['stalled']} (object held) FOLLOWED={r['followed']} (empty)\n"
            f"  carry samples={r['carry_samples']} | hold width {widths}\n"
            f"  -> {verdict(r)}"
        )


if __name__ == "__main__":
    main()
