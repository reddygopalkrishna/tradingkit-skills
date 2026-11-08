#!/usr/bin/env python3
"""Build one .skill (zip) per skill for upload to claude.ai (Customize > Skills), plus SHA256SUMS.

    python3 tools/build_packages.py            # -> dist/<skill>.skill, dist/tradingkit-skills-all.zip
"""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
DIST = ROOT / "dist"


def add_dir(z: zipfile.ZipFile, folder: Path, arc_root: str):
    for p in sorted(folder.rglob("*")):
        if p.is_dir() or "__pycache__" in p.parts or p.suffix == ".pyc" or p.name == ".DS_Store":
            continue
        info = zipfile.ZipInfo(f"{arc_root}/{p.relative_to(folder).as_posix()}", date_time=(2026, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = (0o755 if p.suffix == ".py" else 0o644) << 16
        z.writestr(info, p.read_bytes())


def main():
    DIST.mkdir(exist_ok=True)
    built = []
    for sd in sorted(p for p in SKILLS.iterdir() if (p / "SKILL.md").exists()):
        out = DIST / f"{sd.name}.skill"
        with zipfile.ZipFile(out, "w") as z:
            add_dir(z, sd, sd.name)
        built.append(out)
    bundle = DIST / "tradingkit-skills-all.zip"
    with zipfile.ZipFile(bundle, "w") as z:
        for sd in sorted(p for p in SKILLS.iterdir() if (p / "SKILL.md").exists()):
            add_dir(z, sd, f"skills/{sd.name}")
    built.append(bundle)
    sums = "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in built)
    (DIST / "SHA256SUMS").write_text(sums)
    for p in built:
        print(f"built {p.relative_to(ROOT)} ({p.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
