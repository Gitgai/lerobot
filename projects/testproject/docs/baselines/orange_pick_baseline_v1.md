# orange_pick_baseline_v1 — FROZEN (2026-08-23)

The configuration that produced 9/10 full-task completions on 2026-08-20.
Never overwrite; every future checkpoint is compared against this.

checkpoint      /home/kiran/lerobot_assets/checkpoints/n16_real79_side/checkpoint-10000
                (symlink: checkpoints/orange_pick_baseline_v1; chmod a-w applied)
training data   so101_orange_89_v21_train79 (79 eps; holdout 2,8,13,14,16,54,56,60,75,80)
serving         run_gr00t_server --embodiment-tag NEW_EMBODIMENT --port 5555
client          n16_realarm_client.py @ repo commit ddd8e885
runtime         --rtc=true, jpeg_quality=92, action chunk 16 @ 30 Hz,
                depth-2 pipeline, skip-ahead + 3-tick blend
cameras         front = laptop ACER RGB /dev/video0 (identify by name, not number)
                wrist = Pi cam via proxy http://127.0.0.1:8092/frame
instruction     "pick up the orange and move it to another place"  (byte-exact)
robot           so101_follower @ /dev/ttyACM0, id my_so101_follower
evidence        traces trace_r1..r10.jsonl, frames run_frames_r1..r10 (laptop);
                record: docs/n16_rtc_plan_20260820.md (ten-run set)
link envelope   payload calls 320-390 ms = known-good; >600 ms = postpone
