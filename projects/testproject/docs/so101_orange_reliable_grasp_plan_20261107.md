# SO-101 orange-to-tray reliability plan

Date: 2026-11-07
Status: active; fine-tune 4 close-window diagnosis complete; camera restoration and retained-lift verification next
Primary baseline: fine-tune 3, `row3_all169_conservative_010000`
First candidate: fine-tune 4 checkpoint 2,000
Primary diagnostic: [`../results/so101_bench_20261019/ROW_AH_OFFLINE_DIAGNOSIS.md`](../results/so101_bench_20261019/ROW_AH_OFFLINE_DIAGNOSIS.md)
Auto-reset status: paused; manual orange placement is used during this plan

## 1. Objective

Make the SO-101 reliably complete one narrowly defined task:

```text
orange starts on the table
    -> reach and centre the open gripper
    -> close around the orange
    -> lift while retaining it
    -> carry it to the fixed tray
    -> release it inside the tray
    -> finish safely
```

The development target is at least **45 successes in 50 trials (90%)**. After that target is met, the release
target is at least **90 successes in a fresh 100-trial blind evaluation**, with the Wilson confidence interval and
stage-specific failure counts reported. A 200-trial blind evaluation may be used later for a tighter confidence
interval.

The current heterogeneous fine-tune 3 orange record after five controlled Phase B repetitions and three exploratory
10-action trials is **15/57 (26.3%)**.
Before Phase B it was 14/49. Row AH was **0/6**; all six trials failed
while acquiring the orange. The immediate objective is therefore repeatable acquisition, not more unstructured
end-to-end trials.

### 2026-11-07 execution update

Two action-horizon diagnostics were run after this plan was drafted:

- A five-action-only diagnostic repeatedly replayed the policy's near-start prefix and was stopped at chunk 98. It
  is recorded as void and does not change the success rate.
- AI1 used 20 actions for coarse motion, five actions near the fruit, then 20 actions for recovery. It failed
  acquisition and is counted in the 14/49 record. The shorter horizon produced smaller corrections but did not
  create a secure close.

Offline comparison found AI1's fruit centre near `(335,344)` in the 640×480 wrist frame, below the effective contact
band seen in successful closes. A read-only circle-and-depth prototype calibrated on five successful and seven
failed reviewed frames produced 5/5 eligible positives and blocked or returned unknown for 7/7 negatives. These are
calibration results only. The detector, labels and report are in
`results/so101_bench_20261019/preclose_diagnostic_20261107/`. Phase A physical-baseline checks and held-out Phase C
validation remain incomplete, so the detector must not control actions yet.

An empty-workspace A1 capture was made on 2026-11-07 after removing the orange and tray. Camera freshness, motor
communications, torque-off state, voltage, temperature and calibration identity passed. The gripper was visibly
separated in the top view, but the fixed wrist angle showed only one marked tip clearly, and still images cannot
prove mount rigidity.
The check is recorded in `results/so101_bench_20261019/empty_workspace_check_20261107/`. The open fingers and both
black marks were subsequently confirmed, but the front view retained an approximately 1-2 pixel horizontal and
2-pixel vertical displacement after a light mount/cable check. That is material relative to the 3-5-pixel visual
tolerances. The unpowered arm also drifted, making the wrist-mount comparison inconclusive. A1 therefore fails
until the front mount is secured and a repeat check passes.

The first secured-mount retest was initially stable below 0.01 pixel between consecutive frames, but a second light
touch produced a persistent 3.7-4.1 pixel horizontal translation with strong registration confidence. Tightening
the existing attachment did not solve the compliance. The camera head/hinge and cable need rigid restraint plus
strain relief; no physical trial or transferred pixel target is valid until a repeated touch test passes.

The second repair restrained both the camera head/hinge and cable. Its repeated light-touch test moved the whole
front view about `[-0.21,+1.01]` pixels; independent table regions peaked at 1.52 pixels. The view then remained
stable to 0.007 pixel. The settled post-touch frame is accepted as the new front reference. Phase A1 still requires
the wrist-camera mount check before completion.

