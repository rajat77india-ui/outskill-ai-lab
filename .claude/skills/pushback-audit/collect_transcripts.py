#!/usr/bin/env python3
"""Collect AI-assistant session transcripts from this machine into one archive.

Run this ON YOUR LOCAL MACHINE (not in a cloud sandbox):

    python3 tools/session_failure_analysis/collect_transcripts.py

It scans the standard on-disk locations for:
  - Claude Code (CLI, VS Code / JetBrains extensions)  -> ~/.claude/projects/**/*.jsonl
  - Codex CLI                                          -> ~/.codex/sessions/**/*.jsonl, ~/.codex/history.jsonl
  - Cursor (chat + composer)                           -> Cursor/User/**/state.vscdb (sqlite)
  - Antigravity (VS Code fork)                         -> Antigravity/User/**/state.vscdb (sqlite)
  - VS Code chat sessions (Copilot/other panels)       -> Code/User/workspaceStorage/*/chatSessions/*.json

It produces ./session_failure_analysis_out/ containing:
  - events.jsonl      every extracted user message, with source metadata
  - candidates.jsonl  user messages matching pushback/frustration patterns,
                      each with the preceding assistant snippet for context
  - raw/              raw dumps of chat blobs the extractor could not fully parse
  - summary.txt       counts per source
  - transcripts_bundle.zip  everything above, zipped for handoff

NOT covered (no local files exist): Claude desktop/web app conversations are
stored server-side. Export them at claude.ai -> Settings -> Privacy -> Export
data, and drop the export's conversations.json into the output dir before
zipping (the analyzer understands that format too).

WARNING: transcripts can contain secrets (keys, tokens, internal paths).
Review / share the zip privately; avoid committing it to a public repo.
"""

from __future__ import annotations

import json
import os
import platform
import re
import sqlite3
import sys
import tempfile
import shutil
import zipfile
from pathlib import Path

OUT_DIR = Path.cwd() / "session_failure_analysis_out"
RAW_DIR = OUT_DIR / "raw"
MAX_TEXT = 6000

PUSHBACK = re.compile(
    r"(?i)\b(redo|re-do|do (it|this|that) again|start over|try again|once again"
    r"|that'?s (wrong|not what|incorrect)|not what i (asked|said|meant|wanted)"
    r"|you (ignored|missed|skipped|broke|didn'?t|did not|failed|forgot|removed|deleted)"
    r"|i (told|already told|asked|already asked|said|clearly said|explicitly)"
    r"|why (did|didn'?t|would) you|stop (doing|it|that)|don'?t do that"
    r"|hand[- ]?wav\w*|vague|superficial|lazy|placeholder|stub(bed)?|fake|mock(ed)? data"
    r"|frustrat\w*|annoy\w*|ridiculous|useless|wtf|wth|come on|seriously"
    r"|revert|undo|roll ?back|go back|as i (said|asked|mentioned)"
    r"|wrong file|wrong branch|wrong (approach|direction)|still (broken|failing|wrong|not working)"
    r"|doesn'?t work|does not work|not working|broke (it|the)|you'?re (not|wrong)"
    r"|incomplete|half[- ]done|didn'?t finish|actually (do|implement|fix|run|test)"
    r"|no[,.!]\s|again[.!?])",
)


def clip(s: str, n: int = MAX_TEXT) -> str:
    s = s.strip()
    return s if len(s) <= n else s[:n] + f" …[truncated {len(s) - n} chars]"


def emit(events: list, **kw) -> None:
    kw["text"] = clip(kw.get("text", ""))
    if kw["text"]:
        events.append(kw)


# ---------------------------------------------------------------- claude code
def collect_claude_code(events: list) -> None:
    root = Path.home() / ".claude" / "projects"
    if not root.is_dir():
        return
    for f in sorted(root.rglob("*.jsonl")):
        prev_assistant = ""
        for line in f.read_text(errors="replace").splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg = rec.get("message") or {}
            role = msg.get("role") or rec.get("type")
            content = msg.get("content")
            texts = []
            if isinstance(content, str):
                texts.append(content)
            elif isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "text":
                        texts.append(c.get("text", ""))
            text = "\n".join(t for t in texts if t)
            if role == "assistant":
                prev_assistant = text or prev_assistant
            elif role == "user" and text and not rec.get("isMeta"):
                if text.startswith(("<system-reminder", "<command-", "<local-command")):
                    continue
                emit(
                    events,
                    app="claude-code",
                    file=str(f),
                    project=f.parent.name,
                    session=f.stem,
                    timestamp=rec.get("timestamp"),
                    role="user",
                    text=text,
                    prev_assistant=clip(prev_assistant, 1500),
                )


