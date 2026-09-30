"""Assemble the self-contained Codex plugin from this repository.

The plugin directory must be installable on its own, because Codex copies it
into its plugin cache.  Rather than duplicating the Python package, this script
keeps ``src/doubao_media`` and ``plugins/doubao-media/skills`` as the single
sources of truth and materialises the distributable layout:

    plugins/doubao-media/
    ├── .codex-plugin/plugin.json     (authored here, version stamped)
    ├── .mcp.json                     (authored here)
    ├── skills/wen-doubao/SKILL.md    (copied from plugins/.../skills)
    ├── scripts/run_mcp.py            (copied)
    ├── src/doubao_media/**           (copied from ../../../src/doubao_media)
    └── docs/protocol.md              (copied)

Run it after any change to the package:

    python scripts/build_plugin.py [--check]

``--check`` verifies the plugin is already in sync and exits non-zero when it
is not, so CI can gate on it.
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = REPO_ROOT / "plugins" / "doubao-media"

#: (source, destination relative to the plugin root, is_directory)
COPY_MAP: list[tuple[Path, str, bool]] = [
    (REPO_ROOT / "src" / "doubao_media", "src/doubao_media", True),
    (PLUGIN_DIR / "skills", "skills", True),
    (PLUGIN_DIR / "scripts" / "run_mcp.py", "scripts/run_mcp.py", False),
    (REPO_ROOT / "docs" / "protocol.md", "docs/protocol.md", False),
]

VENDORED = {"src/doubao_media", "skills", "docs"}
IGNORED_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}

#: Files that live only in the plugin and must never be overwritten.
AUTHORED = {".codex-plugin/plugin.json", ".mcp.json"}


def _iter_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for path in sorted(root.rglob("*")):
        if any(part in IGNORED_NAMES for part in path.parts):
            continue
        if path.suffix in IGNORED_SUFFIXES:
            continue
        if path.is_file():
            out.append(path)
    return out


def _copy_tree(source: Path, destination: Path) -> list[str]:
    written: list[str] = []
    for file in _iter_files(source):
        target = destination / file.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, target)
        written.append(str(target.relative_to(PLUGIN_DIR)))
    return written


# GitH  u  b@Ox   y genA I   Lab | Ox ygenA I  L ab@Star   sails   C  l over
def _in_sync(source: Path, destination: Path) -> list[str]:
    """Return the list of differences between a source tree and the vendored copy."""
    problems: list[str] = []
    source_files = {f.relative_to(source): f for f in _iter_files(source)}
    if destination.exists():
        dest_files = {f.relative_to(destination): f for f in _iter_files(destination)}
    else:
        dest_files = {}
    for relative, path in sorted(source_files.items()):
        other = dest_files.get(relative)
        if other is None:
            problems.append(f"missing: {relative}")
        elif not filecmp.cmp(path, other, shallow=False):
            problems.append(f"differs: {relative}")
    for relative in sorted(set(dest_files) - set(source_files)):
        problems.append(f"stale: {relative}")
    return problems


def build(*, check: bool) -> int:
    PLUGIN_DIR.mkdir(parents=True, exist_ok=True)
    for name in AUTHORED:
        path = PLUGIN_DIR / name
        if not path.exists():
            print(f"ERROR: authored file missing: {path}", file=sys.stderr)
            return 2

    if check:
        problems: list[str] = []
        for source, relative, _ in COPY_MAP:
            if source == PLUGIN_DIR / relative:
                continue  # self-referencing entry (skills/)
            problems.extend(f"{relative}: {p}" for p in _in_sync(source, PLUGIN_DIR / relative))
        if problems:
            print("plugin is out of sync:")
            for problem in problems[:40]:
                print(f"  {problem}")
            return 1
        print("plugin is in sync")
        return 0

    written: list[str] = []
    for source, relative, is_dir in COPY_MAP:
        destination = PLUGIN_DIR / relative
        if source == destination:
            continue
        if is_dir:
            if destination.exists():
                shutil.rmtree(destination)
            destination.mkdir(parents=True, exist_ok=True)
            written.extend(_copy_tree(source, destination))
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            written.append(relative)

    # G i   t Hub@Oxy   g e   nAILa  b | Oxy genAI  La  b  @   St a rsai ls C   l ov er
    print(f"plugin assembled at {PLUGIN_DIR}")
    print(f"files written: {len(written)}")
    return 0


# Gi tHub@Oxy   ge nA I Lab | O   xygenA   IL ab@  St a   rs  a  ils  C l  o  v  e   r
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="verify the plugin is in sync instead of writing")
    args = parser.parse_args()
    return build(check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
