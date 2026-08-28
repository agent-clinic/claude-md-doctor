#!/usr/bin/env python3
"""Stage 4a — sessions: condense this repo's Claude Code transcripts.

Reads ~/.claude/projects/<slug>/*.jsonl (located by intake) and reduces each
multi-MB transcript to a compact event stream the backtest can replay: user
text, assistant text, every tool call with its meaningful inputs, and tool
errors. Sidecar records and tool_result bodies are dropped. Parsing is
defensive — the transcript format is undocumented and aborted stub sessions
exist in the wild.

Usage: python3 sessions.py --work DIR [--max-sessions N] [--dir OVERRIDE]
Reads:  <work>/intake.json    Writes: <work>/sessions/<id>.json + sessions_index.json
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import load_json, manifest_add, save_json

TEXT_CAP = 400
NEW_CONTENT_CAP = 1200


def _head(s, cap):
    s = s if isinstance(s, str) else json.dumps(s, ensure_ascii=False)
    return s if len(s) <= cap else s[:cap] + "…"


def condense_file(path):
    """One transcript -> (events, meta). Never raises on bad lines.

    Every event carries `off`, its byte offset in the raw transcript — a
    context-occupancy proxy (tool_result bytes count toward context even
    though their bodies are dropped here). Compaction boundaries (`system`
    records with compactMetadata, or user records with isCompactSummary)
    are emitted as {"t": "compact"} events so the backtest can bucket
    violations by context state (fresh / diluted / post-compact)."""
    events, turns, first_ts, last_ts = [], 0, None, None
    offset = 0
    try:
        fh = open(path, "rb")
    except OSError:
        return [], {}
    with fh:
        for raw in fh:
            line_off, offset = offset, offset + len(raw)
            try:
                rec = json.loads(raw.decode("utf-8", "replace"))
            except ValueError:
                continue
            if not isinstance(rec, dict):
                continue
            ts = rec.get("timestamp")
            if ts:
                first_ts, last_ts = first_ts or ts, ts
            rtype = rec.get("type")
            if (rtype == "system" and "compactMetadata" in rec) or \
                    (rtype == "user" and rec.get("isCompactSummary")):
                events.append({"t": "compact", "turn": turns, "ts": ts,
                               "off": line_off})
                continue
            if rec.get("isMeta") or rec.get("isSidechain"):
                continue  # injected skill/command bodies, subagent records —
                          # they wear type:"user" but are not the human
            msg = rec.get("message") or {}
            content = msg.get("content")
            n_before = len(events)
            if rtype == "user":
                # origin.kind (newer transcripts): "human" = actually typed
                src = (rec.get("origin") or {}).get("kind")
                if isinstance(content, str):
                    turns += 1
                    ev = {"t": "user", "turn": turns, "ts": ts,
                          "text": _head(content, TEXT_CAP)}
                    if src:
                        ev["src"] = src
                    events.append(ev)
                elif isinstance(content, list):
                    texts = [b.get("text", "") for b in content
                             if isinstance(b, dict) and b.get("type") == "text"]
                    if texts:
                        turns += 1
                        ev = {"t": "user", "turn": turns, "ts": ts,
                              "text": _head("\n".join(texts), TEXT_CAP)}
                        if src:
                            ev["src"] = src
                        events.append(ev)
                    for b in content:
                        if isinstance(b, dict) and b.get("type") == "tool_result" \
                                and b.get("is_error"):
                            ev = {"t": "tool_error", "turn": turns, "ts": ts,
                                  "text": _head(b.get("content", ""), 200)}
                            # user-rejected | permission-rule | automode-blocked
                            if rec.get("toolDenialKind"):
                                ev["denial"] = rec["toolDenialKind"]
                            # ties the error to its tool call even when the
                            # assistant batched several calls in one turn
                            if b.get("tool_use_id"):
                                ev["for_id"] = b["tool_use_id"][-8:]
                            events.append(ev)
            elif rtype == "assistant" and isinstance(content, list):
                for b in content:
                    if not isinstance(b, dict):
                        continue
                    btype = b.get("type")
                    if btype == "text" and b.get("text", "").strip():
                        events.append({"t": "assistant", "turn": turns, "ts": ts,
                                       "text": _head(b["text"], TEXT_CAP)})
                    elif btype == "tool_use":
                        name = b.get("name", "?")
                        inp = b.get("input") or {}
                        ev = {"t": "tool", "turn": turns, "ts": ts, "name": name}
                        if b.get("id"):
                            ev["id"] = b["id"][-8:]
                        if name == "Bash":
                            ev["command"] = _head(inp.get("command", ""), 600)
                        elif name in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
                            ev["file_path"] = inp.get("file_path", "")
                            new = inp.get("new_string") or inp.get("content") or ""
                            if name == "MultiEdit":
                                new = "\n".join(e.get("new_string", "")
                                                for e in inp.get("edits", [])
                                                if isinstance(e, dict))
                            ev["new"] = _head(new, NEW_CONTENT_CAP)
                        else:
                            ev["input_keys"] = sorted(inp.keys())[:8]
                        events.append(ev)
            # every other record type (attachment, permission-mode, ai-title,
            # file-history-snapshot, system, …) is a sidecar: skipped
            for ev in events[n_before:]:
                ev.setdefault("off", line_off)
    return events, {"turns": turns, "first_ts": first_ts, "last_ts": last_ts,
                    "total_bytes": offset,
                    "compactions": len([e for e in events if e["t"] == "compact"])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--max-sessions", type=int, default=30)
    ap.add_argument("--dir", default=None, help="override sessions directory")
    args = ap.parse_args()
    intake = load_json(os.path.join(args.work, "intake.json"))
    if not intake:
        sys.exit("sessions: run intake.py first (missing intake.json)")
    sdir = args.dir or (intake.get("sessions") or {}).get("dir")
    out_dir = os.path.join(args.work, "sessions")
    index = {"dir": sdir, "sessions": []}
    if not sdir or not os.path.isdir(sdir):
        save_json(os.path.join(args.work, "sessions_index.json"), index)
        manifest_add(args.work, "sessions", sessions=0, note="no history found")
        print("sessions: no transcript directory found for this repo")
        return

    files = sorted((os.path.join(sdir, f) for f in os.listdir(sdir)
                    if f.endswith(".jsonl")),
                   key=lambda p: os.path.getmtime(p), reverse=True)
    kept = 0
    for path in files[:args.max_sessions]:
        sid = os.path.splitext(os.path.basename(path))[0]
        events, meta = condense_file(path)
        tools = len([e for e in events if e["t"] == "tool"])
        if not events:
            index["sessions"].append({"id": sid, "events": 0, "tools": 0,
                                      "skipped": "empty/stub"})
            continue
        save_json(os.path.join(out_dir, sid + ".json"), events)
        entry = {"id": sid, "events": len(events), "tools": tools,
                 "raw_bytes": os.path.getsize(path)}
        entry.update(meta)
        index["sessions"].append(entry)
        kept += 1
    save_json(os.path.join(args.work, "sessions_index.json"), index)
    manifest_add(args.work, "sessions", sessions=kept,
                 skipped=len(index["sessions"]) - kept)
    total_tools = sum(s.get("tools", 0) for s in index["sessions"])
    print("sessions: condensed %d session(s) (%d stubs skipped), %d tool calls -> %s"
          % (kept, len(index["sessions"]) - kept, total_tools, out_dir))


if __name__ == "__main__":
    main()
