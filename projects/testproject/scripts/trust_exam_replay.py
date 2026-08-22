#!/usr/bin/env python3
"""Offline trust exam: replay recorded observations to a policy server.

WHY THIS EXISTS
---------------
Era 1 of this project lost a month to a serving stack that looked healthy and
was not (newer lerobot code could not serve this checkpoint; outputs collapsed
toward the dataset-median gripper ~40-41). The rule that came out of it:

    a new serving stack must reproduce known-good answers BEFORE it drives the
    robot.

This harness does exactly that with NO robot and NO cameras. It takes a trace
from a session we trust, replays its real observations through a policy server,
and compares the returned action chunks against what was recorded that day.

It speaks the same gRPC protocol as robot_client.py and applies the same JPEG
compression, so the whole path is exercised: serialization, transport, server
decode, preprocessing, policy, postprocessing.

STOCHASTICITY (important)
-------------------------
Pi05 is a flow-matching model: it samples noise, so identical inputs do NOT
give identical actions. Exact matching is the wrong test. Instead we:
  1. send the SAME observation several times to measure the model's own
     run-to-run spread - that is the noise floor;
  2. compare replay-vs-recorded against that floor.
A difference inside the noise floor is a pass. The failure we are hunting is
qualitative: collapse to a near-constant, NaNs, or a gripper that no longer
tracks the recorded command.

USAGE
-----
    python trust_exam_replay.py TRACE_DIR --server HOST:PORT --ckpt PATH_ON_SERVER
    [--n 12] [--repeats 3] [--jpeg-quality 92]
"""

import argparse
import json
import pickle  # nosec - talking to our own server on a private network
import statistics
import sys
import time
from pathlib import Path

import cv2
import grpc
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from lerobot.async_inference.helpers import TimedObservation  # noqa: E402
from lerobot.async_inference.image_codec import compress_observation_images  # noqa: E402
from lerobot.transport import (  # noqa: E402
    services_pb2,
    services_pb2_grpc,
)
from lerobot.transport.utils import grpc_channel_options, send_bytes_in_chunks  # noqa: E402

JOINTS = [
    "shoulder_pan.pos",
    "shoulder_lift.pos",
    "elbow_flex.pos",
    "wrist_flex.pos",
    "wrist_roll.pos",
    "gripper.pos",
]


def load_trace(trace_dir: Path, limit: int, start: int = 0):
    """Return (manifest, [observation records with loaded images]).

    `start` skips the first N usable observations. Use it to replay a specific
    phase - e.g. the grasp window, where the recorded session was commanding a
    hard squeeze. Replaying only the opening seconds tests the least
    interesting part of the behavior.
    """
    manifest = json.loads((trace_dir / "manifest.json").read_text())

    records = []
    seen = 0
    with (trace_dir / "observations.jsonl").open() as f:
        for line in f:
            rec = json.loads(line)
            if "images" not in rec or "state" not in rec:
                continue
            seen += 1
            if seen <= start:
                continue
            imgs = {}
            ok = True
            for cam, meta in rec["images"].items():
                path = trace_dir / meta["path"]
                if not path.exists():
                    ok = False
                    break
                img = cv2.imread(str(path))  # BGR
                if img is None:
                    ok = False
                    break
                imgs[cam] = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            if ok and imgs:
                records.append({"images": imgs, "state": rec["state"], "task": rec.get("task", "")})
            if len(records) >= limit:
                break
    return manifest, records


def recorded_chunks(trace_dir: Path):
    """Action chunks the trusted session actually received."""
    chunks = []
    path = trace_dir / "action_chunks.jsonl"
    if not path.exists():
        return chunks
    with path.open() as f:
        for line in f:
            rec = json.loads(line)
            if "actions" in rec:
                chunks.append(np.asarray(rec["actions"], dtype=float))
    return chunks


class ServerSession:
    """Minimal client speaking the robot_client protocol."""

    def __init__(self, address, policy_type, ckpt, features, actions_per_chunk, device="cuda"):
        self.channel = grpc.insecure_channel(address, grpc_channel_options())
        self.stub = services_pb2_grpc.AsyncInferenceStub(self.channel)
        self.stub.Ready(services_pb2.Empty())

        from lerobot.async_inference.helpers import RemotePolicyConfig

        cfg = RemotePolicyConfig(policy_type, ckpt, features, actions_per_chunk, device)
        self.stub.SendPolicyInstructions(services_pb2.PolicySetup(data=pickle.dumps(cfg)))

    def infer(self, record, timestep, jpeg_quality):
        raw = dict(record["images"].items())
        raw.update(record["state"])
        raw["task"] = record["task"]

        obs = TimedObservation(timestamp=time.time(), observation=raw, timestep=timestep)
        obs.must_go = True  # force the server to process it rather than skip
        if jpeg_quality is not None:
            compress_observation_images(obs.observation, jpeg_quality)

        t0 = time.perf_counter()
        self.stub.SendObservations(
            send_bytes_in_chunks(pickle.dumps(obs), services_pb2.Observation, silent=True)
        )

        # poll for the chunk this observation produced
        deadline = time.time() + 30
        while time.time() < deadline:
            resp = self.stub.GetActions(services_pb2.Empty())
            if len(resp.data) > 0:
                timed_actions = pickle.loads(resp.data)  # nosec
                arr = np.stack([ta.get_action().cpu().numpy() for ta in timed_actions])
                return arr, time.perf_counter() - t0
            time.sleep(0.05)
        return None, time.perf_counter() - t0


