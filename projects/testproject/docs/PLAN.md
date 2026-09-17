# SO-101 — the plan

Live document. Header updated **2026-09-17** after the 10-trial evaluation and
the checkpoint comparison. Previous full rewrite 2026-09-16
(`PLAN_superseded_20260916.md`).

---

## Where we actually are

**`n16_new30_v1/checkpoint-6000` places the orange about half the time on the
real arm — measured 5/10 over ten trials, 2026-09-16, every verdict confirmed by
the front camera.** That is a working model, not yet a good one, and it closes
three weeks in which every arm trial failed.

```text
n16_new30_v1 / checkpoint-6000
  parent      nvidia/GR00T-N1.6-3B          stock, NOT the frozen baseline
  data        30 episodes recorded 2026-09-15 through the OV4689 wrist camera
  steps       12,000, loss 1.115 -> 0.007   (but 6000 is the checkpoint to use)
  ARM RESULT  PLACE 5/10, GRASP 5/10 — every grasp it made, it completed
  baseline    orange_pick_baseline_v1 = 9/10, for comparison
```

**The failure mode is ONE thing, and it names the next job:**

```text
6000's 5 failures were all the same: the arm reaches out over the table and
HOVERS — it never descends onto the fruit. Measured from the logs, the failing
trials spent 5-12% of the run with the arm down; the successes 57-76%. No
overlap. When it DOES descend, it grasps and places every time (5/5).
```

**Checkpoint 12,000 is worse: PLACE 1/10.** More training (13.3 passes vs 6.6)
overfit the *holding* state — three of its four grasps clamped the gripper shut
for 250-281 chunks and carried the fruit home without releasing it. 6000 never
did this. So: use 6000, and never train past ~6,000 steps on this dataset.

>>> DIRECTION (operator, 2026-09-17): the way to raise 5/10 is not more testing,
>>> it is more demonstrations aimed at the descent. Record more episodes.

---

## What was actually wrong, and what fixed it

Three separate faults, each mistaken for the others at some point:

```text
THE CAMERA CHANGED
  For three weeks the model was shown a wrist view it had never seen. No amount
  of matching a new camera to old pictures worked.
  FIX: 30 fresh demonstrations through the camera we intend to keep.

THE FOLLOWER'S USB DROPPED
  Six disconnects in twenty minutes, on two different ports, under four
  different programs. Ruled out software, ports, torque and supply voltage by
  measurement; the leader's identical board never faltered.
  FIX: physical - rewiring the follower onto port 3-3. Three trials since,
  500+ chunks, over ten minutes under torque: ZERO disconnects.

THE SCENE WAS WRONG
  The first trial of 2026-09-16 failed with no orange on the table and the front
  camera 262 px out of position (measured from where the plate sits in frame;
  episode-to-episode variation is under 15 px).
  FIX: re-aim to within 5 px, put an orange down, home the arm first.
```

**None of these were model problems.** The model was never the thing that needed
fixing.

---

## The rig as it now stands

```text
FOLLOWER   serial 5B14114209, USB port 3-3      stable under torque, powered
LEADER     serial 5B14029688, USB (via hub)     plugged in but UNPOWERED as of
                                                2026-09-17 - power its motor
                                                supply before recording
WRIST      OV4689 "AK-Camera"  /dev/video0
FRONT      Logitech C270       /dev/video6      behind two hubs; knocked easily
GPU BOX    kiran-AI90, RTX 5090, New Jersey     all weights and datasets
LAPTOP     Acer, Pune                           arms and cameras, no weights
```

Resolve arms by serial (`arm_ports.py`) and cameras by name (`camfind.py`).
Never by device number — they move. See `MACHINES.md`.

---

## Measured facts that change how trials are run

### JPEG compression is free speed — use it always

Tested 2026-09-16 offline, no arm movement. One frozen observation, sent ten
times raw and ten times at quality 92. **The model is a diffusion policy, so it
answers differently every time; that noise is the yardstick.**

```text
raw  vs raw   (the model's own noise) : 1.624 deg
jpeg vs jpeg  (the model's own noise) : 1.341 deg
raw  vs jpeg  (the effect)            : 1.513 deg     ratio 1.02
```

Every joint checked separately, none above its own noise. **Compression is
quieter than the model's own dice roll.**

```text
latency raw    936 ms      duty cycle 29%
latency jpeg   319 ms      duty cycle 84%      2.9x faster
```

