# Disk ledger — kiran-AI90 root (1.8 TB NVMe) and the 4 TB

Started 2026-10-15. Purpose: one place that says what the big things on disk
are, why they exist, when they were removed and by whose decision, and the
rules that stop the disk from filling under a running job again.
Deleting or moving a checkpoint is RED under the lane's autonomy contract:
every removal below carries the operator's approval date.

## Why this file exists (2026-10-15)

The L4-noEMA full fine-tune was launched with checkpoints every 2,500 steps
without a disk budget. Each checkpoint turned out to be 31 GB (12 GB weights +
19 GB optimizer state), not the ~14 GB assumed; 12 of them need 372 GB against
225 GB free. Caught at step 5.8k with ~33 h to run. The lesson is a rule
(§4). The fix is a cleanup (§3) that needs the operator.

## 1. Snapshot 2026-10-15 04:40Z

```text
/            1.8T  1.5T used  225G free  (88%)   nvme0n1p2
/mnt/dynus4tb  3.6T  3.2T used  456G free  (88%)   ext4, the 4 TB
/tmp         tmpfs 30G, 0.6G used (was 24G of DYNUS scratch until 2026-10-11)

/home/kiran, largest first
  489G  lerobot_assets/         datasets, probes, checkpoints from the LeRobot era (not audited here)
  434G  sim/                    see §2
  176G  .cache/                 HF datasets (physical-intelligence/libero 33G), openpi assets 24G, uv, …
   43G  projects/
   15G  e10_ply/
```

## 2. `sim/` — 434 GB, itemised

```text
232G  pi05-fullft-orange50-20260922   the September orange full fine-tune (LeRobot, rung-4 offload)
       99G   orange45_fullft_15k_candidate/checkpoints/{005000,010000,015000}
               each = 8.8G pretrained_model (the policy: weights+config+normalisers)  KEEP
                    + 25G training_state   (optimizer moments for resume; run finished)
       66G   smoke_training/checkpoints/{000003,000005}          5-step smoke, 2026-09-23
       66G   main_worker_integration_20260923/training/checkpoints/{000002,000003}
                                                                  2-3 step integration check
       <1G   evaluations, manifests, audits, deployment records  KEEP
148G  openpi/                          this week's LIBERO work
      141G   checkpoints/
               80G  pi05_libero_low_mem_finetune/lora_libero_20261010/   9 ckpts × ~9G (6G params + 3G state)
                    → 20000 is the kept policy (396/400); others scored, kept for the curve
               61G  pi05_libero_noema/fullft_noema_libero_20261014/      31G per ckpt, GROWING
                    (run in progress: 12 ckpts planned = 372G)
       7.9G  .venv
 15G  leisaac-venv                     Isaac Lab + LeIsaac (orange sim)                 KEEP
 14G  Isaac-GR00T-n16                  GR00T serving venv (real-arm baseline)           KEEP
 12G  pi05-official-20260922           September LoRA orange baseline + offline evals   reference
9.1G  pi05-rtc-remote-draft-20261007   RTC serving draft (operator's)                   operator to judge
5.0G  pi05-fullft-probe                the LeRobot training venv (.venv312)              KEEP
<1G   leisaac-src, Isaac-GR00T, rendervenv, small probe dirs
```

## 3. Removals and moves

```text
PROPOSED 2026-10-15 (awaiting operator approval) — frees ~207 GB on root:
  rm  sim/pi05-fullft-orange50-20260922/smoke_training/checkpoints/000003            33G
  rm  sim/pi05-fullft-orange50-20260922/smoke_training/checkpoints/000005            33G
  rm  sim/pi05-fullft-orange50-20260922/main_worker_integration_20260923/training/checkpoints/000002   33G
  rm  sim/pi05-fullft-orange50-20260922/main_worker_integration_20260923/training/checkpoints/000003   33G
  rm  sim/pi05-fullft-orange50-20260922/orange45_fullft_15k_candidate/checkpoints/005000/training_state  25G
  rm  …/010000/training_state                                                        25G
  rm  …/015000/training_state                                                        25G
      (pretrained_model/ of all three orange checkpoints is KEPT — nothing evaluated or deployed is touched)
PROPOSED, same approval — frees 74 GB more, no deletion:
  mv  sim/openpi/checkpoints/pi05_libero_low_mem_finetune/lora_libero_20261010/{10000,12500,15000,17500,22500,25000,27500,29999}
      → /mnt/dynus4tb/openpi-checkpoints/lora_libero_20261010/   (20000 stays on root for serving)
PROPOSED, for the RUNNING full-FT: a watcher that, each time a new checkpoint commits,
  removes train_state/ from the previous one (12G weights kept, scoring unaffected; only
  the latest stays resumable). Remaining need drops from 310 GB to ~140 GB.

DONE
  2026-10-11  /tmp: ~24 GB of DYNUS scratch cleared by the operator (restored the Bash tool)
  2026-10-14  openpi smoke checkpoint dirs (smoke_bs*, smoke_fsdp2_*) removed by their own scripts
```

## 4. Rules (added 2026-10-15)

```text
R1  BUDGET BEFORE LAUNCH. Any run that checkpoints must state, in its launch log:
    checkpoint size × number of checkpoints vs free space. openpi full state:
    ~9 bytes/param fp32 (31 GB for 3.4B); LeRobot rung-4: ~34 GB. Measure the
    first checkpoint and re-check the arithmetic; abort or prune if short.
R2  SMOKES DO NOT KEEP CHECKPOINTS. openpi saves at the final step regardless
    of --save-interval; every smoke script must delete its exp dir on exit
    (the L4 scripts do). A 5-step checkpoint is 33 GB of nothing.
R3  CLOSE A RUN = STRIP ITS OPTIMIZER STATE. When a run is finished and its
    checkpoints scored, keep weights (+ config + normalisers) for every
    checkpoint and resume state only for the final one — with the operator's
    approval, logged here.
R4  BIG MEDIA OFF ROOT. mp4s, .rrd traces and spare checkpoints go to the 4 TB
    (/mnt/dynus4tb), never git, per the commit policy.
R5  THIS LEDGER IS UPDATED with every removal, move, or new run over 50 GB.
```
