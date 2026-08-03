# Agent Handoff: SO-101 + Pi05, State of the Project

Last updated: 2026-08-03
Supersedes: `claude_handoff_pi05_20260725.md`, `gemini_handoff_pi05_20260726.md`
(both are historical - their diagnoses were later overturned; see Section 4).

This document is for any agent taking over this work. It states what is
VERIFIED, what is BELIEVED, what is OPEN, and what to do next. Read Sections
1-3 before touching anything; they are the rules and the current truth.

> **ON A NEW MACHINE? Read `../NEW_MACHINE_SETUP.md` FIRST.** This document
> assumes a working environment. A fresh `git clone` is missing six things
> that live outside git - the venv, ROBOT CALIBRATION, SSH keys, correct
> camera device paths (machine-specific!), the HF token, and datasets. Two of
> those fail silently and will look like model problems: missing calibration
> and stale camera paths.

---

## 1. The Project In One Paragraph

A hobbyist (Prakash) is teaching an SO-101 6-DoF arm to pick up fruit using
Pi05, a vision-language-action model, fine-tuned on his own teleop demos and
served from a rented RunPod GPU over an SSH tunnel. The robot can currently
grasp, lift and carry objects - including objects it was never trained on -
and it obeys object names in the instruction. It has NEVER completed a place
(set the object down at a target). The immediate goal is generalization: the
robot should not depend on fruit size or type, and should eventually do more
than one task family.

Paths:

```text
repo:     /home/gaikwad-prakash/PrakashProjects/lerobot/lerobot   (fork: Gitgai/lerobot, branch main)
project:  /home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/projects/testproject
docs:     projects/testproject/docs/
scripts:  projects/testproject/scripts/
traces:   projects/testproject/artifacts/traces/   (NEVER commit these)
```

Read next, in this order:

```text
pi05_active_work_tracker.md              - running log, banner at top = current status
pi05_generalization_roadmap_20260802.md  - THE ACTIVE PLAN (Stages 0-5)
pi05_rtc_first_live_sessions_20260801.md - how the current working recipe was found
pi05_feature_backlog_20260801.md         - deferred features with rationale
pi05_network_payload_reference_20260801.md - why JPEG, what the bottleneck was
```

---

## 2. Hard Rules (from the user - do not violate)

```text
1. OFFICIAL LEROBOT DEFAULTS ONLY. The user rejected a speed cap
   (max_relative_target) explicitly: "I want everything lerobots default, do
   not change that default." Fixes must be official features (this is why RTC
   was pursued) or clearly-marked local wrappers, never silent default edits.
2. NEVER COMMIT artifacts, traces, videos, images, datasets, checkpoints, or
   generated CSVs. Docs and scripts only.
3. NEVER put HF tokens (or any secret) in docs, scripts, logs, or git.
4. THREE CAMERAS OR IT DOESN'T COUNT. A 2-camera run is not a valid result.
5. THE USER MUST BE PHYSICALLY PRESENT for any robot motion. Never start a
   run the user did not just authorize.
6. STOP THE POD after every session (billing). See Section 8.
7. CAMERA-REFERENCE GATE before every session (Section 7).
8. ONE VARIABLE AT A TIME. This project's biggest wins came from clean
   comparisons; its biggest wasted nights came from changing two things.
9. Use `uv run` / the project venv, not raw python or pip.
```

Working style the user expects: evidence before conclusions, plain language
(he asks "explain in simple language" often and means it), documents committed
as work happens, and honesty when a previous claim turns out wrong.

---

## 3. Verified Capability State (as of 2026-08-03)

Every line below was re-verified from trace data with the finger-stall test
(Section 5), not from memory or from watching video.

