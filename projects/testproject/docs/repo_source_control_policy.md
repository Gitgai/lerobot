# Repo Source Control Policy

Last updated: 2026-07-19

This document records the source-control cleanup done for `projects/testproject`.

## 1. What Problem We Had

Before the cleanup, this project had two Git repositories involved:

```text
Parent repo:
  /home/gaikwad-prakash/PrakashProjects/lerobot/lerobot
  remote: https://github.com/Gitgai/lerobot.git

Nested project repo:
  /home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/projects/testproject
  remote: Gitgai/testproject
```

That created confusing Source Control behavior.

Example:

```text
We could commit and push inside projects/testproject,
but VS Code could still show pending files in the parent LeRobot repo.
```

So the same work looked clean in one repo and still pending in another repo.

## 2. What We Changed

On 2026-07-19, after confirming the repos were clean and pushed, the nested Git metadata was moved out of `projects/testproject`.

Moved from:

```text
/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/projects/testproject/.git
```

Moved to backup:

```text
/home/gaikwad-prakash/PrakashProjects/lerobot/git_metadata_backups/testproject_dotgit_20260719_133929
```

Important:

```text
No project files were deleted.
Only the nested .git metadata directory was moved.
```

## 3. Current Repo Rule

`projects/testproject` is now a normal folder inside the main LeRobot repo.

The only active repo for this project is:

```text
/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot
```

The active remote is:

```text
https://github.com/Gitgai/lerobot.git
```

Do not commit or push normal project work to `Gitgai/testproject` anymore.

## 4. Commands To Use Going Forward

Always commit from the parent LeRobot repo:

```bash
cd /home/gaikwad-prakash/PrakashProjects/lerobot/lerobot
git status
git add projects/testproject/...
git commit -m "your commit message"
git push origin main
```

To check which repo owns `projects/testproject`:

```bash
cd /home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/projects/testproject
git rev-parse --show-toplevel
```

Expected output:

```text
/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot
```

## 5. Expected Source Control Result

VS Code Source Control should now show only the parent LeRobot repo for this project work.

Expected behavior:

```text
One repo: Gitgai/lerobot
No duplicate parent-vs-nested pending changes
No separate testproject repo status for normal work
```

## 6. Runtime Source Rule

On 2026-07-19, we found the project virtualenv was importing LeRobot from an old checkout:

```text
/data/projects/lerobot/src
```

That was corrected in the local virtualenv editable path file:

```text
projects/testproject/.venv/lib/python3.12/site-packages/__editable__.lerobot-0.5.2.pth
```

Current expected import path:

```text
/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/src
```

Verification command:

```bash
cd /home/gaikwad-prakash/PrakashProjects/lerobot/lerobot
projects/testproject/.venv/bin/python -c "import lerobot; print(lerobot.__file__)"
```

Expected output:

```text
/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/src/lerobot/__init__.py
```

Reason:

```text
The code we test locally must be the same repo we commit and push.
Otherwise we can accidentally run old /data code while documenting or committing /home code.
```

## 7. Restore Note

The old nested Git metadata was kept as a backup in case we ever need to inspect or restore the previous standalone `testproject` repo.

Restore command, only if intentionally needed:

```bash
mv /home/gaikwad-prakash/PrakashProjects/lerobot/git_metadata_backups/testproject_dotgit_20260719_133929 \
  /home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/projects/testproject/.git
```

Do not restore it casually, because restoring this `.git` directory will recreate the same double-repo Source Control confusion.
