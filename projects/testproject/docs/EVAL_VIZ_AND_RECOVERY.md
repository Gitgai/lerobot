# Visualizing eval trials, and the recovery-data plan

Written 2026-09-18. Two things settled this session: how to replay a policy eval
trial in LeRobot's viewer, and why the fix for the hover failure is *recovery
data* — plus a hard finding that constrains how we can collect it.

---

## 1. Turning an eval trial into a LeRobotDataset you can visualize

Our GR00T eval runs through a separate server/client (`n16_realarm_client.py`),
so it dumps per-chunk JPEGs + a JSON trace instead of a LeRobotDataset. But the
trace already carries the full 6-joint `observation.state` AND the executed
action, so no re-recording is needed — just repackage.

```text
run_trial.sh now preserves the trace:  ~/trial_<N>_trace.jsonl  (per trial)
convert:   trace_to_lerobot.py  <trial_frames_dir>  <trace.jsonl>  <out_root>  <repo_id>
           (writes a v3.0 LeRobotDataset; calls ds.finalize() — REQUIRED, or
            meta/episodes/*.parquet is missing and the dataset won't load)
```

Example (on the Acer):

```bash
cd ~/PrakashProjects/lerobot/lerobot
.venv/bin/python ~/trace_to_lerobot.py \
  ~/trial_90_frames ~/trial_90_trace.jsonl \
  /data/lerobot_datasets/eval_6000_viz local/eval_6000_viz
```

### Viewing it

`lerobot-dataset-viz` needs `rerun-sdk` (extra `[viz]`). It was NOT installed;
install with uv (the venv has no pip):

```bash
~/.local/bin/uv pip install --python ~/PrakashProjects/lerobot/lerobot/.venv/bin/python 'rerun-sdk>=0.24.0,<0.27.0'
```

There is **no `--serve` flag**. Web viewer = `--mode distant`:

```bash
HF_HUB_OFFLINE=1 .venv/bin/lerobot-dataset-viz \
  --repo-id local/eval_6000_viz --root /data/lerobot_datasets/eval_6000_viz \
  --episode-index 0 --mode distant --web-port 9090
```

Gotchas, each hit this session:
- `HF_HUB_OFFLINE=1` is required, or `local/...` tries HuggingFace and 401s.
- The web app (9090) and the DATA server (gRPC 9876) are SEPARATE ports. Opening
  `:9090` bare shows an EMPTY viewer because it can't reach the data. Open with
  the explicit data source:
  `http://<acer-ip>:9090/?url=rerun%2Bhttp://<acer-ip>:9876/proxy`
  and make sure BOTH ports are reachable from the browser machine.
- WebGPU error in the browser → append `?renderer=webgl`.
- Native viewer alternative: `--save 1 --output-dir ~/rrd` writes a `.rrd`, open
  with the VENV rerun (`~/PrakashProjects/.../.venv/bin/rerun file.rrd`) — NOT the
  snap/apt `rerun` (wrong version, rejects the file). Native needs a display
  (the Acer's Wayland session; over SSH set `WAYLAND_DISPLAY=wayland-0
  XDG_RUNTIME_DIR=/run/user/1000`).

### Reading the plots

`state/0..5` and `action/0..5` are the six joints, by index:

```text
0 shoulder_pan   1 shoulder_lift   2 elbow_flex   3 wrist_flex   4 wrist_roll   5 gripper
```

`state` = where the arm IS; `action` = where the policy commanded it. The two
diagnostic curves: **`state/1` (shoulder_lift)** is the descent (success drops to
~-104, hover stays up), and **`state/5` (gripper)** is the grasp (a dip = closed,
a rise = released). The camera decides success; the curves say why.

---

## 2. The hover is covariate shift — recovery data is the documented fix

Measured this session (all verified twice):

```text
training: 30/30 episodes are CLEAN one-shot descents, 0 recoveries, 0 corrections
hover:    the failing policy stays UP-AND-EMPTY ~80 s — 8x the max ever demonstrated
          (training max up-and-empty = 10.7 s)
NOT position: same orange spot (x~180) gave success (trial 7) AND failure (11-13)
NOT lighting: measured brightness identical to the 5/10 morning
```

So the model drifts into a prolonged-hover state that appears nowhere in the 30
demos, and — with no recovery example — can't get out. This is textbook
behaviour cloning covariate shift, and LeRobot documents the fix in
`docs/source/hil_data_collection.mdx` (its own words: "small errors can compound
and push the robot into states never seen during training (distribution shift)")
and implements it in `src/lerobot/rollout/strategies/dagger.py` (the RaC
"Recovery and Correction" paradigm).

---

## 3. HARD FINDING: LeRobot's native groot is N1.5-only — we can't use its DAgger

LeRobot HAS a groot policy (`src/lerobot/policies/groot/`), which would give the
DAgger/HIL tooling for free. But it CANNOT load our checkpoint:

```text
                  LeRobot's groot            our checkpoint
version           GR00T N1.5                 GR00T N1.6 (Gr00tN1d6)
safetensors       single model.safetensors   SHARDED (model-0000N-of-00002)
config            GrootConfig (LeRobot)       config.json (Isaac-GR00T)
```

`GrootPolicy.from_pretrained` detects a fine-tune by looking for a SINGLE
`model.safetensors`; ours is sharded, so it isn't even recognized, then it falls
back to loading a base N1.5 (which ours isn't). Using it would require
downgrading to N1.5 (a step back) or porting N1.6 + a checkpoint converter into
LeRobot (significant work). **So HIL, if we do it, must be built on our
Isaac-GR00T serving path, not LeRobot's dagger.py.**

---

## 4. The plan: recovery data on N1.6

```text
Path 2 (START HERE)  record fresh demos that go OFF-TARGET then CORRECT, then pick.
                     No new code — rec_esp.sh already does leader->follower teleop
                     recording. Needs the leader arm powered. Vary off-target
                     direction and orange position. ~25 episodes -> dataset
                     esp_recovery. episode_time_s bumped to 45 s (trimming removes
                     the tail). Fold into training, fine-tune from 6000, ~6000 steps.

Path 1a (LATER)      HIL: run 6000, human takes over on the hover via the leader,
                     record the correction. Needs custom takeover built into the
                     client (pause policy <-> teleop switch). Only if Path 2 stalls.

Path 1b              RULED OUT — LeRobot's groot is N1.5 (section 3).
```

Do NOT switch the base model (e.g. to the N1.7 community checkpoint): that
`robocurve/gr00t-n1.7-so101-molmoact2` model was evaluated in sim on 2026-08-05
and NEVER acquired the orange despite 2,242 training episodes. The bottleneck is
recovery data, not model version or scale.

---

## 5. Timing / payload reference (measured 2026-09-17..18)

```text
full loop per chunk    871 ms   (round-trip 586 + local 285)
round-trip (rtt_ms)    586 ms   = network 253 (ping) + payload+inference ~333
network RTT (ping)     253 ms   FIXED (transatlantic; independent of payload)
wire payload           ~160 KB/request  (2 JPEG-q92 images + state + lang)
                       raw would be 1.84 MB — 11.5x larger
image sizes            SEND 640x480 per camera; backbone consumes ~256 px
                       (crop_fraction 0.95 + shortest_image_edge 256)
effective bandwidth    ~10.7 Mbps
```

Reducing to 256 px (needs a retrain to match) shrinks payload 160->47 KB but only
saves ~87 ms round-trip — base latency and inference dominate, not payload.
Related documents: `PLAN.md`, `MODELS.md`, `MACHINES.md`, `EPISODE_TRIMMING.md`.