The wrist check then held every raw motor position exactly constant across the light-touch test. The whole wrist
image moved about `[+0.07,+1.10]` pixels; the table and two fingertip regions agreed, and a later frame was stable to
0.08 pixel. The settled post-touch wrist frame is accepted. Phase A1 is complete; Phase A2 offline path construction
and envelope verification is next. No robot movement was issued during A1.

Phase A2 then restored the U1 start target with no policy connection. The initial path used 11 waypoints, stayed
inside the demonstration envelope, moved no arm joint by more than 0.29 degrees per step, and had 5.31 mm modeled
Cartesian displacement with 1.92 mm relative descent. Three returns reached the identical measured pose
`[-7.8242,-104.0000,96.7473,78.1538,-1.2747,51.3329]`; maximum arm error was 0.146 degrees and gripper error 0.033.
Final health was normal and torque-off was independently verified. Evidence is in
`results/so101_bench_20261019/u1_start_restore_20261107/`. Phase A3 scene restoration is next.

Phase A3 then froze the operator-selected current tray position rather than moving the tray to the historical U1
position. The current top frame registered to U1 with 140 inliers and 0.53-pixel median reprojection error. The
transferred U1 orange centre was `(570.65,329.55)` in the current 640x480 view; the operator left the orange slightly
below that cross and asked to continue without further adjustment. This accepted physical scene, camera controls,
registration, overlays and start-pose checks are under
`results/so101_bench_20261019/phase_a3_scene_20261107/`. It is a controlled repeatability scene, but its orange
placement must not be described as an exact reproduction of U1.

The three Phase B repetitions used that unchanged scene. B1 failed acquisition: it idled through chunk 28,
made two close attempts, reached a minimum sent gripper target of 4.8, and left the orange on the table. B2 began
reaching immediately, acquired and lifted the same orange by chunk 46, released it inside the tray by chunk 56 and
returned to the recorded start. B2 had one gripper-delta clamp at chunk 43; the clamp limited a predicted close from
12.88 to 17.19 and the subsequent grasp still succeeded. B3 reached quickly but made three closes with the orange
outside the left finger; the orange never moved or lifted. B3 had zero clamps. Phase B is therefore **1/3
acquisition and 1/3 end-to-end**. Decision B is now fixed: restoring geometry is insufficient. Stop blind policy
trials and proceed to the read-only Phase C diagnostic and corrective-data work.

At the operator's request, two additional unchanged repetitions were subsequently run as B4 and B5. Both failed
acquisition with the orange outside the left finger, making the controlled result **1/5 acquisition and 1/5
end-to-end**. These extensions strengthen the stop decision; they do not reopen Decision B.

On 2026-11-08, three operator-requested trials executed exactly 10 actions per request for the entire episode, with
no adaptive 3-5-action mode. The cap was increased from 75 to 150 requests to preserve the same 1,500-action
maximum. All three failed acquisition: the orange remained outside the left finger during the initial approach and
later closes were empty. The second run's prolonged search accumulated approximately 116 degrees of measured wrist
roll before the cap, despite zero client delta clamps. H10-3 repeated the same lateral miss, made empty closes down
to a 3.25 sent gripper target, and returned to start after 150 requests. All scripted returns passed. The
camera geometry had shifted and the orange placement changed between the two trials, so these are exploratory
results rather than a controlled 10-versus-20 comparison. Ten actions alone did not solve alignment, and a
150-request cap should not be reused without an absolute joint envelope and an earlier acquisition timeout. The
fine-tune 3 controlled-orange total is now **15/57 (26.3%)**.

## 2. What this plan is and is not

This plan improves the policy task. It is separate from the scripted auto-reset system.

