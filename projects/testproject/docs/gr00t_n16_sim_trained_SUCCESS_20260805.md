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

**It did NOT place.** All three `put_*_to_plate` terms stayed 0. So: grasp and
carry yes, complete the task no.

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
1. Why does it not PLACE? It grasps and carries, then loses the orange before
   the plate. Longer runs (this was 900 steps; the state machine needed ~2300 for
   three full place cycles) and multiple seeds.
2. This checkpoint is the REFERENCE for what "working" looks like in this scene.
   Any future fine-tune of ours should be compared against 0.173 m of lift, not
   against a predicate.
3. The fine-tuning plan is UNCHANGED and now better motivated: we know the target
   is achievable on this rig, because we have watched a policy hit it.
```

**Unchanged:** nothing has been tested on the real arm.
