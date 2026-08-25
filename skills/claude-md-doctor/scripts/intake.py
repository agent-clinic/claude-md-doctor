#!/usr/bin/env python3
"""Stage 1 — intake: discover the memory surface a Claude Code session loads.

Finds project/nested/rules/ancestor CLAUDE.md files, follows @imports (depth 4,
fence/backtick-aware), honors claudeMdExcludes, detects the pointer-to-AGENTS.md
pattern, and locates the repo's session-history directory.

Usage: python3 intake.py --repo /path/to/repo [--work DIR] [--include-user]
Writes: <work>/intake.json
"""

import argparse
import fnmatch
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (iter_lines, load_json, manifest_add, read_text, save_json,
                     sha1_of, strip_html_comments, strip_inline_code,
                     parse_frontmatter)

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist",
             "build", ".next", "target", ".claude-md-doctor"}
IMPORT_RE = re.compile(r"(?:^|\s)@([~./A-Za-z0-9_][A-Za-z0-9_.~/\\-]*)")
MAX_IMPORT_DEPTH = 4


def file_record(path, scope, loaded, repo, external=False, **extra):
    text = read_text(path)
    rec = {
        "path": path,
        "rel": os.path.relpath(path, repo) if path.startswith(repo + os.sep) else None,
        "scope": scope,
        "loaded_at_launch": loaded,
        "external": external,
        "exists": text is not None,
        "size_bytes": len(text.encode("utf-8", "replace")) if text is not None else 0,
        "sha1": sha1_of(text) if text is not None else None,
        "is_symlink": os.path.islink(path),
        "symlink_target": os.path.realpath(path) if os.path.islink(path) else None,
        "excluded": False,
        "excluded_by": None,
    }
    rec.update(extra)
    return rec


def find_imports(path, text):
    """@path imports outside fences and inline code (backticked = literal)."""
    found = []
    for lineno, line, in_fence in iter_lines(text):
        if in_fence:
            continue
        clean = strip_inline_code(line)
        for m in IMPORT_RE.finditer(clean):
            ref = m.group(1).rstrip(".,;:)")
            if re.match(r"^[A-Za-z0-9_.-]+$", ref) and "." not in ref and "/" not in ref:
                continue  # bare @word (a mention/handle), not a path import
            found.append({"from": path, "from_line": lineno, "ref": ref})
    return found


def resolve_ref(ref, containing_file):
    if ref.startswith("~"):
        return os.path.expanduser(ref)
    if os.path.isabs(ref):
        return ref
    return os.path.normpath(os.path.join(os.path.dirname(containing_file), ref))


def collect_excludes(repo):
    patterns = []
    for settings in (
        os.path.join(repo, ".claude", "settings.json"),
        os.path.join(repo, ".claude", "settings.local.json"),
        os.path.expanduser("~/.claude/settings.json"),
    ):
        data = load_json(settings)
        if isinstance(data, dict):
            for pat in data.get("claudeMdExcludes", []) or []:
                patterns.append({"pattern": pat, "source": settings})
    return patterns


def apply_excludes(files, patterns):
    for rec in files:
        for p in patterns:
            if fnmatch.fnmatch(rec["path"], p["pattern"]):
                rec["excluded"], rec["excluded_by"] = True, p["pattern"]
                break


def detect_pointer(rec):
    """A CLAUDE.md that is a symlink or whose effective content is only
    @imports (the officially recommended AGENTS.md pattern) is a healthy
    pointer — the patient is the target."""
    if rec["is_symlink"]:
        rec["is_pointer"] = True
        rec["pointer_targets"] = [rec["symlink_target"]]
        return
    text = read_text(rec["path"]) or ""
    clean, _ = strip_html_comments(text)
    meaningful = [l.strip() for l in clean.splitlines() if l.strip()]
    imports = [l for l in meaningful if re.fullmatch(r"@\S+", l)]
    rec["is_pointer"] = bool(meaningful) and len(meaningful) <= 3 and len(imports) >= 1 \
        and all(re.fullmatch(r"@\S+", l) or l.startswith("#") for l in meaningful)
    rec["pointer_targets"] = [resolve_ref(l[1:], rec["path"]) for l in imports] if rec["is_pointer"] else []


