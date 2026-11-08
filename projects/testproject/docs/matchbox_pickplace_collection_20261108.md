# Matchbox pick-and-place demonstration collection

Date: 2026-11-08  
Dataset: `matchbox_pickplace_ft4_20261108`  
Task: `pick up the matchbox and place it on the plate`  
Status: 5/5 accepted

## Purpose

These episodes add language-conditioned object selection and small rectangular-object handling. An orange remains
beside the matchbox as a distractor. The demonstrations consistently select the matchbox, leave the orange
untouched, grasp the matchbox securely, carry it to the tray, release it inside and move the arm clear.

The dataset is stored separately from `orange_grasp_corrective_ft4_20261108`. Its task label names the matchbox, so
the episodes can be included selectively when assembling fine-tune 4 without corrupting the orange-only labels.

## Recording protocol

- Two policy cameras at 640x480 and 30 Hz.
- One 35-second teleoperated episode followed by a 15-second manual reset.
- Fixed tray and orange positions.
- The matchbox is returned to the same left-mid-table position during each reset.
- The operator controls the leader arm; the follower copies and records the full task.
- Both camera streams, joint state and actions are stored in LeRobot v3 format.

## Review result

Episodes 0-4 passed synchronized front/wrist review. Every episode contains the intended matchbox selection, secure
lift, controlled transport, tray release and clean completion. The orange remains on the table and is not contacted.
The final safety check found torque disabled, zero load and normal 6.5 V on all six follower joints.

Before training, keep these episodes as a distinct source group in the fine-tune 4 manifest. Their role is object
selection and matchbox handling; they are not orange grasp-centering corrections.

