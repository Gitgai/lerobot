# FT4 checkpoint 3,000: consolidated review of 30 trials

Date: 2026-11-09  
Policy: FT4 checkpoint 3,000  
Execution: 20 actions per request, 30 Hz, 75-request cap, return to start

## Scope and headline results

These 30 valid trials comprise three separately documented rows:

| Set | Object and purpose | Result |
|---|---|---:|
| A | Regular orange; prospective read-only shadow-verifier row | **3/10 (30%)** |
| B | Large green-yellow citrus; restored-camera object-size test | **0/10 (0%)** |
| C | Regular orange; second controlled row | **1/10 (10%)** |
| Raw total | Mixed objects | **4/30 (13.3%)** |

The fair object-specific regular-orange result across Sets A and C is **4/20 (20%)**. Set B must remain separate
because the large citrus has a different diameter and was outside the distribution of the orange demonstrations.

## Set A — regular orange with read-only shadow verifier: 3/10

The shadow verifier observed images and state but did not control or modify the robot. Therefore these are normal
checkpoint-3,000 physical outcomes.

1. **A1 — acquisition failure.** The arm reached/search-positioned with the gripper open but never produced a close
   that retained the orange. It continued searching until the cap.
2. **A2 — acquisition failure.** A close was attempted, but the orange was not secured between both fingers. The
   verifier would have blocked this close, and the physical result confirmed no retained grasp.
3. **A3 — success.** The robot acquired the orange and released it inside the tray at chunk 60. The orange remained
   visibly in the tray through chunk 69. A hand removed it at chunk 70, after task completion, so the physical success
   is real but the trial is excluded from the stricter hands-clear subset.
4. **A4 — delivery failure.** The robot briefly acquired the orange, but released it outside the tray around chunk
   48. Acquisition occurred; placement accuracy failed.
5. **A5 — retained without release.** The robot still held the orange at the cap. Because no tray release occurred,
   the scripted return carried the orange away from the delivery area.
6. **A6 — retained without tray release.** A second grasp attempt secured the orange, but the robot never completed a
   verified release in the tray before the episode ended.
7. **A7 — success.** The orange was acquired, transported and released in the tray around chunk 65.
8. **A8 — no meaningful task engagement.** The arm stayed near the start pose for almost the entire trial and never
   formed a useful reach or close.
9. **A9 — delivery failure.** A second attempt retained the orange, but it was released on the table beside the tray,
   or outside a verifiable tray region, around chunk 54.
10. **A10 — success.** The orange was acquired, carried and released inside the tray around chunk 64.

Set A had three acquisition failures, four failures after some acquisition and three complete successes. Its outcome
classifier agreed with all ten final physical outcomes. The proposed pre-close motor gate was not enabled because its
rule would also have blocked the successful closes in A3, A7 and A10.

## Set B — large green-yellow citrus: 0/10

This set used the large citrus, not the regular orange. The restored overhead camera and trained orange instruction
were used, but the object's larger diameter required a wider and differently centred grasp.

1. **B1 — repeated closes, no retained lift.** The robot reached the citrus and made several close attempts, but the
   fingers never secured it strongly enough to lift.
2. **B2 — repeated closes, no retained lift.** The same pattern repeated: approach and close activity occurred, but
   the citrus remained on the table.
3. **B3 — late overextended attempt.** The arm waited until approximately chunk 52, then reached too late and extended
   past the useful grasp position. A late close did not secure the fruit.
4. **B4 — no meaningful reach.** The arm remained near start and never attempted acquisition.
5. **B5 — sustained contact without lift.** The gripper reached a contact aperture near 40 degrees and stayed in
   contact, but the larger fruit was not enclosed and retained. No lift followed.
6. **B6 — folded-arm rotation.** The base/arm rotated while the arm remained folded. It never extended to the citrus.
7. **B7 — folded-arm rotation to the left.** Rotation occurred without a useful extension or grasp attempt.
8. **B8 — several close attempts, no retained lift.** The robot reached the citrus and closed repeatedly, but could
   not secure its larger diameter.
9. **B9 — late reach and close.** The acquisition attempt occurred near the cap and did not produce a retained lift.
10. **B10 — immediate reach, repeated closes.** The trial initiated promptly, but repeated closes still failed to
    enclose and lift the citrus.

All ten Set B failures occurred before a retained lift. Three never made a meaningful reach; seven reached/contacted
the object but could not secure it. Together with an earlier separately documented 1/5 exploratory row, this
checkpoint's descriptive large-citrus result is 1/15 (6.7%).

## Set C — regular orange controlled row 2: 1/10

