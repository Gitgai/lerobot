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
Path 2 (DONE 2026-09-18)  record fresh demos that go OFF-TARGET then CORRECT,
                     then pick and place. No new code — rec_esp.sh does the
                     leader->follower teleop. Recorded 30 episodes at 30 s each
                     into esp_recovery, kept WHOLE (not trimmed), folded into a
                     60-episode set, fine-tuned from checkpoint-6000. See
                     section 6 below for what actually happened.

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

---

## 6. Path 2 executed — recovery batch + training (2026-09-18)

30 recovery demonstrations recorded on the Acer into `esp_recovery`, 30 s each,
each: reach OFF-TARGET -> CORRECT onto the orange -> grasp -> carry -> RELEASE on
the plate -> return toward rest. Varied off-target direction and orange position.

### Verifying the batch — and a camera blind spot

Scored every episode's final placement from the FRONT camera with a position-free
plate detector (finds the plate's blue-grey oval anywhere, tests the orange's
centroid against its convex hull). Two detector iterations were needed, and the
SECOND lesson is the important one:

```text
first detector    reported 8/30 on-plate. WRONG - find_orange locked onto warm
                  WOOD-GRAIN on the table (largest warm blob by area), not the
                  orange. Caught by looking at the annotated montage, not the number.
fixed detector    24/30 on-plate, 6 "OFF". Asks the direct question instead:
                  is there a round orange blob INSIDE the plate hull?
the 6 "OFF"       NOT failures. In all 6 the plate sat at the front camera's
                  bottom-LEFT frame EDGE, out of view. The hull was a clipped
                  sliver (bbox x0-84) so every orange read "out" mechanically,
                  and the red "orange" dots were wood-grain false positives.
                  The WRIST camera (looks straight down) shows the orange held
                  over the blue plate at release in every one. 30/30 place.
```

**Rule: the front-camera plate scorer is BLIND to edge-of-frame plates.** Its
"OFF" there means "cannot see", not "missed". Read the wrist camera before
calling a placement a failure. And an automated detector's output is a claim to
verify (montage, wrist view, operator knowledge), never evidence on its own —
established here by over-claiming two failures that were both good places.

### Folded in and training

```text
convert   esp_recovery v3.0 -> v2.1 whole-episode  (convert_recovery_v21.py on
          the Acer; do_trim=False; integrity: video frames == parquet rows)
merge     new30_merged (30) + recovery30_v21 (30) -> new30_plus_recov30 (60 eps,
          50 orange + 10 tomato)  (merge_recov60.py, symlinked videos, renumbered)
stats     REGENERATED for the 60 (gr00t.data.stats + the leisaac modality config
          that registers new_embodiment). Ranges WIDENED vs the 30-ep set
          (shoulder_pan max 57->84, gripper max 70->88) so off-target states are
          normalised, not clipped. Copying the old stats would have clipped them.
train     n16_recovery_v1 - fine-tune FROM checkpoint-6000 (AutoModel.from_pretrained
          loads its sharded weights; fresh output dir -> trainer starts at step 0),
          6000 steps, save 3000+6000, effective batch 32, lr 1e-4, 8-bit adam.
          Launched 2026-09-18 ~12:37. Test BOTH checkpoints on the arm.
```

---

## 7. Recovery model arm eval — n16_recovery_v1 / checkpoint-6000 = 5/10 (2026-09-18)

Ten valid trials on the real arm (numbered 601-611; 101, 606 and one 607 voided
for un-homed start or orange-already-on-plate). Each: home (auto-clear + retry),
run policy, score placement from the FRONT camera, gripper trace kept.

```text
601 ✓  602 ✓  603 ✗  604 ✓  605 ✓  607 ✗  608 ✓  609 ✗  610 ✗  611 ✗   = 5/10
```

Same rate as the pre-recovery model (5/10) BUT a completely different failure mode.

### The hover is gone
All 10 trials the arm set out and descended onto the orange. Zero hovers. The
covariate-shift failure the recovery data targeted is eliminated. The rate is
flat only because a new bottleneck surfaced: the GRASP.

### Grasp timing perfectly separates outcome (the key finding)
```text
success grasp at chunk:  59  67 127 148 171   (first ~55% of the trial)
failure grasp at chunk: 201 207 233 285 317   (last ~65%) - clean gap, no overlap
```

### grip-min is a physical grasp gauge (jaws stop on the orange's diameter)
```text
grip-min 22-25  orange in the jaws          all 5 successes
grip-min 13-14  closed on EMPTY AIR (miss)  609, 610
grip-min 18-20  partial/fumble              603, 611
grip-min 68     never closed                607
```
Release confirms: successes reopen 63-71; three failures stay clamped 18-20.

### Position does NOT drive outcome (hypothesis refuted, by eye not the detector)
Same orange positions gave both outcomes: far-left 601 ✓ vs 607 ✗; centre 604 ✓
vs 609/610 ✗; far-right 608 ✓ vs 611 ✗. The failure is execution inconsistency,
not a hard/OOD position. (The automated orange detector was UNRELIABLE here - it
mislocated 607's far-left orange to centre on a wood-grain false positive - so
positions were read by eye. See the blind-spot lesson, section 6.)

