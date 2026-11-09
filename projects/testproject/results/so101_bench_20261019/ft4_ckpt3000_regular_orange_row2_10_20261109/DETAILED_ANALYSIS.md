# Detailed analysis: FT4 checkpoint 3,000 regular-orange row 2

Date: 2026-11-09  
Scope: the ten valid regular-orange trials in this row  
End-to-end result: **1/10 (10%)**

## How this review was made

Each trial was reviewed from the synchronized overhead and wrist images, measured six-joint state, predicted action
chunks, dispatched actions and request timing. The review uses the following task phases:

1. **Initiation:** leave the recorded start pose and begin a purposeful reach.
2. **Approach:** place the open fingers around the orange.
3. **Close/acquisition:** close with the orange between both fingers.
4. **Retention/lift:** raise the orange without losing it.
5. **Transport:** carry it to the tray.
6. **Release:** open above the tray and leave the orange inside.

The joint values below are measured states in degrees, ordered as shoulder pan, shoulder lift, elbow flex, wrist flex,
wrist roll and gripper. A lower gripper value means a more closed gripper. Chunk numbers are policy requests; each
request supplied 20 actions for execution at 30 Hz.

## Trial-by-trial findings

### Trial 1 — fail: repeated close beside the orange

- **Initiation and approach:** The arm moved promptly. By chunk 20 it had extended from the folded start pose to the
  orange, with the gripper still open at about 62 degrees.
- **First close:** The gripper crossed below 55 degrees at chunk 27. The overhead and wrist images show the orange at
  the outside of one finger rather than centred in the gap. At chunk 36 the gripper was about 51 degrees, but the
  orange was still beside the fingers.
- **Repeated attempts:** The policy continued changing wrist position and closing. Gripper measurements were about 48
  at chunk 49, 24 at chunk 68 and 11 at the cap. These were real close commands, but they occurred around empty space
  or against the orange's edge.
- **Outcome:** There was no retained lift, transport or release. The orange remained on the table.
- **Diagnosis:** **Acquisition geometry failure.** This was not a failure to close. The policy closed several times,
  but lateral alignment was wrong before the close. Continued closing and searching did not recenter the fruit.

### Trial 2 — fail: reach began too late and no close occurred

- **Initiation:** The arm remained folded through chunk 55. Its measured state was still approximately
  `[-7, -104, 97, 75, -5, 80]`, close to the start configuration.
- **Approach:** Purposeful extension began at chunk 56. By chunk 68 the arm had reached the orange area.
- **Close:** No meaningful close command arrived. The gripper remained very open: about 76 degrees at chunk 68 and 74
  at chunk 75.
- **Outcome:** The 75-chunk cap arrived during the approach. There was no acquisition, lift, transport or release.
- **Diagnosis:** **Late initiation/no-close failure.** The cap exposed the delay, but the underlying problem was that
  the policy spent about three quarters of the episode near the start pose before beginning the task.

### Trial 3 — success: centred grasp, retained carry and release

- **Initiation and approach:** The first substantial reach developed from roughly chunks 21–40. At chunk 40 the arm
  was extended toward the orange with the gripper open.
- **Centred close:** At chunk 49 the images show the orange between both fingers, not outside either jaw. The gripper
  closed sharply to about 37 degrees at chunks 49–50 and reached a minimum near 36 at chunk 54.
- **Retention and lift:** The gripper remained near 36 while the shoulder swept across the table. From chunks 50–58,
  the measured shoulder pan changed from about -36 to +49 degrees while the orange stayed in the fingers. This is the
  clearest evidence of a stable grasp in the row.
- **Transport and release:** At chunk 58 the held orange was over the tray. The gripper opened to about 44 at chunk 60,
  and the overhead image shows the orange inside the tray.
- **Return:** By chunk 65 the arm was back near its start pose. The orange remained in the tray through chunk 75.
- **Diagnosis:** **Complete success.** The decisive difference was the position at the moment of closing: both fingers
  surrounded the orange. Once that happened, the same policy successfully executed lift, cross-table transport,
  release and return.

