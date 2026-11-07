# U1 start-pose restoration

Date: 2026-11-07  
Purpose: Phase A2 of the orange-to-tray reliability plan  
Policy connection: none  
Result: **PASS**

## Movement

The measured starting pose was approximately:

```text
[-7.8242, -105.2308, 96.7473, 77.4505, 1.8901, 54.0670]
```

The documented successful U1 target was:

```text
[-7.8, -104.0, 96.7, 78.3, -1.3, 51.3]
```

Offline verification produced 11 initial waypoints. Maximum step size was 0.29 degrees for the arm and 0.252
gripper unit. All waypoints were inside the demonstration envelope. The kinematic model predicted 5.31 mm maximum
Cartesian displacement from the measured start and 1.92 mm maximum relative descent.

The live mover wrote the measured pose as the goal before enabling torque, restored the audited gripper protection
registers, executed the path, and released torque on exit. Two additional one-degree wrist-roll probe-and-return
cycles tested repeatability without leaving the already traversed local envelope.

## Acceptance result

All three returns reached the identical measured pose:

```text
[-7.8242, -104.0000, 96.7473, 78.1538, -1.2747, 51.3329]
```

- maximum arm error from target: 0.146 degrees;
- maximum gripper error: 0.033 unit;
- measured spread across the three returns: zero on all six axes;
- final temperatures: 32-34 C;
- final voltage: 7.1-7.2 V;
- final torque readback: off on all six motors.

The final front and wrist images show no table or base contact. A tray/object remains at the far lower-left edge of
the front image, outside this small local path. A cable also crosses the top-camera scene. Phase A3 must restore the
tray to its fixed outline, route the cable outside the policy view/swept volume, and establish the new scene
reference before any policy trial.

`dry_run_report.json` and `execute_report.json` contain the complete machine-readable path and readbacks.