```text
CAN DO (verified):
  understand object names in the instruction .... 4/4 novel objects selected
                                                  correctly (onion, tomato,
                                                  banana, tomato-vs-orange)
  approach and reach ............................ reliable
  grasp round mid-size objects .................. AT THE PRACTICED LOCATION
  lift .......................................... reliable when grasp succeeded
  sustained carry ............................... best 40 s, full height (onion)
  soft-object grip force ........................ tomato carried, not crushed
  novel wrist alignment ......................... rotated toward banana's axis

CANNOT DO (verified, repeatedly):
  place / release at a target ................... 0 successes in ENTIRE project
  goal-directed transport ("on the plate") ...... no plate-directed motion ever
  grasp low/flat objects (banana) ............... approach height too high
  grasp at an UNPRACTICED position .............. 2026-08-02: 10 min, 145 empty
                                                  squeezes on a relocated onion
  tolerate scene changes ........................ same onion held 40 s in the
                                                  morning scene, never held in
                                                  the evening scene
```

One-sentence model: **language understanding and transport survived the
fine-tune; grasp geometry and goals are welded to the exact scene it trained
in.** Every gap on that list is a DATA problem (Stage 2), not a model or
infrastructure problem.

Five-run reliability count (2026-08-02, small orange, frozen recipe):
grips 4/5, lifts 4/5, sustained carries 2/5, places 0/5.

---

## 4. History: What Was Tried And How It Went

Compressed, because the wrong turns matter as much as the wins.

```text
ERA 1  Jul 20-22   "The model is broken"          -> WRONG DIAGNOSIS
  Nothing worked live. Local offline probes seemed to prove checkpoint 012000
  had collapsed. Both were artifacts of a BROKEN HARNESS: newer lerobot code
  cannot serve this checkpoint (proved by a trust exam: gripper corr 0.197
  FAIL vs 0.83 on training-era code), plus a starved network path (7-8 act/s).
  LESSON, now a project rule: SUSPECT THE HARNESS BEFORE THE MODEL. Validate
  any new measurement tool against a known-good answer before believing it.

ERA 2  Jul 28      First real grasp               -> BREAKTHROUGH
  Fix set: serve on training-era code, chunk_size_threshold 0.85, corrected
  camera devices, JPEG-compressed observations (2.77 MB -> ~190 KB, 14.6x;
  the bottleneck was gRPC over the SSH tunnel, ~2 MB/s, NOT the uplink), and
  a decoupled observation thread. Trace shows 100 stalled squeezes at width
  29 - the first genuine hold.

ERA 3  Jul 29-Aug 1  Speed + RTC                  -> SOLVED, OFFICIALLY
  The arm moved too fast: latency ate ~60% of each 50-action chunk, so the
  client fast-forwarded through the remainder (lerobot-default behavior, not
  a bug). The user refused a speed cap, so the fix had to be official: RTC
  (Real-Time Chunking) already existed in the old code; only an async-server
  adapter was missing. Built it (env-gated, idempotent patch). RTC_ENABLE=1
  with RTC_EXEC_HORIZON=35 (default 10 is too small - horizon must exceed the
  ~30-step latency) produced the first grasp -> lift -> CARRY.

ERA 4  Aug 2 AM    Five-run count + slip cause    -> BASELINE ESTABLISHED
  Carry-slip mechanism identified from the user's own video: the gripper
  pinches the fruit at its EDGE, not across its center. Demos gripped the
  larger practice fruit at width 31-33; the small orange holds at 28 = the
  slip zone. Trace analysis independently caught run 5's "carry" as an
  empty-finger lift, which is what motivated Section 5's method.

ERA 5  Aug 2 midday  Zero-shot probes             -> BEST RESULT OF PROJECT
  Selection 4/4. Onion (never trained) carried 40 s - better than the trained
  fruit. Tomato: fastest grab ever, no crushing, chosen over a look-alike
  orange. Banana: wrist rotated to its axis (novel) but never picked - flat
  profile vs learned approach height. Goal probe (put on plate): no plate-
  directed motion in 3 attempts.

ERA 6  Aug 2 PM    Plate scenes                   -> ALL FAILED, two causes
  (a) BEHAVIORAL: onion->plate run 1 had healthy rates and still closed on
      air 145 times in 10 minutes. Same onion, same checkpoint, 2 hours after
      a 40 s carry. What changed was the SCENE (plate in view, onion moved).
      This is the position-generalization failure, and it is the real finding.
  (b) INFRASTRUCTURE: every other evening run was starved (0.3-0.4 obs/s -
      one image every ~2.6 s) as the SSH tunnel degraded and died. Those runs
      prove nothing. An external agent (codex) independently read the video as
      "reach and press, never a real grasp" - the traces confirmed it exactly.
  Because no pick completed, the PLATE QUESTION GOT NO NEW EVIDENCE that
  evening. The "goal-conditioning not observed" finding rests on the midday
  probes only.
```