| Workstream | Purpose | Decision for this plan |
|---|---|---|
| Policy reliability | Make orange-to-tray succeed | Active priority |
| Measurement and trace capture | Explain each failure stage | Active priority |
| Pre-close visual check | Detect a bad grasp pose before closing | Build read-only first, then gate only after validation |
| Corrective demonstrations and fine-tuning | Teach centred approaches and recovery | Conditional on the controlled diagnosis, expected to be required |
| Scripted auto-reset | Move the orange from tray to table between trials | Paused; it does not repair grasp acquisition |
| Other objects and multi-object selection | Tomato, capsicum, pen, selection | Deferred until orange-to-tray is reliable |

Auto-reset will be reconsidered after the policy passes the 50-trial development test. Until then, a person places
the orange on marked positions and confirms that hands are clear before motion.

## 3. Evidence we are acting on

The plan follows the measured Row AH results rather than assuming a single fixed offset:

1. The five selected successful trials started near
   `[-6.7, -104.6, 96.6, 78.5, -3.8, 51.8]` on average. Row AH started near
   `[2.2, -100.5, 96.7, 76.4, -4.1, 42.9]`. The largest shifts were shoulder pan and gripper state.
2. Successful pre-close wrist images had the orange within approximately 0-6 pixels of the reviewed jaw-corridor
   centre. Four AH trials missed far to the left, one missed to the right, and AH5 was laterally centred but too
   shallow/far for contact.
3. Only one of 9,000 AH action sends was clamped, and it was unrelated to acquisition. Action clamping is not the
   primary cause.
4. Motor tracking was broadly comparable with successful U1. A gross motor failure is unlikely, but finger height,
   parallelism, backlash and camera rigidity still need a physical check.
5. The error changed sign and depth. A fixed blind wrist offset is therefore not justified.

These observations imply that a useful pre-close check needs at least lateral alignment **and** a depth/contact
signal. It must tolerate normal variation and must not depend on reproducing one exact pixel coordinate.

## 4. Fixed trial definition

All development comparisons use the same protocol unless a row is explicitly labelled as an ablation.

```text
object                  one orange
instruction             unchanged from the fine-tune 3 orange protocol
receptacle              the normal tray, fixed to its marked outline
policy                   one named checkpoint per row
action execution         20 actions per requested chunk at 30 Hz
trial cap                75 chunks
transport                JPEG quality 85, no RTC for the first controlled baseline
return to start          scripted after the trial; it is not counted as policy success
reset                    manual orange placement; auto-reset disabled
recording                front and wrist policy inputs, measured state, predicted and sent actions,
                         clamping, request latency, camera freshness, trial/chunk number and start/end images
```

The first controlled row keeps JPEG/no-RTC because successful U1 used that path and changing transport at the same
time would confound the diagnosis. RTC and alternative action horizons are later ablations, after acquisition is
repeatable.

### Outcome labels

Every trial receives one terminal result and one failure stage:

| Stage | Success condition | Typical failure |
|---|---|---|
| Acquisition | Orange enclosed and visibly follows the first lift | Close beside it, push, hover, shallow close |
| Retention | Orange remains held through lift and initial turn | Slip or drop after lift |
| Transport | Held orange reaches the tray area | Wrong-direction carry, collision, drop |
| Release | Orange is released and remains inside tray | No release, rim hit, release outside |
| Completion | Arm finishes without fault and trial closes at cap | Fault, stale camera, unsafe stop |

End-to-end success requires all five stages. Acquisition success is also reported separately because it is the
current bottleneck.

## 5. Phase A — freeze and document the physical baseline

**Purpose:** remove avoidable geometry changes before judging the policy.

### A1. Empty-workspace check

With no fruit, tray or hands in the arm's swept volume:

- capture fresh front and wrist images;
- inspect that both finger tips, including their black marks, are visible and at comparable height;
- check finger parallelism, opening symmetry and gripper zero/open readings;
- check that the wrist and overhead/front camera mounts do not move under light cable motion;
- inspect cable routing and confirm it cannot pull the wrist during a reach;
- read motor status, temperature, voltage, torque state and calibration identity;
- save the images and readings in the run directory.

