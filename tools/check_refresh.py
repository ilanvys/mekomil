#!/usr/bin/env python3
"""Check generated metadata and client artifacts after a catalog refresh."""

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SLUG = re.compile(r"^## ([a-z0-9][a-z0-9-]*)\s+`", re.MULTILINE)


def markdown_files(directory):
    return {path.name: path.read_bytes() for path in directory.glob("*.md")}


def catalog_slugs(files):
    seen = {}
    duplicates = []
    for name, raw in files.items():
        if name == "_index.md":
            continue
        for slug in SLUG.findall(raw.decode("utf-8")):
            if slug in seen:
                duplicates.append(f"{slug} ({seen[slug]}, {name})")
            seen[slug] = name
    return set(seen), duplicates


def main():
    mcp = ROOT / "mcp"

    failures = []
    catalog = markdown_files(mcp / "data" / "catalog")
    slugs, duplicates = catalog_slugs(catalog)
    failures += [f"duplicate catalog slug: {item}" for item in duplicates]

    manifest_path = mcp / "data" / "manifest.json"
    if not manifest_path.is_file():
        failures.append(f"manifest not found: {manifest_path}")
        manifest = {"skills": {}, "defaultBranches": {}}
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_slugs = set(manifest.get("skills", {}))

    only_catalog = sorted(slugs - manifest_slugs)
    only_manifest = sorted(manifest_slugs - slugs)
    if only_catalog:
        failures.append("catalog only (unsafe; MCP cannot load): " + ", ".join(only_catalog))
    if only_manifest:
        failures.append("manifest only (unroutable): " + ", ".join(only_manifest))

    branches = manifest.get("defaultBranches", {})
    for slug, skill in manifest.get("skills", {}).items():
        if "SKILL.md" not in skill.get("files", []):
            failures.append(f"{slug}: manifest has no SKILL.md")
        if skill.get("repo") not in branches:
            failures.append(f"{slug}: no recorded default branch for {skill.get('repo')}")

    plugin_skill = ROOT / "plugin" / "skills" / "mekomil" / "SKILL.md"
    canonical_skill = ROOT / "skill" / "SKILL.md"
    if not plugin_skill.is_file() or not canonical_skill.is_file() or plugin_skill.read_bytes() != canonical_skill.read_bytes():
        failures.append("plugin SKILL.md differs from skill/SKILL.md")
    plugin_catalog_dir = plugin_skill.parent / "catalog"
    if plugin_catalog_dir.exists():
        failures.append("plugin still bundles catalog metadata")

    if failures:
        print("refresh check failed:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1

    print(
        f"refresh check OK: {len(slugs)} skills, {len(catalog) - 1} categories, "
        "catalog = manifest; plugin uses MCP"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
