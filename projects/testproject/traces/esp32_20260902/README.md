# ESP32 wrist-camera arm trials — 2026-09-02

Raw evidence for the conclusion in `docs/plate_v2_and_hardware_20260901.md` §6:
neither model grasps through the ESP32 camera.

```text
file                 model            scene            result
trace_ctrl1.jsonl    baseline 10k     plate present    NO GRASP  7 sustained cycles
trace_ctrl2.jsonl    baseline 10k     NO plate         NO GRASP  9 sustained cycles
trace_t1.jsonl       plate_v1         plate present    NO GRASP  4 sustained cycles
```

Each is a real arm run: ~640 control cycles over ~146 s, joints swinging
130-150 degrees, servo positions read back from the hardware.

The wrist source was the ESP32, identifiable independently of any note: median
frame age 1 ms. The Pi proxy runs ~45 ms because frames cross the network; the
ESP32 captures on demand.

A grasp requires BOTH a sustained >=10-cycle finger block AND the orange
leaving its start position. Calibrated on the 2026-08-20 9/10 runs, where the
longest unbroken block was 10 and 20 cycles. In all three runs here the orange
moved 1 px.

CAVEAT ON ctrl1: the scene was meant to have no plate and did. The confound was
found by the operator and ctrl2 is the clean rerun.

Frames: *_start.jpg are the first front-camera frames (used for the
orange-moved test). ctrl1_front_grid / ctrl1_wrist_grid show the run that
produced a FALSE grasp reading before the scorer was fixed.
wrist_camera_compare.jpg is the OV5647 view the model trained on, beside the
ESP32 view it failed on.
