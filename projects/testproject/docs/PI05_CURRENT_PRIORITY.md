# π0.5 lane — Current Priority and Status

Last updated: 2026-10-20

**This file is the ROUTER and the TRACKER: what is open, in what order, and
where each step stands. It is NOT a log.** Detail, gates and pre-registered
readings live in the plan docs; results get written into the plan docs'
results blocks and only the one-word status is mirrored here.
**Hard limit ~100 lines.** Status words: `todo` `next` `running` `blocked`
`done` `dropped`. Every step has an ID; the plan docs use the same IDs.

> Why this file exists: priority once lived only in chat and the top item got
> buried. When summarising open work read the item BODY in the plan doc, not
> this row — a stale row can outlive the ruling that killed it.

---

## THE QUESTION (one line)

openpi says LoRA fits a consumer card and full fine-tuning needs 80 GB. Does
the route our 32 GB card can run produce a working policy, and how does it
stand next to the route it cannot run — on LIBERO first, then on the arm's
real task.

---

## ▶ L — LIBERO: LoRA vs full fine-tune (plan: `pi05_libero_openpi_vs_ours_plan_20261010.md` · **results: `RESULTS_pi05_libero_lora_vs_fullft_20261013.md`**)

```text
ID   step                                                      status   owner/when
L1   openpi JAX stack runs on the 5090 (venv, GPU seen,        done     2026-10-10 18:15Z
     one forward pass). jax 0.5.3 sees the GPU; pi05_libero            results/pi05_libero_20261010/
     forward pass finite (10,7), 59 ms warm. Caveat: /tmp               l1_gate.log
     quota exhausted → TMPDIR must be on /home for every run.
L2   score THEIR pi05_libero full-FT checkpoint, our sim,      done     2026-10-10 18:30Z
     Spatial n=200, RTC off. → 200/200 = 100% (CI95 98.1-100),           results/pi05_libero_20261010/
     their 98.8 is inside the interval: HARNESS AGREES. 9.2 min          L2_openpi_pi05_libero_spatial_n200/
     wall. Loop: l2_eval_openpi.py (their convention, logged).
L3   train openpi LoRA on LIBERO here, 30k steps from          done     2026-10-12 13:43Z
     pi05_base. Trainable 467M of 3.40B (LoRA 50M + SigLIP 415M            bs32, 3.4 s/step, ~28 h of
     + proj 2M = openpi's own "low_mem" = "LoRA + vision encoder").         GPU incl. an 8.6 h loss to a
     Loss 0.094 → 0.014. 9 checkpoints kept (10k, 12.5k…27.5k, 29999).      host reboot at 18.8k
L4   reproduce THEIR full FT on 72 GB: as published it does    done     trained 10-14→10-16 (30k, bs 32,
     NOT fit (OOM at 66+17 GB; fsdp refused — mixed GPUs).               EMA off, ~44 h GPU 1); scored
     OPERATOR AMENDED (2026-10-14): EMA OFF, nothing else changed;        10-16 20:08Z, all 12 ckpts.
     row labelled "full FT, EMA off". bf16 stays forbidden.              ★ final 194/200 = 97.0%
     12 ckpts × 31 GB = 372 GB on root (optimizer state stripping         pooled 10k-30k 1635/1800 = 90.8%
     per ledger R3 proposed, RED).                                         curve jagged: 78.5…97.0
L5   score every checkpoint, same sim, same seeds, RTC off     done     2026-10-12 15:08Z (L3 side)
     ★ LoRA vs their full FT on LIBERO Spatial, n=200 each:                L4's row pending
       their full FT        200/200 = 100%
       our full FT, EMA off (bs 32): 2.5k 68.5 · 5k 90.5 · 7.5k 84.0 · 10k 78.5 ·
         12.5k 87.5 · 15k 93.0 · 17.5k 82.0 · 20k 95.5 · 22.5k 94.5 · 25k 92.5 ·
         27.5k 97.0 · 30k 97.0  (pooled 10k-30k 90.8% vs LoRA 97.8%)
       LoRA 10k/12.5k/15k   195 / 195 / 198
       LoRA 17.5k/20k/22.5k 195 / 199 / 190
       LoRA 25k/27.5k/30k   197 / 197 / 195      pooled 1761/1800 = 97.8%
     n=400 on 15k/20k/22.5k (2nd layout set): 98.0 / 99.0 / 96.2.
     ★ KEEP LoRA 20k (396/400). VERDICT: the 32 GB route WORKS. Our
     full FT (EMA off, bs 32) ends level with LoRA (97.0 vs 97.5-99.5)
     but its curve is far noisier; no advantage to full FT shown here. Failures = grasp-and-extract timeouts
     on the drawer task (filmed). Rerun traces per episode now recorded.
```