def sessions_dir_for(repo):
    base = os.path.expanduser("~/.claude/projects")
    for cand in (re.sub(r"[/.]", "-", repo), repo.replace("/", "-")):
        d = os.path.join(base, cand)
        if os.path.isdir(d):
            n = len([f for f in os.listdir(d) if f.endswith(".jsonl")])
            return {"dir": d, "session_files": n}
    return {"dir": None, "session_files": 0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument("--work", default=None)
    ap.add_argument("--include-user", action="store_true")
    args = ap.parse_args()

    repo = os.path.realpath(args.repo)
    work = args.work or os.path.join(repo, ".claude-md-doctor", "work")
    files, edges = [], []

    # Project root files (launch-loaded)
    for name in ("CLAUDE.md", os.path.join(".claude", "CLAUDE.md"), "CLAUDE.local.md"):
        p = os.path.join(repo, name)
        if os.path.lexists(p):
            files.append(file_record(p, "project", True, repo))

    # Nested (on-demand) + rules
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        rel_dir = os.path.relpath(dirpath, repo)
        in_rules = os.sep.join([".claude", "rules"]) in os.path.join(rel_dir, "")
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            if in_rules and fn.endswith(".md"):
                meta, _ = parse_frontmatter(read_text(p) or "")
                paths = meta.get("paths") or []
                if isinstance(paths, str):
                    paths = [paths]
                files.append(file_record(p, "rules", not paths, repo, rules_paths=paths))
            elif fn in ("CLAUDE.md", "CLAUDE.local.md") and dirpath != repo \
                    and ".claude" not in dirpath.split(os.sep):
                files.append(file_record(p, "nested", False, repo))

    # Ancestors above the repo (launch-loaded, but not the repo's to fix)
    parent = os.path.dirname(repo)
    while parent and parent != os.path.dirname(parent):
        for name in ("CLAUDE.md", "CLAUDE.local.md"):
            p = os.path.join(parent, name)
            if os.path.isfile(p):
                files.append(file_record(p, "ancestor", True, repo, external=True))
        parent = os.path.dirname(parent)

    # User scope (opt-in for diagnosis; existence always noted)
    user_claude = os.path.expanduser("~/.claude/CLAUDE.md")
    user_rules_dir = os.path.expanduser("~/.claude/rules")
    user_note = {
        "user_claude_md_exists": os.path.isfile(user_claude),
        "user_rules_count": len([f for f in os.listdir(user_rules_dir)
                                 if f.endswith(".md")]) if os.path.isdir(user_rules_dir) else 0,
        "included_in_exam": bool(args.include_user),
    }
    if args.include_user and os.path.isfile(user_claude):
        files.append(file_record(user_claude, "user", True, repo, external=True))

    # Managed policy (noted, never diagnosed)
    managed = [p for p in ("/Library/Application Support/ClaudeCode/CLAUDE.md",
                           "/etc/claude-code/CLAUDE.md") if os.path.isfile(p)]

    apply_excludes(files, collect_excludes(repo))

    # Pointer detection on project-root CLAUDE.md
    for rec in files:
        if rec["scope"] == "project" and rec["exists"]:
            detect_pointer(rec)

    # Follow @imports from every loaded, non-excluded file
    frontier = [(rec["path"], rec["loaded_at_launch"], 0)
                for rec in files if rec["exists"] and not rec["excluded"]]
    known = {rec["path"] for rec in files}
    while frontier:
        path, loaded, depth = frontier.pop(0)
        if depth >= MAX_IMPORT_DEPTH:
            continue
        text = read_text(path)
        if text is None:
            continue
        for imp in find_imports(path, text):
            resolved = resolve_ref(imp["ref"], path)
            exists = os.path.isfile(resolved)
            edges.append({**imp, "resolved": resolved, "exists": exists,
                          "depth": depth + 1})
            if exists and resolved not in known:
                known.add(resolved)
                files.append(file_record(
                    resolved, "import", loaded, repo,
                    external=not resolved.startswith(repo + os.sep)))
                frontier.append((resolved, loaded, depth + 1))

    effective = [f["path"] for f in files
                 if f["exists"] and not f["excluded"] and f["loaded_at_launch"]
                 and not f["external"]]

    out = {
        "repo": repo,
        "files": files,
        "import_edges": edges,
        "effective_launch_loaded": effective,
        "user_scope": user_note,
        "managed_policy_files": managed,
        "sessions": sessions_dir_for(repo),
    }
    save_json(os.path.join(work, "intake.json"), out)
    manifest_add(work, "intake", files=len(files), imports=len(edges),
                 effective=len(effective))
    print("intake: %d files (%d launch-loaded in-repo), %d import edges -> %s"
          % (len(files), len(effective), len(edges),
             os.path.join(work, "intake.json")))


if __name__ == "__main__":
    main()
