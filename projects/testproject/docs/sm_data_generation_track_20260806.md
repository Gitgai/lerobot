# Data-generation track: state machine + variations → diverse episodes → fine-tune Pi0.5

Date: 2026-08-06. Status: **EXECUTING — generator BUILT, smoke test in
flight, overnight batches staged.** (Sections 2-4 preserve the investigation;
the tinted-paradox warning in section 3 was resolved by the control in 4b,
and 4b itself now carries a correction — read 4d.)

## 1. The user's proposal, and why it is sound

```text
Run the scripted state machine under all the scene variations. If it still
works, mass-record demonstration episodes across them - a DIVERSE dataset,
generated with no teleop and no hardware - and fine-tune Pi0.5 on it.
```

Three properties make this attractive:

```text
1. THE SM IS VISION-BLIND. Verified in code: get_action reads
   env.scene["Orange00N"].data.root_pos_w and Plate LIVE each step
   (pick_orange.py). Appearance variations cost the DEMONSTRATIONS nothing
   while enriching every recorded camera frame - textbook domain
   randomization with a demonstrator that cannot be fooled.
2. DECOY SCENES BECOME TRAINING SIGNAL. The SM ignores decoys (GT-driven);
   demos recorded with them present teach "the REAL orange despite
   lookalikes" - exactly the fragility the N1.6 evaluation exposed.
3. PI0.5 CLOSES THE 2x2. Pi05 failed even in-domain on the real arm, and we
   never separated architecture from data. Fine-tuned on clean verified sim
   data: success exonerates the architecture and indicts our 89 real
   episodes; failure (where GR00T succeeded on comparable data) convicts the
   architecture. Either answer is one Pi05's failures never gave us.
   PRACTICAL BONUS: isaaclab2lerobotv3.py converts straight to v3.0 - exactly
   what Pi05's training-era LeRobot speaks. No format pain (GR00T needed v2 +
   3 extra meta files + an AV1 transcode).
```

## 2. The variation battery (n=1 per condition — see section 3 before believing)

```text
run        placed  lifts                 (canonical reference: 3/3, n=1)
moved       1/3    [0.00, 0.00, 0.19]
scatter     1/3    [0.07, 0.00, 0.17]
plate10     2/3    [0.16, 0.18, 0.19]
decoys      0/3    [0.00, 0.00, 0.19]
smallOrng   HUNG at boot (transient - the eval battery ran the same flag fine;
            bigOrng used the same mechanism minutes later and ran)
bigOrng     1/3    [0.16, 0.00, 0.22]
tinted      1/3    [0.16, 0.00, 0.20]   <- THE PARADOX
combo       2/3    [0.00, 0.04, 0.20]
```

Taken at face value: the scripted SM under variation scores WORSE than the
neural policy did on the same scenes (N1.6: 2/3-3/3). Do not take it at face
value yet:

## 3. *** THE TINTED PARADOX — this battery is CONFOUNDED ***

```text
`tinted` is APPEARANCE-ONLY (blue plate + half light). The SM never reads
pixels. A variation the actor cannot perceive CANNOT degrade it - yet tinted
scored 1/3. Therefore something else drags these runs down, and the prime
suspect is the SM's OWN RUN-TO-RUN VARIANCE:
  - physics contact is not deterministic run to run
  - the env RANDOMIZES object layouts per reset by itself (visible in the
    snapshots: canonical and tinted show different orange arrangements)
  - the canonical 3/3 was n=1 - possibly a lucky draw

THE CONTROL NOW RUNNING: 3x canonical re-runs (scripts/sm_baseline_variance.sh).
  baseline ~3/3  -> variations genuinely hurt the SM (its choreography is
                    scene-tuned even though it reads live poses)
  baseline ~1-2/3 -> the SM is simply UNRELIABLE at n=1 and the "variation
                    degradation" above is mostly noise; a usable envelope
                    needs per-condition success RATES, not single runs.

DESIGN RULE, learned now for the THIRD time (N1.6 "stochastic" at n=2, then
100% at n=5; N1.6 "never places" at 900 steps; now this):
*** ONE RUN PER CONDITION IS AN ANECDOTE. Contact-rich sim runs get n>=3. ***
```

## 4. Reference snapshots (user request)

`logs/sm_variations/snapshots/` — 36 PNGs, front+wrist at steps 30/60 for all
nine scenes including canonical; the POLICY'S-EYE 640x480 view, regenerable via
`scripts/sm_variation_snapshots.sh`. Verified: tint/dim/decoys/scales all
clearly visible in-frame.

**Bonus finding from the images:** the decoy spheres render pale YELLOW, not
orange — and they still cratered the neural policy (1/3). Even stronger
evidence that N1.6 keys on saturated-blob structure, not hue.

## 4b. THE CONTROL CAME BACK — the demonstrator is the variable, not the scenes

