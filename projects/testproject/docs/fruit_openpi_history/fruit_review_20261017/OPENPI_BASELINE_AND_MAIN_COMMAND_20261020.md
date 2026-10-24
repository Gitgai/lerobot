> Historical source snapshot copied on 24 October 2026 for repository consolidation. Original: `/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_review_20261017/OPENPI_BASELINE_AND_MAIN_COMMAND_20261020.md`. Statements below describe their recorded dates, not fresh runtime checks. Relative links to excluded evidence are now absolute Acer paths; that evidence was not copied or pushed. Do not run historical commands without checking the current task-specific status.

# Full baseline and staged main command — 20 October2026

## Completed execution — current status

The baseline, transition check, preflight, 5,000 main updates and all five full checkpoint evaluations completed successfully. Main launch to completion was approximately 9h32m33s, including validations and saves, excluding the earlier baseline. All five checkpoints remain saved. [Comparison and candidate recommendation](OPENPI_FRUIT_CHECKPOINT_SELECTION_20261020.md) supersedes the queued/launch-pending descriptions below, retained as execution history. Do not relaunch this completed run.

## User approval and automatic execution — supersedes manual-launch wording below

The user explicitly approved proceeding with training and asked not to be asked repeatedly for permission. **The agreed5,000-update LoRA-plus-vision run is authorized.** Further routine approval is not required for this fixed workflow. Stop on a failed check or material change of method/budget/data, rather than silently changing settings.

An AI90 one-shot supervisor, `launch_approved_training.py`, has been launched detached from SSH. It waits for the existing full baseline to complete and its process to exit, verifies complete baseline counts, runs `check_train_eval_transition.py`, runs main preflight, then automatically executes `train_fruit_main.py --run`. The transition check uses two disposable training updates around33 held-out observations, without saving altered weights. This verifies that the persistent training loader and training state can continue after evaluation.

**Current launch state: queued behind the running baseline, not yet performing main-run updates.** Live status is `approved_launch_status.json`; supervisor log `approved_supervisor.log`. Subsequent logs are `approved_transition.log`, `approved_preflight.log`, and `approved_main_training.log`. The status records child PIDs and failure details. Duplicate supervisors are locked out, prior runs are not overwritten, unexpected GPU allocation stops the sequence, and no modified-config retry is attempted. This is a one-shot local job sequence, not a recurring watcher or a promise of periodic notifications.

If intervention is needed, inspect the current supervisor/child PIDs and command lines before stopping only this workflow. Stopping a supervisor alone is not a guarantee that an already-launched child has stopped. Preserve completed checkpoints and logs; do not use broad process-kill or deletion commands.

## Current execution

Full held-out **general-base, zero-update baseline launched** on AI90, PID1520123 at launch. This is evaluation, not training. It uses the same seeded reference trainer initialization (seed1000, generalπ0.5 base plus untrained LoRA factors), casts model parameters to bfloat16 as official inference does, and applies the verified fruit training-only normalization. No optimizer updates are performed.

Scope: all10,307 held-out timestamps:8,511 orange /1,796 tomato,11 complete retained episodes. Per-fruit/episode MAE in arm degrees and gripper points; padding excluded. No robot access.

Environment: `/home/kiran/sim/openpi/.venv/bin/python`.
Stage: `/home/kiran/sim/openpi-fruit-prep-20261020-0tn2mX`.
Only GPU UUID `GPU-9245300a-3a82-0401-5417-dbeb319e5858` is visible.

Files in staging:

- `base_full.log`: progress every100 observations and failures.
- `base_full_result.manifest.json`: full preselected observation list.
- `base_full_result.progress.jsonl`: completed observation metrics, flushed by closing each append.
- `base_full_result.json`: only written when the whole evaluation completes. Its absence means completion is not established.

The baseline process was launched with `nohup`, disconnected stdin and a log file so an SSH-session close does not terminate it. The separately launched approved supervisor now handles subsequent checks and training automatically. No recurring watcher was created. Interrupted partial results must not be labeled a full baseline; the present evaluator does not resume a partial output automatically.

## Repeatability investigation

Two fresh-process captured evaluations:33/33 decoded input+noise hashes matched. Every immediate same-process repeated prediction matched exactly (maximum delta0). Cross-process maximum individual target difference:0.48837 arm degrees /0.11012 gripper points. The earlier0.01618-degree number described a difference in an **aggregate error score**, not maximum joint-target change.

Evidence: `captured_repeat_1.json`, `captured_repeat_2.json`, `captured_repeat_analysis.json`. This narrows the observed variation to inference execution across processes rather than different decoded inputs/noise. It does not prove a specific GPU kernel, compiler option or global variation bound.

Do not require bitwise identity as a new mandatory official rule. Do not rank nearly tied checkpoints on tiny single-run score differences. Repeat close comparisons with the same held-out manifest/seeds and report the observed spread; if scores trade off between fruits, report that rather than declaring a universal winner. No precision or kernel flags were silently changed to force agreement.

## Approved main entry point — queued, not yet training

`train_fruit_main.py` reuses official initialization, loss/optimizer update and checkpoint functions. It retains a continuous shuffled training loader across validation pauses, rather than restarting the first batches after every checkpoint.

- 5,000 updates, batch32, horizon30; general-base initialization, not continuation of the disposable smoke/throughput tests.
- Same agreed LoRA+vision filter, EMAoff,500-update warmup and5k cosine schedule.
- Full resumable checkpoints at actual completed updates1000/2000/3000/4000/5000. All five retained; nominal47.6GB based on measured9.51GB smoke checkpoint, plus reports and temporary save space.
- Full10,307-timestamp per-fruit evaluation after each checkpoint using bf16 inference from current weights. Baseline remains separate.
- Flags simultaneous worsening across two successive evaluations; no silent budget extension, oversampling, motor changes or automatic modified retries.
- Default invocation is preflight only. It refuses to run without a completed full baseline and refuses an existing output directory. Main-loop evaluation coexistence has not yet been exercised end to end; do not call the launcher fully verified merely because its components passed separately.

Preflight command (after baseline completes):

```bash
CUDA_VISIBLE_DEVICES=GPU-9245300a-3a82-0401-5417-dbeb319e5858 \
XLA_PYTHON_CLIENT_MEM_FRACTION=0.9 HF_HUB_OFFLINE=1 \
/home/kiran/sim/openpi/.venv/bin/python \
/home/kiran/sim/openpi-fruit-prep-20261020-0tn2mX/train_fruit_main.py
```

The main-run command is the same with `--run`. **The approved supervisor will invoke it automatically after the baseline, transition check and preflight pass; do not launch a duplicate manually.** No overwrite/resume flag is provided; recovery from a stopped main run must be explicitly reconciled with saved state and loader position.

Output root:
`/home/kiran/sim/openpi-fruit-prep-20261020-0tn2mX/checkpoints/pi05_fruit55_lora_vision/fruit55_lora_vision_5k`.

Training-only timing is approximately5h18m from the30-update benchmark. Add five full validations, initialization and saves. A final end-to-end estimate awaits full-baseline runtime. Zero-update baseline or smoke predictions do not establish robot success or a90% success guarantee.
