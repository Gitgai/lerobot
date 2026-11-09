# Fine-tune 4 execution plan

Date: 2026-11-08
Status: checkpoint comparison and close-window diagnosis complete; no candidate advances to matched ten

## Objective

Fine-tune the existing `row3_all169_conservative_010000` policy to improve the weak acquisition phase: centre both
fingers around the orange, correct lateral or depth errors before closing, and establish a secure initial grasp.
The small matchbox group adds language-conditioned object selection while an orange distractor is present.

## Accepted demonstrations

| Source | Accepted | Training | Validation | Purpose |
|---|---:|---:|---:|---|
| Orange direct | 15 | 13 | 2 | Centred bilateral grasp |
| Orange lateral-left | 5 | 4 | 1 | Correct one lateral error direction |
| Orange lateral-right | 5 | 4 | 1 | Correct the opposite direction |
| Orange depth | 5 | 4 | 1 | Advance from a shallow approach before closing |
| Matchbox with orange distractor | 5 | 4 | 1 | Select the named object and leave the distractor untouched |
| **Total** | **35** | **29** | **6** | Complete-episode split |

Orange source episode 0 remains preserved as a rejected attempt and is absent from both derived datasets.

## Audit result

The automated audit passed all 35 accepted episodes. It checked:

- source metadata and contiguous frame indices;
- accepted human-review labels;
- both 640×480, 30 Hz camera streams;
- nonblank and changing camera samples;
- front/wrist episode timing agreement;
- exact duplicate action/state trajectories;
- full decode and exact frame counts after materialization.

The first derived merge exposed a LeRobot codec mismatch: sliced files could be AV1 while their metadata still said
H.264. That copy was discarded. The preparation script now normalizes every derived clip to H.264 before merging.
The corrected datasets contain exactly 30,376 training frames and 6,284 validation frames in each camera stream.
Merged video files are capped at 30 MB so random frame access during training remains practical.

## Dataset locations

```text
local train: /home/gaikwad-prakash/ft4_datasets_20261108/train29
local val:   /home/gaikwad-prakash/ft4_datasets_20261108/val6
```

The exact source audit, split, file hashes and training provenance are stored under
`results/so101_bench_20261019/ft4_dataset_20261108/`.

## Training configuration

The run continues from the frozen fine-tune 3 checkpoint with a fresh LoRA adapter:

```text
checkpoint: /home/kiran/lerobot_assets/ckpt_mirror/row3_all169_conservative_010000
GPU:        AI90 GPU 0, RTX 5090
output:     /home/kiran/lerobot_assets/training/ft4_orange_matchbox_corrective_20261108
HF cache:   /home/kiran/hf-cache-recovered (the /mnt/data4tb cache link is unavailable)
batch:      4 × 2 gradient accumulation = effective batch 8
steps:      3,000
LR:         1e-5 cosine decay; 150 warm-up steps
delay aug:  0-8 frames, matching fine-tune 3
checkpoints: 1,000, 2,000 and 3,000
```

Natural episode sampling gives orange 25/29 (86.2%) and matchbox 4/29 (13.8%). The task strings remain distinct.
The six validation episodes are never included in training.

## Execution gates

1. Stage the train/validation datasets, configuration, audit and manifest on AI90.
2. Load the training dataset and run a 20-step smoke test. Require finite loss, correct camera keys, correct task
   strings, checkpoint writing and no decoding failure.
3. Start the 3,000-step run only after the smoke test passes.
4. Rank checkpoints 1,000, 2,000 and 3,000 using the six held-out episodes. This selected checkpoint 2,000 as the
   first physical candidate. Validation only rejects broken or clearly weaker candidates; it cannot prove robot
   success.
5. Evaluate the selected candidates on the robot through watched 3, matched 10, development 50 and blind 100-trial
   gates. The development target is at least 45/50; the release target is at least 90/100.
6. Use the measured failure distribution to decide whether more demonstrations are needed. Resume auto-reset work
   only after acquisition is stable.

## Execution record

The AI90 package passed remote hash verification and loaded through the deployed PyAV data path. A first batch-8
smoke attempt reached the forward pass but exceeded the RTX 5090's 31.36 GiB capacity. The tested configuration used
batch 4 with two-step accumulation, retaining effective batch 8. Its 20-step smoke run completed with finite losses
from 0.006 to 0.029 and saved checkpoint 000020.

The full 3,000-step run completed on the RTX 5090 at 2026-11-08 17:45:40 +05:30. It processed 24,000 samples
(approximately 0.79 epoch), ended at loss 0.008 and saved checkpoints 1,000, 2,000 and 3,000 with recorded hashes.
No NaN or decode failure occurred.

