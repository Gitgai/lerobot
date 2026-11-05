# SO-101 scripted tray-pickup root-cause audit

Date: 2026-11-05

Scope: the scripted auto-reset pickup from the tray. This is separate from the
fine-tune policy that picks fruit from the table and places it in the tray.

## Conclusion

The gripper close controller is not the current blocker. The verified centre
pickup stalled at 21.9, lifted the orange, carried it sideways and released it.
Failed off-centre attempts stalled at 2.1, 5.9 or 7.4, which means the jaws
closed on air or beside the orange. The failure occurs before closure: the
script does not put the physical jaw closing centre around the orange
repeatably.

The latest attempt was stopped before closing. The orange remained about 68
pixels to the right of the successful wrist-image reference at the most
corrected candidate, so another push-aside failure was likely.

## Findings

### 1. The latest placement was a centre placement, not a left placement

The marked target produced an overhead orange centre of `(135.7, 137.2)`.
The calibrated tray centre is `(150.0, 143.5)`, so the offset was
`(-14.3, -6.3)` pixels and its magnitude was 15.6 pixels. `bench_reset.py`
defines the centre region as 35 percent of the 90-pixel tray radius, or 31.5
pixels. The correct classifier result for this placement is therefore
`centre`.

The already verified centre pickup should have been used. Treating this
placement as `left` sent the calibration down an unnecessary path. A stable
left calibration point must be outside the 31.5-pixel centre radius and have a
larger horizontal than vertical offset, for example approximately `(115,143)`
on the current 640 by 480 top image.

### 2. The front/back solver did not preserve gripper orientation

`generate_tray_left_front_back_path.py` used three joints to preserve only the
three-dimensional position of the URDF gripper frame. It did not constrain
tool pitch or the physical jaw orientation.

From offset 0 to -12 mm, the commanded pose changed from:

```text
[63.2, -63.5184, 85.8777, 36.4823, 0.0]
```

to:

```text
[63.2, -61.9414, 89.5261, 25.0820, 0.0]
```

Wrist flex changed by -11.4 degrees. The URDF tool z axis changed from
`[0.2333,-0.4618,-0.8557]` to `[0.2734,-0.5413,-0.7951]`. This rotated the
wrist camera and the jaws while the calibration treated the wrist-image motion
as a pure front/back translation.

The orange wrist centroid moved from `(385.0,118.7)` to `(393.5,149.1)`. Its
vertical coordinate improved toward the successful reference `(325.2,165.9)`,
but its horizontal error remained 68.3 pixels. The path corrected one image
coordinate while worsening the combined grasp geometry.

### 3. Pan and front/back corrections are coupled

The previous lateral calibration measured approximately `(-10.8,+1.4)` wrist
pixels per degree of pan. The latest bounded front/back path measured roughly
`(+0.7,+2.5)` wrist pixels per millimetre in its negative direction. These are
two non-orthogonal image motions. Applying one scalar correction and then the
other cannot preserve the first alignment.

A rough two-axis solve predicts that the latest placement would have required
about +6.5 degrees of pan and 15 mm of the negative local translation from the
offset-zero pose. That combined pose was never collision-checked, and the
position-only solver would still rotate the tool. It must not be replayed as an
operational grasp.

### 4. The software models the URDF frame, not the jaw contact centre

The FK target is `gripper_frame_joint`. The useful grasp point is the midpoint
between the two contact surfaces below their black tip marks. No measured
transform currently connects those two points. The successful centre image is
therefore more trustworthy than the URDF frame for final alignment, but the
current calibration compares raw orange pixels without normalizing them to the
two visible finger marks.

### 5. The live tray detector currently fails

On the latest unobstructed top frame, `tray_centre()` returned `None`. The tray
interior had median HSV saturation about 59, directly on the detector's minimum
of 60. The mask split into components; the largest was about 6,355 pixels,
below the required 12,000-pixel contour. Lowering the saturation threshold
alone merged the tray with image-edge clutter.