If a finger is bent, loose, vertically offset, or the camera moves, stop here and repair it. Policy experiments are
invalid until a second empty-workspace check passes.

### A2. Restore one known successful start

The first candidate is U1's recorded start:

```text
[-7.8, -104.0, 96.7, 78.3, -1.3, 51.3]
```

This pose is a reference, not an instruction to move blindly. First interpolate it offline, verify every waypoint
against the existing motion envelope, then run an empty-workspace clearance test with slow bounded motion. Record
the achieved joint state rather than assuming the commanded target was reached.

Acceptance:

- no contact or near-contact with the table, tray or base;
- no motor fault;
- achieved arm joints within 1 degree of the recorded target and gripper within 2 units;
- three returns reach the same state within those tolerances.

If it cannot be restored safely or repeatably, select another documented successful start and record the reason.

### A3. Fix the scene

- keep the tray on its marked outline;
- lock or mark every camera mount;
- capture a reference image and record resolution, exposure/brightness and camera device identifiers;
- register the current front image to a successful reference before transferring an old orange location;
- create three physical placement marks: centre of the successful cluster plus two nearby offsets inside the
  demonstrated area.

Raw historical pixel coordinates must not be copied after a camera move. The registered overlay defines the
current physical marks.

**Phase A output:** a baseline manifest containing checkpoint, client commit, start pose, camera IDs/settings,
tray reference, placement marks, transport settings and safety readings.

## 6. Phase B — controlled reproduction experiment

**Purpose:** determine whether the main failure is the changed physical/input distribution or an unstable policy
even under restored conditions.

Run three trials from the same verified start and the central registered placement. Before every trial:

1. place the orange on the mark;
2. confirm the tray and cameras match the reference;
3. confirm the measured start state is inside tolerance;
4. confirm hands are clear;
5. run the unchanged policy and capture the full trace.

Do not tune offsets between these three trials. Changing the setup after each miss would destroy the repeatability
test.

### Decision B

| Result | Interpretation | Next action |
|---|---|---|
| 3/3 acquisitions | Restored distribution is a strong factor | Run seven more identical trials, then Phase C |
| 2/3 acquisitions | Promising but unstable | Run seven more; require at least 8/10 total before broadening positions |
| 0/3 or 1/3 | Restoring geometry is insufficient | Stop blind trials; proceed to Phase C and corrective data collection |
| Mechanical/camera anomaly | Trial evidence is invalid | Repair and repeat Phase A |

Ten repetitions at one location diagnose repeatability; they are not the final generalisation score.

## 7. Phase C — build a read-only pre-close diagnostic

**Purpose:** measure whether a proposed close is spatially eligible before allowing software to alter robot
behaviour.

### C1. Trigger

For each predicted action stream, flag a candidate close when the gripper target begins a sustained movement toward
the closed direction. Save a short window before and after the trigger with:

- wrist and front image;
- measured state;
- predicted action chunk;
- sent action after client safety processing;
- orange and jaw measurements;
- eventual acquisition result.

### C2. Measurements

The diagnostic should estimate:

1. **Jaw corridor:** region between the inner edges of the two fingers near their tips.
2. **Lateral error:** orange centre minus corridor centre, preferably normalised by the measured finger gap.
3. **Depth/contact readiness:** orange apparent diameter or mask area relative to finger geometry, plus overlap or
   proximity to both inner finger edges.
4. **Visibility/confidence:** both finger marks and enough of the orange must be visible; uncertainty is not treated
   as alignment.
5. **Temporal stability:** the condition should persist for several consecutive observations rather than one noisy
   frame.

AH5 is the required negative example: it must fail the depth/contact condition even though it passes the lateral
condition. AH1-AH4 and AH6 must fail lateral alignment. O1, R2, R3, R5 and the successful U1 recovery are positive
references.

### C3. Threshold fitting

Do not hard-code the historical 0-6 pixel observation as the final threshold. Label all available positive and
negative pre-close windows, then choose thresholds from normalised measurements. Keep separate calibration and
validation sets.

