# Fine-tune bench live trial viewer

The full live view uses the same journal-following architecture as the earlier traced π0.5 viewer. The physical client owns the cameras and arm. It writes an append-only trace. A separate read-only Rerun adapter follows that trace and never opens a camera, motor, or policy connection.

The dashboard shows:

- the exact front and wrist images recorded before each policy request;
- episode and chunk number, countdown, return-to-start state, and trace health;
- measured six-joint state before each request;
- every row of the returned 20-action prediction;
- every action passed to `robot.send_action`, including whether the client clamp changed it;
- request latency and episode/chunk plots;
- measured, predicted, and sent values for all six joints.

The implementation is custom project instrumentation, not a built-in LeRobot client default. It does not change the policy request, action chunk size, 30 Hz execution, clamps, episode cap, or return-to-start behavior.

## Files

- `results/so101_bench_20261019/bench_client.py`: physical client; `--trace-dir` enables the full trace.
- `scripts/watch_bench_trial.py`: read-only Rerun follower.
- `results/so101_lora_on_top_20261019/bench_trace_row3s_orange_live_20261031/`: first complete fine-tune 3 live-view trace, 75 observations, 75 full predictions, and 1,500 dispatched actions.

## Start the viewer before the trial

Use the existing visualization environment, not the robot client environment:

```bash
/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/.venv/bin/rerun \
  --serve-web --bind 127.0.0.1 --port 9882 --web-viewer-port 9116 \
  --server-memory-limit 1GB
```

In another terminal, point the follower at the fresh trace directory that the client will create:

```bash
cd /home/gaikwad-prakash/Documents/ChatGPT/Lerobot
/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/.venv/bin/python -u \
  watch_bench_trial.py /home/gaikwad-prakash/bench_trace_<run_name> \
  --connect rerun+http://127.0.0.1:9882/proxy
```

Open:

```text
http://127.0.0.1:9116/?url=rerun%2Bhttp%3A%2F%2F127.0.0.1%3A9882%2Fproxy
```

## Start the physical client

Add a fresh `--trace-dir` to the normal bench command. The path must not already exist; refusing an old directory prevents one run from being mixed with another.

```bash
/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/.venv-official-client-061/bin/python -u \
  /home/gaikwad-prakash/bench_client.py \
  --server 192.168.194.220:8081 \
  --port /dev/serial/by-id/usb-1a86_USB_Single_Serial_5B14114209-if00 \
  --robot-id my_so101_follower \
  --front /dev/v4l/by-id/usb-046d_C270_HD_WEBCAM_FC7A6780-video-index0 \
  --wrist /dev/v4l/by-id/usb-SunplusIT_Inc_AK-Camera_JV-video-index0 \
  --task "Grab oranges and place into plate." \
  --fps 30 --actions-per-chunk 20 --max-chunks 75 \
  --episodes 1 --auto --pause-between 30 --return-start \
  --out /home/gaikwad-prakash/bench_<run_name>.jsonl \
  --trace-dir /home/gaikwad-prakash/bench_trace_<run_name>
```

The client saves each policy-input image as JPEG 85 and appends complete JSON events with line buffering. Row S added about 8.3 MB for a 75-chunk trial. The viewer can replay a completed trace with the same command plus `--once`.
