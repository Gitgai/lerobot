# Phase B held-out wrist diagnostic

Date: 2026-11-07  
Evidence: controlled trials BCTRL1-BCTRL3  
Safety: offline, read-only; no robot connection and no action modification

These six wrist-camera frames were selected after the grasp-band thresholds had already been fixed. They therefore
form a small held-out check rather than additional calibration data.

| trial frame | physical outcome | detector | gate decision |
|---|---|---|---|
| B1 c46 | close did not lift orange | unknown | block |
| B1 c61 | recovery close did not lift orange | ineligible | block |
| B2 c43 | close led to stable lift and delivery | eligible | allow |
| B3 c21 | orange outside left finger | unknown | block |
| B3 c39 | orange outside left finger | unknown | block |
| B3 c66 | orange outside left finger | unknown | block |

The offline gate decision agrees with all six reviewed outcomes: the one successful close is eligible, and all five
failed closes are blocked. Four failures are `unknown` because the fruit is only partly visible at the image edge;
`unknown` is deliberately blocking rather than permission to close.

This is useful evidence that a pre-close gate could reject these observed bad closes. It is not sufficient to enable
motor control. The set contains only one successful close, uses selected frames rather than a prospective stream,
and does not test consecutive-frame stability. The detector also cannot generate a centring correction. The next
step is shadow-mode logging over new controlled demonstrations, followed by corrective demonstrations and a new
checkpoint.

Artifacts:

- `labels.csv`: reviewed physical outcomes.
- `measurements.csv`: detector outputs.
- `samples/`: exact held-out wrist frames.
- `annotated/`: decision overlays.
- `annotated_montage.jpg`: combined visual review.
