#!/usr/bin/env python3
"""Derive the auto-reset waypoints FROM DATA WE ALREADY HAVE (operator, 2026-10-28: "we already have a lot of data"),
instead of a hand calibration session. Sources:
  * the 60 September episodes (overhead camera, same arm/table): first-frame orange pixel → the joint pose at the
    moment the human closed the gripper on it (grasp), the pose ~1 s earlier (approach from above), and the pose
    at release over the tray
  * Sunday's bench episodes (today's camera): the 7 confirmed holds give (bench pixel, grasp pose) pairs that
    anchor a September-pixel → bench-pixel similarity transform (the September camera was closer: same scene,
    ~0.7x scale), plus 3 releases over the tray in today's layout
Products: results/so101_bench_20261019/reset/reset_waypoints.json (+ _review.jpg, + _report.txt).
Assumption stated: the arm base and the table have not moved since September (joint poses transfer); the tray's
position today is read from the bench frames. The dry run (gripper open, 3 cm high) is the check on all of it.
Run in /home/kiran/sim/vlash-venv.
"""
import json, pathlib
import numpy as np, cv2, av, pandas as pd

D = pathlib.Path("/home/kiran/lerobot_assets/datasets"); OUT = pathlib.Path("results/so101_bench_20261019/reset")
exec(open("results/so101_bench_20261019/bench_reset.py").read().split("# ---------- the routine")[0])   # detectors
CONFIRMED_HOLDS = {("A", 1), ("B", 1), ("D", 2), ("D", 4), ("E", 1), ("E", 3), ("E", 5)}   # from bench_runs.md 2026-10-26
START = [0, -99, 97, 75, 2, 41]


def first_frame(ds, ep):
    with av.open(str(D / ds / f"videos/chunk-000/observation.images.front/episode_{ep:06d}.mp4")) as c:
        for f in c.decode(video=0): return f.to_ndarray(format="bgr24")


def september():
    out = []
    for ds in ("new30_merged", "recovery30_v21"):
        n = json.load(open(D / ds / "meta/info.json"))["total_episodes"]
        for ep in range(n):
            bgr = first_frame(ds, ep); px = orange_centroid(bgr); tc = tray_centre(bgr)
            st = np.stack(pd.read_parquet(D / ds / f"data/chunk-000/episode_{ep:06d}.parquet", columns=["observation.state"])["observation.state"].to_numpy())
            g = st[:, 5]
            # grasp = the first OPEN->CLOSED transition with the arm out of rest (the September rest gripper sits near 30,
            # so "first frame below 30" is the rest pose, not a grasp — found 2026-10-28)
            held = [i for i in range(10, len(g) - 30) if g[i - 5] > 34 and g[i] <= 30 and (g[i:i + 30] < 34).all() and st[i, 1] > -60]
            if px is None or not held: continue
            i = held[0]; rel = np.where((np.arange(len(g)) > i + 30) & (g > 36))[0]
            out.append({"set": ds, "ep": ep, "px": px, "tray_px": tc, "grasp": st[i].tolist(), "approach": st[max(0, i - 30)].tolist(),
                        "release": st[rel[0]].tolist() if len(rel) else None, "tray_right": bool(tc and tc[0] > 320)})
    return out


def similarity_fit(src, dst):
    """least-squares x' = s R x + t (2-D similarity) from paired points"""
    src, dst = np.asarray(src, float), np.asarray(dst, float); ms, md = src.mean(0), dst.mean(0)
    A, B = src - ms, dst - md; H = A.T @ B; U, S, Vt = np.linalg.svd(H); R = Vt.T @ U.T
    if np.linalg.det(R) < 0: Vt[-1] *= -1; R = Vt.T @ U.T
    s = S.sum() / (A ** 2).sum(); t = md - s * R @ ms
    return s, R, t


