# *** A POLICY FINALLY PICKED UP THE ORANGE ***

Date: 2026-08-05. Checkpoint: `12e21/gr00t_n1d6_leisaac_pick_orange` (GR00T N1.6,
fine-tuned **inside LeIsaac** on this exact task). Scene
`LeIsaac-SO101-PickOrange-v0`, 900 steps, scored from simulator ground truth.

---

## 1. The result

```text
run                              d_min  d_grasp  <0.20m  gripRng  pickT  place   objLift
state machine (KNOWN-GOOD)       0.111    0.021    58%     n/a      842     16    0.1959
*** N1.6 SIM-TRAINED ***         0.111    0.029    88%    1.00      103      0    0.1730
N1.7 real-world (valid run)      0.098    0.045    96%    0.29       31      0    0.0029
Pi05 012000 (its own task)       0.130      -      71%    1.39        0      0    0.0000
```

**It lifted the orange 0.173 m — against the known-good state machine's 0.196 m.**
Not a predicate artefact, not a nudge. A grasp.

### Verified, not assumed

```text
pick_orange001: 72 TRUE steps, longest hold 59 CONSECUTIVE (steps 561-619)
   orange z:  0.9217 at rest  ->  1.0918 at peak      = +0.1701 m LIFT
   z during that single hold:  0.9188 .. 1.0918       = it rose WHILE HELD
   d_grasp at hold start: 0.039 m                     (threshold 0.05)
   net horizontal travel: 0.2601 m                    = it was CARRIED

pick_orange002: 31 TRUE steps, longest hold 23, lift +0.039 m, moved 0.115 m
   a weaker second attempt
```

The orange rose 17 cm *during a single unbroken 59-step hold* and moved 26 cm
sideways. Compare GR00T N1.7's best: predicate TRUE for 80 steps, object
displaced 0.0029 m. **The displacement metric separates these instantly, and it
is the only metric that does.**

**It did NOT place** *in that 900-step run*. All three `put_*_to_plate` stayed 0.

## 1b. *** IT PLACES. ALL THREE. THE RUN WAS JUST TOO SHORT. ***

Re-run at **3,000 steps**, everything else identical:

```text
orange   grasped        peak lift            ON PLATE      final rest vs table
003      ~448-1681      step 1667  +0.162 m  1682-1683     +0.0095 m
002      ~449-2815      step 2056  +0.190 m  2076-2224     +0.0344 m
001      ~2159-2528     step 2197  +0.187 m  2215-2532     +0.0230 m

ALL THREE put_orange00N_to_plate FIRED.
place-term steps   GR00T N1.6: 33     state machine: 16
```

The physical sequence is exactly right and it repeats three times: **grasp →
lift ~0.17-0.19 m → carry → place → release**. Each `put_*_to_plate` fires
immediately *after* that orange's peak lift, and each orange comes to rest
ABOVE its table height — sitting on the plate.

```text
=> THE "GRASPS BUT NEVER PLACES" QUESTION WAS AN ARTEFACT OF RUN LENGTH.
   This policy COMPLETES THE WHOLE TASK - three full pick-and-place cycles -
   and logs MORE place-term steps than the scripted state machine.
```

**Lesson: 900 steps is not a run, it is a snapshot.** The state machine needed
~2,300 steps for three cycles and this policy needed ~2,500. Every earlier
900-step verdict in this project describes only the first third of an episode.
Pi05 and GR00T N1.7 were both judged at 600-1500 steps — those runs are not
wrong about what they saw, but they cannot support "never does X".

---

## 2. Why this matters more than the score

```text
1. THE APPROACH IS SOUND. A policy trained in this simulator SUCCEEDS in this
   simulator. Before today every policy we had run failed, and "maybe sim
   manipulation just does not work here" was still live. It is now dead.

2. IT RE-CONFIRMS THE HARNESS from the opposite direction. The positive control
   proved our scoring detects the SCRIPTED state machine. This proves it detects
   a NEURAL POLICY doing the same thing, through a completely different serving
   path (ZMQ, LeIsaac's native n1.6 client) and a different action space
   (6-DoF joint, not 8-dim EE pose).

3. IT REFRAMES EVERY EARLIER FAILURE. Pi05 and GR00T N1.7 are REAL-WORLD-trained
   checkpoints failing in SIM. That is a genuine domain gap, not our tooling and
   not a broken metric - because a SIM-trained checkpoint on the same rig, same
   scene, same cameras, same scoring picks the fruit up.
```

