#!/usr/bin/env python3
"""Where did OUR demonstrations put the orange at the start of each episode? (auto-reset plan, MAIN-row grid)
Reads the first front-camera frame of every episode in the given v2.1 sets, finds the orange (HSV blob detector from
scripts/score_recovery_placement.py) and the tray (blue-grey convex hull), and writes:
  - a scatter of start positions in overhead-camera pixels (the September sets share the bench's overhead view;
    the August sets are low-front and are plotted separately, not used for the grid)
  - 10 grid cells covering the central 90 % of the September distribution (5 x 2 k-means-like bins by x then y)
Outputs results/so101_bench_20261019/reset/demo_placement_area.{json,jpg}. Run in /home/kiran/sim/vlash-venv.
"""
import json, pathlib, sys
import numpy as np, cv2, av

D = pathlib.Path("/home/kiran/lerobot_assets/datasets"); OUT = pathlib.Path("results/so101_bench_20261019/reset"); OUT.mkdir(parents=True, exist_ok=True)
SETS = {"overhead": ["new30_merged", "recovery30_v21"], "lowfront": ["so101_orange_89_v21", "plate_demos_v21"]}


def first_frame(ds, ep):
    with av.open(str(D / ds / f"videos/chunk-000/observation.images.front/episode_{ep:06d}.mp4")) as c:
        for f in c.decode(video=0): return f.to_ndarray(format="bgr24")


def orange_blobs(bgr):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV); m = cv2.inRange(hsv, (5, 120, 90), (28, 255, 255))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)); m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    out = []
    for c in cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]:
        a = cv2.contourArea(c)
        if a < 400: continue
        x, y, w, h = cv2.boundingRect(c)
        if a / (w * h) < 0.5 or min(w, h) / max(w, h) < 0.45: continue
        out.append((a, (x + w / 2, y + h / 2)))
    return sorted(out, reverse=True)


def find_plate(bgr):
    b, g, r = cv2.split(bgr.astype(np.int16)); val = bgr.max(2)
    mask = (((b - r) > 10) & (val > 60) & (val < 210)).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)); mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    cs = [c for c in cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0] if cv2.contourArea(c) > 12000]
    if not cs: return None
    c = max(cs, key=cv2.contourArea); M = cv2.moments(c); return (M["m10"] / M["m00"], M["m01"] / M["m00"])


def main():
    res = {}
    for view, sets in SETS.items():
        pts, trays, miss = [], [], 0
        for ds in sets:
            n = json.load(open(D / ds / "meta/info.json"))["total_episodes"]
            for ep in range(n):
                bgr = first_frame(ds, ep); bl = orange_blobs(bgr); pl = find_plate(bgr)
                if bl: pts.append({"set": ds, "ep": ep, "xy": bl[0][1], "area": bl[0][0]})
                else: miss += 1
                if pl: trays.append(pl)
        res[view] = {"n_found": len(pts), "n_missed": miss, "points": pts, "tray_centres": trays}
        print(f"{view}: orange found in {len(pts)} first frames, missed {miss}; tray found in {len(trays)}")
    # grid from the overhead points: central 90 % box, 5 columns x 2 rows, cell centre = median of its members
    P = np.array([p["xy"] for p in res["overhead"]["points"]])
    lo, hi = np.percentile(P, 5, axis=0), np.percentile(P, 95, axis=0)
    inbox = P[(P[:, 0] >= lo[0]) & (P[:, 0] <= hi[0]) & (P[:, 1] >= lo[1]) & (P[:, 1] <= hi[1])]
    xs = np.linspace(lo[0], hi[0], 6); ys = np.linspace(lo[1], hi[1], 3); cells = []
    for j in range(2):
        for i in range(5):
            m = inbox[(inbox[:, 0] >= xs[i]) & (inbox[:, 0] <= xs[i + 1]) & (inbox[:, 1] >= ys[j]) & (inbox[:, 1] <= ys[j + 1])]
            centre = m.mean(0) if len(m) else np.array([(xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2])
            cells.append({"slot": len(cells), "px": centre.round(1).tolist(), "n_demos": int(len(m)), "box": [xs[i], ys[j], xs[i + 1], ys[j + 1]]})
    res["grid_overhead_px"] = {"box90": [lo.tolist(), hi.tolist()], "cells": cells, "note": "pixel targets in the overhead view; joint-space slots come from the calibration session"}
    json.dump(res, open(OUT / "demo_placement_area.json", "w"), indent=1, default=float)
    # scatter on a representative frame
    bg = first_frame("new30_merged", 0)
    for p in res["overhead"]["points"]:
        x, y = p["xy"]; cv2.circle(bg, (int(x), int(y)), 6, (0, 140, 255) if "recovery" not in p["set"] else (0, 200, 255), 2)
    for t in res["overhead"]["tray_centres"]: cv2.circle(bg, (int(t[0]), int(t[1])), 4, (255, 0, 0), -1)
    for c in cells:
        x0, y0, x1, y1 = [int(v) for v in c["box"]]; cv2.rectangle(bg, (x0, y0), (x1, y1), (0, 255, 0), 1)
        cv2.putText(bg, f"S{c['slot']} n{c['n_demos']}", (x0 + 3, y0 + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
    cv2.putText(bg, f"orange start positions, {len(P)} September demos (overhead cam); blue = tray centres; green = 10 MAIN-row slots", (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.imwrite(str(OUT / "demo_placement_area.jpg"), bg); print("wrote", OUT / "demo_placement_area.jpg")
    for c in cells: print(" ", c["slot"], c["px"], "demos", c["n_demos"])


if __name__ == "__main__":
    main()
