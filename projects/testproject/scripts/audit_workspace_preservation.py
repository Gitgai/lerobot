#!/usr/bin/env python3
"""Inventory a legacy workspace without following links or accessing hardware.

Compare small source/document/config files by exact Git blob identity against
explicit committed refs. Output contains paths and hashes, never file contents.
Large evidence is counted, not hashed; this is an inventory, not a verified backup.
"""

import argparse
import collections
import hashlib
import json
import os
import stat as stat_module
import subprocess
from pathlib import Path


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args])


def audit(workspace, repo, refs, output):
    workspace, repo, output = (Path(p).resolve() for p in (workspace, repo, output))
    if output == workspace or workspace in output.parents:
        raise ValueError("Output must be outside the workspace being inventoried")
    exact = collections.defaultdict(list)
    names = collections.defaultdict(list)
    revisions = {}
    object_format = git(repo, "rev-parse", "--show-object-format").decode().strip()
    for ref in refs:
        revision = git(repo, "rev-parse", "--verify", ref + "^{commit}").decode().strip()
        revisions[ref] = revision
        for entry in git(repo, "ls-tree", "-rz", "--full-tree", revision).split(b"\0"):
            if not entry:
                continue
            meta, path = entry.split(b"\t", 1)
            mode, kind, oid = meta.decode().split()
            if kind != "blob" or mode == "120000":
                continue
            path = path.decode(errors="surrogateescape")
            record = {"ref": ref, "path": path}
            exact[oid].append(record)
            names[Path(path).name].append(record)

    suffixes = {
        ".py",
        ".sh",
        ".md",
        ".rst",
        ".txt",
        ".toml",
        ".yaml",
        ".yml",
        ".json",
        ".html",
        ".js",
        ".ts",
        ".css",
        ".ipynb",
        ".docx",
        ".pdf",
    }
    skip_names = {
        ".git",
        "__pycache__",
        "node_modules",
        "vendor",
        "upstream",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
    }
    skipped, symlinks, errors, candidates = [], [], [], []
    groups = collections.defaultdict(lambda: {"files": 0, "bytes": 0, "candidates": 0})

    def error(exc):
        errors.append({"path": str(exc.filename), "error": str(exc)})

    for directory, dirs, files in os.walk(workspace, followlinks=False, onerror=error):
        parent = Path(directory)
        for name in list(dirs):
            path = parent / name
            rel = str(path.relative_to(workspace))
            if path.is_symlink():
                symlinks.append({"path": rel, "target": os.readlink(path)})
                dirs.remove(name)
            elif name in skip_names or name.startswith((".venv", "venv")):
                skipped.append(rel)
                dirs.remove(name)
        for name in sorted(files):
            path = parent / name
            rel = str(path.relative_to(workspace))
            if path.is_symlink():
                symlinks.append({"path": rel, "target": os.readlink(path)})
                continue
            try:
                stat = path.stat()
                if not stat_module.S_ISREG(stat.st_mode):
                    errors.append({"path": rel, "error": "not a regular file; not read"})
                    continue
                group = groups[rel.split("/")[0] if "/" in rel else "(root files)"]
                group["files"] += 1
                group["bytes"] += stat.st_size
                if path.suffix.lower() not in suffixes or stat.st_size > 8 * 1024**2:
                    continue
                content = path.read_bytes()
                after = path.stat()
                if stat.st_size != after.st_size or stat.st_mtime_ns != after.st_mtime_ns:
                    errors.append({"path": rel, "error": "changed during read; rerun required"})
                    continue
                oid = hashlib.new(
                    object_format,
                    b"blob " + str(len(content)).encode() + b"\0" + content,
                    usedforsecurity=False,
                ).hexdigest()
                matches = exact.get(oid, [])
                candidates.append(
                    {
                        "path": rel,
                        "bytes": len(content),
                        "sha256": hashlib.sha256(content).hexdigest(),
                        "git_blob": oid,
                        "status": "exact_in_git" if matches else "needs_review",
                        "exact_matches": matches,
                        "same_name_candidates": [] if matches else names.get(name, []),
                    }
                )
                group["candidates"] += 1
            except OSError as exc:
                error(exc)

    candidates.sort(key=lambda row: row["path"])
    summary = {
        "workspace": str(workspace),
        "repository": str(repo),
        "revisions": revisions,
        "scope": "Regular files inventoried except explicit skipped trees; selected suffixes <=8 MiB hashed. Symlinks not followed. No bulk evidence checksums or remote-host audit.",
        "candidate_suffixes": sorted(suffixes),
        "candidate_max_bytes": 8 * 1024**2,
        "counts": dict(collections.Counter(row["status"] for row in candidates)),
        "candidate_bytes": sum(row["bytes"] for row in candidates),
        "groups": dict(sorted(groups.items())),
        "skipped_trees": sorted(skipped),
        "symlinks": symlinks,
        "errors": errors,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    with (output / "source_inventory.jsonl").open("w") as stream:
        for row in candidates:
            stream.write(json.dumps(row) + "\n")
    print(
        json.dumps(
            {
                "counts": summary["counts"],
                "candidate_bytes": summary["candidate_bytes"],
                "inventoried_files": sum(g["files"] for g in groups.values()),
                "inventoried_bytes": sum(g["bytes"] for g in groups.values()),
                "skipped_trees": len(skipped),
                "errors": len(errors),
            },
            indent=2,
        )
    )
    return bool(errors)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--ref", action="append", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    raise SystemExit(audit(args.workspace, args.repo, args.ref, args.output))
