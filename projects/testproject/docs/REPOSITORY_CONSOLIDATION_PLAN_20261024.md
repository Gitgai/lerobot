# One-repository consolidation plan

Updated: 24 October 2026. Scope: organize and preserve project work, not run a robot trial.

## Current Git status and what merging means

The selected migration and all nine earlier local files are committed and pushed on `codex/consolidate-fruit-openpi-20261024`, through `ff0b0b36`. The repository working tree was clean after that push. The main branch remains at `aff7b4c7`; these are two branches of **one repository**, not separate projects. Merging would add the branch's changes to the main project version. Pushing has already saved them remotely; merging is a separate step.

The older Documents/ChatGPT workspace is still retained and only selected contents have migrated. A clean repository does not establish complete workspace consolidation, data backup or hardware readiness. The earlier pending-commit statements below are historical and superseded for these completed batches.

### Merge-readiness review — 24 October

Ran `pre-commit run --all-files` on an isolated checkout of **origin/main itself** (`aff7b4c7`). It failed the same check categories as the preservation branch: EOF/whitespace, Ruff formatting/lint, spelling, Python modernization, Markdown formatting and Bandit. Both first passes reported `274 errors (82 fixed, 192 remaining)` from Ruff. These counts are after preceding format hooks and must not be confused with a raw Ruff scan. Secret/large-file, YAML/TOML, workflow security and type checks passed. The temporary baseline checkout was disposable; its formatter changes were not applied to the working repository.

All 19 targeted tests and scoped checks passed for the selected branch changes. This distinguishes existing check debt from the consolidation changes; it does not prove all behavior correct. No simulator, server or physical robot run was performed for this Git review.

**Decision:** prepare a draft pull request, do not claim CI is green, and do not silently force a merge or disable checks. Quality runs on pull requests targeting main or pushes to main; ordinary pushes to this feature branch do not trigger that workflow, explaining the previously empty run list. Review the actual PR check state separately from local results.

### Remaining merge phases

1. Preserve the scoped branch and open a draft PR with explicit baseline-versus-branch results.
2. Triage existing failures separately: distinguish mechanical formatting from changes that can affect closure capture, action scheduling, loop semantics, loading or network exposure. No blanket unsafe auto-fix or global exclusions.
3. Review and test any necessary remediation in a separate scoped change; do not change motor defaults or bypass protections to satisfy static checks.
4. Re-run repository-wide checks and review the PR. Then merge through the normal reviewed workflow and verify GitHub main and the local checkout agree. Do not force-push, delete the old workspace, or describe this step as completed before verifying it.

## The simple rule

Use **Gitgai/lerobot** as the single source-controlled project. On Acer its root is `/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot`; robot-project work belongs under `projects/testproject/`. AI90's checkout is another copy of that same repository, not a different project.

`/home/gaikwad-prakash/Documents/ChatGPT/Lerobot` is the older session workspace containing newer, uncommitted work. Keep it intact until migration is verified. Do not create another remote for it. This session still runs there; documenting a destination does not relocate the session or any running command.

## Progress

**Follow-up preservation batch, October 24:** the five pre-existing modified files and four untracked files have now been reviewed and selected for preservation on the same branch. See [local changes review](LOCAL_CHANGES_REVIEW_20261024.md). Historical documents/snapshot are explicitly not current launch instructions. Added five hardware-free command/config tests; these and the fourteen fruit contract/timing tests passed. Scoped quality/security checks passed after formatting and making the cleanup helper's previously silent disconnect exception visible as a warning. Known launcher limitations remain documented, not silently fixed. Once this batch is committed and the remote hash verified, earlier statements about these nine files being uncommitted are historical; other workspace migration and main-branch merging remain incomplete.

- [x] Inventory the original project: environments, evidence, scripts and old instructions are mixed together. The pre-update folder occupied approximately 31 GB; this is not a post-update size measurement.
- [x] Preserve the five modified tracked files and four untracked files before updating.
- [x] Fetch GitHub and compare incoming changes. No incoming differences touched those five locally modified paths, `src/`, `pyproject.toml` or `uv.lock`.
- [x] Fast-forward Acer main from `ad10219f` to `aff7b4c7` (165 commits). This brought in existing shared project scripts/docs/results; it was not merely a documentation update. No environments were rebuilt and no robot commands were run.
- [x] Add an entry banner to the project README and this plan.
- [ ] Inventory newer session-workspace code/docs against the now-current repository; identify exact duplicates, conflicts, machine-specific paths and dependencies.
- [ ] Copy selected active code/tests/docs into agreed locations, without deleting the originals. Record source/destination hashes and provenance. Exclude secrets and generated bulk data.
- [ ] Check imports, relative links and absolute runtime paths; run relevant non-moving tests before changing launch paths. Existing launch commands remain at their existing locations meanwhile.
- [x] Review the selected batches' staged diffs and secret/large-file exclusions; run scoped checks and commit/push those batches. This does not cover every old workspace file or a merge into main.
- [ ] Only after verification, label superseded instructions as historical and give the old workspace a redirect. No deletion is required to complete consolidation.

## Preservation record

Archive: `/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/repo_preservation_20261024_PmnCuT/acer_uncommitted_files.tar.gz`.

SHA-256: `854857b65d146ce9e67febed590baae4b35e2bc636ff9c11a7d9746948a5cbfa`.

