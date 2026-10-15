# September 2026 orange full fine-tune — archived record

Copied 2026-10-15 from `/home/kiran/sim/pi05-fullft-orange50-20260922/` (not a git
repo) so the record survives that folder's cleanup (see `../DISK_LEDGER.md`).

What it was: π0.5 (LeRobot port, 4.14B params, rung-4 host-RAM AdamW) fully
fine-tuned on 36 real SO-101 orange episodes, 15,000 updates, 2026-09-23/24.
Outcome: trained in 12 h 9 min; checkpoints 5k/10k/15k all passed structural and
fresh-process inference checks; 10k had the best offline full-sequence action
agreement and was the deployment candidate; 32 network predictions matched the
offline reference exactly; no physical trial; LoRA comparison excluded by the
operator at the time. Read the PI05_*.md files in date order; `records/` holds
the JSON reports and configs they cite (no checkpoints, no .npz).

The weights of the three checkpoints stay on disk at
`…/orange45_fullft_15k_candidate/checkpoints/{005000,010000,015000}/pretrained_model`.