The automatic reset would therefore stop at `LOOK` under the current lighting,
even before motion. Tray localization should use the taped fixed ROI plus edge
or template geometry, with HSV only as supporting evidence.

### 6. Manual placement variation is large enough to invalidate scalar tuning

The successful centre pickup began with the orange near top pixel
`(151.0,121.5)`. The previous lateral attempt used approximately `(137,150)`;
the latest placement was `(135.7,137.2)`. A shift of 10-30 overhead pixels is
roughly 1-4 cm at the configured 8 px/cm. Reusing a pan-to-pixel correction from
one placement for another is not a repeatable calibration method.

### 7. The cautious dry runs were justified but amplified the cost

An earlier estimated tray transit physically moved the tray. After that event,
every new path correctly required an empty-tray clearance test and exact reverse
retreat. The safety process prevented another contact, but the underlying
one-axis model kept generating new paths, so the safe workflow repeated many
times without converging.

### 8. The requested 2 cm wrist clearance was not the grasp blocker

The URDF `gripper_frame_link` is near the jaw tips, not at the wrist motor.
That frame reached an absolute z of about 5 mm at the latest alignment, but the
physical arm-body reference points remained much higher:

| Pose | Wrist-link origin z | Gripper-body origin z | Jaw-tip frame z |
| --- | ---: | ---: | ---: |
| verified centre success | 152.1 mm | 99.5 mm | 11.0 mm |
| front/back offset 0 | 145.4 mm | 93.1 mm | 5.0 mm |
| front/back offset -12 mm | 136.4 mm | 87.8 mm | 5.0 mm |

The wrist and gripper body therefore remained well above the requested 20 mm
clearance. Only the jaws descended around the fruit. Phase correlation on two
mostly unoccluded tray-border patches found less than 1.3 pixels of apparent
motion between the pre-approach and -12 mm images, and visual inspection found
no tray displacement. No close was issued.

The earlier tray displacement came from an unsafe swept transit path. The
replacement guarded transit kept the jaw-tip frame near 40 mm during pan and
did not repeat that contact. The 2 cm wrist-body rule should still become an
explicit runtime guard, using the wrist/gripper collision geometry rather than
the jaw-tip frame alone.

## Replacement design

1. Keep the verified centre pickup unchanged and use it whenever the overhead
   orange centre lies inside the existing 31.5-pixel centre region.
2. Replace the five blind off-centre joint poses with a coarse overhead
   camera-to-tray map. The fixed taped tray ROI supplies local tray coordinates.
3. Approach at the verified 40 mm clearance with a fixed tool orientation.
4. Preserve gripper pitch and roll in IK. Solve pan, shoulder, elbow and wrist
   flex together for `[x,y,z,pitch]`; reject any solution that changes the jaw
   orientation outside a small bound.
5. At a collision-checked open-gripper alignment height, detect the orange and
   both black finger marks in the wrist image. Express the orange relative to
   the line joining the finger marks, rather than as an absolute camera pixel.
6. Measure a local 2 by 2 image Jacobian using two small orthogonal Cartesian
   probes at fixed orientation. Solve both image errors together, move through
   bounded candidates, re-image, and allow at most two corrections.
7. Descend vertically while preserving orientation. Close only when the orange
   lies inside the acceptance window learned from the successful centre image.
8. Keep the existing stall, lift and sideways-carry proof. A stall reading alone
   remains insufficient.
9. Replace the HSV-only tray detector with a fixed-ROI contour/template check
   and validate it across saved bright and dark frames before any reset run.

## Shortest next validation

The orange is currently in the script's centre region. The shortest useful
physical test is one replay of the already verified centre path, with the
successful wrist image used as the pre-close gate. This tests the known path and
does not continue the rejected tray-left calibration.

For a true left-path development test, first place the orange near `(115,143)`
in the top image, remove it for one fixed-orientation rectangular dry run, then
perform one watched two-axis visual-servo grasp. Do not resume the sequential
pan-then-front/back procedure.