# --------------------------------------------------------------------- codex
def _walk_user_texts(obj, out: list) -> None:
    """Best-effort: find {role: user, content: ...} shapes anywhere in a JSON tree."""
    if isinstance(obj, dict):
        if obj.get("role") == "user":
            c = obj.get("content")
            if isinstance(c, str):
                out.append(c)
            elif isinstance(c, list):
                for part in c:
                    if isinstance(part, dict):
                        t = part.get("text") or part.get("content")
                        if isinstance(t, str):
                            out.append(t)
        for v in obj.values():
            _walk_user_texts(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _walk_user_texts(v, out)


def collect_codex(events: list) -> None:
    root = Path.home() / ".codex"
    if not root.is_dir():
        return
    files = list((root / "sessions").rglob("*.jsonl")) if (root / "sessions").is_dir() else []
    hist = root / "history.jsonl"
    if hist.is_file():
        files.append(hist)
    for f in sorted(files):
        got_any = False
        for line in f.read_text(errors="replace").splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            texts: list = []
            _walk_user_texts(rec, texts)
            if not texts and isinstance(rec.get("text"), str):  # history.jsonl shape
                texts.append(rec["text"])
            for t in texts:
                got_any = True
                emit(
                    events,
                    app="codex",
                    file=str(f),
                    session=f.stem,
                    timestamp=rec.get("timestamp") or rec.get("ts"),
                    role="user",
                    text=t,
                )
        if not got_any:
            save_raw(f, "codex")


# ------------------------------------------------------- vscdb (cursor et al)
CHAT_KEY_HINTS = ("aichat", "composer", "chat", "prompt", "aiService", "inlineChat")


def collect_vscdb_app(events: list, app_name: str, user_dir: Path) -> None:
    if not user_dir.is_dir():
        return
    dbs = list(user_dir.rglob("state.vscdb"))
    for db in dbs:
        # copy first: the IDE may hold a lock
        with tempfile.NamedTemporaryFile(suffix=".vscdb", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            shutil.copy2(db, tmp_path)
            con = sqlite3.connect(f"file:{tmp_path}?mode=ro", uri=True)
            try:
                rows = con.execute("SELECT key, value FROM ItemTable").fetchall()
            finally:
                con.close()
        except Exception as e:
            print(f"  ! could not read {db}: {e}", file=sys.stderr)
            continue
        finally:
            tmp_path.unlink(missing_ok=True)

        for key, value in rows:
            if not any(h.lower() in str(key).lower() for h in CHAT_KEY_HINTS):
                continue
            if not isinstance(value, (str, bytes)):
                continue
            raw = value.decode("utf-8", "replace") if isinstance(value, bytes) else value
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            texts: list = []
            _walk_user_texts(data, texts)
            _walk_cursor_bubbles(data, texts)
            if texts:
                for t in texts:
                    emit(
                        events,
                        app=app_name,
                        file=str(db),
                        key=key,
                        role="user",
                        text=t,
                    )
            else:
                save_raw_blob(raw, f"{app_name}_{db.parent.parent.name}_{sanitize(key)}.json")


def _walk_cursor_bubbles(obj, out: list) -> None:
    """Cursor stores chat as bubbles with type==1 for user turns."""
    if isinstance(obj, dict):
        if obj.get("type") == 1 and isinstance(obj.get("text"), str) and obj["text"].strip():
            out.append(obj["text"])
        for v in obj.values():
            _walk_cursor_bubbles(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _walk_cursor_bubbles(v, out)


def collect_vscode_chat_sessions(events: list, app_name: str, user_dir: Path) -> None:
    if not user_dir.is_dir():
        return
    for f in user_dir.rglob("chatSessions/*.json"):
        try:
            data = json.loads(f.read_text(errors="replace"))
        except json.JSONDecodeError:
            continue
        for req in data.get("requests", []):
            msg = req.get("message")
            text = msg.get("text") if isinstance(msg, dict) else msg if isinstance(msg, str) else ""
            if text:
                emit(events, app=app_name, file=str(f), role="user", text=text)


# --------------------------------------------------------------------- utils
def sanitize(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", s)[:80]


def save_raw(f: Path, prefix: str) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    dest = RAW_DIR / f"{prefix}_{sanitize(f.name)}"
    try:
        shutil.copy2(f, dest)
    except OSError:
        pass


def save_raw_blob(raw: str, name: str) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / name).write_text(raw, errors="replace")


def app_user_dirs() -> dict:
    home = Path.home()
    sysname = platform.system()
    if sysname == "Darwin":
        base = home / "Library" / "Application Support"
    elif sysname == "Windows":
        base = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
    return {
        "cursor": base / "Cursor" / "User",
        "antigravity": base / "Antigravity" / "User",
        "vscode": base / "Code" / "User",
        "vscode-insiders": base / "Code - Insiders" / "User",
    }


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    events: list = []

    print("Scanning Claude Code transcripts…")
    collect_claude_code(events)
    print("Scanning Codex…")
    collect_codex(events)
    for app, user_dir in app_user_dirs().items():
        print(f"Scanning {app} ({user_dir})…")
        collect_vscdb_app(events, app, user_dir)
        collect_vscode_chat_sessions(events, app, user_dir)

    with (OUT_DIR / "events.jsonl").open("w") as fh:
        for e in events:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")

    candidates = [e for e in events if PUSHBACK.search(e["text"])]
    with (OUT_DIR / "candidates.jsonl").open("w") as fh:
        for e in candidates:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")

    counts: dict = {}
    for e in events:
        counts[e["app"]] = counts.get(e["app"], 0) + 1
    lines = [f"total user messages: {len(events)}", f"pushback candidates: {len(candidates)}"]
    lines += [f"  {app}: {n}" for app, n in sorted(counts.items())]
    raw_n = len(list(RAW_DIR.glob("*"))) if RAW_DIR.is_dir() else 0
    lines.append(f"raw unparsed blobs saved: {raw_n}")
    summary = "\n".join(lines)
    (OUT_DIR / "summary.txt").write_text(summary + "\n")
    print(summary)

    zip_path = OUT_DIR / "transcripts_bundle.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in OUT_DIR.rglob("*"):
            if p.is_file() and p != zip_path:
                z.write(p, p.relative_to(OUT_DIR))
    print(f"\nBundle ready: {zip_path}")
    print("Hand this zip to the analysis session (do NOT commit it to a public repo).")


if __name__ == "__main__":
    main()