1. **C1 — repeated close beside.** The arm reached promptly and issued real close commands, eventually closing to
   about 11 degrees. The orange remained outside one finger, so the closes occurred around empty space or its edge.
2. **C2 — late reach, no close.** The arm stayed folded through chunk 55, reached from chunk 56 and arrived near the
   orange around chunk 68. The gripper remained open through the chunk-75 cap.
3. **C3 — success.** At chunks 49–50 the orange was centred between both fingers and the gripper closed to about 36
   degrees. It remained held during the cross-table carry and was released inside the tray at chunks 59–60.
4. **C4 — edge contact and push.** The arm reached and closed from about 62 to 41 degrees, but the orange was against
   the gripper edge rather than between both fingers. Contact pushed it instead of lifting it.
5. **C5 — no engagement.** The arm stayed folded for all 75 chunks. Small joint drift occurred without a reach.
6. **C6 — late reach passed beside.** A reach developed after approximately chunk 32, but the gripper passed beside
   the orange. A partial close arrived only near chunks 72–75 and did not retain it.
7. **C7 — no engagement.** The arm remained at the start area with the gripper open.
8. **C8 — no engagement.** This was the most stationary trial; no meaningful reach or close occurred.
9. **C9 — no engagement.** Slow shoulder drift occurred, but the arm stayed folded and never contacted the orange.
10. **C10 — extremely late reach.** The arm stayed folded through chunk 66, reached during chunks 67–75 and hit the
    cap with the gripper still open.

Set C contained four no-engagement failures, three late-reach/no-useful-close failures, two close-beside/edge-contact
failures and one complete success.

## What happened across all 30

Classifying each trial by the furthest meaningful stage reached gives:

| Furthest outcome | Count | Trials |
|---|---:|---|
| No meaningful reach | 8 | A8; B4, B6, B7; C5, C7, C8, C9 |
| Reached/closed but no meaningful retained acquisition | 14 | A1, A2; B1, B2, B3, B5, B8, B9, B10; C1, C2, C4, C6, C10 |
| Some acquisition, but delivery/release failed | 4 | A4, A5, A6, A9 |
| Complete success | 4 | A3, A7, A10, C3 |

Thus, **22/30 trials failed before a meaningful retained acquisition**. Four more acquired the object but failed to
release it correctly. Four completed the task. Of the eight trials that achieved at least some meaningful acquisition,
four completed, but this small conditional sample does not establish a reliable 50% post-acquisition rate.

For the 20 regular-orange trials only:

- End-to-end success: **4/20 (20%)**.
- No meaningful reach: **5/20**.
- Reach/acquisition failure: **7/20**.
- Post-acquisition delivery/release failure: **4/20**.
- Complete success: **4/20**.

## Main conclusions

1. **Initiation is unstable.** Nearly identical initial scenes can produce a prompt reach, a reach delayed until the
   cap, or no reach. Five of the twenty regular-orange trials never formed a meaningful reach.
2. **Acquisition is the largest bottleneck.** Across all objects, 22/30 trials failed before the robot retained an
   object. The failures include closing beside the fruit, contacting it with one finger, pushing it and keeping the
   gripper open after a late reach.
3. **The large citrus is a separate generalization failure.** It was 0/10 because the policy did not adapt its aperture
   and centring to the larger diameter. It should not lower the reported regular-orange score.
4. **Transport and release are possible but not reliable.** The three Set A successes and C3 prove that the full
   behavior exists. A4, A5, A6 and A9 show that acquisition alone does not guarantee correct tray release.
5. **The current verifier is useful for scoring, not motor control.** It classified all ten Set A outcomes correctly,
   but its pre-close rule would have rejected all three real successes. It must remain read-only until revised.
6. **Latency is a constraint rather than the sole cause.** Median request latency was approximately 1.18–1.21 seconds
   across the rows. This reduces correction opportunities near the object, but successful and stationary trials both
   occurred under the same transport conditions.

The evidence does not support more blind repetition as the main next step. The model needs additional data and/or
control changes that specifically teach prompt task initiation, centred two-finger acquisition, recovery after edge
contact and verified release over the tray. Large-citrus improvement additionally requires demonstrations using that
object size.

## Source reports

- `../ft4_shadow_verifier_prospective_20261109/README.md`
- `../ft4_ckpt3000_large_citrus_restored_camera_10_20261109/README.md`
- `../ft4_ckpt3000_regular_orange_row2_10_20261109/README.md`

Excluded attempts are not part of these 30: one large-citrus run was stopped after using an incorrect `apple`
instruction, and one regular-orange attempt was stopped because the orange remained in the tray after a preceding
success.
