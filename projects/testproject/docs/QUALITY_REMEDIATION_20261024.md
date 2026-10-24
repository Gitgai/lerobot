# Repository quality remediation

24 October 2026. Parent before cleanup: `6b83ecfd`. Applies to draft PR #1 on the consolidation branch; not merged into main.

## Completed first phase

Ran the repository's existing pre-commit hooks across tracked files. Reviewed automatic formatting, import sorting/unused-import cleanup and Python modernization. Corrected documentation spelling without changing the quoted timestamps, torque settings or network identifier. The spellchecker now recognizes one exact ZeroTier network identifier rather than treating its hexadecimal substring as English; no security checks or broad path exclusions were added.

The mechanical batch affects 204 existing files: 48 Markdown, 104 JSON, 49 Python, two shell files and the typo configuration in `pyproject.toml`. This report and plan update are additional documentation. No package/dependency versions, installed environments, checkpoints, motor settings or network configuration were changed. No scripts that operate hardware or models were executed.

Import review found two required registration imports removed by the unused-import fixer. Restored `vlash.policies.pi05.configuration_pi05` in `r1_dry_inference.py` and `leisaac_so101_gr00t_config` in `gen_stats_recovery.py`, with targeted `F401` explanations. These are required side effects, not dead code. Simulator imports remain after application initialization. Do not assume all formatter suggestions are behavior-neutral without review.

## Verification

- All 104 changed JSON files parse to exactly the same data as the parent. Their bytes changed (primarily final newlines); raw original evidence/checksums remain recoverable from `6b83ecfd`. A verifier requiring original byte hashes must use that revision, not the formatted copies.
- All 49 changed Python files parse successfully with the existing Python 3.12 environment. This is not runtime coverage of every historical script.
- All nine migrated-code and eleven migrated-document destination SHA-256 values still match their provenance manifests.
- All 19 targeted tests pass: fourteen fruit contract/timing tests and five launcher command/config tests. No camera, servo, GPU or network inference used.
- Formatting, spelling and Python-modernization hooks now pass. Existing secret/large-file, YAML/TOML, workflow and type checks pass.

## Still unresolved — do not merge as green

Ruff reports 163 remaining issues after the formatting passes, including closure variables inside loops, missing explicit zip behavior, unused/ambiguous names and legacy formatting constructs. These need reviewed edits; no blanket unsafe fixes were applied.

Bandit still reports existing findings including pickle-based network response deserialization, broad listening interfaces, silent exception handling, a hard-coded temporary path, and non-security hashes not marked as such. These are static findings, not proof of exploitation. Protocol and listening-address changes can break the split AI90/Acer workflow, so they require compatibility tests and explicit design, not warning suppression.

## Next phases

1. Resolve remaining lint with explicit equivalence checks: preserve zip truncation unless a contract change is intended; review lifetime/binding of closures; keep registration side effects.
2. Review the legacy network serialization trust boundary. Reject unsafe/untrusted input through a compatible design rather than adding `nosec` to pickle loads or disabling Bandit. Preserve historical results and distinguish active code from archived experiment sources.
3. Review exception cleanup, temporary-file handling and non-security hashing individually. Do not silently change motor behavior or default network reachability.
4. Re-run all checks and targeted tests, inspect actual GitHub CI, then consider marking PR #1 ready and merging. Until then the branch is a saved, reviewable work-in-progress.

The current robot's storage-reliability issue remains separate. Quality checks passing would not authorize or validate a physical trial.
