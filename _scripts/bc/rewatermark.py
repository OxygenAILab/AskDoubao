"""Re-apply the development watermark after a repository change.

The organisation spec resolves the watermark from the repository owner, so a repo
move invalidates every existing watermark: keeping the previous owner's name would
be exactly the "hardcoded previous repository's owner" the spec forbids.

This tool therefore does a clean re-roll:

1. strip every existing watermark line (owner-agnostic detection),
2. re-insert one watermark per 50-ordinary-line window with the canonical value
   currently configured in ``insert_watermark.CANONICAL``.

Usage::

    python _scripts/bc/rewatermark.py --check
    python _scripts/bc/rewatermark.py --apply
"""

from __future__ import annotations

import argparse
import pathlib
import random
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import insert_watermark as W  # noqa: E402

#: Owner-agnostic watermark body detector: spaces are presentation-only, so a
#: real watermark always reduces to ``GitHub@<owner>[ | <org>@<login>]``.
BODY_RE = re.compile(r"(?:<!--|#|//)\s*([A-Za-z@|][^\n]*?)\s*(?:-->)?\s*$")


def is_watermark_line(line: str) -> bool:
    match = BODY_RE.search(line.strip())
    if not match:
        return False
    body = match.group(1).replace(" ", "")
    return body.startswith("GitHub@") and "@" in body[7:]


def strip_watermarks(text: str) -> tuple[str, int]:
    lines = text.split("\n")
    kept = [line for line in lines if not is_watermark_line(line)]
    return "\n".join(kept), len(lines) - len(kept)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--apply", action="store_true")
    group.add_argument("--check", action="store_true")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    print(f"canonical watermark: {W.CANONICAL}")
    print(f"files in scope      : {len(W.iter_files())}\n")

    stale: list[str] = []
    stripped_total = 0
    inserted_total = 0
    touched = 0

    for path in W.iter_files():
        original = path.read_text(encoding="utf-8")
        cleaned, removed = strip_watermarks(original)

        # Detect watermarks carrying a *different* owner than the current one.
        for line in original.split("\n"):
            if is_watermark_line(line) and W.strip_spacing(
                BODY_RE.search(line.strip()).group(1)  # type: ignore[union-attr]
            ) != W.CANONICAL_KEY:
                stale.append(f"{path.relative_to(W.REPO_ROOT)}: {line.strip()[:60]}")
                break

        if args.check:
            continue

        new_text, count = W.insert(cleaned, path.suffix, rng)
        if cleaned != original or new_text != cleaned:
            path.write_text(new_text, encoding="utf-8", newline="\n")
            touched += 1
            stripped_total += removed
            inserted_total += count

    if args.check:
        if stale:
            print(f"watermarks with a stale owner ({len(stale)}):")
            for item in stale:
                print(f"  {item}")
            return 1
        print("every watermark matches the current canonical value")
        return 0

    print(f"rewrote {touched} file(s): removed {stripped_total}, inserted {inserted_total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