L6   does inference latency change success? time-faithful    done     2026-10-17 01:12Z (RESULTS §5.5)
     LIBERO mode, delay sweep, LoRA 20k, n=200/row:                      0 ms 99.0 · 100 ms 99.5 · 250 ms 95.5 ·
     plain chunking: free at 100 ms, -4 pts at 250, DEAD at 500 ms        500 ms 0.0 · 1000 ms 0.0
     (= chunk length). Operating point 300-500 ms is on the cliff →      next: same sweep with RTC ON
     RTC sweep in the LeIsaac stage.                                      (LeRobot stack, O-stage)

L7   "EMA-in-RAM full fine-tune": full FT with EMA ON, EMA    parked   2026-10-20: after the simulator work;
     copy in HOST RAM (bs 32 the only deviation left).                 plan: pi05_libero_fullft_ema_in_ram_plan_20261018.md
     only deviation left). Isolates whether L4's jagged curve             ~54 h GPU 1 + scoring; ~50-line openpi change
     (78→93→82→95) is EMA-off or batch-32. Row: "EMA on (host)".        + smoke gate; awaiting operator go
L6b  latency sweep with RTC ON (LeRobot pi0.5, same 5 delays) proposed  decides local vs remote policy for the arm
L8   batch-256 on one card IF L7 leaves the swings: gradient       parked   routes + budget in the L7 plan appendix;
     accumulation (exact, ~2 wk) or activation remat (+offloads,            optimizer-to-RAM alone only reaches ~bs 64
     exact, ~3-4 d) or a bigger machine                                     — not worth building on its own

Answers: does LoRA work here · does full FT work when WE run it · LoRA vs
full at matched data. A gap to their checkpoint is partly their 7.7M
examples: reported, not attributed.

## ▶ R — Public real-SO-101 π0.5 base: audit + test BEFORE recording our own (plan: `pi05_so101_real_base_audit_plan_20261019.md`)

