#!/usr/bin/env python3
"""Stage 3 — records check: do the things the memory files point at exist?

Deterministic extraction and existence-checking of file paths, globs, commands
(package.json scripts / Makefile targets), and rules-file path scopes. Ambiguous
extractions are emitted with status "review" for the model to judge — the script
never guesses.

Usage: python3 refcheck.py --work DIR
Reads:  <work>/intake.json    Writes: <work>/refcheck.json
"""

import argparse
import glob as globmod
import itertools
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import iter_lines, load_json, manifest_add, read_text, save_json

PATH_EXTS = (".md", ".markdown", ".json", ".jsonc", ".ts", ".tsx", ".js", ".jsx",
             ".mjs", ".py", ".rb", ".go", ".rs", ".css", ".scss", ".html",
             ".yml", ".yaml", ".toml", ".txt", ".sh", ".sql", ".proto",
             ".d.ts", ".env", ".xml", ".swift", ".java", ".c", ".h", ".cpp")
URL_RE = re.compile(r"^[a-z][a-z0-9+.-]*://|^mailto:", re.I)
BACKTICK_RE = re.compile(r"`([^`\n]+)`")
CMD_RE = re.compile(
    r"\b(pnpm run|pnpm|npm run|yarn run|yarn|bun run|make|just)\s+"
    r"([A-Za-z0-9:._-]+)")
PNPM_BUILTINS = {"install", "i", "add", "remove", "rm", "update", "up", "dlx",
                 "exec", "publish", "link", "why", "list", "ls", "outdated",
                 "audit", "store", "config", "setup", "import", "rebuild",
                 "prune", "patch", "create", "init", "-v", "--version"}
YARN_BUILTINS = PNPM_BUILTINS | {"workspaces", "workspace", "dedupe", "info"}


API_PATH_RE = re.compile(r"^/(v\d+|api|graphql)(/|$)")


def looks_pathish(token):
    if URL_RE.search(token) or " " in token or token.startswith("@"):
        return False
    if API_PATH_RE.match(token):
        return False  # /v1/... style API endpoint, not a filesystem path
    if any(ch in token for ch in "<>{}$()|;"):
        return False
    if not re.search(r"[A-Za-z0-9]", token):
        return False  # pure punctuation like /** or --- is never a path
    if "/" in token:
        return bool(re.match(r"^[~./A-Za-z0-9_*\[\]-][A-Za-z0-9_.*/\[\]~-]*$", token))
    return token.endswith(PATH_EXTS) and len(token) > len(".x")


def expand_braces(pattern):
    m = re.search(r"\{([^{}]*)\}", pattern)
    if not m:
        return [pattern]
    head, tail = pattern[:m.start()], pattern[m.end():]
    out = []
    for opt in m.group(1).split(","):
        out.extend(expand_braces(head + opt + tail))
    return out[:1000]


def check_path(token, containing_file, repo):
    """Return (status, detail). Statuses: ok | ok_external | missing |
    machine_specific | glob_ok | glob_empty."""
    tok = os.path.expanduser(token)
    is_glob = any(c in tok for c in "*[")
    if is_glob:
        if os.path.isabs(tok):
            return "review", "absolute glob — not expanded (safety cap)"
        bases = [repo, os.path.dirname(containing_file)]
        for base in bases:
            n = 0
            for pat in expand_braces(tok):
                # iglob + islice caps the walk so a broad pattern can't crawl
                # the world (or node_modules) to exhaustion
                it = globmod.iglob(os.path.join(base, pat), recursive=True)
                n += sum(1 for _ in itertools.islice(it, 500))
                if n >= 500:
                    break
            if n:
                return "glob_ok", ("%d matches" % n) if n < 500 else "500+ matches"
        return "glob_empty", "no matches from repo root or file dir"
    candidates = ([tok] if os.path.isabs(tok) else
                  [os.path.join(repo, tok),
                   os.path.join(os.path.dirname(containing_file), tok)])
    for cand in candidates:
        if os.path.exists(cand):
            inside = os.path.realpath(cand).startswith(repo + os.sep)
            return ("ok" if inside else "ok_external"), cand
    if os.path.isabs(tok):
        m = re.match(r"^/(Users|home)/([^/]+)/", tok)
        me = os.path.basename(os.path.expanduser("~"))
        if m and m.group(2) != me:
            return "machine_specific", "absolute path under another user's home"
        return "missing", "absolute path not found on this machine"
    return "missing", "not found from repo root or containing dir"


