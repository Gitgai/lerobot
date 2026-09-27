# Live visualization plan (rerun) — GR00T trials, replays, teleop

Living doc. Created **2026-09-26**. Goal: replace after-the-fact snapshot+trace
forensics with a **live view (cameras + joint/grip plots + fault flags)** viewable
remotely from the GPU box or a browser, during trials/replays/teleop.

Motivation: this session's whole diagnosis chain — the grip-min trace, the voltage
sag, the exact tick a gripper fault fired — was reconstructed *after* each run from
`trace.jsonl` + still frames. A live grip plot + camera + Status flag would have
shown all of it as it happened. Live view = faster iteration and faults caught in
the act, not autopsied.

---

## What exists today (verified 2026-09-26, against the installed lerobot + rerun 0.26.2)

```text
lerobot-dataset-viz     RECORDED datasets only (--repo-id/--episode-index). No live source.
--display_data          LIVE rerun on lerobot's own commands (record / teleoperate / rollout).
                        Calls init_rerun() -> rr.log() images + state each control step
                        (utils/visualization_utils.py).
REMOTE viewing          ALREADY supported: lerobot_record.py:334
                          init_rerun(ip=cfg.display_ip, port=cfg.display_port)
                        -> with --display_ip/--display_port it connect_grpc()s to a remote
                           viewer; without them it rr.spawn()s a LOCAL GUI.
rerun 0.26.2 API        serve_web, serve_web_viewer, serve_grpc, connect_grpc, GrpcSink,
                        start_web_viewer_server, spawn  (all present)
our GR00T client        n16_realarm_client.py has NO rerun at all -> no live view for the
                        POLICY trial path (the one that matters most).
```

## The one real constraint: the Acer is headless (SSH)
`rr.spawn()` opens a viewer window **on the Acer's screen**, which we can't see over
SSH. So every path below must either (a) `connect_grpc` to a viewer running where a
human/agent can see it, or (b) `serve_web` so it's viewable in a **browser** over
ZeroTier. Browser is preferred: the agent can open it in the Browser pane and the
operator can open the same URL.

```text
hosts (ZeroTier)   AI90 192.168.194.220   |   Acer 192.168.194.228
```

---

## Plan (phased, smallest useful first)

### Phase 0 — prerequisites
- rerun 0.26.2 installed on the Acer venv. DONE.
- Cameras ON (the "camera drop" on 2026-09-26 was the front cam simply not powered
  on, not flaky hardware). DONE.
- Power fix (STS3215 at 7.4 V, not 5 V) is parked but INDEPENDENT of live-viz — do
  live-viz work regardless; it will make the power test easier to watch.

### Phase 1 — Quick win: live view for lerobot-native commands (NO code change)
Prove the remote pipeline end to end using a command that already supports it.
```text
1. Start a viewer we can see:
     option A (browser):  on the Acer, a tiny script: rr.init("live"); rr.serve_web()
                          -> open the served URL in the Browser pane / operator browser
     option B (grpc):     run `rerun` viewer on AI90/laptop; note its grpc port
2. Drive a command with remote display:
     lerobot-teleoperate ... --display_data=true --display_ip=<viewer> --display_port=<port>
   (replay: confirm whether lerobot-replay exposes --display_data in this version;
    record/rollout/teleoperate are confirmed. If replay lacks it, use teleop for the
    Phase-1 proof.)
Success: live cameras + state scalars appear in the browser/viewer from the Acer.
```

### Phase 2 — Add rerun to the GR00T client (the main deliverable)
`n16_realarm_client.py` is the policy-trial path and has no rerun. Add it, mirroring
lerobot's own pattern so it behaves identically and stays OFF by default.
```text
- new CLI fields:  display_data: bool = False, display_ip: str|None, display_port: int|None
- on start (if display_data):  init_rerun(session_name="n16_trial",
                                          ip=display_ip, port=display_port)
  (reuse lerobot.utils.visualization_utils.init_rerun; or serve_web when no ip/port)
- in the RTC loop, once per chunk, rr.log:
    front + wrist images        (the adapter already has obs["front"]/["wrist"], ~line 191-195)
    6 joint positions + gripper.pos  (state, ~line 198-199)  -> the LIVE grip trace
    action0 (commanded) vs state (executed)  -> tracking error live
    rtt_ms, chunk_age_ms, starved_ticks      -> RTC health live
    Status register (fault flags)            -> see a voltage/overload fault the INSTANT it fires
- default OFF: a scored trial with display_data unset logs nothing and is byte-for-byte
  the current behaviour.
```

### Phase 3 — Wire into the trial runner + auto-open
```text
- so101_trial_runner.py: pass through --display_data/--display_ip/--display_port to the
  client command (execute(), ~line 193-205 where the client argv is built).
- convenience: when display_data is on, print/open the web-viewer URL so the operator
  (and the agent's Browser pane) can jump straight to it.
```

---

## What to log (so the view answers the questions we actually ask)
```text
cameras     front + wrist            see approach/grasp/place live
grip.pos    the grip trace, live     the single best predictor of outcome this whole project
joints x6   state vs action0         spot undershoot / tracking error (undertorque) live
rtt/age     starved_ticks            RTC pipeline health (duty) live
Status      per-motor fault byte     a voltage(1)/overload(32) fault shows the moment it trips
```
That set turns every lesson from this session into a real-time readout.

## Guardrails
```text
- display_data OFF for SCORED trials: perf + reproducibility. A scored number must come
  from the un-instrumented path.
- Do NOT slow the RTC control loop: rerun logging is async, but image encodes are heavy.
  Throttle -> log images every Nth chunk (e.g. 2-3 Hz), downscale logged images, keep
  scalars every chunk (cheap). Never block the control thread on a log call.
- Camera/USB bandwidth is already tight (2x 640x480 MJPEG + arm serial on one controller).
  Logging full-res images adds load -> downscale for the viewer.
- Keep the log calls off the safety path; a viewer hiccup must never affect motor commands.
```

## Success criteria
Watch a **live GR00T trial** — front+wrist cameras, a live grip-position plot, joint
tracking, RTC duty, and motor fault flags — in a **browser on the GPU box**, in real
time, while the scored-run path stays untouched when `--display_data` is off.

## Effort estimate
```text
Phase 1  ~30 min   config only, proves remote pipeline
Phase 2  ~1-2 hr   client edit + test (the real deliverable)
Phase 3  ~30 min   runner passthrough + auto-open
```

## Open items to confirm at implementation
- Exact rerun 0.26 serve call for the browser path (`serve_web` vs
  `serve_grpc` + `serve_web_viewer`) — pick whichever gives a single URL to open.
- Whether `lerobot-replay` exposes `--display_data` in this version (record/rollout/
  teleoperate confirmed; replay TBD).
- ZeroTier port for the viewer (open it on the chosen host).

Evidence base: lerobot_record.py:147/334 (display_data + display_ip/display_port ->
init_rerun -> connect_grpc); utils/visualization_utils.py:26-48 (init_rerun spawn vs
connect_grpc), :100-129 (rr.log scalars/images); n16_realarm_client.py adapter
~line 187-205 (obs images + state + action0); rerun 0.26.2 dir() (serve_web/serve_grpc/
connect_grpc present).
