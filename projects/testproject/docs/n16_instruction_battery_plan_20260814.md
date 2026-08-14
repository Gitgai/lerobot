# Plan: does the client's instruction string stop the policy finding the orange?

Created 2026-08-14. Status: **not started, awaiting go-ahead.** ~30 min, no hardware.

---

## 0. Why this, and why now

The operator watched the Aug 8 run and reports: **the arm moved, but did not try
to reach the orange, and never picked one.**

That observation is the single most discriminating fact we have, and **nothing
tested so far reproduces it.** Every condition run to date produces a policy that
still tries:

```text
condition                 closest approach   still reaches?
canonical (86%)               0.015 m            yes
staleness 740 ms (22%)        0.016 m            yes - grips 2-3 of 3 every run
wrist off-task (0%)           0.09-0.10 m        NO
```

Only wrist-off-task matches "does not reach" — and that is ruled out for the real
rig: the gripper-in-wrist-frame measurement shows the camera moved **1.6 deg**
across the whole Aug 8 run. The mount held.

⇒ **The cause of the observed failure is still unidentified.** This tests the
  cheapest remaining candidate.

## The candidate

GR00T is instruction-conditioned: the sentence is fed in as
`annotation.human.task_description` and changes behaviour.

```text
  REAL CLIENT   "Grab orange and place into plate"
                n16_realarm_client.py:184, the default, used on Aug 8

  EVERY SIM RUN the environment's own cfg.task_description
                a different sentence, used by all ~100 sim runs to date
```

**The exact string the arm sends has never been through the simulator.** Flagged
as "the cheapest untested candidate remaining" on 2026-08-11 and not run since.

A policy given a sentence that does not map onto what it sees would produce
smooth motion from its priors with no object-directed component — moves, does not
reach. That is the observed signature.

### Why not lighting too

Originally planned as a 4-arm battery including a dimmed condition, on the
measurement that the object appeared at brightness 91 versus 219 in training
(whole scene 100 vs 167). **Dropped on the operator's objection, correctly:** the
lighting has since been fixed — the wrist camera went 18 -> 110 and the same room
lights feed the front view. Testing it now would mostly confirm a solved problem.
Its only remaining value is predictive, which does not justify half a battery.

---

## 1. Design

```text
  canonical    the environment's own sentence     n=6   control
  realInstr    --policy_language_instruction="Grab orange and place into plate"
                                                  n=6
```

Interleaved, same session, same server. 12 runs, ~30 min.

One variable. The eval script's own help text warns that
`--policy_language_instruction` should be overridden **only** for a deliberate
instruction experiment — which this is.

---

## 2. The number that matters

Not the score. **`d_grasp_min`** — how close the grasp frame ever gets to an
orange. That is what separates "tried and failed" from "never tried", and it is
the only column that speaks to the operator's observation.

```text
  realInstr scores ~0 AND d_grasp_min stays ~0.10 m
      -> the Aug 8 signature reproduced for the first time. Cause identified.
  realInstr scores ~0 BUT d_grasp_min ~0.015 m
      -> another completion failure. Does NOT match. Report as such.
  no significant change
      -> instruction ruled out. Search moves on.
```

All three outcomes are worth the 30 minutes. The middle one is the trap: a score
drop alone would look like success and would not be.

---

## 3. What this does NOT test

```text
  - whether the TRAINING data used a different sentence again. The checkpoint
    trained on so101_pick_orange_v2.1, which is not on this machine, and the
    89-episode set's tasks.parquet carries only a task_index, no text. So the
    string the policy actually learned is UNKNOWN.
  - the real object's appearance vs training. They look different (matte pebbled
    sphere vs glossy flattened), but measured hue is similar (11 vs 16) and the
    dominant difference is brightness. Not settled, not tested here.
```

If the instruction comes back null, recovering the training sentence from
`so101_pick_orange_v2.1` becomes the next step — and that dataset needs locating.

---

## 4. Method note

Carry the harness lessons already paid for:

```text
  timeout -k 30    Isaac Sim blocks SIGTERM; a plain timeout was ignored for 45 min
  kill by PID      `pkill -f run_gr00t_server` matches the calling shell and
                   killed it twice
  interleave       cross-session comparison has produced a wrong conclusion here
  n=6, not n=1     a single run produced a wrong conclusion here
```
