# Remaining Acer changes — preservation review

24 October 2026. Scope: version existing work, not certify or run hardware commands.

## Files being preserved

| File                                                  | Existing change / purpose                                                                             |
| ----------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `AGENTS.md`                                           | Fork orientation and machine roles; corrected the overly broad "newest date wins" rule                |
| `START_HERE.md`                                       | Earlier task/camera/default notes; retained its explicit obsolete status and corrected its navigation |
| `config/so101.json`                                   | Acer paths, two physical cameras, serial identities, historical tomato task; not a universal config   |
| `docs/so101_commands.md`                              | Earlier recording/replay examples and cleanup notes, now clearly historical                           |
| `scripts/so101_runner.py`                             | Existing two-camera recording, countdown, dataset-root/resume and torque cleanup additions            |
| `docs/CAMERA_RECORDING_STATUS.md`                     | September 15 camera/dataset evidence, not a fresh camera check                                        |
| `docs/CLAUDE_HANDOVER_SO101_20260915.md`              | Historical handover; old conclusions and paths are not current authority                              |
| `scripts/disable_follower_torque.py`                  | Existing serial-identified cleanup helper, not executed during this review                            |
| `scripts/realarm/n16_realarm_client.py.aug8-original` | Historical GR00T source snapshot, not the active client; do not launch it                             |

The original pre-review versions of all nine are preserved in the archive documented by the consolidation plan. Any repository-hook formatting is distinct from runtime testing; no robot configuration or motor register was changed by this preservation work. Runtime settings in the JSON were already present locally, not newly selected here.

## Known issues — not fixed by committing

1. `positions` calls a follower connection path that can enable torque. Its read-only description is misleading; do not use it as a torque-free diagnostic.
2. The runner's no-log path discards the cleanup boolean; its Ctrl+C path can return before raising for cleanup failure. The helper's first read can fail before reaching `disable_torque`. During preservation, the previously silent disconnect exception was changed to a warning on stderr; its return-code behavior is unchanged. Thus success/interrupt completion is not a universal torque-off guarantee.
3. `record --delete` calls recursive deletion on a user/config-supplied dataset path without a broad-path safeguard, and can be combined with `--resume`. Do not use it as part of consolidation or automate it.
4. Device resolution falls back to numeric ports when serial paths are absent. This is not sufficient physical identity assurance.
5. Config retains historical `top` fields alongside front/wrist, with C270 appearing under both labels. The revised recording builder emits only front/wrist; other legacy consumers need separate review.
6. The launcher sources the existing virtual-environment activation script; migration does not establish that every activation/shebang path is repaired.

These findings are follow-up implementation work, not permission to silently alter behavior while preserving source. Existing fruit OpenPI migration uses a separate integration; do not substitute the legacy runner for it.

## Verification scope

Unit tests exercise config loading, camera strings, command construction and default argument omission only. The process-dispatch function is replaced by a capture function in those tests, so no subprocess, camera or motor action is performed. This is ordinary software unit testing, not a simulated physical trial. CLI help and syntax checks likewise do not establish real-device compatibility or cleanup behavior.

Repository-wide checks already have unrelated failures documented in the consolidation plan. Commit/push status is established by Git, not implied by this review. Original workspace scripts, data and environments remain in place.