---

## 3. What it cost, and the claim I got wrong

I had told the user this comparison was effectively out of reach: *"old
checkpoint eras pin old torch, which has no sm_120, so Era 1 and Blackwell
conflict."* **I asserted that instead of checking it.** The real pins:

```text
release          torch pin    sm_120 / Blackwell?
n1.5-release     2.5.1        NO   <- the claim is true ONLY here
n1.6-release     2.7.1        YES  <- 2.7.1+cu128, verified: sm_120 present
n1.7-release     2.9.0        YES
```

Checking that was one `curl` against the release tag. Had I checked first, the
7.1 GB N1.5 download would not have happened and this run would have come hours
earlier.

### The build, for reproduction

```text
git clone --depth 1 --branch n1.6-release https://github.com/NVIDIA/Isaac-GR00T
  -> ~/sim/Isaac-GR00T-n16      (our N1.7 copy is a SHALLOW clone: 1 commit, no
                                 history, and carries ONLY gr00t_n1d7 - there was
                                 no older revision to check out)
uv venv --python 3.11
uv pip install torch==2.7.1 torchvision==0.22.1 --index-url .../whl/cu128
  -> torch 2.7.1+cu128, sm_120 present  (CONFIRM THIS BEFORE GOING FURTHER)

THREE PACKAGING TRAPS, each with a cheap fix:
  tensorrt-cu13-libs  needs wheel_stub declared as a build dep
      fix: uv pip install wheel_stub setuptools wheel, then --no-build-isolation
  flash-attn==2.7.4.post1  tries to COMPILE and needs CUDA_HOME/nvcc, which this
      machine does not have
      fix: install the PREBUILT wheel - no CUDA toolkit, no sudo:
        flash_attn-2.7.4.post1+cu12torch2.7cxx11abiTRUE-cp311-cp311-linux_x86_64
      pick the abi variant with torch._C._GLIBCXX_USE_CXX11_ABI (ours: True)
  deepspeed  imported by transformers, dies on missing CUDA_HOME
      fix: uninstall it. It is a TRAINING dependency; serving does not need it.

server:
  python -m gr00t.eval.run_gr00t_server --model_path=<ckpt>/ckpt/checkpoint-10000 \
      --embodiment-tag=NEW_EMBODIMENT --port=5556
  NOTE: n1.6 wants --embodiment-tag (hyphen) and UPPERCASE NEW_EMBODIMENT.
        n1.7 accepted --embodiment_tag=new_embodiment. They differ.
  ~8.2 GB VRAM, 1,091,722,240 DiT params.
```

The whole environment took roughly an hour and needed **no sudo**.

---

## 4. No adapter of ours in the path

This run used LeIsaac's own `Gr00t16ServicePolicyClient`, not our N1.7 adapter.
That is the strongest part of the result: **our code is not in the measurement.**

It also independently corroborates the hardest-won lesson of the N1.7 work — the
native client does the unit conversion (`convert_leisaac_action_to_lerobot`) and
does **no** relative-action composition, exactly matching what probing the wire
proved for N1.7. See `gr00t_n17_sim_evaluation_20260805.md` section 2b.

---

## 5. Next

```text
1. ANSWERED - it DOES place, all three. See 1b. The open question is closed and
   the cause was our run length, not the policy.
2. RE-RUN THE LONG-STANDING VERDICTS AT 3,000 STEPS. Pi05 (600-1500) and GR00T
   N1.7 (900) were both judged on partial episodes. Neither showed any sign of
   acquisition, so this is unlikely to overturn them - but "never grasps" is a
   claim we have not actually earned at that horizon, and the run is cheap.
3. This checkpoint is the REFERENCE for what "working" looks like in this scene:
   0.17-0.19 m of lift, three complete pick-and-place cycles, ~2,500 steps.
   Compare any future fine-tune of ours against THAT, not against a predicate.
4. Reliability is UNMEASURED: n=2 runs, no seed control, and the two differed
   (the 900-step run got one strong grasp; this one completed everything). Flow
   matching samples stochastically. Several seeded runs would tell us the real
   success rate.
```

**Unchanged:** nothing has been tested on the real arm.
