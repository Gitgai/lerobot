# R — The public real-SO-101 π0.5 base: audit the data, test the checkpoint, before recording our own

Date: 2026-10-19. Status: **R0 (audit) starting; R1 ready to start; R2 optional; R3 needs a person at the arm.**
Split out of pi05_leisaac_lora_vs_fullft_plan_20261010.md Stage 3 (O3), which now points here.

## Why this comes before our own recordings
dongyoonkim/so101-pi05-base is π0.5 fully fine-tuned on 13,969 REAL SO-101 episodes merged from 156
public uploads (7.27M frames, 3 camera slots with masks, v2.1). If it already picks an orange on our
bench, Stage 3 starts from that floor and our recording becomes fine-tuning on top. Testing that is an
afternoon of arm time; recording 450 episodes is days. The sim comparison (O1) keeps its purpose —
LoRA vs full FT at matched data, scored on hundreds of seeded episodes, which a real arm cannot do —
but it can wait behind this. We have NOT evaluated this checkpoint and no published numbers were found.

## R0 — Audit the 13,969 episodes (offline, AI90, no GPU)  ← operator's question 2026-10-19
Large merged sets are only as good as their parts. Before trusting it (or training on it) we look at
EVERY episode, from metadata first and video second:
```text
R0.1  pull meta only: meta/info.json, tasks, episodes table, stats; parquet state/action streams
      (no video) → /mnt/data4tb/huggingface-cache (archive drive, ledger R4)
R0.2  provenance: map every episode to its source upload (the merge keeps source ids or episode
      ranges? read the card/README; else infer from task string + fps + camera set + length pattern);
      list the 156 sources with episode counts; which of our survey's other sets (armnet, hungho77,
      wsagi, LightwheelAI real orange) are INSIDE it already (overlap = do not double count)
R0.3  tasks: distinct instruction strings, grouped into skills (pick/place/stack/sort/push/…); counts;
      how many involve an ORANGE or any fruit; how many are our kind of pick-and-place
R0.4  cameras + rig: per source, which of the 3 slots are real vs masked; image sizes; fps (450 ep
      are 10 fps inside a 30 fps set); compare camera naming/placement with OUR rig (front + wrist)
R0.5  duplicates: exact (identical state/action streams → hash), near (same source re-uploaded
      under another name: same episode count + lengths + task strings), and degenerate episodes
      (near-zero motion, < 2 s, missing camera, NaNs)
R0.6  value verdict per source: KEEP / KEEP-WITH-CAVEAT / DROP, with the reason; a cleaned manifest
      (episode ids) is the output, plus a one-page summary table in this doc
R0.7  sample videos: 2 episodes from each of the 20 largest sources, watched (montage), to confirm
      the metadata story matches the pictures
```
Output: `results/so101_real_base_audit_20261019/` (manifest.csv, sources.csv, tasks.csv, audit.md).
Reading: if ≥ ~30% of episodes are duplicates/degenerate, the "14k" is really smaller and the
checkpoint was trained on repeats → weigh its result accordingly; if orange/fruit episodes are
few, do not expect zero-shot orange picking.

## R1 — Load and serve the checkpoint from AI90 (no arm needed)
Download dongyoonkim/so101-pi05-base; load in the LeRobot probe venv; confirm input spec (camera
slots, state dims, instruction format) against our rig's observation layout; serve over the existing
socket harness with RTC ON (RTCConfig as for the arm); one dry inference on a recorded frame from
our own August real episodes; measure latency. Ready-to-run state recorded here.

## R2 — Zero-shot in LeIsaac (optional, a HINT not a number)
Real-trained model on rendered images: confounded. 20 episodes, orange task, RTC off, logged as
"hint" — only to see whether it moves toward the orange at all.

## R3 — 20 real trials on the bench (needs a person at the arm in NJ; operator is in India)
Protocol as the September arm trials (RTC on, ~95% duty): 20 placements of the orange on a grid,
success = orange in the bowl, no contact with anything else; filmed; the pipeline flag checked
(--rtc) before blaming latency. Reading: ≥ 10/20 → start Stage 3 from this checkpoint;
< 5/20 → our own data is needed and R0 tells us what kind.

## Tracking
R0 todo→running today · R1 todo (after R0.1 pull, same day) · R2 optional · R3 blocked on presence.
Decisions: real sets are for the arm; sim sets are for the controlled comparison; never mix fps in
one run; camera placement must match the rig; archive downloads go to /mnt/data4tb.
