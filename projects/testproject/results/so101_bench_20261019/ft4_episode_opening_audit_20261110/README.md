# FT4 episode-opening and training-mixture audit

Date: 2026-11-10  
Scope: all 35 visually accepted demonstrations and the exact FT4 training configuration

## Correction to the earlier assessment

The 35 episodes **are valid, good demonstrations of the complete tasks**. The synchronized review correctly found
centred grasps, retained lifts, controlled transport and tray release. The new physical and replay failures do not
invalidate that review.

The earlier review did not test four different deployment-alignment questions: what action labels appear during the
opening seconds, how closely the starting state matches deployment, whether the training and deployment task strings
match exactly, and how much of the dataset training actually processed. Calling the episodes simply “good enough”
without those qualifications was incomplete.

## Measured findings

### 1. Every orange demonstration contains a stationary or preparatory prefix

Across the 30 accepted orange episodes:

- first noticeable arm motion: **1.60–4.40 s**, median **2.18 s**;
- first purposeful shoulder/elbow reach: **2.40–6.87 s**, median **3.35 s**;
- demonstrations reaching within two seconds: **0/30**.

The 29-episode training split contains **3,156 pre-reach frames out of 30,376 frames (10.4%)**. Those frames show a
start-like image/state paired with small or stationary actions. PI05 uses one observation step and receives no
elapsed-episode-time input. It therefore cannot distinguish “wait at the beginning” from “the same-looking frame,
but now begin reaching” using time context.

This matches the frozen policy replay: all 70 replays of seven deployed chunk-1 observations predicted no immediate
reach, while an identical later T3 transition observation produced a reach in only 5/10 samples. The training labels
and deployed stochastic behavior are consistent with the same idle-versus-reach ambiguity.

### 2. The demonstrated and deployed starts are both functional rest poses

Compared with the deployed start `[-5, -104, 97, 78, -2, 65]`:

- median five-arm-joint MAE: **1.73°**;
- median largest single-joint error: **5.69°**;
- all five arm joints within a strict post-hoc 2° threshold: **2/30 episodes**;
- demonstration start gripper at least 64°: **5/30 episodes**;
- deployed trials normally start near 65°.

Most of the numerical difference is wrist-roll or shoulder-pan variation. All episodes visibly and functionally
start at rest. The strict all-five-joints threshold was not a collection requirement and must not be used to reject
episodes or claim that only two have a valid start pose.

### 3. The correction demonstrations and earlier physical trials used different task strings

- FT4 orange demonstrations: `pick up the orange and place it on the plate`
- Physical FT4 trials: `Grab oranges and place into plate.`

PI05 can generalize across paraphrases, so this mismatch is not proven to be the sole cause. However, the new
centering/recovery supervision was attached to the first string, while deployment requested the second. For a small
corrective LoRA dataset, this is an avoidable source of transfer uncertainty.

The user selected the original recording sentence for future training and deployment:
`pick up the orange and place it on the plate`.

### 4. Training did not complete one full effective pass over the new dataset

- accepted demonstrations: **35**;
- actual training episodes: **29** (25 orange, 4 matchbox);
- validation-only episodes: **6** (5 orange, 1 matchbox);
- training frames: **30,376**;
- samples processed: **24,000**;
- effective exposure: **0.7901 epoch**.

There were no explicit phase or source weights. Natural episode sampling gave orange 25/29 and matchbox 4/29. The
run improved held-out action MAE, so it learned from the data, but it stopped before one full effective epoch and did
not specifically emphasize start-to-reach or close-to-lift frames.

## Conclusion

The episodes passed the acceptance criteria they were designed for. The weak physical result comes from the
**training representation and exposure**, not from discovering that the centred grasps were visually bad.

The strongest measured explanation for no-engagement is that the dataset explicitly contains several seconds of
start-like frames with small actions, while the policy has no time context and samples stochastically. Limited
training exposure, task-text mismatch and incomplete exact-start coverage make the corrective behavior weaker.

## Recommended reuse of the existing episodes

Do not discard or rerecord all 35 episodes. Build a revised derived dataset from them:

1. Trim the stationary opening prefix so the first start-like observations are paired with purposeful reach actions.
2. Preserve the exact recorded orange sentence and use it unchanged during deployment.
3. Upweight start-to-reach, centring, correction and retained-lift windows while retaining complete episodes for
   transport and release.
4. Train for multiple effective passes, with checkpoints selected by frozen start-observation replay as well as
   held-out action error.
5. Require high immediate-reach frequency on the saved deployment starts before another physical trial.

Only if that revised run still fails the frozen replay should we record a small additional set at the exact deployed
start pose. The current evidence does not justify rerecording the full collection.

## Artifacts

- `audit.json`: per-episode opening, start-pose and split measurements.
- `audit_openings.py`: reproducible parquet audit.
- `../ft4_initial_observation_replay_20261110/`: exact saved-observation replay evidence.