```text
canonical scene, no variations, 3 fresh runs:   1/3, 2/3, 2/3
all nine lifts healthy (0.16-0.22)              <- grasping is RELIABLE
placement is what fails                          <- the PLACE phase is fragile

VERDICTS
1. Yesterday's canonical 3/3 was a lucky n=1. The SM's real rate is ~56% of
   oranges per run on its OWN scene.
2. The entire variation table (1/3-2/3) is WITHIN the control's own range.
   NO variation - geometry included - shows a clear effect beyond SM variance.
   Even decoys' 0/3 is at most marginal. My earlier "the SM is scene-tuned,
   geometry must move to Mimic" call was premature; the data say the SM is
   equally shaky EVERYWHERE, canonical included.
3. Ironic and worth saying: the NEURAL POLICY out-places the scripted
   demonstrator (N1.6: 3/3 in 6 of 7 full-length runs; SM: 1-2/3 typical).
```

### Consequence: the SHAKY-BASELINE branch of the decision tree fires

Success-filtered generation. `generate.py` already supports
`EXPORT_SUCCEEDED_ONLY` — record until N episodes SUCCEED, keep only those.
This is exactly how the project's original 4 episodes / 12 place operations
were made, so the mechanism is proven. A ~50-60% demonstrator costs ~2x
generation time and zero data quality. **All variation types stay usable,
geometry included** — the filter, not the demonstrator, guarantees the corpus.

## 4c. Snapshot addendum (user request: arm + room color)

```text
greenArm   WORKS - arm cleanly recolored, oranges/plate untouched
warmRoom / coolRoom / dimRoom(0.25)   WEAK - the kitchen's DOME light
           dominates the frame and largely ignores inputs:intensity/color on
           the other lights. Light-based "room color" is not an effective knob
           in THIS scene. Practical room-appearance proxies that DO work:
           entity tints on large surfaces (the table would be the big one) or
           swapping the dome texture. Note for the generation recipe.

FURNITURE TINTING (user question, answered empirically 2026-08-06):
  The kitchen exposes 44 INDIVIDUALLY TINTABLE furniture prims under
  /Root/Scene: walls, floor, two counters, seven cabinets, fridge, stove,
  sink, microwave, dishwasher, four dish stacks, outlets, switches.
  *** counter_main_main_group IS THE WORK SURFACE *** - tinting it recolors
  ~80% of the front camera's frame, which makes it THE room-appearance lever
  the lights could not provide. Verified: snap_furniture_front_step30.png
  (bright blue surface, arm/oranges/plate untouched).
  Generation recipe: randomize counter_main_main_group + wall_room + a couple
  of cabinets per batch; skip light-color entirely.
```

## 4d. CORRECTION to 4b — the control harness HANDICAPPED the demonstrator

```text
Found while replicating generate.py line-by-line for the generator (2026-08-06):

  sm.setup(env)     generate.py calls it BEFORE the loop - FK calibration that
                    records the rest-pose EE target used by the return-home
                    phase and task_done(). The positive-control script NEVER
                    CALLED IT, so _rest_joint_pos/_rest_ee_pos_world were None
                    in every PC run - including the variance control.
  gravity disable   generate.py turns gravity OFF on every robot link prim.
                    The PC script left it on.

=> The "~56% per-orange, everywhere" verdict of 4b was measured on a state
   machine MISSING ITS CALIBRATION STEP under different physics. It is an
   overstatement of the demonstrator's weakness. What SURVIVES from 4b:
   variations still show no effect beyond the (mismeasured) baseline, and
   success filtering remains the right design regardless of the true rate.
   The TRUE pipeline rate gets measured tonight for free - every generation
   episode logs SUCCESS/failed with a running rate.

META: this is the second time in one day a harness deviation quietly became a
"finding" (the tinted paradox exposed the first). The generation wrapper is a
FAITHFUL replica precisely because of this: when reusing someone's actor,
replicate their WHOLE pipeline, not just the loop that looks important.
```

## 4e. "Should we re-test N1.6 under variations first?" — asked and answered

```text
NO - not before generating. N1.6 plays no role in the generation pipeline;
the demonstrator is the SM and it is measured. The n=1 N1.6 variation numbers
are only load-bearing where they sit FAR outside the n=12 baseline (decoys
1/3, gamma 0/3 vs 94% - both effectively certain); the mild 2/3 results decide
nothing. Tight per-condition N1.6 rates become useful exactly ONCE: as the
comparison baseline after the Pi0.5 fine-tune exists. Run that head-to-head
(both models, same seeds, n>=3, canonical + decoys + geometry) ONE time, then.
```

## 5. Decision tree (pre-agreed) — RESOLVED: the shaky-baseline branch fired