Initial diagnostic acceptance criteria:

- detect at least 95% of known gross AH misses as ineligible;
- mark every selected historical successful close as eligible;
- reject AH5 based on depth/contact readiness;
- return `unknown`, not `eligible`, when visibility is inadequate;
- process a frame fast enough to run before the close without starving the 30 Hz action loop.

This phase is strictly read-only. It logs `eligible`, `ineligible` or `unknown`; it does not modify actions.

### C4. Current evidence, 2026-11-07

The fixed calibration detector was applied without retuning to six selected Phase B frames. It allowed B2 c43, the
only close that produced a stable lift and delivery, and blocked all five failed closes. One failed close was
`ineligible`; four partly visible edge cases were `unknown`, which is also blocking. The artifacts are under
`results/so101_bench_20261019/preclose_diagnostic_20261107/heldout_phase_b/`.

This is enough to proceed to shadow-mode logging, but not enough to enable an action gate. There is only one
held-out positive, the frames were selected retrospectively, and consecutive-frame reliability has not been tested.
No further blind trials should be run with the current checkpoint; the next physical data collection should produce
expert centred grasps and corrective examples while recording the detector in shadow mode.

## 8. Phase D — shadow validation, then a bounded close gate

### D1. Shadow mode

Run ten controlled trials over the three marked positions. The policy remains unchanged, while the diagnostic logs
what it would have allowed or blocked.

Enable a real gate only if:

- no successful acquisition would have been blocked;
- every gross outside-the-jaws close is flagged;
- shallow/far closes such as AH5 are flagged;
- camera uncertainty produces `unknown` and a recorded reason;
- the added processing does not cause stale frames or destabilise execution.

### D2. Gate version 1: hold and re-observe

When the policy proposes a close:

```text
eligible   -> permit the close
ineligible -> keep the gripper open, hold the arm briefly, request a fresh observation
unknown    -> hold and request a fresh observation; abort safely if uncertainty persists
```

Version 1 does not invent a Cartesian correction. It gives the policy a fresh observation and a chance to re-plan.
Allow at most two blocked close attempts. If no eligible pose appears, retreat to the start state and mark the trial
as an acquisition failure. This prevents a long search from being mistaken for recovery.

### D3. Gate version 2: correction, only if separately proven

If hold-and-replan cannot recover, a small visual correction may be added. It requires its own empty-workspace
clearance tests, bounded correction envelope, dry run and watched trials. The correction must preserve wrist
orientation and use both lateral and depth error. A fixed blind offset is prohibited by the AH evidence.

Gate success criteria over 20 development trials:

- zero collisions and faults;
- acquisition improves relative to the unchanged-policy control row;
- the gate never converts an eligible successful close into a failure;
- every intervention and retry is logged;
- results are reported both with and without recovery credit.

If the gate does not improve acquisition, remove it from the active client and continue with training data rather
than accumulating wrapper complexity.

## 9. Phase E — collect corrective and balanced demonstrations

### 2026-11-08 data decision

Fine-tune 3 already contains the earlier 30-episode `esp_recovery` / `recovery30_v21` batch. Those demonstrations
successfully taught the arm to descend and correct from an off-target reach, but the subsequent evaluation showed a
new bottleneck: precise initial contact and early grasp. Recording another generic recovery batch would repeat data
that the current checkpoint has already seen.

The next dataset is therefore `orange_grasp_corrective_ft4_20261108`. Begin with a five-episode pilot, review every
episode, and continue to 30 accepted episodes only if the pilot has the required camera views and grasp sequence.
The 30 accepted episodes are balanced as follows:

| Demonstration type | Accepted episodes | Required behavior |
|---|---:|---|
| Direct centred grasp | 15 | Approach open, place both fingers around the orange, close bilaterally, lift 3-5 cm, hold, then deliver |
| Lateral correction | 10 | Five safe left-side and five safe right-side misalignments; stop open, re-centre, then close and lift |
| Depth correction | 5 | Begin slightly shallow/far, advance while open until contact depth is clear, then close and lift |

