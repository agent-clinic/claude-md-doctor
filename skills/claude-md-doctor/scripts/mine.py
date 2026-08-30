#!/usr/bin/env python3
"""Stage B1 (and 4f) — mine: extract rule/fact candidates from the sessions.

The inverse of the backtest: instead of replaying a memory file's rules over
the history, mine the history for the rules that were never written down.
Five signal families, each mechanically pre-filtered here and JUDGED by the
model afterwards (high recall, moderate precision — the calibration corpus
put the lexical markers at ~65–75% precision, which is a judge feed, not a
verdict):

  corrections       user messages that redirect the agent or state a durable
                    preference ("use pnpm not npm", "make sure we never …")
  failure_recovery  a failed command followed by a similar one that worked
                    (npm test → pnpm test; the fix IS the rule)
  rediscovery       commands run in the first turns of many sessions — facts
                    the agent re-derives every time because no file states them
  denials           tool calls the user rejected at the permission prompt or
                    a settings rule denied (auto-mode classifier blocks are
                    counted but NOT proposed — that is the harness, not the user)
  preambles         near-identical session-opening explanations — context the
                    user keeps retyping

Recurrence gates keep one-off taste out: grouped families need >=2 sessions
or >=3 occurrences — except rediscovery, which needs >=3 distinct sessions
strictly (a command run ten times in one session is a loop). Corrections
are UNGATED: they stay ungrouped (wording varies), deduped, and capped
newest-first — judge them hardest. Groups whose last occurrence is
older than the median session are flagged `stale` — a preference the repo
may have moved past must not resurface.

Usage: python3 mine.py --work DIR [--max-corrections N]
Reads:  <work>/sessions/*.json, <work>/sessions_index.json
Writes: <work>/candidates.json
"""

import argparse
import os
import re
import shlex
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import est_tokens, load_json, manifest_add, save_json
from backtest import ENV_PREFIX_RE, command_word

MIN_SESSIONS = 2          # a grouped signal recurring in this many sessions …
MIN_OCCURRENCES = 3       # … or this many times total survives the gate
REDISCOVERY_MIN_SESSIONS = 3   # noisier family, higher bar
EARLY_TURNS = 3           # "session start" = the first three user turns
STARTUP_TAX_TURN = 4      # bytes before this turn = the re-discovery tax
MAX_SAMPLES = 3
SIM_THRESHOLD = 0.5       # token overlap for failed→retry pairing
PREAMBLE_SIM = 0.55
PREAMBLE_MIN_CHARS = 40

# --- user-text exclusions (verified against a real 2.1.x transcript corpus) ---
# Automation injections (<ci-monitor-event> etc.) are stamped origin "human",
# so metadata alone cannot filter them: any leading <tag> is excluded.
TAG_OPEN_RE = re.compile(r"^\s*<[A-Za-z][\w-]*[ >]")
WRAPPER_MARKERS = ("<command-name>", "<local-command-stdout>",
                   "<local-command-caveat>")
SYS_REMINDER_RE = re.compile(r"<system-reminder>.*?(</system-reminder>|$)",
                             re.S)
INTERRUPT_TEXTS = {"[Request interrupted by user]",
                   "[Request interrupted by user for tool use]"}