def main():
    sep = september(); bench = json.load(open(OUT / "bench_grasp_samples.json"))["samples"]
    rep = [f"September demos with first-frame orange + a held grasp: {len(sep)} (tray right: {sum(s['tray_right'] for s in sep)})"]
    # --- transform September px -> bench px, anchored on confirmed bench holds matched to the nearest September grasp pose
    pairs = []
    for b in bench:
        if (b["row"], b["ep"]) not in CONFIRMED_HOLDS or b["fruit_px"] is None: continue
        q = np.array(b["grasp"][:5]); near = min(sep, key=lambda s: np.linalg.norm(np.array(s["grasp"][:5]) - q))
        d = np.linalg.norm(np.array(near["grasp"][:5]) - q)
        if d < 25: pairs.append((near["px"], b["fruit_px"], d, f"{b['row']}{b['ep']}~{near['set'][:4]}{near['ep']}"))
    rep.append(f"transform anchor pairs (joint distance < 25 deg): {len(pairs)} " + ", ".join(f"{p[3]}(d={p[2]:.0f})" for p in pairs))
    if len(pairs) >= 3:
        s, R, t = similarity_fit([p[0] for p in pairs], [p[1] for p in pairs]); resid = np.mean([np.linalg.norm(s * R @ np.array(p[0]) + t - np.array(p[1])) for p in pairs])
    else:   # fallback: scale from the tray width (Sept ≈ 220 px, bench ≈ 160 px), translation from the arm base
        s, R, t, resid = 0.73, np.eye(2), np.array([350 - 0.73 * 330, 0.0]), float("nan")
    T = lambda p: (s * R @ np.array(p, float) + t)
    rep.append(f"September->bench similarity: scale {s:.3f}, rotation {np.degrees(np.arctan2(R[1,0],R[0,0])):.1f} deg, shift {t.round(1).tolist()}, mean residual {resid:.1f} px")
    # --- bench tray today (right layout): median centre over bench frames with the tray on the right
    tray_b = np.array([b for b in [tray_centre(cv2.imread(x["frame"])) for x in bench] if b and b[0] > 400]); tray_c = np.median(tray_b, 0)
    tray_r = 80.0
    rep.append(f"bench tray centre (right layout) {tray_c.round(0).tolist()} from {len(tray_b)} frames; radius used {tray_r:.0f} px")
    # --- slots: pixel targets from the September k-means (in Sept px) -> joint poses from the 3 nearest Sept grasps (Sept px space) -> bench px via T
    cells = json.load(open(OUT / "demo_placement_area.json"))["grid_overhead_px"]["cells"]
    right = [x for x in sep if x["tray_right"]]
    slots = []
    for c in cells:
        p = np.array(c["px"]); near = sorted(right, key=lambda x: np.linalg.norm(np.array(x["px"]) - p))[:3]
        place = np.median([x["grasp"] for x in near], 0); hover = np.median([x["approach"] for x in near], 0)
        hover[5] = 45; place[5] = 45
        spread = np.max(np.std([x["grasp"][:5] for x in near], 0))
        slots.append({"slot": c["slot"], "px": T(p).round(1).tolist(), "px_september": c["px"], "hover": hover.round(1).tolist(), "place": place.round(1).tolist(),
                      "n_demos": len(near), "max_joint_std_deg": round(float(spread), 1), "sources": [f"{x['set'][:4]}{x['ep']}" for x in near]})
    # --- tray descend poses: September grasps whose (transformed) pixel lies inside today's tray footprint (the tray-left episodes)
    in_tray = [x for x in sep if np.linalg.norm(T(x["px"]) - tray_c) < tray_r * 1.1]
    rep.append(f"September grasps that fall inside today's tray footprint (descend-pose donors): {len(in_tray)}")
    def bucket(x):
        dx, dy = T(x["px"]) - tray_c
        if np.hypot(dx, dy) < tray_r * 0.35: return "centre"
        return ("left" if dx < 0 else "right") if abs(dx) > abs(dy) else ("far" if dy < 0 else "near")
    desc = {}
    for k in ("centre", "near", "far", "left", "right"):
        m = [x for x in in_tray if bucket(x) == k]
        donors = m if len(m) >= 2 else sorted(in_tray, key=lambda x: np.linalg.norm(T(x["px"]) - (tray_c + {"centre": (0, 0), "near": (0, tray_r * .5), "far": (0, -tray_r * .5), "left": (-tray_r * .5, 0), "right": (tray_r * .5, 0)}[k])))[:3]
        pose = np.median([x["grasp"] for x in donors], 0); pose[1] -= 2.0; pose[5] = 45      # -2 deg shoulder_lift ≈ +1 cm: the tray floor sits above the table
        desc[k] = pose.round(1).tolist(); rep.append(f"  descend {k}: {len(m)} in-bucket donors ({len(donors)} used) -> {desc[k]}")
    rel_b = [np.array(b["release"]) for b in bench if b.get("release")]; rel_s = [np.array(x["release"]) for x in in_tray if x["release"]]
    hover_t = np.median(rel_b, 0) if len(rel_b) >= 2 else np.median([x["approach"] for x in in_tray], 0); hover_t[5] = 45
    rep.append(f"tray hover = median of {len(rel_b)} Sunday releases: {hover_t.round(1).tolist()}")
    env = json.load(open(OUT / "motion_envelope.json"))
    W = {"date": "2026-10-28", "derived_from": "September demos + Sunday bench holds (scripts/derive_reset_waypoints.py), NOT a hand calibration; dry-run before any live reset",
         "tray_photo": None, "px_per_cm": round(float(8.0 * s / 0.73), 2), "start": START,
         "tray": {"px_centre": tray_c.round(1).tolist(), "px_radius": tray_r, "hover": hover_t.round(1).tolist(), "descend": desc},
         "slots": slots, "envelope": {"min": env["min"], "max": env["max"], "margin_deg": 5}}
    json.dump(W, open(OUT / "reset_waypoints.json", "w"), indent=1); (OUT / "reset_waypoints_report.txt").write_text("\n".join(rep) + "\n")
    # --- review image on a bench frame
    bg = cv2.imread(bench[0]["frame"])
    for x in right: q = T(x["px"]); cv2.circle(bg, (int(q[0]), int(q[1])), 4, (0, 140, 255), 1)
    for sl in slots: q = sl["px"]; cv2.circle(bg, (int(q[0]), int(q[1])), 14, (0, 255, 0), 2); cv2.putText(bg, f"S{sl['slot']} sd{sl['max_joint_std_deg']:.0f}", (int(q[0]) - 20, int(q[1]) - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
    cv2.circle(bg, (int(tray_c[0]), int(tray_c[1])), int(tray_r), (255, 0, 0), 2)
    for x in in_tray: q = T(x["px"]); cv2.circle(bg, (int(q[0]), int(q[1])), 5, (255, 0, 255), -1)
    cv2.putText(bg, "slots (green) = Sept demos mapped to today's camera; magenta = tray descend donors; blue = tray", (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.imwrite(str(OUT / "reset_waypoints_review.jpg"), bg); print("\n".join(rep)); print("wrote", OUT / "reset_waypoints.json")


if __name__ == "__main__":
    main()