Use five marked positions with six accepted episodes per position. Position order and demonstration type must be
written before each recording. Rejected attempts remain on disk and in the manifest with the rejection reason; they
are excluded from training rather than deleted.

After the 30-episode acquisition-focused batch passes audit, expand toward the longer-term target only if physical
evaluation shows remaining coverage gaps. The expected eventual target remains:

- approximately **200 clean expert demonstrations**;
- **50-100 corrective/recovery demonstrations** covering the observed acquisition errors.

These are new training trajectories, not failed autonomous traces relabelled as expert actions.

### E1. Balance

Split clean demonstrations across:

- the three initial marks and additional positions spanning the central demonstrated region;
- near/far and left/right approach errors;
- small start-state variation inside a documented safe cluster;
- normal lighting variation that the deployed cameras actually experience;
- direct successes and recoveries from a deliberately imperfect but safe approach.

Do not mix tomato, capsicum, pen or multi-object selection into this checkpoint. First solve one object, one
instruction and one receptacle.

### E2. Demonstration quality

Accept a clean demonstration only when it contains:

```text
orange visible in the policy cameras
open gripper approaches with both fingers around it
centred close with contact on both sides
visible lift and retention
controlled carry to the tray
release inside the tray
clean completion without hand occlusion or camera disturbance
```

Corrective demonstrations must show the observation of an error and the action that fixes it, for example:

- stop before an outside-jaw close;
- reopen after weak contact;
- re-centre laterally;
- advance to contact depth;
- close, verify lift, and retry once if the orange does not follow.

### E3. Trace reuse

Existing successful and failed policy traces are useful for:

- detector/guard training and validation;
- mining hard starting states and placements;
- measuring prediction versus execution;
- selecting what corrective demonstrations to record;
- evaluating failure classifiers.

They are not automatically suitable as positive imitation targets. A failed trace contains the action that caused
the miss. Use it as a negative diagnostic example unless a human supplies the correct action sequence or a verified
successful recovery follows.

### E4. Dataset audit

Before training, produce:

- episode manifest and source hashes;
- success and correction labels;
- distribution by placement, start state and lighting;
- grasp-centering/depth summary;
- camera freshness and synchronization checks;
- duplicate and corrupted-episode report;
- held-out validation split by complete episode.

The first five episodes are a quality gate. Continue recording only if all five contain both camera streams, a
centred bilateral close, visible lift and retention, and a valid tray release. One failed pilot episode does not
invalidate the recorder; it is labelled rejected and replaced with another accepted demonstration.

## 10. Phase F — fine-tune and select a new checkpoint

Freeze the current fine-tune 3 checkpoint and data as the baseline. Train a new named checkpoint using the audited
clean and corrective dataset. Record:

- base checkpoint and exact dataset versions;
- training configuration, seed, steps and hardware;
- loss curves and saved checkpoint schedule;
- code commit and environment lock;
- any sampling weights used for corrective windows.

Use offline validation only to reject broken runs; do not claim physical success from training loss. Select a small
number of candidate checkpoints before touching the robot.

Candidate screening:

1. action/state units and camera keys match deployment;
2. predictions remain inside the established motion envelope;
3. predicted grasp windows contain a coherent open-centre-close-lift pattern;
4. no NaNs, stale-camera dependence or instruction mismatch;
5. checkpoint loads through the same server/client route used for evaluation.

## 11. Phase G — staged physical evaluation

### G1. Smoke test

For each candidate, run at most three watched trials at the central mark. Stop a candidate for a mechanical fault,
repeated unsafe trajectory, or 0/3 acquisition.

### G2. Ten-trial comparison

Compare promising candidates using the same start/placement order and client settings. Report acquisition and
end-to-end success separately. Advance only candidates with at least 8/10 acquisition and no safety fault.

### G3. Fifty-trial development test

Use a pre-written balanced placement order. Do not tune the model, guard or placement marks during the row.

