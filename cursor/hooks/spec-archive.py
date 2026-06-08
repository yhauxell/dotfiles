#!/usr/bin/env python3
"""
afterFileEdit hook: when a versioned SPEC is written
(`.cursor/specs/<slug>.spec.vN.md` with N >= 2), move every older sibling
(`<slug>.spec.md` and `<slug>.spec.v1.md` ... `<slug>.spec.v(N-1).md`)
into `.cursor/specs/archive/`.

Why:
- SPECs are append-only: the architect bumps the suffix when revising.
- Over the life of a feature, v1..v5 pile up in the active dir and obscure
  "which one is current". Auto-archive enforces "only the current spec lives
  next to active specs".

Why a hook and not just architect instructions:
- The architect might forget. A hook makes the invariant unconditional.

Failure mode:
- failClosed: false. If anything goes wrong, we silently no-op so the user's
  workflow is never blocked by housekeeping.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from typing import Dict, List, Optional, Tuple

# Matches: <slug>.spec.md OR <slug>.spec.vN.md (N >= 1).
# Captures: (slug, version) where version is None for the unversioned form.
SPEC_RE = re.compile(r"^(?P<slug>.+?)\.spec(?:\.v(?P<v>\d+))?\.md$")


def _first_str(payload: Dict, keys: Tuple[str, ...]) -> Optional[str]:
    for k in keys:
        v = payload.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    args = payload.get("arguments")
    if isinstance(args, dict):
        for k in keys:
            v = args.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return None


def _extract_path(payload: Dict) -> Optional[str]:
    return _first_str(payload, ("file", "path", "file_path", "target"))


def _parse_spec_filename(filename: str) -> Optional[Tuple[str, int]]:
    """Return (slug, version) or None. Unversioned form returns version=0."""
    m = SPEC_RE.match(filename)
    if not m:
        return None
    slug = m.group("slug")
    v_raw = m.group("v")
    version = int(v_raw) if v_raw is not None else 0
    return slug, version


def _allow() -> int:
    sys.stdout.write(json.dumps({"permission": "allow"}))
    return 0


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        return _allow()

    try:
        payload = json.loads(raw)
    except Exception:
        return _allow()
    if not isinstance(payload, dict):
        return _allow()

    file_path = _extract_path(payload)
    if not file_path:
        return _allow()

    # Only care about specs under .cursor/specs/, never inside .cursor/specs/archive/.
    norm = file_path.replace("\\", "/")
    if "/.cursor/specs/" not in norm and not norm.startswith(".cursor/specs/"):
        return _allow()
    if "/.cursor/specs/archive/" in norm or norm.startswith(".cursor/specs/archive/"):
        return _allow()

    spec_dir = os.path.dirname(file_path)
    filename = os.path.basename(file_path)

    parsed = _parse_spec_filename(filename)
    if not parsed:
        return _allow()

    slug, version = parsed
    if version < 2:
        # No archive to do: v0 (unversioned) or v1 is the first spec.
        return _allow()

    # Find older siblings for the same slug in spec_dir.
    try:
        entries = os.listdir(spec_dir)
    except OSError:
        return _allow()

    older: List[str] = []
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
        return _allow()

    archive_dir = os.path.join(spec_dir, "archive")
    try:
        os.makedirs(archive_dir, exist_ok=True)
    except OSError:
        return _allow()

    moved: List[str] = []
    for name in older:
        src = os.path.join(spec_dir, name)
        dst = os.path.join(archive_dir, name)
        # If a same-named file already exists in archive (re-runs), leave it.
        if os.path.exists(dst):
            continue
        try:
            shutil.move(src, dst)
            moved.append(name)
        except OSError:
            continue

    if not moved:
        return _allow()

    msg = (
        f"Archived {len(moved)} older SPEC version(s) for slug `{slug}` -> "
        f"{archive_dir}/: {', '.join(sorted(moved))}"
    )
    sys.stdout.write(json.dumps({
        "permission": "allow",
        "followup_message": msg,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