def load_command_targets(repo):
    scripts, make_targets = {}, set()
    pkg = load_json(os.path.join(repo, "package.json"))
    if isinstance(pkg, dict):
        scripts = {k: True for k in (pkg.get("scripts") or {})}
    mk = read_text(os.path.join(repo, "Makefile"))
    if mk:
        for line in mk.splitlines():
            m = re.match(r"^([A-Za-z0-9_.-]+)\s*:([^=]|$)", line)
            if m and not m.group(1).startswith("."):
                make_targets.add(m.group(1))
    return scripts, make_targets


def check_command(runner, target, scripts, make_targets, has_pkg, has_make):
    if runner in ("pnpm", "yarn"):
        builtins = PNPM_BUILTINS if runner == "pnpm" else YARN_BUILTINS
        if target in builtins:
            return "builtin", ""
    if runner == "make":
        if not has_make:
            return "review", "no Makefile at repo root"
        return ("ok", "") if target in make_targets else ("missing", "no such Makefile target")
    if not has_pkg:
        return "review", "no package.json at repo root"
    return ("ok", "") if target in scripts else ("missing", "no such script in package.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    args = ap.parse_args()
    intake = load_json(os.path.join(args.work, "intake.json"))
    if not intake:
        sys.exit("refcheck: run intake.py first (missing intake.json)")
    repo = intake["repo"]
    scripts, make_targets = load_command_targets(repo)
    has_pkg = os.path.isfile(os.path.join(repo, "package.json"))
    has_make = os.path.isfile(os.path.join(repo, "Makefile"))

    references, commands, seen = [], [], set()
    examined = [r for r in intake["files"]
                if r["exists"] and not r["excluded"] and not r["external"]]

    for rec in examined:
        text = read_text(rec["path"]) or ""
        for lineno, line, in_fence in iter_lines(text):
            # inline code + fenced code are prime territory for paths/commands
            tokens = BACKTICK_RE.findall(line)
            if in_fence and line.strip() and not line.strip().startswith(("```", "~~~")):
                tokens.append(line.strip())
            for token in tokens:
                token = token.strip()
                for m in CMD_RE.finditer(token):
                    runner = m.group(1).split()[0]
                    target = m.group(2)
                    key = ("cmd", runner, target)
                    if key in seen:
                        continue
                    seen.add(key)
                    status, detail = check_command(runner, target, scripts,
                                                   make_targets, has_pkg, has_make)
                    commands.append({"file": rec["path"], "line": lineno,
                                     "command": "%s %s" % (m.group(1), target),
                                     "status": status, "detail": detail})
                for part in re.split(r"[\s,]+", token):
                    part = part.strip("().,;:'\"")
                    if not looks_pathish(part):
                        continue
                    key = ("path", part)
                    if key in seen:
                        continue
                    seen.add(key)
                    status, detail = check_path(part, rec["path"], repo)
                    references.append({"file": rec["path"], "line": lineno,
                                       "ref": part, "status": status,
                                       "detail": detail})

    # Import edges that failed to resolve are dead references too
    for edge in intake["import_edges"]:
        if not edge["exists"]:
            references.append({"file": edge["from"], "line": edge["from_line"],
                               "ref": "@" + edge["ref"], "status": "missing",
                               "detail": "import target not found: " + edge["resolved"]})

    # Rules files whose paths: scope matches nothing
    rule_scopes = []
    for rec in intake["files"]:
        if rec["scope"] != "rules" or not rec.get("rules_paths"):
            continue
        total = 0
        for pat in rec["rules_paths"]:
            for expanded in expand_braces(pat):
                total += len(globmod.glob(os.path.join(repo, expanded),
                                          recursive=True))
        rule_scopes.append({"file": rec["path"], "patterns": rec["rules_paths"],
                            "matches": total,
                            "status": "ok" if total else "dead_scope"})

    bad = [r for r in references if r["status"] in
           ("missing", "machine_specific", "glob_empty")]
    out = {
        "references": references,
        "commands": commands,
        "rule_scopes": rule_scopes,
        "stats": {
            "files_examined": len(examined),
            "references_checked": len(references),
            "references_bad": len(bad),
            "commands_checked": len(commands),
            "commands_missing": len([c for c in commands
                                     if c["status"] == "missing"]),
        },
    }
    save_json(os.path.join(args.work, "refcheck.json"), out)
    manifest_add(args.work, "refcheck", **out["stats"])
    print("refcheck: %d refs (%d bad), %d commands (%d missing) -> refcheck.json"
          % (len(references), len(bad), len(commands),
             out["stats"]["commands_missing"]))


if __name__ == "__main__":
    main()
