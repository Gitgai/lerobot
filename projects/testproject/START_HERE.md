# Start here — our robotics project

Updated: 2026-11-13. This is the main entry point for current work.

## Where we are

We are moving daily robotics work to the new workstation, **ryzen9**:
`prakash-gaikwad@192.168.1.23` (ZeroTier `192.168.194.23`). A read-only SSH inspection
confirmed Ubuntu 26.04.1, Ryzen 9 9950X, RTX PRO 5000 Blackwell 72 GB, driver
595.99.02, approximately 29 GiB usable RAM and a WD Blue SN5100 4 TB SSD with
about 3.4 TiB available. The C270 camera was detected; the arm controllers and
wrist camera were not. These are observations from the inspection, not continuous monitoring.

**Migration is not complete.** The inspected `~/projects` folder was empty.
No project transfer, dependency installation, GPU inference or robot test has
been performed on ryzen9 by this task. The new `~/Robotics` layout below is planned.
Code and records are on GitHub and Acer; additional data/models and runtime
provenance must be gathered from Acer and AI90.

## What we are building

An SO-101 robot that reliably picks up an orange and places it on a plate, with
recorded demonstrations, reproducible training and evidence from physical trials.
The latest recorded training run is **FT4B, 9,000 steps** using the VLASH π0.5 stack.
Its watched physical gate scored **0/3**. The November 11 diagnosis identified
mismatched starting pose, fruit placement and camera geometry. It is a candidate
for further testing, not a proven reliable policy.

The exact instruction remains `pick up the orange and place it on the plate`.
See the [FT4B plan and diagnosis](docs/fine_tune_4_execution_plan_20261108.md) for
model paths, dataset identities and the next experimental gate. Migration does
not change that experiment or authorize an unattended physical run.

## The documents to use

| Need                                              | Read                                                                  |
| ------------------------------------------------- | --------------------------------------------------------------------- |
| How we organize and move all work                 | [Workstation plan](docs/WORKSTATION_PLAN_20261113.md)                 |
| SSD space, compression and backups                | [Storage policy](docs/SSD_STORAGE_POLICY_20261113.md)                 |
| Machine setup and runtime requirements            | [Setup guide](NEW_MACHINE_SETUP.md)                                   |
| What is saved in Git and what is still outside it | [Preservation audit](docs/NEW_MACHINE_PRESERVATION_AUDIT_20261113.md) |
| Current training and robot results                | [FT4B execution plan](docs/fine_tune_4_execution_plan_20261108.md)    |

## Next action

Prepare the **source-to-destination transfer manifest**, starting with the Acer
calibration/source snapshot, the accepted FT4 demonstrations and derivatives, and
the AI90 FT4B/base-model/runtime dependencies. Measure AI90 before promising that
all historical assets fit. Copy and verify current essentials first; catalog older
work for later transfer. Keep source copies until restoration is verified.

## Everyday routine after migration

1. Read this page for the active experiment and next task.
2. Use a clean Git branch for code changes. Record the commit used by each run.
3. Give each training run or physical trial a unique ID; save its settings,
   model/dataset identities, logs and outcome together outside the Git checkout.
4. Update the experiment's result ledger and this page when the current decision changes.
5. Push reviewed code/docs and verify a separate backup of new irreplaceable data.

Approved run commands will be added here only after they work on ryzen9.
Historical commands, including [the old entry page](docs/history/START_HERE_before_20261113.md),
are reference material and may contain obsolete paths or settings.