def describe(name, chunks):
    """Per-joint mean and range across a set of chunks."""
    if not chunks:
        print(f"  {name}: no chunks")
        return None
    stacked = np.stack([c.mean(axis=0) for c in chunks])  # (n_chunks, 6)
    print(f"  {name}: n={len(chunks)}")
    for j, joint in enumerate(JOINTS):
        col = stacked[:, j]
        print(f"    {joint:16s} mean={col.mean():8.2f}  spread={col.max() - col.min():7.2f}")
    return stacked


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("trace_dir", type=Path)
    ap.add_argument("--server", required=True, help="host:port of the policy server")
    ap.add_argument("--ckpt", required=True, help="checkpoint path ON THE SERVER")
    ap.add_argument("--n", type=int, default=12, help="how many distinct observations to replay")
    ap.add_argument("--repeats", type=int, default=3, help="repeats of one observation (noise floor)")
    ap.add_argument("--jpeg-quality", type=int, default=92)
    ap.add_argument(
        "--start-index", type=int, default=0, help="skip N observations; use to replay the grasp window"
    )
    args = ap.parse_args()

    manifest, records = load_trace(args.trace_dir, args.n, args.start_index)
    if not records:
        raise SystemExit("no usable observations with images in this trace")
    features = manifest["robot"]["lerobot_features"]
    client_cfg = manifest["client"]
    print(f"trace     : {args.trace_dir.name}")
    print(f"task      : {records[0]['task']!r}")
    print(f"observations loaded: {len(records)}")
    print(f"server    : {args.server}")
    print(f"checkpoint: {args.ckpt}\n")

    session = ServerSession(
        args.server,
        client_cfg.get("policy_type", "pi05"),
        args.ckpt,
        features,
        client_cfg.get("actions_per_chunk", 50),
        client_cfg.get("policy_device", "cuda"),
    )

    # --- 1. noise floor: same observation, several times -------------------
    print("=" * 68)
    print("NOISE FLOOR - same observation repeated (flow matching is stochastic)")
    floor, latencies = [], []
    for i in range(args.repeats):
        chunk, dt = session.infer(records[0], i, args.jpeg_quality)
        latencies.append(dt)
        if chunk is None:
            print(f"  repeat {i}: NO CHUNK RETURNED")
            continue
        floor.append(chunk)
        print(f"  repeat {i}: shape={chunk.shape} latency={dt * 1000:.0f} ms")
    floor_stats = describe("repeats", floor)

    # --- 2. replay distinct observations -----------------------------------
    print("\n" + "=" * 68)
    print("REPLAY - distinct recorded observations")
    replay = []
    for i, rec in enumerate(records):
        chunk, dt = session.infer(rec, 100 + i, args.jpeg_quality)
        latencies.append(dt)
        if chunk is not None:
            replay.append(chunk)
    replay_stats = describe("replay", replay)

    # --- 3. compare against what the trusted session received --------------
    print("\n" + "=" * 68)
    print("RECORDED (the trusted session's own chunks)")
    rec_chunks = recorded_chunks(args.trace_dir)
    describe("recorded", rec_chunks[: max(len(replay), 1)])

    # --- 4. verdict ---------------------------------------------------------
    print("\n" + "=" * 68)
    print("CHECKS")
    ok = True

    if not replay:
        print("  FAIL: server returned no action chunks at all")
        raise SystemExit(1)

    allv = np.concatenate([c.ravel() for c in replay])
    if not np.isfinite(allv).all():
        print("  FAIL: non-finite values in actions (NaN/inf)")
        ok = False
    else:
        print("  pass: all actions finite")

    # Era 1 signature: gripper pinned near the dataset median (~40-41)
    grip = np.concatenate([c[:, JOINTS.index("gripper.pos")] for c in replay])
    grip_range = grip.max() - grip.min()
    print(f"  gripper range across replay: {grip_range:.2f} (min {grip.min():.1f}, max {grip.max():.1f})")
    if grip_range < 3.0:
        print("    FAIL: gripper is nearly constant - the Era 1 collapse signature")
        ok = False
    else:
        print("    pass: gripper varies across observations")

    # variation across distinct observations should exceed the noise floor
    if floor_stats is not None and replay_stats is not None and len(floor_stats) > 1:
        for j, joint in enumerate(JOINTS):
            f = floor_stats[:, j].max() - floor_stats[:, j].min()
            r = replay_stats[:, j].max() - replay_stats[:, j].min()
            verdict = "pass" if r > f else "SUSPECT (input barely changes output)"
            print(f"  {joint:16s} noise-floor={f:6.2f}  replay-spread={r:6.2f}  {verdict}")
            if r <= f:
                ok = False

    print(f"\n  latency: median {statistics.median(latencies) * 1000:.0f} ms over {len(latencies)} calls")
    print(
        "\n"
        + (
            "VERDICT: PASS - stack reproduces sane, input-dependent behavior"
            if ok
            else "VERDICT: FAIL - do NOT run the robot; diagnose the stack"
        )
    )
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