Pass criteria:

- at least 45/50 end-to-end successes;
- no uncontrolled collision or persistent motor fault;
- every failure has a stage label and complete trace;
- results do not depend on one placement cluster;
- success with guard/retry is reported separately from first-attempt success.

If the result is below 45/50, update the dataset from the measured failure distribution, train a new checkpoint and
repeat a new development row. Do not reinterpret the threshold after seeing the result.

### G4. Blind release evaluation

After development is frozen, run 100 fresh trials with a new pre-written placement order. No changes are allowed to
the checkpoint, guard, camera geometry, action horizon or success definition. Report:

- end-to-end successes out of 100;
- Wilson 95% confidence interval;
- first-attempt acquisition rate;
- recovery-assisted success rate;
- failure counts for acquisition, retention, transport, release and completion;
- result by placement and run order;
- latency, clamp, stale-frame and fault summaries.

The release target is at least 90/100 end-to-end successes. If stronger statistical evidence is required, extend
the frozen evaluation to 200 trials rather than tuning after the first 100.

## 12. Phase H — RTC, action horizon and auto-reset

Only after the new baseline is stable:

1. compare no-RTC and RTC on matched placement orders;
2. test shorter/adaptive action horizons around acquisition while keeping transport unchanged;
3. change one variable per ablation;
4. retain a change only when it improves the pre-registered metric without adding faults.

Resume auto-reset development after the 50-trial policy target passes. Complete its off-centre tray localisation and
V1-V4 validation separately. Auto-reset results must never be pooled with manually reset results unless the starting
placement distribution is shown to match.

## 13. Stop conditions

Stop the current physical run immediately for:

- a person or unplanned object entering the swept volume;
- camera or tray movement from its reference;
- stale or blank policy-input images;
- motor fault, abnormal temperature/voltage, unexpected resistance or cable snag;
- an action outside the validated envelope;
- loss of server/client synchronization;
- repeated guard uncertainty or two failed recovery attempts.

After a stop, torque off, save the trace, record the reason and inspect before continuing. A stopped or aborted run
is logged but is not silently counted as an ordinary policy failure.

## 14. Required artifacts

```text
baseline_manifest.json                 frozen physical/software configuration
placement_overlay.jpg                  registered current placement marks
mechanical_camera_check/               fresh images and hardware readings
preclose_labels.csv                    close windows and eligibility labels
preclose_diagnostic_report.md          detector metrics and shadow-mode result
dataset_manifest.json                  accepted clean/corrective episodes and hashes
training_manifest.json                 exact new checkpoint provenance
development_50.jsonl                   frozen 50-trial row
blind_100.jsonl                        frozen blind release row
orange_reliability_report.md           metrics, confidence intervals and failure analysis
```

All physical rows also retain their full Rerun traces and start/end images under a unique dated run name.

## 15. Immediate execution order

```text
1. Preserve fine-tune 3 and its 15/57 result as the frozen baseline.
2. Preflight the two-camera teleoperation recorder without moving either arm.
3. Record and audit five pilot episodes for `orange_grasp_corrective_ft4_20261108`.
4. If the pilot passes, record replacements until there are 30 accepted, balanced episodes.
5. Build a dataset manifest, contact sheets, checksums and an episode-level train/validation split.
6. Train fine-tune 4 from the frozen fine-tune 3 lineage with explicit sampling weights for the new data.
7. Screen checkpoints offline, then evaluate through watched 3, matched 10, development 50 and blind 100-trial gates.
8. Resume close-gate or auto-reset work only after the new policy shows stable acquisition.
```

