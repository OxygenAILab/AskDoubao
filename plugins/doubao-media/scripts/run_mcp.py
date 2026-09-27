"""Launcher for the doubao-media MCP server.

The plugin is a thin shell over the `doubao_media` package that lives in this
repository's ``src/`` directory, so the launcher resolves that directory from
its own location instead of relying on a fragile relative ``cwd``.

Resolution order:
1. ``DOUBAO_MEDIA_SRC`` environment variable, when set.
2. A sibling ``src/doubao_media`` walking up from this file (repository layout).
3. An already-installed ``doubao_media`` on ``sys.path``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _candidate_roots() -> list[Path]:
    roots: list[Path] = []
    override = os.environ.get("DOUBAO_MEDIA_SRC")
    if override:
        roots.append(Path(override).expanduser())
    here = Path(__file__).resolve()
    for parent in here.parents:
        roots.append(parent / "src")
    return roots


def _ensure_importable() -> None:
    for root in _candidate_roots():
        if (root / "doubao_media" / "__init__.py").is_file():
            if str(root) not in sys.path:
                sys.path.insert(0, str(root))
            return


def main() -> int:
    _ensure_importable()
    try:
        from doubao_media.mcp.server import main as serve
    except ImportError as exc:  # pragma: no cover - environment diagnosis
        print(
            "doubao-media: cannot import the doubao_media package "
            f"({exc}).\nSet DOUBAO_MEDIA_SRC to the directory containing "
            "'doubao_media', or install the package with "
            "'pip install -e <repo>'.",
            file=sys.stderr,
        )
        return 2
    serve()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