```text
ID   step                                                      status   owner/when
R0   audit all 13,969 episodes of dongyoonkim/so101-pi05-base-  done     2026-10-20 (audit.md verdict):
     dataset: provenance (156 sources), tasks/skills, orange            406 tasks, cube-heavy; real orange-fruit
     count, cameras/fps vs our rig, exact+near duplicates,              ~61 ep (+part of 200); ≥4 SIM sources inside;
     degenerate episodes → cleaned manifest + verdict per source        82% of episodes = our 2-camera layout;
                                                                        450 ep at 10 fps; 1,810 ep (13%) with wrist/
                                                                        external SWAPPED; dups 1, degenerate 34 — clean
R1   download + serve dongyoonkim/so101-pi05-base from AI90    done     2026-10-19: VLASH env + author's patches;
     (input spec vs our rig, dry inference, latency)                    sane chunk on our real frame; 57 ms/call
                                                                        compiled (137 uncompiled) on the 5090
R4   cleaned manifest for OUR use: slot-swap fix (1,810 ep),   done     2026-10-20: manifest_clean.csv keeps 13,292
     sim out (304), 10-fps split (450), dups + degenerate out,           + survivor counts; feeds O3 fine-tune
     quality flags, real-orange subset listed                            (LoRA on top is the author's advice)
R2   "simulator test": the public checkpoint driving the       running  LIVE 2/2 SUCCESS zero-shot (2026-10-20 03:15Z);
     LeIsaac orange task; smoke 2 eps, live-window 2 eps,                50+50 headless scored run in progress;
     LeIsaac orange task, 50+50 seeded eps, RTC off, ground-             LeIsaac orange episodes → in-distribution;
     truth success; reuses the W0 policy wrapper over the socket
     wrapper over the socket harness; GPU 0, ~2 h                        tests what open-loop replay cannot
W0   "policy wrapper": the public π0.5 (VLASH, author's      built    2026-10-20: scripts/so101_base_policy_server.py,
     patches) behind LeRobot's gRPC async policy server,               unit so101-base-server :8080 on GPU 1; LeIsaac's
     slot mapping front→base, wrist→left_wrist                          client connected first try; consumed by
     empty_cameras=1, compiled) behind a socket, slot mapping            R2 (sim) and R3a (bench adapter)
     front→base, wrist→left_wrist; 20-step chunks
R2b  "generalisation ladder": same checkpoint zero-shot on   running  plan: pi05_so101_sim_generalisation_ladder_20261020.md
     LeIsaac LiftCube + CleanToyTable (queued behind the orange           scenes downloaded; MuJoCo venv building;
     run), then MuJoCo EnvHub envs (namenu pick-place, nexus 6)           50 eps per rung, same wrapper
R3a  "bench serving adapter": the wrapper behind the bench   proposed plan: pi05_so101_bench_adapter_plan_20261020.md
     client's Zenoh protocol + ARM-LESS verification
     (loopback replay, open-loop replay of our real episodes,           ~1 day build + 2 h; GPU 0; needs AI90's key
     remote replay from the Acer, fault cases)                          on the Acer for the remote leg
R3   "bench trials": 20 real attempts in Pune, NON-PIPELINED  blocked
     client, filmed  arm is in PUNE with the operator; needs a
                                                                        serving adapter (VLASH policy behind the
                                                                        bench client's Zenoh protocol) — operator's call
     ≥10/20 → Stage 3 starts from this checkpoint; <5/20 → record ours
```

## ▶ O — Orange task in LeIsaac (plan: `pi05_leisaac_lora_vs_fullft_plan_20261010.md`)

```text
ID   step                                                      status   owner/when
O0   verify EverNorif/so101_place_orange_isaaclab is our       todo     anytime, ~30 min
     kitchen scene (decides 120 vs 200 starting episodes)
O1a  "orange recorder": record to 450 pick-orange episodes     todo     GPU 0 or 1; can run beside the
     (log attempts, successes, s/episode from hour one;                 simulator test / adapter work
     project; stop) — sim only
O1b  train full FT (72 GB machine) + LoRA (5090), same data,   todo     after O1a, L4 box
     LeRobot; 100 seeded 3000-step eps per row, RTC off
O2   10-20 instruction variants over the 3 single-arm          todo     only if O1b is clear
     scenes; Mimic for data; 50 eps/task; one model
O3   real arm: start from dongyoonkim/so101-pi05-base,         todo     now gated by R0-R3 (plan split out
     + LightwheelAI real orange + ours; async + RTC ON                   2026-10-19); after O1b or earlier
```

Public data surveyed 2026-10-10 (plan Appendix B): ~120-200 orange episodes
in our scene; 3,300-ep 11-task Isaac Lab corpus (other scene, train-only);
~14k real SO-101 episodes incl. a 16.7k-episode full fine-tune checkpoint.

## Order of work