Contains `AGENTS.md`, project `START_HERE.md`, `config/so101.json`, `docs/so101_commands.md`, `scripts/so101_runner.py`, `docs/CAMERA_RECORDING_STATUS.md`, `docs/CLAUDE_HANDOVER_SO101_20260915.md`, `scripts/disable_follower_torque.py`, and `scripts/realarm/n16_realarm_client.py.aug8-original`. Archive entries were listed and all nine originals byte-compared after the fast-forward. This local archive is not an independent disk backup. No secrets, virtual environments or recordings were included.

## Organization policy

### Second migration batch — documentation and checks

Eleven selected historical training/deployment/storage documents now live under `docs/fruit_openpi_history/`, with an index, provenance manifests and explicit historical banners. Checked 57 local Markdown links: all resolve on Acer; 30 refer to external evidence retained in the old workspace and are not GitHub-portable. No claim is made that the entire workspace is migrated. Later backup activity in source documents is preserved, not independently rechecked here.

Repository hooks formatted the nine copied Python files, sorted/cleaned imports, and applied equivalent literal/loop-variable cleanup. This supersedes the initial byte-identical description below; final hashes are regenerated after formatting. All 14 pure tests and client help passed again. Scoped checks for formatting, spelling, large files, secrets and static security passed. Pre-commit installed its own missing cached formatting-hook environment; robot/network/training environments were not changed.

Only this migration batch and its README/plan/index are selected for commit. Original user changes to AGENTS, START_HERE, rig config, launcher, command docs and the earlier untracked files remain outside the batch. No blanket staging, history rewriting, branch force-push or removal is authorized. Publish a scoped branch, not a silent overwrite of main. Full-workspace migration, active launch-path replacement and raw-data preservation remain separate unfinished work.

### First source migration completed — 24 October

Nine selected Python sources were copied to `scripts/inference/fruit_openpi/`, with original/destination SHA-256 values in its `MIGRATION_HASHES.json`. Seven are identical; `client.py` and `transport.py` only have import/environment path adaptations. Recorder and safety helpers are co-located; original networking environment and pinned codec stay at their current absolute paths. Sources are retained, no installed environment or active launch path was replaced. There was no same-path destination to overwrite.

Verification: all 14 contract/timing tests passed; client `--help` passed; worker/codec imported in the existing network environment without connecting; all nine sources parsed successfully. No server import/load, network handshake, camera or motor operation was performed. This is a migration candidate, not validated deployment. The new `docs/ACER_FRUIT_OPENPI_STATUS.md` is an explicit index to evidence still outside the repository. Full workspace inventory/document migration and commit/push remain outstanding; the unchecked phases above are intentionally not marked complete by this first batch.

- Keep the existing directory name for now; renaming it can break absolute paths.
- Use README as the stable entry point, linking to explicit task-specific status documents. A newer date alone does not make a document applicable to every model or experiment.
- Separate active code by recording/training/inference/diagnostics where useful, but audit callers before moving scripts. Preserve historical evidence and original dates.
- Consolidate `config/` and `configs/` only after auditing references: they currently serve different rig and simulator/model purposes.
- Keep large datasets, checkpoints, videos, environments and secrets out of new commits. Existing tracked results require case-by-case review, not blanket deletion or history rewriting.
- Preserve existing environments and machine paths until replacements are verified. Do not relocate `.venv` or remove the old environment as part of this phase.

## Runtime status — historical evidence, not a fresh rig check

The Acer fruit OpenPI work last tested a provisional 4k checkpoint with RTC off and network JPEG off. The October 22 physical trial did not demonstrate placement and had a roughly 56-second host pause correlated with NVMe errors; an earlier October 8 reset was also found. Physical retries remain paused in that workflow. The recovery report is currently at `/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_openpi_client/storage_investigation_20261022/RECOVERY_PROGRESS.md`. Other AI90 training/simulation tracks have separate status; do not conflate their checkpoints or results.

## Rollback

No destructive reset, clean, forced checkout, force-push or automatic stash is allowed in this workflow. If migration breaks something, retain both copies and restore only the affected, reviewed file from its saved source. Git fast-forward recovery is a separate explicit operation: record old/new revisions, preserve all current modifications, and agree on the target before changing checkout history. Do not run `git reset --hard` to undo this work.

## Completion criteria

### Commit and repository-wide check record

Migration batch committed as `13d33c21` on `codex/consolidate-fruit-openpi-20261024`: 27 files, nine Python sources, eleven historical document snapshots, manifests and navigation. This is a selected batch, not all local work.

`pre-commit run --all-files` was executed in a temporary detached checkout of this commit, protecting unrelated local edits from automatic formatters. It failed on older files outside the migration batch: formatting, lint, spelling and static-security findings. The first pass changed 203 existing files in that disposable checkout; none of the 27 migration paths changed. A repeat still reported Ruff, spelling, Markdown-formatting and Bandit failures; secret, large-file and type checks passed. These pre-existing paths were not changed in the actual repository and were not added to the migration commit. Scoped checks for the migration batch passed. Do not claim repository-wide CI is green or merge this branch on that assumption.

Publishing this branch does not merge it into main, migrate all external evidence, replace installed environments, switch active robot commands, or commit the five pre-existing modified files and four pre-existing untracked files. Their preservation archive remains available. Separate review is needed for those local changes and the repository-wide check debt.

One clear project entry point; migrated code/docs tested and committed; remote commit verified; large-data locations and backup scope documented; existing local modifications preserved or explicitly reconciled; no silent runtime/environment changes. Until then, do not claim everything is committed, pushed or migrated.
