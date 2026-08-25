"""Shared helpers for claude-md-doctor scripts. Stdlib only; Python 3.9+."""

import hashlib
import json
import os
import re
import time

FENCE_RE = re.compile(r"^\s*(```|~~~)")
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return None


def sha1_of(text):
    return hashlib.sha1(text.encode("utf-8", "replace")).hexdigest()[:12]


def iter_lines(text):
    """Yield (lineno, line, in_fence) with fenced-code tracking (``` / ~~~)."""
    in_fence = False
    fence_marker = None
    for i, line in enumerate(text.splitlines(), start=1):
        m = FENCE_RE.match(line)
        if m:
            marker = m.group(1)
            if not in_fence:
                in_fence, fence_marker = True, marker
                yield i, line, True
                continue
            if marker == fence_marker:
                yield i, line, True
                in_fence, fence_marker = False, None
                continue
        yield i, line, in_fence


def strip_inline_code(line):
    """Replace `code spans` with spaces (preserves indices loosely)."""
    return INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), line)


def strip_html_comments(text):
    """Remove <!-- --> blocks outside code fences (Claude Code strips these
    before injection). Returns (clean_text, removed_line_count)."""
    out, removed = [], 0
    in_comment = False
    for _, line, in_fence in iter_lines(text):
        if in_fence:
            out.append(line)
            continue
        buf = line
        keep = ""
        while buf:
            if in_comment:
                end = buf.find("-->")
                if end == -1:
                    buf = ""
                else:
                    buf = buf[end + 3:]
                    in_comment = False
            else:
                start = buf.find("<!--")
                if start == -1:
                    keep += buf
                    buf = ""
                else:
                    keep += buf[:start]
                    buf = buf[start + 4:]
                    in_comment = True
        if keep.strip() or (not line.strip()):
            out.append(keep)
        else:
            removed += 1
    return "\n".join(out), removed


def parse_frontmatter(text):
    """Minimal YAML frontmatter parser: returns (meta_dict, body).
    Supports `key: value` and `key:` + `- item` lists. Not a YAML parser."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    meta, i, current_key = {}, 1, None
    while i < len(lines):
        line = lines[i]
        if line.strip() == "---":
            return meta, "\n".join(lines[i + 1:])
        item = re.match(r"^\s+-\s+(.*)$", line)
        kv = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if item and current_key:
            meta.setdefault(current_key, [])
            if isinstance(meta[current_key], list):
                meta[current_key].append(item.group(1).strip().strip("\"'"))
        elif kv:
            key, val = kv.group(1), kv.group(2).strip()
            if val == "":
                meta[key] = []
                current_key = key
            else:
                meta[key] = val.strip("\"'")
                current_key = None
        i += 1
    return {}, text  # unterminated frontmatter: treat as body


def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def manifest_add(work_dir, stage, **info):
    """Append a stage record to the exam's work-state manifest. The report
    verifies this so a silently skipped stage is visible (SIGIL principle)."""
    path = os.path.join(work_dir, "manifest.json")
    manifest = load_json(path, default={"stages": []})
    manifest["stages"] = [s for s in manifest["stages"] if s.get("stage") != stage]
    record = {"stage": stage, "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    record.update(info)
    manifest["stages"].append(record)
    save_json(path, manifest)


def est_tokens(chars):
    """Crude estimate (~4 chars/token). Labeled as an estimate everywhere."""
    return int(round(chars / 4.0))