# --- correction markers, calibrated on 624 real user messages (precision
# noted per pattern; the union fires on ~8% of messages at ~65-75%) ---
MARKERS = [
    ("pivot", r"(?im)^(no|nope|nah|don'?t|stop|never|wait|but|actually|hmm)\b"),   # ~86%
    ("you-said", r"(?i)\b(you (said|previously said|claimed|told me)"
                 r"|didn'?t you (already )?say|why (did|are|would|do) you"
                 r"|i thought (you|i (told|asked)))\b"),                           # 83%
    ("still-broken", r"(?i)\bstill\b.{0,40}\b(wrong|broken|fail(s|ing|ed)?"
                     r"|not work(ing)?|empty|missing|off)\b"),                     # 100%, small n
    ("instead-of", r"(?i)\binstead of\b"),                                         # 75%
    ("not-right", r"(?i)\b(wrong|not what i (asked|meant|want(ed)?)"
                  r"|that'?s not (what|right|it))\b"),                             # 73%
    ("standing", r"(?im)\b(from now on|going forward|always remember)\b"
                 r"|\bmake sure\b[^.\n]{0,60}\b(always|never|only)\b"
                 r"|^\s*[-*]?\s*never [a-z]+"
                 r"|\blet'?s (use|follow) the rules?\b"),                          # standing prefs
]
# 0% precision on session-opening probe prompts — only counts mid-session
GATED_MARKERS = [
    ("dont-verb", r"(?i)\b(don'?t|do not|never|stop) "
                  r"(use|do|touch|run|add|create|delete|commit|push)\b"),
]
MARKERS_C = [(n, re.compile(p)) for n, p in MARKERS]
GATED_C = [(n, re.compile(p)) for n, p in GATED_MARKERS]

# fallback for condensed events without the `denial` field (older condensations)
DENIAL_PREFIXES = (
    ("user-rejected", "The user doesn't want to proceed"),
    ("automode-blocked", "Permission for this action was denied by the Claude "
                         "Code auto mode classifier"),
    ("permission-rule", "Permission to use "),
)


def clean_user_text(text):
    """Human text or None. Excludes command wrappers, automation injections,
    interruption markers; strips system-reminder spans."""
    if not text:
        return None
    if text.strip() in INTERRUPT_TEXTS:
        return None
    if any(m in text for m in WRAPPER_MARKERS) or text.startswith("Caveat:"):
        return None
    # strip reminder spans BEFORE the tag check — a reminder can be
    # prepended to genuine human text in the same record
    text = SYS_REMINDER_RE.sub(" ", text).strip()
    if not text or TAG_OPEN_RE.match(text):
        return None
    return text


def denial_kind(ev):
    if ev.get("denial"):
        return ev["denial"]
    text = ev.get("text", "")
    for kind, prefix in DENIAL_PREFIXES:
        if text.startswith(prefix):
            return kind
    return None


def tokens_of(text):
    return set(t.lower() for t in re.findall(r"[A-Za-z0-9_./-]{2,}", text or ""))