```text
CONTROL SAYS BASELINE IS SOLID (~3/3):
  the SM really is scene-tuned -> geometry diversity comes from Isaac Lab
  MIMIC (its whole purpose: adapt demo trajectories to new object poses);
  the SM generates APPEARANCE-varied episodes only (tints, lighting) - which
  the control will have shown it survives.

CONTROL SAYS BASELINE IS SHAKY (~1-2/3):
  measure per-condition RATES (n>=3) before trusting the SM as a bulk
  generator at all; consider generating with the recorder's
  EXPORT_SUCCEEDED_ONLY so only completed episodes enter the dataset - a
  shaky demonstrator + success filtering can still yield a clean corpus,
  just at a slower rate.

EITHER WAY the fine-tune target stays Pi0.5 on v3.0 sim episodes, and the
memory question from the GR00T attempt (26 GB floor on a 32 GB card) must be
re-checked for Pi05's 4.14B before promising a training run.
```


---

## 6. THE EXECUTABLE RECIPE (final — everything below is verified)

### 6.1 What still has to be BUILT (one item)

```text
scripts/sm_generate_varied.py - a generation wrapper.  *** BUILT 2026-08-06,
smoke test in flight (tinted counter, 1 success or 3 attempts). Batch driver
scripts/sm_generate_batches.sh staged: 8 looks x 6 successes, 15-attempt cap,
HDF5s to ~/sim/leisaac-src/datasets/varied/ (outside git). ***
LeIsaac's generate.py does the recording (state machine + recorder + success
gating) but has NO variation flags; our variation code lives in the eval/PC
scripts but does not record. The wrapper reuses generate.py's loop (it is
~300 readable lines) and adds the variation args. Cfg-side variations
(moves/scatter/scale/decoys) apply before gym.make; tints apply to the stage
after. ~1 hour of work. LOCAL PATCHES TO LEISAAC ARE NOT NEEDED.
```

### 6.2 The batch matrix (each batch = one look; sample fresh colors per batch)

```text
batch 1  canonical                                (anchor - never skip it)
batch 2  counter tint A + wall tint
batch 3  counter tint B + 2 cabinet tints
batch 4  plate tint + counter tint C
batch 5  green/other arm tint + counter tint D
batch 6  decoys x2 (the anti-decoy signal batch)
batch 7  orange scale 0.8 + counter tint E
batch 8  geometry: moved/scattered oranges + moved plate + counter tint F
DROPPED: light-color/intensity (dome-dominated, does nothing - proven)
KEY LEVER: counter_main_main_group recolors ~80% of the front frame.
```

### 6.3 Success filtering — the honest throughput math

```text
The env's own success term is ALL THREE oranges placed + arm at rest. The
control says the SM full-episode rate is LOW (0 of 3 control runs completed
3/3; the lucky first run did). Two options:

A. STRICT: generate.py --record with EXPORT_SUCCEEDED_ONLY.
   Proven mechanism (made the original 12 place ops), zero curation, but
   expect roughly 2-5 kept episodes per hour. Overnight runs.
B. POST-FILTER (recommended): record EXPORT_ALL, then keep episodes by OUR
   GT criterion (e.g. >=2 oranges placed, or slice per-orange successful
   pick-and-place segments). More kept data per sim-hour, criterion is ours
   to tune, and the scorer for it already exists. Costs disk (day-1 HDF5s ran
   ~2 GB/episode raw - budget accordingly, and NEVER commit them).

Either way the DEMONSTRATIONS kept are clean; the filter, not the SM's ~56%
per-orange rate, guarantees corpus quality.
```

### 6.4 Convert and train

```text
1. HDF5 -> LeRobot v3.0 via LeIsaac scripts/convert/isaaclab2lerobotv3.py
   (v3 converter; check its pins - the v2 converter wanted lerobot 0.3.3, the
   v3 one must be checked the same way before building any venv for it).
2. Fine-tune Pi0.5 ON TRAINING-ERA CODE (lerobot_trainingera venv, 0.6.1) -
   Era 1 applies to training as much as serving.
   OPEN CHECK before promising a run: does a 4.14B fine-tune fit in 32 GB?
   The GR00T attempt taught the arithmetic (weights+grads+Adam); do the same
   audit for Pi05's trainable set FIRST, and expect to need 8-bit Adam.
3. Score in sim at 3,000 steps, n>=3 (the rules of this project), against BOTH
   baselines: Pi05 012000 (0 grasps ever) and sim-N1.6 (~94% oranges).
   SUCCESS = any real grasp (lift >0.10 m). That alone closes the
   architecture-vs-data question, because 012000 has never grasped anywhere.
```

### 6.5 Standing constraints

```text
- hardware test PREEMPTS this track the moment the arm is plugged in
- artifacts (HDF5, videos, PNGs, datasets) NEVER go to git; scripts/docs only
- n>=3 for any number anyone will quote; report drops alongside successes
```
