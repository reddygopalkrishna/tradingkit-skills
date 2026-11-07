#!/usr/bin/env python3
"""Vendor core/tradekit into every skill's scripts/_vendor/tradekit.

Each skill must work when installed on its own (skills.sh, claude.ai uploads), so
the shared library is copied into each skill. Edit core/tradekit only, then run:

    python3 tools/sync_core.py          # copy
    python3 tools/sync_core.py --check  # CI: fail if any copy is stale
"""

from __future__ import annotations

import filecmp
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core" / "tradekit"
SKILLS = ROOT / "skills"
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc")
EXAMPLES = ROOT / "examples"
# example files bundled into skills so each skill works when installed alone
ASSETS = {
    "stock-screener": ["watchlists"],
    "chart-patterns": ["watchlists"],
    "market-regime": ["watchlists"],
    "trading-navigator": ["watchlists"],
    "backtester": ["strategies"],
}


def skill_dirs():
    return sorted(p for p in SKILLS.iterdir() if (p / "SKILL.md").exists() and (p / "scripts").is_dir())


def files(base: Path):
    return sorted(p.relative_to(base) for p in base.rglob("*.py") if "__pycache__" not in p.parts)


def stale(dest: Path) -> list:
    problems = []
    src_files = files(CORE)
    if not dest.exists():
        return ["missing"]
    dst_files = files(dest)
    if src_files != dst_files:
        problems.append(f"file set differs: {sorted(set(map(str, src_files)) ^ set(map(str, dst_files)))}")
    for f in src_files:
        if (dest / f).exists() and not filecmp.cmp(CORE / f, dest / f, shallow=False):
            problems.append(f"{f} differs")
    return problems


def main():
    check = "--check" in sys.argv
    bad = 0
    for sd in skill_dirs():
        dest = sd / "scripts" / "_vendor" / "tradekit"
        if check:
            p = stale(dest)
            for folder in ASSETS.get(sd.name, []):
                src, dst = EXAMPLES / folder, sd / "assets" / folder
                if not dst.exists() or filecmp.dircmp(src, dst).diff_files or \
                        set(x.name for x in src.iterdir()) != set(x.name for x in dst.iterdir()):
                    p.append(f"assets/{folder} out of date")
            if p:
                bad += 1
                print(f"STALE {sd.name}: {'; '.join(p)}")
        else:
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(CORE, dest, ignore=IGNORE)
            for folder in ASSETS.get(sd.name, []):
                dst = sd / "assets" / folder
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(EXAMPLES / folder, dst)
            print(f"synced {sd.name}")
    if check:
        if bad:
            print(f"\n{bad} skill(s) have a stale vendored core. Run: python3 tools/sync_core.py")
            sys.exit(1)
        print("All vendored cores are in sync.")


if __name__ == "__main__":
    main()