def similar(a, b):
    """Overlap coefficient, not Jaccard — a 2-token command pair like
    `npm test` → `pnpm test` must still score 0.5."""
    ta, tb = tokens_of(a), tokens_of(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / float(min(len(ta), len(tb)))


def head_key(cmd):
    """First two meaningful words of a command — the rediscovery grouping key
    (`cat package.json`, `pnpm install`, `git log`)."""
    words = []
    # `cd <dir> && <real work>` is navigation, not the thing being rediscovered:
    # key on the first segment that does actual work, else fall back to the cd.
    for seg in re.split(r"&&|\|\||;|\|", cmd or ""):
        seg = ENV_PREFIX_RE.sub("", seg.strip())
        if not seg:
            continue
        try:
            w = shlex.split(seg)          # quote-aware: `cd "/my repo" && ...`
        except ValueError:                # unbalanced quotes — fall back
            w = [x.strip("'\"") for x in seg.split()]
        if not w or not w[0]:
            continue
        words = words or w
        if os.path.basename(w[0]) not in ("cd", "pushd", "popd"):
            words = w
            break
    if not words or not words[0]:
        return "?"
    head = os.path.basename(words[0])[:24]
    if len(words) > 1 and re.match(r"^[A-Za-z0-9_./@-]+$", words[1]) \
            and not words[1].startswith("-"):
        return "%s %s" % (head, os.path.basename(words[1])[:32])
    return head


def mine_session(events, sess_id):
    """One condensed session -> raw findings for cross-session grouping."""
    out = {"corrections": [], "pairs": [], "early_cmds": [], "denials": [],
           "opener": None, "startup_bytes": None, "automode": 0}
    tool_count, opener_seen = 0, False
    bash_idx = [i for i, e in enumerate(events)
                if e["t"] == "tool" and e.get("name") == "Bash"]
    id_idx = {e["id"]: i for i, e in enumerate(events)
              if e["t"] == "tool" and e.get("id")}
    prev_kind = [None] * len(events)  # rolling context for after-interrupt

    for i, ev in enumerate(events):
        t = ev["t"]
        if out["startup_bytes"] is None and ev.get("turn", 0) >= STARTUP_TAX_TURN:
            out["startup_bytes"] = ev.get("off", 0)
        if t == "tool":
            tool_count += 1
            if ev.get("name") == "Bash" and ev.get("turn", 0) <= EARLY_TURNS:
                # offset gap to the next event ≈ this call's record + result
                # bytes — the attributable cost of one discovery command
                span = max(0, events[i + 1].get("off", 0) - ev.get("off", 0)) \
                    if i + 1 < len(events) else 0
                out["early_cmds"].append((head_key(ev.get("command", "")),
                                          ev.get("command", ""), span))
            continue
        if t == "tool_error":
            kind = denial_kind(ev)
            if kind == "automode-blocked":
                out["automode"] += 1
                continue
            # what call was this? by id when the condenser carried one
            # (batched calls make "nearest preceding" wrong), else proximity
            src = None
            if ev.get("for_id") in id_idx:
                src = events[id_idx[ev["for_id"]]]
            else:
                for j in range(i - 1, max(-1, i - 5), -1):
                    if events[j]["t"] == "tool":
                        src = events[j]
                        break
            if kind:
                key = command_word(src.get("command", "")) \
                    if src and src.get("name") == "Bash" \
                    else (src or {}).get("name", "?")
                out["denials"].append(
                    {"kind": kind, "tool": (src or {}).get("name", "?"),
                     "key": key, "session": sess_id,
                     "turn": ev.get("turn", 0), "ts": ev.get("ts"),
                     "cmd": (src or {}).get("command", "")[:160]})
            elif src and src.get("name") == "Bash":
                # genuine failure: does a similar command follow and differ?
                failed = src.get("command", "")
                nxt = next((events[k] for k in bash_idx if k > i), None)
                if nxt is not None:
                    retry = nxt.get("command", "")
                    if retry != failed and similar(failed, retry) >= SIM_THRESHOLD:
                        out["pairs"].append(
                            {"failed": failed[:200], "retry": retry[:200],
                             "session": sess_id, "turn": ev.get("turn", 0),
                             "ts": ev.get("ts")})
            continue
        if t == "user":
            text = clean_user_text(ev.get("text", ""))
            if text is None:
                prev_kind[i] = ("interrupt"
                                if ev.get("text", "").strip() in INTERRUPT_TEXTS
                                else None)
                continue
            if not opener_seen:
                opener_seen = True  # only the session's FIRST human text opens it
                if len(text) >= PREAMBLE_MIN_CHARS:
                    out["opener"] = {"session": sess_id, "text": text[:300],
                                     "ts": ev.get("ts")}
            signals = [n for n, rx in MARKERS_C if rx.search(text)]
            if tool_count >= 3 and len(text) < 300:
                signals += [n for n, rx in GATED_C if rx.search(text)]
            after_interrupt = any(
                prev_kind[j] == "interrupt"
                for j in range(max(0, i - 3), i)) or any(
                events[j]["t"] == "tool_error"
                and denial_kind(events[j]) == "user-rejected"
                for j in range(max(0, i - 3), i))
            if after_interrupt:
                signals.append("after-interrupt")
            if signals:
                if tool_count >= 3 and len(text) < 120:
                    signals.append("mid-session")  # judge feature, not a gate
                out["corrections"].append(
                    {"session": sess_id, "turn": ev.get("turn", 0),
                     "ts": ev.get("ts"), "text": text[:300],
                     "signals": signals})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--max-corrections", type=int, default=120)
    args = ap.parse_args()
    index = load_json(os.path.join(args.work, "sessions_index.json"))
    if not index:
        sys.exit("mine: run sessions.py first (missing sessions_index.json)")
    sess_dir = os.path.join(args.work, "sessions")
    sessions = [s for s in index.get("sessions", [])
                if s.get("events") and s.get("tools", 0) > 0]
    if not sessions:
        save_json(os.path.join(args.work, "candidates.json"),
                  {"meta": {"sessions_scanned": 0,
                            "note": "no usable sessions"}})
        manifest_add(args.work, "mine", sessions=0)
        print("mine: no usable sessions to mine")
        return

    last_ts_sorted = sorted(s.get("last_ts") or "" for s in sessions)
    median_ts = last_ts_sorted[len(last_ts_sorted) // 2]

    corrections, pair_groups, early_groups = [], {}, {}
    denial_groups, openers, taxes = {}, [], []
    automode_total = 0
    seen_correction_texts = set()  # forked sessions duplicate whole prefixes

    for sess in sessions:  # index order = newest first
        events = load_json(os.path.join(sess_dir, sess["id"] + ".json")) or []
        found = mine_session(events, sess["id"])
        automode_total += found["automode"]
        if found["startup_bytes"]:
            taxes.append(found["startup_bytes"])
        if found["opener"]:
            openers.append(found["opener"])
        for c in found["corrections"]:
            key = re.sub(r"\s+", " ", c["text"].lower()).strip()
            if key in seen_correction_texts:
                continue
            seen_correction_texts.add(key)
            corrections.append(c)
        for p in found["pairs"]:
            key = (command_word(p["failed"]), command_word(p["retry"]))
            g = pair_groups.setdefault(
                key, {"failed_word": key[0], "retry_word": key[1],
                      "occurrences": 0, "_sessions": set(), "last_ts": "",
                      "samples": []})
            g["occurrences"] += 1
            g["_sessions"].add(p["session"])
            g["last_ts"] = max(g["last_ts"], p.get("ts") or "")
            if len(g["samples"]) < MAX_SAMPLES:
                g["samples"].append(p)
        for key, cmd, span in found["early_cmds"]:
            g = early_groups.setdefault(
                key, {"key": key, "occurrences": 0, "_sessions": set(),
                      "bytes": 0, "samples": []})
            g["occurrences"] += 1
            g["_sessions"].add(sess["id"])
            g["bytes"] += span
            if len(g["samples"]) < MAX_SAMPLES:
                g["samples"].append({"session": sess["id"], "cmd": cmd[:160]})
        for d in found["denials"]:
            key = (d["kind"], d["tool"], d["key"])
            g = denial_groups.setdefault(
                key, {"kind": d["kind"], "tool": d["tool"], "key": d["key"],
                      "occurrences": 0, "_sessions": set(), "last_ts": "",
                      "samples": []})
            g["occurrences"] += 1
            g["_sessions"].add(d["session"])
            g["last_ts"] = max(g["last_ts"], d.get("ts") or "")
            if len(g["samples"]) < MAX_SAMPLES:
                g["samples"].append(d)

    def finish(groups, min_sessions=MIN_SESSIONS, occ_fallback=True):
        out = []
        for g in groups:
            sess_set = g.pop("_sessions")
            g["sessions"] = len(sess_set)
            if g["sessions"] >= min_sessions or \
                    (occ_fallback and g["occurrences"] >= MIN_OCCURRENCES):
                if g.get("last_ts"):
                    g["stale"] = g["last_ts"] < median_ts
                out.append(g)
        return sorted(out, key=lambda g: (-g["sessions"], -g["occurrences"]))

    pairs = finish(list(pair_groups.values()))
    early_sessions = {g["key"]: set(g["_sessions"])
                      for g in early_groups.values()}
    # rediscovery needs CROSS-session recurrence — a command run ten times
    # in one session is a loop, not a re-discovery
    rediscovery = finish(list(early_groups.values()),
                         min_sessions=REDISCOVERY_MIN_SESSIONS,
                         occ_fallback=False)
    denials = finish(list(denial_groups.values()))

    # preambles: cluster near-identical session openers (union-find on
    # pairwise token overlap); identical texts are usually forked-session
    # echoes, so support counts distinct sessions but flags echo clusters
    parent = list(range(len(openers)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(openers)):
        for j in range(i + 1, len(openers)):
            if similar(openers[i]["text"], openers[j]["text"]) >= PREAMBLE_SIM:
                parent[find(i)] = find(j)
    clusters = {}
    for i, o in enumerate(openers):
        clusters.setdefault(find(i), []).append(o)
    preambles = []
    for members in clusters.values():
        sess_set = {m["session"] for m in members}
        if len(sess_set) < MIN_SESSIONS:
            continue
        texts = {m["text"] for m in members}
        preambles.append({"sessions": len(sess_set),
                          "occurrences": len(members),
                          "identical_echo": len(texts) == 1,
                          "samples": members[:MAX_SAMPLES]})
    preambles.sort(key=lambda p: -p["sessions"])

    corrections = corrections[:args.max_corrections]
    # tax = bytes attributable to the RECURRING discovery commands only —
    # bytes-before-turn-N would blame long first tasks for "re-discovery"
    tax = {}
    tax_bytes = sum(g.get("bytes", 0) for g in rediscovery)
    if tax_bytes:
        tax_sessions = set()
        for g in rediscovery:
            tax_sessions |= early_sessions.get(g["key"], set())
        tax = {"est_tokens": est_tokens(tax_bytes),
               "sessions": len(tax_sessions)}
    if taxes:
        taxes.sort()
        tax["early_window_median_bytes"] = taxes[len(taxes) // 2]

    out = {
        "meta": {
            "sessions_scanned": len(sessions),
            "gates": {"min_sessions": MIN_SESSIONS,
                      "min_occurrences": MIN_OCCURRENCES,
                      "rediscovery_min_sessions": REDISCOVERY_MIN_SESSIONS,
                      "note": "rediscovery: sessions gate only (no occurrence "
                              "fallback); corrections: ungated, judge them"},
            "corrections_found": len(seen_correction_texts),
            "corrections_kept": len(corrections),
            "automode_blocked": automode_total,
            "known_gaps": "bare factual corrections without lexical markers "
                          "escape the pre-filter; the judge pass may scan a "
                          "few raw sessions to spot-check recall",
        },
        "corrections": corrections,
        "failure_recovery": pairs,
        "rediscovery": rediscovery,
        "denials": denials,
        "preambles": preambles,
        "startup_tax": tax,
    }
    save_json(os.path.join(args.work, "candidates.json"), out)
    manifest_add(args.work, "mine", sessions=len(sessions),
                 corrections=len(corrections), pairs=len(pairs),
                 rediscovery=len(rediscovery), denials=len(denials),
                 preambles=len(preambles))
    print("mine: %d session(s) -> %d correction(s), %d failed→fixed pair "
          "group(s), %d rediscovery group(s), %d denial group(s), "
          "%d preamble cluster(s)%s -> candidates.json"
          % (len(sessions), len(corrections), len(pairs), len(rediscovery),
             len(denials), len(preambles),
             ", ~%d-token re-discovery tax" % tax["est_tokens"]
             if tax.get("est_tokens") else ""))
    if automode_total:
        print("mine: %d auto-mode classifier block(s) counted but not "
              "proposed — that is the harness, not the user" % automode_total)


if __name__ == "__main__":
    main()