### Two earlier claims corrected by the data
- "The correction meanders/dithers" - WRONG. Failures UNDER-move: 603/607/611
  had arm joint travel 262-487 deg, below every success (960-1769). They STALLED
  (arm stuck, didn't complete); 609/610 moved a normal amount but the grasp
  missed. No failure meandered.
- "607 failed because far-left/OOD" - reframed: 601 succeeded from the same
  far-left spot. Position is not the cause.

### Mechanism
Recovery data made the APPROACH reliable but the GRASP is not. Per stochastic
rollout the model either locks on and grasps cleanly in the first half (success)
or it doesn't get the grasp geometry early and then stalls (603, 611), never
commits (607), or completes a motion that closes on air (609, 610). Same
positions, variable outcomes = a grasp reliability/precision problem, not a
coverage problem. Likely cause: the recovery demos taught "come down and try"
but not enough PRECISE, DECISIVE grasps.

### Confound not resolved
**BIGGER confound found later — see section 8: ALL these trials ran with the RTC
pipeline OFF (~31% duty), so the arm stalled ~650 ms between chunks. The 5/10 was
measured CRIPPLED; the true rate is unknown until re-tested with --rtc.**

Later trials failed more (first 5: 4/5; last 5: 1/5). Position is ruled out;
remaining candidates are small-sample stochasticity and hardware warming
(gripper closing hard, one overload trip) reducing precision over ~30 min.
Homing stayed accurate (0.3-0.8 deg worst joint every trial), which argues
against gross drift. A controlled re-test (rest arm, repeat positions) would
settle it.

### Next
1. Test checkpoint-3000 (recovery).
2. Next data need is PRECISE grasp demos (clean early closes at grip~22), NOT
   more descent demos.
3. Controlled re-test to isolate warming vs stochastic.

Tooling added this session: home_and_trial.sh (home w/ retry + clear_overload.py
before each trial), clear_overload.py (toggles TorqueEnable to clear a latched
Feetech gripper OVERLOAD - id 6 tripped after a hard close on trial 603),
trial_sheet.py (front+wrist contact sheet), srv_wrap_recov.py (RECOV_CKPT=3000|6000).

---

## 8. CRITICAL: those evals ran with the RTC pipeline OFF — and that's how the old 9/10 worked (2026-09-19)

Surfaced by the operator's question: "how did the old model get 9/10 over this
same transatlantic link?" The answer corrects section 7's implied cause.

### The old 9/10 used RTC (real-time chunking); this session's evals did not
`orange_pick_baseline_v1` (9/10 on the arm, 2026-08-20) ran the client with RTC
ENABLED — a PIPELINED loop that keeps one request always in flight, so the arm
moves continuously while the next chunk's inference happens in the background.
The transatlantic round-trip is HIDDEN behind the arm's motion.

```text
OLD 9/10   --rtc ON   ->  95.4% duty cycle, zero starvation  (arm moves continuously)
                          git 9e7203b7 "RTC pipelined client - G0 (95.4% duty)"
                          git 5c2092ad "RTC ten-run set: 9/10 completions"
THIS SESSION (601-611, 301-305, 621):  --rtc OFF (sequential)
                          run_trial.sh never passes --rtc
                          n16_realarm_client.py line 236: rtc=False (default)
                          measured chunk interval 919 ms, duty ~29%
                          == the client's own "sequential baseline 31%" (line 336)
```
Sequential = move 267 ms -> FREEZE ~650 ms waiting for the round-trip -> move ->
freeze. During the freezes the arm is blind/open-loop — exactly the imprecise
final-approach behaviour section 7 diagnosed.

### Correction to the latency conclusion
An earlier read this session concluded the ~1.1 Hz loop was an unavoidable
consequence of the transatlantic link and that the fix was serving on a local /
Mumbai cloud GPU. **That was wrong.** The latency was already solved in August by
the RTC pipeline; these trials simply didn't turn it on. The 9/10 proves this
exact rig + link grasps reliably WHEN THE PIPELINE IS ON. A closer/faster GPU is
UNNECESSARY, not just secondary: the live AI90->Acer ping is ~307 ms DIRECT
(2026-09-19), essentially the 9/10 era's 321 ms — the rig is already in the regime
that produced 9/10. depth-2 RTC keeps 2 requests in flight and HIDES the
round-trip; it is throughput-bound, not latency-bound. (The 256px-payload /
fewer-diffusion-steps ideas are also minor; diffusion steps are already at the
minimum of 4. The whole local/Mumbai-GPU line of thought was a wrong turn.)

### Implication
The recovery model's 5/10 and checkpoint-3000's 0/5 were measured CRIPPLED
(RTC off). Their true rates are unknown until re-tested with --rtc. The whole
"new camera -> 5/10" narrative may itself be partly confounded by RTC being off
in those evals — to be measured, not assumed.

### The fix (free, no GPU, no retrain, proven)
```text
add  --rtc  to run_trial.sh  ->  re-enable the ~95% duty pipeline  ->  re-test 6000
```
`_rtc_loop()` (client line 474, "one request always in flight") is the real arm
path, gated at line 694 by `if cfg.rtc`. It passed gates G0-G2 and drove the 9/10
run, so it is proven — but verify it still runs cleanly before trusting a number.

Evidence: git 9e7203b7, 65eaa3ad ("skip-ahead + micro-blend + depth-2 pipeline"),
3007e7b0, 5c2092ad; client lines 236/398/474/694; run_trial.sh (no --rtc);
measured duty 29% ~= sequential baseline 31%.

### Lesson
Before attributing a slow control loop to network latency, CHECK WHETHER THE
PIPELINE (RTC) IS ENABLED. A measured 1.1 Hz was read as "the link is too slow /
needs a local GPU" when the real cause was a client flag defaulting to off. The
operator's "but the old model worked 9/10" caught it.

