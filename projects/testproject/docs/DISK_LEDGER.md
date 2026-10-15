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
/mnt/dynus4tb  3.6T  3.2T used  456G free  (88%)   ext4, DYNUS flight data
/mnt/data4tb   3.6T  ~0 used   3.6T free          ext4, label data4tb — EMPTY archive drive (found 2026-10-15)
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
PROPOSED 2026-10-15 — superseded by the DONE block below (rows 1, 3 executed; row 2 executed as a MOVE):
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

DONE 2026-10-15 (operator approved rows 1 and 3 of the proposal; row 2 changed from
"delete" to "move" at the operator's request; no compression — measured zstd ratio 88.7%)
  05:14Z  rm   the four September smoke checkpoints                                   −132 GB root
  05:16Z  mv   8 spare LoRA checkpoints → /mnt/dynus4tb (WRONG drive, see below)      −74 GB root
  05:18Z  mv   the same 8 → /mnt/data4tb/openpi-checkpoints/lora_libero_20261010/   (symlinks under
          ~/sim/openpi/checkpoints/... re-pointed; 20000 stays on root; readable in place)
  05:20Z  mv   orange45 {005000,010000,015000}/training_state → /mnt/data4tb/pi05-fullft-orange50-20260922/...
          (symlinks left; pretrained_model untouched; all three still resumable)       −75 GB root
  result  root 222 → 496 GB free (72% used); data4tb 144 GB used of 3.6 TB; dynus4tb back to 524 GB free
  scripts results/pi05_libero_20261010/disk_cleanup_20261015.sh, disk_relocate_data4tb_20261015.sh (logs beside them)
  the running L4-noEMA job (310 GB still to write) now fits without stripping anything
  ⚠ there are TWO 4 TB drives: /mnt/data4tb (label data4tb, was EMPTY) is the archive drive;
    /mnt/dynus4tb is the DYNUS flight-data drive (86% full) — do not park checkpoints there.
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
R4  BIG MEDIA OFF ROOT. mp4s, .rrd traces and spare checkpoints go to the
    ARCHIVE 4 TB (/mnt/data4tb), never to /mnt/dynus4tb and never to git.
R5  THIS LEDGER IS UPDATED with every removal, move, or new run over 50 GB.
```

## 5. INCIDENT 2026-10-15 15:30Z — /var/log/syslog at 160 GB and growing 8 GB/h

Found by the hourly health heartbeat: root free fell 8-9 GB/h between checkpoints.
Cause: the Claude desktop app on AI90 (pid 7727, started at boot 2026-10-13 23:58 local,
66% CPU) loops on "GPU process launch failed: error_code=1002" and rsyslog writes every
line: 2 MB/s into /var/log/syslog (160 GB at 15:30Z; journald capped at 4 GB).
Projection at 15:30Z: 325 GB free; 7 checkpoints x 31 GB = 217 GB still to write
(~9 GB/h) + 8 GB/h of log = ~17 GB/h -> root FULL in ~19 h, before the run ends (~22 h).
Cannot be fixed from this account: syslog is root-owned; the desktop app is the PARENT
of this Claude Code session (killing it kills the session). Needs the operator:
  sudo truncate -s 0 /var/log/syslog                      # frees 160 GB at once
  printf ':msg, contains, "GPU process launch failed" stop\n' | sudo tee /etc/rsyslog.d/05-claude-desktop-gpu-flood.conf
  sudo systemctl restart rsyslog                          # stops the growth, session survives
(Restarting the desktop app would also stop it but ends this session.)
Fallback if neither can happen in time: move landed full-FT checkpoints to /mnt/data4tb
behind symlinks as the LoRA spares were (RED, needs approval).

UPDATE 16:59Z: the operator killed the Claude desktop app (pid 7727) at ~16:54Z. The syslog flood
stopped (0 kB/s since; file static at 165 GB — truncation still needed, root). Side effect: the kill
took the whole process tree, trainer included (step 14.7k; last ckpt 12500). Resumed 16:59Z as
systemd user units. Budget now: 310 GB free vs 7 × 31 = 217 GB to write → fits (~90 GB margin),
no further log growth assumed; the new desktop app (pid 1398552, 12:56 local) is NOT looping.
DONE ~17:00Z (operator, root): /var/log/syslog truncated (165 GB → 0) and rsyslog drop rule
/etc/rsyslog.d/05-claude-desktop-gpu-flood.conf installed. Root 310 → 470 GB free. Incident §5 closed.

## 6. NOTE 2026-10-15 20:30Z — host RAM at checkpoint time (resumed run)
The 15k save (first since the resume) pushed swap from 18 to 50 GB of 63 for ~1 min with
500-700 MB/s of swap traffic; trainer unit peak = 39 GB RSS + 37 GB swap (systemd accounting).
Orbax stages the whole 31 GB train state in host memory to write it; the resumed process seems to
hold more host memory than the original (pre-kill saves showed swap ≤8 GB). The save committed
at 20:31Z and the rate returned to 5.1 s/step; swap settled at 22 GB. Headroom: 59 GB RAM +
63 GB swap vs ~76 GB peak → OK but not comfortable; 6 saves to go. Docker/DYNUS containers hold
only MBs; the 11 GB /tmp scratch (DYNUS) is the one reclaimable block if it gets tight.