### Trial 4 — fail: edge contact pushed the orange

- **Initiation and approach:** The arm began developing a reach around chunks 32–44. At chunk 44 it was beside the
  orange with the gripper open at about 62 degrees.
- **Close:** The gripper closed gradually: approximately 50 degrees at chunk 51 and 41 at chunk 59.
- **Contact:** At chunk 59 the overhead image shows the orange pressed against the outer/edge region of the gripper.
  The wrist view is filled by the nearby orange, but it is not enclosed between both fingers.
- **After contact:** The arm continued searching and partly reopened; the gripper was about 53 degrees at the cap.
  There was no retained lift.
- **Outcome:** The orange was pushed on the table and never transported.
- **Diagnosis:** **Acquisition geometry failure.** Like Trial 1, the robot reached and closed, but it arrived laterally
  offset. Contact moved the orange instead of securing it.

### Trial 5 — fail: no task engagement

- **Initiation:** The arm remained folded for all 75 chunks. At chunk 40 the state was about
  `[-11, -105, 97, 76, -4, 75]`; at chunk 75 it was `[-19, -104, 97, 65, -10, 71]`.
- **Motion:** There was slow shoulder-pan and wrist drift, but shoulder lift and elbow stayed at their folded start
  values. This was not a reach toward the orange.
- **Close:** The gripper never crossed below 55 degrees; its minimum was about 65.
- **Outcome:** No approach, contact, grasp, lift, transport or release occurred.
- **Diagnosis:** **No-engagement failure.** The policy repeatedly selected small start-area motions despite fresh
  observations containing a visible orange.

### Trial 6 — fail: late approach passed beside the orange

- **Initiation:** The arm stayed close to start until about chunk 32, then extended during chunks 33–56.
- **Approach:** At chunk 56 the arm was fully forward, but the overhead image shows the orange outside the side of the
  gripper rather than inside its opening.
- **Close:** The gripper remained mostly open during the approach. A partial close occurred only near the end: it
  crossed below 55 at chunk 72 and reached about 51 at chunks 74–75.
- **Outcome:** No stable grasp or lift occurred before the cap.
- **Diagnosis:** **Late reach plus acquisition miss.** The approach used much of the episode and finished beside the
  orange. The final partial close was too late and was not centred.

### Trial 7 — fail: no task engagement

- **Initiation:** The arm remained folded throughout the trial. At chunk 40 it was approximately
  `[-7, -103, 97, 73, -8, 78]`, and at chunk 75 it was `[2, -104, 96, 65, -4, 75]`.
- **Motion:** Small pan and wrist changes occurred, but the shoulder-lift/elbow pair never formed a reach.
- **Close:** The gripper stayed open and never crossed below 55 degrees.
- **Outcome:** No approach or contact occurred.
- **Diagnosis:** **No-engagement failure.** The action sequence varied slightly, but it did not begin the instructed
  pick-and-place task.

### Trial 8 — fail: no task engagement

- **Initiation:** This was the clearest stationary failure. The measured arm pose stayed close to start for the entire
  cap: about `[-9, -104, 97, 78, -6, 67]` at chunk 40 and `[-7, -104, 96, 76, -7, 72]` at chunk 75.
- **Close:** The gripper minimum was about 64 degrees and there was no grasp command.
- **Outcome:** No reach, contact, lift, transport or release occurred.
- **Diagnosis:** **No-engagement failure.** The orange was visible and the setup was unchanged, but the policy remained
  in a near-start action pattern.

### Trial 9 — fail: no task engagement

- **Initiation:** The arm again remained folded. At chunk 40 its state was approximately
  `[-10, -103, 97, 73, -8, 73]`; at the cap it was `[-16, -104, 97, 78, -8, 67]`.
