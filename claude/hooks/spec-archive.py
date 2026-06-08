#!/usr/bin/env python3
"""
PostToolUse hook: when a versioned SPEC is written
(`.claude/specs/<slug>.spec.vN.md` with N >= 2), move every older sibling
(`<slug>.spec.md` and `<slug>.spec.v1.md` ... `<slug>.spec.v(N-1).md`)
into `.claude/specs/archive/`.

Why:
- SPECs are append-only: the architect bumps the suffix when revising.
- Over the life of a feature, v1..v5 pile up in the active dir and obscure
  "which one is current". Auto-archive enforces "only the current spec lives
  next to active specs".

Claude Code event contract (PostToolUse):
- stdin: JSON with `tool_name`, `tool_input` (e.g. `{"file_path": "..."}`),
  `tool_response`.
- stdout: optional informational message (does not affect tool result).
- exit 0: continue.
- failClosed: false — housekeeping never blocks workflow.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys

# Matches: <slug>.spec.md OR <slug>.spec.vN.md (N >= 1).
SPEC_RE = re.compile(r"^(?P<slug>.+?)\.spec(?:\.v(?P<v>\d+))?\.md$")


def _extract_file_path(payload):
    if not isinstance(payload, dict):
        return None
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        for key in ("file_path", "path", "filename"):
            value = tool_input.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    # Fallback: top-level fields.
    for key in ("file", "path", "file_path"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _parse_spec_filename(filename):
    m = SPEC_RE.match(filename)
    if not m:
        return None
    slug = m.group("slug")
    v_raw = m.group("v")
    version = int(v_raw) if v_raw is not None else 0
    return slug, version


def main():
    try:
        raw = sys.stdin.read()
    except Exception:
        return 0
    if not raw.strip():
        return 0

    try:
        payload = json.loads(raw)
    except Exception:
        return 0

    file_path = _extract_file_path(payload)
    if not file_path:
        return 0

    norm = file_path.replace("\\", "/")
    if "/.claude/specs/" not in norm and not norm.startswith(".claude/specs/"):
        return 0
    if "/.claude/specs/archive/" in norm or norm.startswith(".claude/specs/archive/"):
        return 0

    spec_dir = os.path.dirname(file_path)
    filename = os.path.basename(file_path)

    parsed = _parse_spec_filename(filename)
    if not parsed:
        return 0

    slug, version = parsed
    if version < 2:
        return 0

    try:
        entries = os.listdir(spec_dir)
    except OSError:
        return 0

    older = []
    for name in entries:
        if name == filename:
            continue
        parsed_other = _parse_spec_filename(name)
        if not parsed_other:
            continue
        slug_other, v_other = parsed_other
        if slug_other == slug and v_other < version:
            older.append(name)

    if not older:
        return 0

    archive_dir = os.path.join(spec_dir, "archive")
    try:
        os.makedirs(archive_dir, exist_ok=True)
    except OSError:
        return 0

    moved = []
    for name in older:
        src = os.path.join(spec_dir, name)
        dst = os.path.join(archive_dir, name)
        if os.path.exists(dst):
            continue
        try:
            shutil.move(src, dst)
            moved.append(name)
        except OSError:
            continue

    if moved:
        sys.stdout.write(
            f"[spec-archive] Archived {len(moved)} older SPEC version(s) "
            f"for slug `{slug}` -> {archive_dir}/: {', '.join(sorted(moved))}\n"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