>>> RULING (2026-09-16): `--jpeg_quality=92` on every trial from now on.

### The arm must be homed before every trial

Every training episode begins at the same rest posture. A trial starting
elsewhere asks the model for a t=0 it has never seen.

```text
shoulder_lift  -104.3    ANCHOR, all 30 episodes within 1.0 deg
elbow_flex       96.7    ANCHOR, within 0.1 deg
wrist_flex       78.4    ANCHOR, within 3.3 deg
pan / roll / gripper     vary legitimately - do NOT test these
```

`home_arm.py` drives there in interpolated steps over 5 s. Never command the
target directly: the arm can be 35 deg away and would lunge.

### Latency shapes the tempo

Each chunk returns 16 actions, 8 are executed at 30 fps = **0.27 s of motion**.
Everything else is waiting. With raw images the arm moved a third of the time
and trial 3 needed 280 chunks; with JPEG it should need well under half that.

A trial timeout must allow for this. 130 s was too short and cut a run off
mid-grasp, which looked like failure and was not.

---

## Step 1 — record more demonstrations, aimed at the descent (NEXT)

The 5/10 evaluation and the 6000-vs-12000 comparison are DONE (see above). The
single failure mode is the hover — the arm not committing to the descent. More
trials measure that; they do not fix it. Demonstrations do.

```text
GOAL   teach a clean, committed reach-and-descend, so the model stops hovering.

WHAT   ~25-30 new episodes:
  - every episode shows a DECISIVE descent onto the fruit - no hesitation,
    no hovering. The model copies what it sees most; give it confident descents.
  - VARY the orange position deliberately - left, centre, right, near, far.
    The hover clusters at some positions; spread the coverage.
  - keep them tight: reach, grasp, place, done.

HOLD OUT   keep 5 episodes out of training (the lesson relearned all session:
           without a hold-out there is no offline measure).

TRAIN      from checkpoint-6000 (NOT stock, NOT 12000), fold the new demos in
           with the existing 30, stop at ~6,000 steps. 12000 overfit the release.

TEST       held-out episodes offline first, then the arm, varied positions.
```

Recording rig checklist (2026-09-17): follower, both cameras, and rec_esp.sh are
ready; **the LEADER ARM was enumerated on USB but UNPOWERED** (motors gave no
response - the dead-but-visible pattern). Recording is blocked until the
leader's motor supply is on. Record one episode and inspect it before the set.

---

## Deferred — still open, lower priority than the descent fix

```text
FIRM UP THE 5/10
  10 trials give a wide band (~25-75%). More would tighten it, but they measure,
  they don't improve. Only worth it with VARIED positions - a batch that hammers
  one spot (as happened 2026-09-17, trials 11-14 all bottom-left, 0/4) tells you
  about that spot, not the model. Do this only if a firmer number is needed for
  a decision.

DOES THE TOMATO WORK?
  Trained on 10 episodes, never tested on the arm.

DOES THE MODEL READ THE INSTRUCTION AT ALL?
  Almost certainly not yet: wrong-sentence penalty -0.04 (2026-08-26), and the
  tomato set was recorded with the tomato ALONE, so the picture already says
  which fruit. A language-grounding set needs BOTH fruits present with the words
  choosing. Separate, later job.
```

---

## Solved and closed — do not re-open

```text
WHICH MODEL IS THIS PROJECT USING?
  GR00T N1.6, settled 2026-08-19. Every checkpoint now carries LINEAGE.json AND
  TASKS.json. Searching for train_config.json finds only dead ends - that is a
  LeRobot convention and GR00T does not write one.

THE INSTRUCTION MISMATCH
  Every arm trial from August to mid-September sent "Grab orange and place into
  plate", a sentence in NO training set. Fixed 2026-09-16: default corrected,
  and the client now REFUSES an instruction the serving model was not trained on,
  reading the list from ~/model_tasks.json. Tested against all three cases.

ARE THE TWO ARMS IN SYNC?
  Yes. Five joints agree within 0.5 deg, reached by the follower tracking the
  leader. The gripper's apparent 61 deg gap is a trigger versus a pair of jaws -
  different mechanisms, not a fault.

WHAT BATCH SIZE FITS ON THIS CARD?
  per_device 4 with 8 accumulation steps = effective 32. Four attempts at 64 and
  32 died out of memory. bf16 is already the default and was never the variable.
  Read what worked from the previous runs' training_args.bin rather than
  reasoning about what should work.

6000 vs 12000 (settled 2026-09-17, 10 arm trials each)
  6000 PLACE 5/10, every grasp completed. 12000 PLACE 1/10 - it overfit the
  gripper-closed state and would not release (3 grasps carried home still held).
  USE 6000. Do not re-run this comparison; the arm settled it.
```