---

## 5. The Measurement Method (use this; do not trust eyeballs)

`scripts/analyze_grasp_from_trace.py` - run it on any trace directory.

The physical test: fingers cannot pass through an object. When the policy
commands a hard squeeze (< 22), either the measured width STALLS above the
command (something is between the fingers = real grasp) or it FOLLOWS the
command down (closed on air = empty).

```bash
cd projects/testproject
.venv/bin/python scripts/analyze_grasp_from_trace.py artifacts/traces/<RUN>
```

Validated against known outcomes: the best carry (onion) reports 62 stalls /
30 carry samples at width 30-31; the failed evening run reports 3 stalls /
145 empty; the starved run is flagged UNTRUSTWORTHY automatically.

```text
ALSO A HARD GATE: if obs_rate < 0.8/s the run is BLIND (policy steering on
seconds-old images) and its behavioral result must be discarded as
infrastructure, not behavior. Check this BEFORE interpreting any run.
```

Two earlier verbal claims were corrected by this tool (an assistant's own
"carries happened" read of the evening runs, and run 5 of the five-run count).
Trust the tool over narration, including your own.

---

## 6. Architecture Finding: What Pi05 Actually Ships

Investigated 2026-08-02 against PI's blog (pi.website/blog/pi05), the openpi
repo, and lerobot's port. This reframes the place/goal failures.

```text
Full pi05 as described by PI = TWO brains:
  HIGH-LEVEL: the model DECODES TEXT - given "clean the bedroom" it writes
              "pick up the pillow" to itself, then acts on that subtask.
  LOW-LEVEL:  flow-matching action expert, 50-step chunks (what moves joints).

What Physical Intelligence RELEASED: the low-level half only. openpi states
plainly: "we currently only support the flow matching head for both pi0.5
training and inference." No text generation, no hierarchical inference. The
10k+ hour pre-training mixture and the subtask/verbal-instruction data are
NOT released either.

Therefore lerobot's policies/pi05 is a FAITHFUL port of what exists - the
hierarchy was never available to port. Our compound instruction ("pick up the
onion and put it on the plate") goes straight to the motor expert, which was
never meant to plan multi-step on its own.
```

Verified by reading code (both new repo code AND the training-era commit
e40b58a8 that the pod actually runs):

```text
client sends task with EVERY observation .......... robot_client.py:469
old server preserves task from each observation ... raw_observation_to_observation
old server rebuilds + retokenizes the prompt every
  inference, NO caching ........................... Pi05PrepareStateTokenizerProcessorStep
  builds f"Task: {text}, State: {state};\nAction: " fresh each call
our pod patches never touch the task path ......... verified in both patch scripts
```

**Consequence: the task string CAN be changed mid-episode and the model will
genuinely re-read it, with zero pod changes.** That makes the "be the writer
ourselves" experiment (Section 9, item 1) legitimate rather than wishful.

