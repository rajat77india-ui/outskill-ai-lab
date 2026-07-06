---
name: pushback-audit
description: Mine all local AI-assistant session transcripts (Claude Code, Codex, Cursor, Antigravity, VS Code) for every time the user pushed back — redo requests, corrections, frustration at hand-waving — then cluster the events into named failure mechanisms and rank them by emotional cost, time/token cost, and recurrence. Use when the user asks to audit past sessions, find where the assistant failed them, analyze redo/correction patterns, or asks "what do you keep getting wrong". Run this in a LOCAL session on the user's machine — transcripts do not exist in cloud sandboxes.
---

# Pushback Audit

Produce a forensic report of every place the user pushed back on an AI
assistant across their local session histories, clustered into named failure
mechanisms and ranked three ways.

## Phase 0 — Check you can see the data

Transcripts live only on the user's machine. Verify before promising anything:

```bash
ls ~/.claude/projects/ 2>/dev/null | head
ls ~/.codex/sessions/ 2>/dev/null | head
```

If both are empty AND no bundle (`transcripts_bundle.zip` /
`session_failure_analysis_out/`) was provided, you are probably in a cloud
sandbox. Say so plainly, point the user at
`tools/session_failure_analysis/README.md`, and stop — do not fabricate
events.

## Phase 1 — Collect

Run the collector bundled in this skill's own directory (stdlib-only, safe,
read-only) — resolve the path relative to this SKILL.md file:

```bash
python3 <this-skill-directory>/collect_transcripts.py
```

It writes `session_failure_analysis_out/` with `events.jsonl` (every user
message + source metadata + preceding assistant snippet), `candidates.jsonl`
(regex-flagged pushback), and `raw/` (unparsed chat blobs). If the user
supplied a claude.ai export, its `conversations.json` counts as another
source: user turns are in `chat_messages[].sender == "human"`.

If the collector is missing (repo not checked out), read
`~/.claude/projects/**/*.jsonl` and `~/.codex/sessions/**/*.jsonl` directly.

## Phase 2 — Extract verbatim events

`candidates.jsonl` is a wide net — it has false positives (e.g. "again" in a
benign sentence) and misses quiet corrections. Do both passes:

1. Review every candidate; keep only genuine pushback.
2. Sample `events.jsonl` beyond the regex hits for quiet corrections the
   regex missed: short imperative replies right after an assistant turn
   ("no", "not that file", "read it first"), repeated near-identical requests
   (the user re-asking = a silent redo), and messages that restate an earlier
   instruction.
3. Check `raw/` blobs for Cursor/Antigravity chats the extractor couldn't
   parse; parse the JSON by hand if any exist.

For every confirmed event record: **verbatim user quote** (never paraphrase;
trim with `…` only for length), source app, project, session id, timestamp,
and a one-line description of what the assistant did to provoke it (from
`prev_assistant` or by opening the source transcript for context).

Severity-tag each event:
- `correction` — factual/technical fix, low heat ("that's the wrong port")
- `redo` — work rejected, must be redone ("redo this", re-asking the same thing)
- `frustration` — emotional load: caps, profanity, "I already told you",
  exasperation, sarcasm

## Phase 3 — Cluster into named failure mechanisms

Group events by the *assistant behavior that caused them*, not by surface
wording. Give each mechanism a short memorable name and a one-sentence
definition. Derive clusters from the data; typical mechanisms to test
against (do not force-fit):

- **Hand-wave completion** — claimed done/working without running or testing it
- **Placeholder padding** — stubs, mocks, fake data, TODOs passed off as implementation
- **Instruction decay** — an explicit earlier instruction ignored later in the session
- **Wrong-target edit** — edited the wrong file/branch/function or clobbered work
- **Scope drift** — did something adjacent to, but not, what was asked
- **Premature victory lap** — verbose summary of success while the thing is still broken
- **Context amnesia** — re-asked for or re-derived information already given

Every event belongs to exactly one mechanism; use an `Unclustered` bucket
rather than inventing a mechanism for one-offs.

## Phase 4 — Rank three ways

Score each mechanism independently on three axes and present three separate
rankings (they will differ — that difference is a finding):

1. **Rage ranking** — weight events by severity tag (frustration=3, redo=2,
   correction=1); note escalation patterns (same session, rising heat).
2. **Cost ranking** — estimate wasted effort per mechanism: count of redo
   cycles, size of discarded assistant output (chars of `prev_assistant` and
   follow-up turns), sessions abandoned after the event.
3. **Recurrence ranking** — distinct sessions and distinct calendar weeks in
   which the mechanism appears; a mechanism spanning months and tools
   outranks a one-day flare-up.

## Phase 5 — Report

Deliver a markdown report (`session_failure_analysis_out/pushback_report.md`)
containing:

1. **Coverage statement first** — which sources and date ranges were actually
   found on disk, and which are missing (pruned storage, other machines,
   desktop-app export not provided). Never imply completeness you don't have.
2. The three rankings, each with a one-line takeaway.
3. Per mechanism: name, definition, scores, and every event verbatim with
   source (`app / project / session / timestamp`).
4. **Countermeasures** — for the top mechanisms, concrete CLAUDE.md /
   AGENTS.md rules or hooks the user could add so future sessions don't
   repeat them. Offer to write these into the repo.

Also send the report file to the user, and give a plain-prose summary of the
top finding on each ranking in chat.

## Rules

- Quotes are verbatim or not included. No paraphrase presented as quote.
- Do not editorialize about the user's tone; the frustration is the data.
- Transcripts may contain secrets — redact anything that looks like a key or
  token in the report, and never commit `session_failure_analysis_out/`.
