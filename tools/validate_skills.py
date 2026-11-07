#!/usr/bin/env python3
"""Validate every skill against the Agent Skills spec plus this repo's conventions.

Checks: SKILL.md frontmatter (name/description rules), folder name == name, body length,
referenced files exist, scripts compile and answer --help, marketplace.json lists every skill.
"""

from __future__ import annotations

import json
import py_compile
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ALLOWED_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}


def parse_frontmatter(text: str):
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md must start with '---' frontmatter")
    end = text.find("\n---", 4)
    if end < 0:
        raise ValueError("frontmatter not closed")
    raw = text[4:end]
    body = text[end + 4:]
    meta, key = {}, None
    for line in raw.splitlines():
        if not line.strip():
            continue
        if line.startswith((" ", "\t")) and key:
            meta[key] = (meta[key] + "\n" + line.strip()) if isinstance(meta[key], str) and meta[key] else line.strip()
            continue
        k, sep, v = line.partition(":")
        if not sep:
            raise ValueError(f"bad frontmatter line: {line!r}")
        key = k.strip()
        meta[key] = v.strip().strip('"')
    return meta, body


def main():
    errors, warnings = [], []
    names = []
    for sd in sorted(p for p in SKILLS.iterdir() if p.is_dir()):
        f = sd / "SKILL.md"
        if not f.exists():
            errors.append(f"{sd.name}: missing SKILL.md")
            continue
        text = f.read_text()
        try:
            meta, body = parse_frontmatter(text)
        except ValueError as e:
            errors.append(f"{sd.name}: {e}")
            continue
        name = meta.get("name", "")
        desc = meta.get("description", "")
        names.append(name)
        for k in meta:
            if k not in ALLOWED_KEYS:
                errors.append(f"{sd.name}: unknown frontmatter key {k!r}")
        if not NAME_RE.match(name) or len(name) > 64:
            errors.append(f"{sd.name}: invalid name {name!r}")
        if name != sd.name:
            errors.append(f"{sd.name}: name {name!r} must match folder")
        if not (50 <= len(desc) <= 1024):
            errors.append(f"{sd.name}: description length {len(desc)} (50-1024)")
        if "use when" not in desc.lower():
            warnings.append(f"{sd.name}: description should say when to use it")
        if "<" in desc or ">" in desc:
            errors.append(f"{sd.name}: description must not contain angle brackets")
        words = len(body.split())
        if words > 3500:
            warnings.append(f"{sd.name}: SKILL.md body is {words} words; move detail into references/")
        for ref in re.findall(r"\]\(((?:references|scripts|assets)/[^)#]+)\)", body):
            if not (sd / ref).exists():
                errors.append(f"{sd.name}: link to missing file {ref}")
        for script in re.findall(r"python3 (scripts/[\w\-]+\.py)", body):
            if not (sd / script).exists():
                errors.append(f"{sd.name}: SKILL.md mentions missing {script}")
        for py in (sd / "scripts").glob("*.py") if (sd / "scripts").exists() else []:
            try:
                py_compile.compile(str(py), doraise=True)
            except py_compile.PyCompileError as e:
                errors.append(f"{sd.name}: {py.name} does not compile: {e.msg}")
                continue
            r = subprocess.run([sys.executable, str(py), "--help"], capture_output=True, text=True, timeout=60)
            if r.returncode != 0:
                errors.append(f"{sd.name}: {py.name} --help failed: {r.stderr.strip()[-300:]}")
        if not (sd / "scripts" / "_vendor" / "tradekit").exists() and (sd / "scripts").exists():
            errors.append(f"{sd.name}: vendored core missing - run tools/sync_core.py")

    mp = ROOT / ".claude-plugin" / "marketplace.json"
    if not mp.exists():
        errors.append("missing .claude-plugin/marketplace.json")
    if mp.exists():
        data = json.loads(mp.read_text())
        listed = set()
        for pl in data.get("plugins", []):
            for s in pl.get("skills", []):
                listed.add(Path(s).name)
        if listed and set(names) - listed:
            errors.append(f"marketplace.json does not list: {sorted(set(names) - listed)}")

    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    print(f"\n{len(names)} skills checked, {len(errors)} errors, {len(warnings)} warnings")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
