# Brain B Under RTC: The Tempo-vs-Camera Check

Date: 2026-08-21
Status: PLAN — ready to execute
Prerequisites: `n16_rtc_plan_20260820.md` (RTC implementation + gates, all
passed), the 20-run sequential A/B record and the 10-run RTC set in
`sim_to_real_camera_alignment_20260809.md`.

## 0. The question this answers

The sequential A/B concluded Brain A (side camera) > Brain B (overhead):
A grasped 10/10 with one failure mode; B grasped 7/10 with three (stall,
overreach, slip). But that verdict was measured at stutter tempo (31% duty,
30-100 decisions per carry) — and RTC has since shown that tempo alone took
Brain A from 4/10 to 9/10. B's stalls and slips are plausibly the same
long-rollout diseases A had.

So the open question: **was the A/B measuring camera quality, or tempo
tolerance?** Three runs of B under RTC discriminate:

```text
B + RTC ~ 3/3 or 2/3   -> tempo was most of the story. Camera choice is a
                          convenience decision; either rig works.
B + RTC still stalls / -> the gap is genuinely visual. A's win stands on
slips (0-1/3)             its camera; future rigs keep the side view.
```

Either answer changes what we build next (whether plate-round demos need
re-recording per-camera, and which camera any new task uses).

## 1. What changes vs yesterday's RTC set — exactly two things

```text
checkpoint   n16_real79_side  ->  n16_real79_top   (server swap, NJ side)
front camera laptop /dev/video0 -> overhead C270   (physical, Pune side)
```

Everything else is FROZEN to keep the comparison clean: RTC on, same client,
same instruction ("pick up the orange and move it to another place"), same
reset-to-rest between runs, same 120 s limit, same mid-table placements,
same scoring (grip-gap holds, wide-open release, operator confirms the
orange moved).

## 2. Steps

```text
S1 (NJ)    swap server: comm-checked kill of the Brain A server, start
           start-n16-brainB.sh (checkpoint n16_real79_top/checkpoint-10000,
           port 5555). Verify with a --dry_run ping.
S2 (Pune)  plug the C270 into the laptop; mount on the stand aimed straight
           down: table fills the frame, base enters from the right, no wall.
           DO NOT move the laptop (Brain A's camera stays aimed for the
           switch back).
S3 (NJ)    find the C270's /dev/video node (it can move on replug; the ACER
           laptop exposes 4 built-in nodes - identify by "C270" card name).
           Capture a warmed-up frame (>=40 reads), blend against the July
           overhead reference (ref56 topfront), iterate aim with the
           operator until the base/table composition matches.
S4         three scored runs: reset to rest -> operator places orange
           mid-table -> run with --rtc=true and the C270 node as front ->
           score from trace -> operator confirms where the orange ended.
S5         verdict per section 0, recorded in the campaign doc. Switch the
           server back to Brain A afterwards (A remains the base either way
           unless B sweeps 3/3 with cleaner quality than A's RTC set).
```

## 3. Scoring and comparison table (filled during S4)

```text
                    B sequential (n=10)   B + RTC (n=3)   A + RTC (n=10)
grasps                    7/10                ?/3              9/10
completions               2/10                ?/3              9/10
stalls                    2                   ?                0
overreaches               2                   ?                1 (R7 miss)
slips                     3                   ?                0
median carry              30-90 s+            ?                ~13 s
```

Three runs decide nothing to a decimal — they place B's RTC behaviour in
one of the two regimes above, which is all the decision needs.

## 4. Risks / gotchas (all previously bitten)

```text
C270 node moves on replug        identify by card name, never by number
C270 needs 20-60 warm-up frames  capture loop reads >=40 before judging
camera aim off vs training       S3's blend check gates S4; the A/B's own
                                 evidence: wrong view = policy blind
connect-time bus faults (6 so    retry once; if repeated, stop and check
far, PSU suspected)              the motor power brick before continuing
operator absent orange resets    every run needs the operator at the rig
```

## 5. Out of scope

The plate-demo recording round and its fine-tune (separate plan, next),
any change to Brain A's serving, RTC parameter tuning, more than 3 runs.
