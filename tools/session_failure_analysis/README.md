# Session failure analysis — transcript collector

Goal: find every place you pushed back on the assistant ("redo", corrections,
frustration at hand-waving) across Claude Code, Codex, Cursor, Antigravity,
and VS Code, then cluster those events into named failure mechanisms and rank
them by rage, by time/token cost, and by recurrence.

The transcripts live **only on your local machine(s)** — cloud sessions cannot
see them. This directory contains the collector you run locally.

**Easiest path:** run `claude` locally in this repo and invoke
`/pushback-audit` (defined in `.claude/skills/pushback-audit/`). It runs this
collector, verifies candidates, clusters them into failure mechanisms, and
writes the ranked report end to end.

## Where each tool keeps its history

| Tool | Location |
|---|---|
| Claude Code (CLI + VS Code/JetBrains extensions) | `~/.claude/projects/<project>/<session>.jsonl` |
| Codex CLI | `~/.codex/sessions/**/*.jsonl`, `~/.codex/history.jsonl` |
| Cursor | `…/Cursor/User/{workspaceStorage,globalStorage}/**/state.vscdb` (sqlite) |
| Antigravity | `…/Antigravity/User/**/state.vscdb` (same layout as Cursor) |
| VS Code chat panels | `…/Code/User/workspaceStorage/*/chatSessions/*.json` |
| Claude desktop/web app | **Server-side only** — export at claude.ai → Settings → Privacy → Export data |

(`…` = `~/Library/Application Support` on macOS, `%APPDATA%` on Windows,
`~/.config` on Linux.)

## How to run

On each machine where you've used these tools:

```bash
python3 tools/session_failure_analysis/collect_transcripts.py
```

Stdlib only — no dependencies. It writes `session_failure_analysis_out/`:

- `events.jsonl` — every user message with source metadata
- `candidates.jsonl` — messages matching pushback/frustration patterns, each
  paired with the preceding assistant snippet
- `raw/` — chat blobs it couldn't confidently parse (kept so nothing is lost)
- `transcripts_bundle.zip` — all of the above

If you use the Claude desktop/web app, request the data export from claude.ai
and drop its `conversations.json` into the output folder before zipping.

## Handing it off

Give the zip back to an analysis session (attach it in the desktop app, or
run `claude` locally in this repo — a local session can read `~/.claude` and
the output folder directly, no zip needed). **Do not commit the zip to a
public repo** — transcripts often contain keys, tokens, and private paths.

The analysis pass then produces: verbatim pushback events with sources,
clustered into named failure mechanisms, ranked three ways (emotional cost,
time/token cost, recurrence).
