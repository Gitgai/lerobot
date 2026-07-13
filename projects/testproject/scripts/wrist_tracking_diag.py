#!/usr/bin/env python3
"""Instrumented teleop diagnostic: log leader-vs-follower joint tracking.

Runs a teleop loop for a fixed duration while logging, every step, the LEADER
commanded position and the FOLLOWER actual position for all 6 joints. Then prints
a per-joint tracking report (max error, mean error, did it move, direction) so we
can see exactly how a joint (e.g. wrist_roll) misbehaves.

Move the leader arm — especially the wrist — during the run.
"""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path

from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.teleoperators.so_leader.config_so_leader import SOLeaderTeleopConfig
from lerobot.teleoperators.so_leader.so_leader import SOLeader

MOTORS = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DURATION_S = 25.0


def resolve(cfg: dict, kind: str) -> str:
    s = Path(cfg[f"{kind}_serial"])
    return str(s.resolve()) if s.exists() else cfg[f"{kind}_port"]


def main() -> None:
    cfg = json.load((PROJECT_ROOT / "config" / "so101.json").open())
    out_csv = PROJECT_ROOT / "logs" / "wrist_tracking.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    leader = SOLeader(SOLeaderTeleopConfig(port=resolve(cfg, "leader"), id=cfg["leader_id"]))
    follower = SOFollower(
        SOFollowerRobotConfig(
            port=resolve(cfg, "follower"), id=cfg["follower_id"], disable_torque_on_disconnect=False
        )
    )
    leader.connect()
    follower.connect()
    print(f"Connected. Logging {DURATION_S:.0f}s — MOVE THE LEADER WRIST NOW.")

    rows = []
    t0 = time.perf_counter()
    with out_csv.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t"] + [f"L_{m}" for m in MOTORS] + [f"F_{m}" for m in MOTORS])
        try:
            while time.perf_counter() - t0 < DURATION_S:
                act = leader.get_action()
                follower.send_action(act)
                obs = follower.get_observation()
                t = time.perf_counter() - t0
                L = [float(act[f"{m}.pos"]) for m in MOTORS]
                F = [float(obs[f"{m}.pos"]) for m in MOTORS]
                rows.append((L, F))
                w.writerow([f"{t:.3f}"] + [f"{v:.2f}" for v in L] + [f"{v:.2f}" for v in F])
                time.sleep(0.03)
        finally:
            try:
                leader.disconnect()
            except Exception:
                pass
            try:
                follower.disconnect()
            except Exception:
                pass

    # ---- per-joint tracking report ----
    print(f"\nlogged {len(rows)} steps -> {out_csv}\n")
    print(f"{'motor':<14}{'L_range':>10}{'F_range':>10}{'mean|err|':>11}{'max|err|':>10}   verdict")
    print("-" * 78)
    for i, m in enumerate(MOTORS):
        Ls = [r[0][i] for r in rows]
        Fs = [r[1][i] for r in rows]
        errs = [abs(l - f) for l, f in zip(Ls, Fs)]
        l_range = max(Ls) - min(Ls)
        f_range = max(Fs) - min(Fs)
        mean_err = sum(errs) / len(errs)
        max_err = max(errs)
        # verdict heuristics
        if l_range < 3:
            verdict = "(leader barely moved this joint)"
        elif f_range < 0.3 * l_range:
            verdict = "FOLLOWER STUCK — barely moved while leader did"
        elif mean_err > 8:
            verdict = "POOR TRACKING / offset"
        elif max_err > 20:
            verdict = "tracks but big transient spikes"
        else:
            verdict = "tracks OK"
        print(f"{m:<14}{l_range:>10.1f}{f_range:>10.1f}{mean_err:>11.1f}{max_err:>10.1f}   {verdict}")


if __name__ == "__main__":
    main()