```text
1  ✔ L1, L2, L3, L5(LoRA) done 2026-10-10..12 — LoRA works on LIBERO
   ✔ results write-up: RESULTS_pi05_libero_lora_vs_fullft_20261013.md
2  ✔ L4-noEMA trained + scored 2026-10-16; ✔ L6 latency sweep 2026-10-17
2b EMA-in-RAM full fine-tune (GPU 1, ~2.5 d) — PARKED 2026-10-20 until the simulator work is done
2c L6b RTC latency sweep — proposed, build while L7 trains
2d ledger §7 optimizer-state strip (RED) — awaiting approval
3  openpi mirror push (needs operator: create Gitgai/openpi, 3 commands)
4  ✔ R0 + R4 audit CLOSED 2026-10-20 (95% usable; 13% slot-swap; 96 real orange) · ✔ R1
5  AWAITING GO (independent, can all start the same day):
   a  W0 wrapper (½ day) → R2 sim gate (2 h, GPU 0) → R3a adapter + arm-less gates incl. the public
      replay ladder (½-1 day) → R3 bench
      (R2 first: cheapest closed-loop evidence; a < 20% result sends us back to plumbing before any bench time)
   b  L7 full FT with EMA in host RAM, GPU 1, ~54 h (plan 2026-10-18)
   c  O0 + O1a orange recorder, GPU 0, days (plan 2026-10-10)
   d  ledger §7 optimizer-state strip (209 GB, RED) · empty Gitgai/openpi repo for the mirror
```

## Standing decisions (do not reopen without a new fact)

```text
openpi stack first, LeRobot fallback          their recipe NEVER bent to fit a card
their checkpoint evaluated, not retrained     one simulator per table
EMA-off allowed on 72 GB (2026-10-14); bf16 not  the "EMA off" label travels with the row
EMA in HOST RAM proposed (2026-10-18): same formula, moved not bent; bf16 EMA and every-k-steps EMA NOT taken
n=200 LIBERO · 100/row LeIsaac · 50/task O2   RTC off in sim; on the arm: non-pipelined first, pipelined only WITH RTC (2026-10-20)
August full-FT results not compared           LeRobot (not openpi) for the SO-101 task
DYNUS capped at 16 GB; shut it down for long runs (the old "47 GB" is stale)
```

## Standing rules for this lane

```text
E1 preflight before ANY run >1 h (preflight_features.py) · a rung is a POC
until it checkpoints AND resumes · loss is NOT a proxy for capability · state
every lever explicitly, defaults included (dtype and gradient_checkpointing
both default OFF in lerobot) · setsid for long runs · check
nvidia-smi --query-compute-apps before launching · confirm rtc_config=None
at every sim policy load · checkpoint every 2.5k steps on any run
longer than ~10 h (operator, 2026-10-11; a reboot cost 8.6 h the same day) · TMPDIR=/home/kiran/tmp in every
launched script while /tmp's quota is exhausted · never cap JAX memory below
what the smoke needs — a 0.6 fraction masqueraded as an OOM on 2026-10-10 ·
disk budget before any checkpointing run; smokes delete their checkpoints;
closed runs lose their optimizer state (DISK_LEDGER.md R1-R5, 2026-10-15) ·
long jobs run as `systemd-run --user` units, never setsid/nohup from a session
(the 2026-10-15 16:54Z app kill took setsid'd trainer+chain+watchdog with it)
```

---

## Legacy items (compressed; bodies in `pi05_training_capability_plan_20260811.md`)

```text
P0   rung 4 (fp32 Adam in host RAM) trains, checkpoints, resumes   done 2026-08-15
P1   move the display to the iGPU, frees ~1-1.9 GiB VRAM           blocked on operator (cable + reboot)
P2   8-bit vs fp32 Adam, single-variable, 24 h                     dormant — L5/O1b will
                                                                     partly answer it
P3   3g rerun (starting-checkpoint hypothesis)                     dormant, premise retracted
P4   our 89 real episodes (STEP 4)                                 superseded by O3
Sept orange full FT (15k, rung 4, 10k = candidate)                 archived: docs/september_orange_fullft/
not doing: rung 5 parameter offload (operator) · DeepSpeed (CPUOffloadAdamW is ~70 lines, verified)
```