Offline screening evaluated 108 next-ten-action probes from the six held-out episodes. Lower mean absolute error is
better:

| Checkpoint | All-action MAE | Orange MAE | Gripper MAE | Step-10 gripper agreement |
|---|---:|---:|---:|---:|
| Fine-tune 3 baseline | 2.6209 | 2.6569 | 2.2869 | 94.44% |
| Fine-tune 4, step 1,000 | 2.4962 | 2.4589 | 1.6879 | 99.07% |
| **Fine-tune 4, step 2,000** | **2.3294** | **2.2921** | **1.4261** | **99.07%** |
| Fine-tune 4, step 3,000 | 2.3498 | 2.3086 | 1.4396 | 99.07% |

Checkpoint 2,000 is therefore the first robot-test candidate. These are imitation errors against held-out expert
actions, not a physical success rate. The next gate is exactly three watched orange trials at the central mark.

## Watched physical gate

Checkpoint 2,000 was tested on six controlled central-area orange placements with 20 executed actions per policy
request, a 75-request cap, two live camera inputs and return-to-start enabled:

| Trial | Acquisition | End-to-end | Observed failure or completion |
|---|---|---|---|
| 1 | Fruit centred between both fingers | Fail | Closed to about 20 but did not secure or lift the orange |
| 2 | No | Fail | Approach and repeated closes landed outside the right finger |
| 3 | Yes | **Success** | Closed by chunk 15, airborne by 18, released in the tray by 24, back at rest around 40 |
| 4 | No | Fail | Offset close pushed the orange right; it was never secured or lifted |
| 5 | Yes | **Success** | Secure grasp by about chunk 29 and released in the tray by 38; manually reset after completion at 56 |
| 6 | No | Fail | Repeated closes landed offset; the orange stayed on the table and no transport began |

The expanded watched result is **2/6 end to end (33.3%)**. This proves that the FT4 serving path and learned task
sequence are functional, but it does not establish reliability or support a 90% claim. Three failures were offset
close-beside acquisition errors and one was a centred close without a retained lift. One earlier forward-right
exploratory failure is excluded from
this controlled score because its placement did not match the central protocol. Exact logs, stage labels and key
frames are in `results/so101_bench_20261019/ft4_physical_gate_20261108/`.

This result triggered the same three-trial watched gate on checkpoint 3,000 before committing ten trials to either
candidate. Offline checkpoint 3,000 had ranked a close second, making that direct comparison the next gate.

### Checkpoint 3,000 comparison gate

Checkpoint 3,000 then ran the same watched three-trial protocol. Trial 1 recovered from early offset attempts, secured
the orange around chunks 67–68 and released it in the tray at the 75-chunk cap. Trial 2 passed the orange with the
jaws open and later closed over empty table. Trial 3 repeatedly centred and closed around the orange but never
retained it through lift. The result was **1/3 (33.3%)**.

Checkpoint 3,000 did not improve on checkpoint 2,000's **2/6 (33.3%)**. Neither candidate advances to the matched
ten-trial row. The next gate is offline close-window comparison and a grasp-strategy revision; more blind repetitions
of these two candidates are paused.

### Close-window diagnosis

The read-only comparison of all nine controlled FT4 trials split the six failures evenly: three offset/pass-by
acquisition errors and three visually centred closes without retained lift. Applying the previously fixed wrist
detector without retuning marked all three successes eligible, but blocked only three of six failures. It falsely
permitted one offset close and two centred retention failures. A 2D pre-close fruit centre is therefore insufficient
as a motor gate.

The successful trials showed a sustained contact aperture followed by fruit motion with the gripper. Two centred
failures closed more tightly and immediately reopened, while one remained closed without lifting. Aperture alone is
also insufficient. The next implementation must combine pre-close geometry, post-close contact stability and visual
evidence that a short lift moves the fruit off the table. The full measurements are in
`results/so101_bench_20261019/ft4_close_window_diagnosis_20261109/`.

The analysis also identified two experimental confounds. Checkpoint 2,000's first three trials used the larger
green-yellow citrus and its next three used the small orange; each subgroup scored 1/3. Later large-citrus trials used
a shifted low/side front-camera view and remain exploratory. Restore the documented overhead camera geometry and use
one fixed small orange before prospective shadow-mode verification.

### Large-citrus exploratory row, 2026-11-09