---

## Standing rules earned the hard way

```text
CAMERA     ENFORCED IN CODE since 2026-09-03. The client refuses to start unless
           the wrist frame is < 1.5 s old AND two fetches a second apart DIFFER.
           HTTP 200 is not proof - a frozen proxy returns 200 forever.
INSTRUCTION ENFORCED IN CODE since 2026-09-16. The client refuses a sentence the
           serving model was not trained on.
USB        Resolve arms by SERIAL and cameras by NAME, never by device number.
           /dev/ttyACM0 was the leader one morning and the follower by evening.
TORQUE     Survives a crash. When the USB drops, disconnect() never completes and
           the arm stays stiff and holding. Run safe.py after ANY crashed run.
SCENE      Photograph the scene BEFORE a run and check it against a training
           frame. Measure the camera by where the plate sits - it never moves.
           262 px of drift cost a trial on 2026-09-16.
SERVER     Launch the policy server with nohup and NO `timeout` wrapper. On
           2026-09-17 a `timeout 900` wrapper sent SIGTERM at 15 min and killed
           the server mid-trial; srv_wrap.py catches SIGINT/SIGSTKFLT but not
           SIGTERM. The stable earlier runs used plain nohup. (Separately, the
           box intermittently kills long GPU processes with signal 16 / exit 144;
           srv_wrap.py ignores signal 16. Root cause of the 16-killer unknown -
           needs auditd on kiran-AI90 or a reboot; resource tests ruled out
           memory, oomd, and GPU/CPU limits.)
LIGHTING   NOT a known factor. On 2026-09-17 a 0/4 batch was blamed on "dimmer
           light"; measured frame brightness was essentially identical to the
           morning's 5/10 (wrist ~156-161 both times). Do not chase lighting
           without measuring it first. The real confound that day was orange
           POSITION (all four at bottom-left).
GRIPPER    THE GRIPPER TRACE CANNOT SCORE THE TASK. A gentle release and a failed
           release are identical in the numbers. The camera decides.
FRAMES     Verify frames against the source before analysing them. A cp bug once
           nested today's frames under August's and an analysis ran on the wrong
           day's pictures.
DETECTION  Require ROUNDNESS and a saturation floor. Wood grain has outscored the
           fruit. And find the PLATE by position, not size or shape: the robot
           arm is the same colour and sometimes the larger blob.
SHARPNESS  Laplacian variance measures EDGES IN THE SCENE, not focus. Never
           compare it across frames of different content.
MACHINE    The GPU box also runs the DYNUS flight campaign. EXIT=143 with a clean
           log is systemd-oomd, not a bug. Flights are the priority.
PREMISE    Test the premise before building the fix. Offline first, always, when
           an offline test exists - the JPEG question was settled in two minutes
           without touching the arm.
```

---

## Open questions, honestly labelled

```text
How often does it work?
  ONE trial. Step 1 answers this. Everything else waits on it.

Is 12,000 steps overfitted?
  UNKNOWN and unmeasurable offline - all 30 episodes were trained on, by
  operator decision, so no hold-out exists. Five fresh episodes recorded later
  would serve as a retrospective hold-out for all four checkpoints.

Would mixing the old 79+20 demos back in help?
  NEVER TESTED. The argument for replay weakened once the old camera was gone:
  it protects a skill that can no longer be exercised. Worth trying only if the
  30-episode model plateaus.

Was Brain B really worse, or just less tempo-tolerant?
  UNRESOLVED since 2026-08-21. Three RTC runs would answer it. Lower priority now
  that a working model exists.

Would full fine-tuning help?
  NEVER TESTED. The vision encoder is frozen. Unfreezing needs more memory than
  the card has spare, and 30 episodes is very thin for 1.87 B parameters.

Why does the Pune site drop off the network so often?
  Both machines vanish together, pointing at the site network. Roughly one third
  availability. Still costs more time than any technical problem here.
```

---

## Related documents

```text
MODELS.md              the model registry - authoritative on what exists
MACHINES.md            which machine holds what, and how to reach it
EPISODE_TRIMMING.md    the trimming rule and the front-camera scoring
scripts/bench/         the bench scripts, and which ones move the arm
```
