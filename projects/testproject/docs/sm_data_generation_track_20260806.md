# Data-generation track: state machine + variations → diverse episodes → fine-tune Pi0.5

Date: 2026-08-06. Status: **variation battery DONE (n=1/condition, confounded);
canonical variance control RUNNING — read section 3 before quoting any number
from section 2.**

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

## 5. What happens next (decision tree, pre-agreed)

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