Also found and NOT yet used: `use_relative_actions` (OpenPI's DeltaActions).
We trained ABSOLUTE joint targets, which literally encode the practiced table
position - exactly our verified failure mode. Relative actions learn offsets
from the current state instead (gripper stays absolute). It is a TRAINING-time
choice: it cannot help 012000, only the next fine-tune.

PI's own ablations rank our data priorities: removing environment diversity
hurt worst (OOD success -> 31%), worse than removing cross-embodiment (49%)
or web data (80% follow rate). Translation for a one-table setup: VARY THE
SCENE, not just the object.

---

## 7. Hardware And Session Runbook

```text
CAMERAS (the 3-camera rule)
  top   = Logitech C270, by-id:
          /dev/v4l/by-id/usb-046d_C270_HD_WEBCAM_FC7A6780-video-index0
  front = laptop built-in ACER, MUST use by-path (the by-id name jumped to the
          IR sensor after a reboot and silently gave GREY 640x360@15):
          /dev/v4l/by-path/pci-0000:00:14.0-usb-0:5:1.0-video-index0
  wrist = Raspberry Pi camera, served over HTTP by a laptop-side proxy at
          http://127.0.0.1:8092/frame
  Config lives in config/so101.json. /dev/videoN numbers MOVE - verify before
  every session. The laptop must physically FACE the robot (this has bitten
  three times).

RASPBERRY PI (wrist)
  ssh raspi@192.168.1.15   (IP has moved before: was .14)
  BEFORE a session: sudo systemctl stop timelapse.service pipics.service
  AFTER  a session: start them again (the user's other projects use them).
  "no cameras available" = electrical (reseat ribbon).
  "failed to acquire / pipeline in use" = something else holds it (services,
  or a Chrome tab - the user closes it).

POD (RunPod, RTX 3090)
  Serves the policy on TRAINING-ERA CODE at /workspace/lerobot (upstream
  e40b58a8). The checkpoint ONLY works there - see Era 1.
  After ANY pod migration, repair the environment:
      python3 -m pip install -q uv
      uv python install 3.12.13      # restores /workspace/venv312 interpreter
      export HF_HOME=/workspace/hf_cache
  Then re-apply (idempotent, env-gated):
      scripts/runpod/apply_jpeg_decode_patch.sh
      scripts/runpod/apply_rtc_server_adapter.sh
  Server env for the working recipe: RTC_ENABLE=1 RTC_EXEC_HORIZON=35
  Tunnel: ssh -N -L 8080:localhost:8080 -o ServerAliveInterval=15 \
              -o ServerAliveCountMax=8 -p <PORT> -i ~/.ssh/runpod_ed25519 root@<IP>
  The tunnel DIED THREE TIMES in one evening. Rebuild it fresh before each
  run and re-check the obs rate (Section 5) rather than trusting it.

LAUNCH (the frozen "h35 recipe" - do not vary without a reason)
  cd /home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/projects/testproject/scripts
  ../.venv/bin/python async_client_3cam.py \
    --policy-type pi05 \
    --task "pick up the onion and move it to another place" \
    --ckpt /workspace/outputs/pi05_orange49_plus_grasp_focus_bs4_from003000_restart_012000/checkpoints/012000/pretrained_model \
    --chunk-size-threshold 0.85 --max-relative-target null \
    --jpeg-quality 92 --trace-dir ../artifacts/traces/NAME_$(date +%H%M%S)
```

Grip-width predictor (useful live): fingers >= 31 = secure carry;
<= 28 = slip risk. Healthy run: ~1.5-2 obs/s, ~20 act/s.

---

## 8. Traps That Have Already Cost Time Or Money

```text
pkill self-match: a compound shell command containing the process name kills
  its own shell (exit 144). Use bracket patterns: pkill -f 'async_client_3cam[.]py'
Background shells start in the REPO ROOT, not the scripts dir. Use absolute
  paths or cd first.
Pod migrations RESTART STOPPED PODS and rotate the SSH port. The user must
  re-stop after each migration; this has drained balance repeatedly ($7,
  $1.40, $0.50 incidents). Network volumes also bill silently (~$25/mo leaked
  across five volumes; three deleted, one 10GB EU-RO-1 "silent_coffee_tick"
  still pending inspect-then-delete).
Congested pod hosts (load > 100) produce 5.7 s latency and annul runs. A
  fresh deploy rolls a new host.
Serial glitches "Incorrect status packet" on motors 4/5/6 at connect: a retry
  clears it, but FREQUENCY IS INCREASING - hardware watch item.
Never diagnose from video alone, and never from the command stream alone.
  Use Section 5.
```

---

## 9. What To Do Next (priority order)

**1. Subtask-switching probe (15 min of robot time, no training, high value).**
Verified feasible in Section 6. Be the high-level brain ourselves: start the
episode with `"pick up the onion"`; the moment the live stall test says the
onion is held (commanded < 22, measured > commanded + 10, measured in 25-36,
sustained ~2 s = 3-4 observations), switch the task string to
`"put the onion on the plate"`.

```text
Implementation note (checked): RobotClient takes the task ONCE into both
loops (robot_client.py:581-586), so this needs a small subclassed wrapper
with a mutable current_task plus a watcher thread; the watcher must also
wrap robot.send_action (line 424) to capture the COMMANDED gripper width,
because self.latest_action is only an index. Add a manual override key -
the user is present anyway.
Scene: onion at its PRACTICED morning spot, plate elsewhere. We are isolating
the goal question, not re-testing position generalization.
Outcome either way is informative: no change = the place skill is genuinely
absent and only Stage 2 data fixes it; any plate-directed motion = P6 failed
partly on PROMPT STRUCTURE, and subtask-style strings become standard in how
we run AND record everything.
```

**2. Stage 2: the generalist recording session (one focused evening, free).**
40-60 teleop episodes. The spec, updated by everything learned since it was
written:

```text
objects:   small orange, big orange, onion, tomato, banana, a ball/block
POSITIONS: vary object AND plate positions widely  <- NEW, from the 08-02
           evening failure; this is now co-top priority
HEIGHTS:   include low/flat objects to break the fixed approach height
SCENE:     vary background/lighting/camera nudges (PI ablation: environment
           diversity mattered most)
GOAL:      every episode driven to completion - grasp, lift, carry, PLACE ON
           THE PLATE (the user's idea; gives the never-learned place phase a
           clear, visually unambiguous signal)
STRINGS:   correct per-object task strings, AND record at two specificity
           levels - some compound ("pick up the onion and put it on the
           plate"), some single-subtask ("pick up the onion" / "put the onion
           on the plate"). This is how PI built the hierarchy, and it makes
           item 1's switching strategy trainable rather than a hack.
optional:  +10-15 push/slide episodes as a second task family.
```

**3. Stage 3: the generalist fine-tune (overnight, ~$3-5).**

```text
Train on the NEW lerobot code (code-pairing rule; native RTC - the adapter
retires). Enable banked features: image_transforms ON, wandb ON, eval_split ON.
NEW DECISION, from Section 6: set use_relative_actions=true
  --policy.use_relative_actions=true --policy.relative_exclude_joints='["gripper"]'
Init from BASE, not from 012000: the base weights carry the web + multi-robot
co-training that our single-task fine-tune partially overwrote; body adaptation
is cheap to re-learn from diverse data, that education is not.
Gate offline (exam harness) before spending robot time.
```

**4. Stage 4: scoring matrix.** Five-run counts per object x phase (grasp /
lift / carry / place), including one object NOT in training (e.g. a lemon) as
the true generalization test. Score with `analyze_grasp_from_trace.py` rather
than by eye.

**5. Optional loose end:** the P5 push probe ("push the orange to the left") -
the only unanswered Stage 1 question, ~10 minutes.

**Deprioritized:** Stage 0 (big-orange five-run count). Its two purposes -
confirming the edge-grip mechanism and testing the place phase - are both
already answered from other directions.

---

## 10. Open Questions

```text
Does the place skill exist in the weights at all, addressable by a clean
  subtask string?                                  -> item 1 answers this
Does any non-pick motion (push) remain accessible? -> P5 probe
Will relative actions + position diversity actually fix position
  generalization on this arm?                      -> Stage 3/4 measure it
Are the increasing serial glitches a failing cable/servo?  -> hardware watch
Is a second VLM as an autonomous subtask writer worth building? -> only if
  item 1 shows subtask switching helps
```

---

## 11. Status At Handoff

```text
Branch main, last commit 95925d87 (five-run count, edge-grip diagnosis,
generalization roadmap, Stage 1 probe results).
Uncommitted at handoff: this document, scripts/analyze_grasp_from_trace.py,
and the 08-02 evening addendum if not yet written into the roadmap doc.
Pod: was vertical_tomato_antelope (213.192.2.109:40144) - CONNECTION REFUSED
as of 2026-08-02 night, i.e. stopped or migrated. Verify state before assuming
either; a migration silently restarts it.
Pi services: restored (timelapse + pipics active) after the 08-02 session.
No run is in flight. No background process should be left running.
```