- **Motion:** Slow pan drift occurred, but shoulder lift and elbow remained at start values. No useful reach developed.
- **Close:** The gripper never crossed below 55 degrees.
- **Outcome:** No contact or later task phase occurred.
- **Diagnosis:** **No-engagement failure.** This repeats the same policy-level initiation problem seen in Trials 5,
  7 and 8.

### Trial 10 — fail: extremely late reach and no close

- **Initiation:** The arm stayed largely folded through chunk 66. It began extending at chunk 67, when shoulder lift
  changed from roughly -103 toward -83 degrees.
- **Approach:** By chunks 73–75 it had reached the orange area. The overhead image shows the fruit at the gripper edge.
- **Close:** The gripper remained wide open, approximately 68 degrees at chunk 73 and 66 at chunk 75.
- **Outcome:** The cap arrived before any close, grasp, lift or transport.
- **Diagnosis:** **Extremely late initiation/no-close failure.** More cap time might have allowed another action, but
  it would not correct the underlying 66-chunk delay or guarantee centring.

## What the ten trials establish

The failures occurred before transport:

| Failure stage | Trials | Count |
|---|---:|---:|
| No purposeful task engagement | T5, T7, T8, T9 | 4 |
| Reach began late and produced no useful close | T2, T6, T10 | 3 |
| Reached but closed/contacted beside the orange | T1, T4 | 2 |
| Retained grasp followed by transport/release failure | none | 0 |
| Complete success | T3 | 1 |

Seven of the nine failures were dominated by **initiation and timing**. Two were dominated by **pre-close lateral
alignment**. Only one trial acquired a retained grasp, and that one completed the task. This row therefore does not
show a transport or release regression; it shows that checkpoint 3,000 rarely gets into a valid grasp state.

The setup alone does not explain the variation. The same regular orange, restored overhead camera, tray geometry,
task text, start-return routine and server produced both Trial 3's success and the failures. Camera freshness counters
were zero in the reviewed observations, and all ten valid trials produced the full trace. The robot also physically
executed large motions and a full carry in Trial 3. Those facts argue against a disconnected camera, dead motor or
globally broken execution path.

The approximately 1.2-second request latency and 20-action execution horizon can make correction near the orange
harder, because a lateral error can persist through several actions before another observation is processed. They do
not, by themselves, explain the four stationary trials: the same latency and horizon were present during the success.
Latency is therefore a contributing constraint, not the sole cause of the 10% result.

The evidence supports two model-side weaknesses:

1. **Unstable task initiation:** given nearly identical initial scenes, the policy sometimes reaches promptly,
   sometimes waits until the cap is nearly exhausted, and sometimes never reaches.
2. **Weak final acquisition accuracy:** when the policy does reach, it can place the orange outside one finger and
   close or push without a successful recenter-and-retry behavior.

The successful Trial 3 is useful positive evidence, but one success cannot establish a reliable post-grasp success
rate. It establishes only that this checkpoint is capable of the full behavior under this setup.

## Relationship to the other controlled checkpoint-3,000 rows

The current row is **1/10**. The documented controlled regular-orange results for the same checkpoint are 1/3 in the
initial gate, 1/5 in the restored-camera probe, 3/10 in the prospective shadow-verifier row and 1/10 here, for a
descriptive total of **6/28 (21.4%)**. Because these rows served different diagnostic purposes, 21.4% is useful as a
summary of observed performance, not as a single preregistered benchmark estimate.

## Evidence files

- `contact_sheet.jpg`: overhead key/cap comparison for all ten trials.
- `summary.json`: row outcome and latency summary.
- `/home/gaikwad-prakash/bench_trace_ft4_ckpt3000_regular_orange10_row2f_20261109`: T1–T3 and the excluded partial attempt.
- `/home/gaikwad-prakash/bench_trace_ft4_ckpt3000_regular_orange10_row2_remaining7_20261109`: T4–T10.

The partial attempt after Trial 3 is not counted. The orange was still in the tray, and the runner was stopped at
chunk 9 before a valid table pickup trial occurred.