At the operator's request, checkpoint 3,000 ran five additional valid trials with the larger citrus while the front
camera remained in the shifted low/side position. This row is deliberately separate from the controlled small-orange
comparison and does not change its **1/3** score.

The exploratory row scored **1/5 end to end (20%)**. Trials 1–3 failed during acquisition. Trial 4 recovered after
several edge contacts, grasped the citrus at chunk 49 and released it in the tray by chunk 52. Trial 5 obtained a
stable grasp and carried the citrus across the table, but released it on the table just short of the tray. Two starts
with the citrus already in the tray were stopped and excluded before meaningful task motion.

This row reinforces the diagnosis rather than changing the plan: acquisition remains inconsistent, and the one
delivery failure shows that a retained-lift check alone cannot guarantee tray placement. Restore the reference camera,
return to the fixed small orange and central marks, then validate the proposed pre-close centring plus retained-lift
and tray-release checks in shadow mode. Evidence and per-trial labels are in
`results/so101_bench_20261019/ft4_ckpt3000_large_citrus_lowcam_20261109/`.

### Restored-camera small-orange row and offline verification, 2026-11-09

The front camera was returned to the documented overhead geometry and verified before motion: tray upper-left, arm
upper-centre, table filling the image and the orange unobstructed below the gripper. Five checkpoint 3,000 trials ran
with the normal 20-action requests and 75-request cap. The row scored **1/5 (20%)**. Three trials failed acquisition,
one secured and carried the orange but left it on the table immediately in front of the tray, and one completed the
task. The four-trial extension alone scored **1/4**.

The existing fixed wrist-image pre-close detector was then applied offline, without retuning, to one reviewed close
frame per trial. It allowed both genuine grasps and blocked two of the three acquisition failures, for **4/5** total
agreement. T5 was the decisive false positive: the orange appeared centred before closing but did not remain between
the fingers during lift. A prospective verifier must therefore combine pre-close geometry with retained-lift evidence;
the T4 delivery failure separately requires confirmation that the orange remains in the tray after release.

The camera correction removed an experimental confound but did not remove the acquisition failure. Further blind
repetitions are paused until the three checks can be logged prospectively in shadow mode. Evidence, detector outputs
and per-trial key frames are in
`results/so101_bench_20261019/ft4_ckpt3000_restored_camera_probe_20261109/`.

The read-only state machine is now implemented behind `bench_client.py --shadow-grasp-verifier` and displayed by
the existing Rerun watcher. It never changes the predicted or dispatched action. Calibration replay classified all
five saved trials at the correct stage and averaged 11.79 ms per observation. Because its thresholds were developed
from these same trials, this is an implementation check rather than independent validation. Run the next controlled
row prospectively with shadow logging enabled; do not enable a motor gate from the replay result.

Prospective Phase D trial 1 then ran for the full 75-request cap. The policy searched with the gripper open and never
issued a close, so both reviewed outcome and shadow verdict were acquisition failure. All 75 verifier records, 75
predictions and 1,500 dispatched actions were captured with zero stale camera frames. This validates integration and
the no-close path only; retained-lift and tray-release branches still require prospective examples. Evidence is in
`results/so101_bench_20261019/ft4_shadow_verifier_prospective_20261109/`.

Phase D1 is now complete at **10/10 prospective trials**. Trials 2-10 ran back to back with the same checkpoint and
unchanged dispatch settings. Physical task success was **3/10**: T3, T7 and T10 delivered the orange. T3 had a hand
remove the orange after its successful c60 release but before the cap, so the strict hands-clear subset is **2/9**.
The other outcomes were three acquisition failures and four post-acquisition delivery/retention failures. The shadow
outcome classifier agreed with all ten reviewed task outcomes and both cameras recorded zero stale observations.

This agreement does **not** authorize the motor gate. The proposed two-consecutive-frame pre-close rule would have
blocked the decisive close in all three successful trials. That directly fails the requirement to preserve successful
acquisitions. Keep the verifier read-only, revise its pre-close timing on the frozen 750-observation trace and require
the next candidate to preserve T3, T7 and T10 before any further physical gate test. The current policy's 30% row also
confirms that FT4 checkpoint 3,000 is not the 90% solution by itself. Full results and key frames are in
`results/so101_bench_20261019/ft4_shadow_verifier_prospective_20261109/`.

## Reproducible commands

```text
scripts/audit_ft4_datasets.py
scripts/prepare_ft4_datasets.py
scripts/evaluate_ft4_holdout.py
configs/ft4_orange_matchbox_corrective_20261108.yaml
```