The balanced orange collection is complete: 15 direct grasps, five left corrections, five right corrections and
five depth corrections passed review. Five separately labelled matchbox demonstrations with an orange distractor
also passed and remain a distinct source group. All 35 accepted episodes passed the automated metadata, camera,
synchronization, freshness, duplicate and full-decode audit. A complete-episode split now provides 29 training
episodes and six held-out episodes. See `fine_tune_4_execution_plan_20261108.md` for the exact run configuration and
gates. Fine-tune 4 completed 3,000 steps and saved three candidates. Held-out next-ten-action screening ranked
checkpoint 2,000 first (orange MAE 2.2921 versus 2.6569 for fine-tune 3; gripper MAE 1.4261 versus 2.4780). This is
an offline candidate ranking, not a robot success claim. Its six-trial watched physical gate scored 2/6: two complete
orange-to-tray successes, one centred close without a secure lift, and three offset close-beside acquisition failures.
The two successes both secured the orange before transport and released it in the tray. This expanded gate is enough
to reject checkpoint 2,000 as the reliable candidate. Compare these close windows and test checkpoint 3,000 through
the same watched gate before selecting a candidate for the matched ten-trial row.
Auto-reset and the action gate remain disabled until the new policy demonstrates stable acquisition.

Checkpoint 3,000 subsequently scored **1/3 (33.3%)** under the same protocol. Its only success required late recovery
and completed at the cap; the other trials were a pass-by acquisition miss and a centred close without retained
lift. This matches checkpoint 2,000's observed 33.3% rate and leaves no candidate for the matched ten-trial row.
Pause blind repetitions and use the saved close windows to revise centring and retained-lift behavior first.

The completed nine-trial close-window review found three offset/pass-by failures and three visually centred closes
without retained lift. The existing fixed wrist detector recognized all three successes but would have permitted
three of six failures, so it cannot be enabled as a motor gate. The replacement shadow verifier must require both a
plausible pre-close pose and post-close evidence that the fruit remains between the fingers during a short lift. The
current front-camera view has also shifted from the controlled overhead reference and must be restored before any
new matched row. See `../results/so101_bench_20261019/ft4_close_window_diagnosis_20261109/README.md`.

The front camera was subsequently restored and checkpoint 3,000 ran a five-trial fixed-small-orange row. It scored
**1/5**: three acquisition failures, one grasp-and-carry followed by a release failure, and one complete success. The
fixed pre-close wrist detector agreed with reviewed outcomes on **4/5** frames. It allowed both real grasps but also
allowed one centred close that failed to retain the fruit. This evidence preserves the planned design: pre-close
centring is useful, but the shadow verifier must also require post-close fruit motion during a short lift and verify
tray retention after release. See
`../results/so101_bench_20261019/ft4_ckpt3000_restored_camera_probe_20261109/README.md`.

The combined verifier is now implemented as read-only bench-client instrumentation. Replaying the five-trial row
produced the five reviewed stage labels and took 11.79 ms per observation. This is same-row calibration evidence,
so Phase D1 remains open: the next row must measure prospective shadow decisions while leaving policy execution
unchanged.

Phase D1 prospective trial 1 is complete. The policy never closed during its 75-request search; physical review and
the shadow verifier both labelled acquisition failure. The trace contains all 75 verifier decisions with no stale
camera frames. This covers the no-close path but provides no new retained-lift or release example, so Phase D1 is
**1/10** and remains open.

Phase D1 subsequently completed all **10/10** prospective trials. Reviewed task success was **3/10** (T3, T7 and
T10), with three acquisition failures and four failures after some acquisition. T3 was physically successful before
a hand removed the orange between c69 and c70; exclude it from the strict hands-clear subset while retaining its real
c60 release as verifier evidence. The shadow outcome labels agreed with all ten reviewed end-to-end outcomes and no
camera observation was stale.

The close gate nevertheless fails the D1 acceptance rule. Its two-consecutive-frame pre-close condition reported
`blocked` for the decisive close in **all three successful trials**. Enabling it would therefore risk removing every
observed success. Keep it in shadow mode. The next work is offline threshold/timing revision against the frozen
prospective trace, with T3, T7 and T10 treated as mandatory preserve cases. Do not run another physical gate row until
that replay passes. Evidence is in
`../results/so101_bench_20261019/ft4_shadow_verifier_prospective_20261109/README.md`.
