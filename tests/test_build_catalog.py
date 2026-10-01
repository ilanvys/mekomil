#!/usr/bin/env python3
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "mcp" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import build_catalog
from build_catalog import parse_frontmatter


class ParseFrontmatterTests(unittest.TestCase):
    def test_folded_description(self):
        body = """---
name: folded
description: >-
  First line with : punctuation.
  Second line in the same paragraph.
---
# Folded
"""
        self.assertEqual(
            parse_frontmatter(body)["description"],
            "First line with : punctuation. Second line in the same paragraph.",
        )

    def test_literal_description_and_unicode(self):
        body = """---
name: literal
description: |
  שורה ראשונה
  שורה שנייה
---
# Literal
"""
        self.assertEqual(
            parse_frontmatter(body)["description"],
            "שורה ראשונה\nשורה שנייה",
        )

    def test_quotes_are_parsed_by_yaml(self):
        body = '''---
name: quoted
description: "Use when the value is: \\"quoted\\"."
---
# Quoted
'''
        self.assertEqual(
            parse_frontmatter(body)["description"],
            'Use when the value is: "quoted".',
        )

    def test_malformed_yaml_fails_with_source(self):
        with self.assertRaisesRegex(ValueError, r"repo/skill/SKILL.md: malformed YAML"):
            parse_frontmatter(
                "---\ndescription: [unterminated\n---\n# Bad\n",
                "repo/skill/SKILL.md",
            )

    def test_missing_description_fails(self):
        with self.assertRaisesRegex(ValueError, "description must be a non-empty string"):
            parse_frontmatter("---\nname: no-description\n---\n# Missing\n")

    def test_placeholder_description_fails(self):
        with self.assertRaisesRegex(ValueError, "description is a placeholder"):
            parse_frontmatter('---\nname: placeholder\ndescription: ">-"\n---\n# Placeholder\n')

    def test_unterminated_frontmatter_fails(self):
        with self.assertRaisesRegex(ValueError, "missing or unterminated"):
            parse_frontmatter("---\nname: broken\ndescription: never closes\n")


class PublishTests(unittest.TestCase):
    def test_complete_candidate_replaces_previous_catalog(self):
        with tempfile.TemporaryDirectory() as root:
            out = os.path.join(root, "catalog")
            os.mkdir(out)
            with open(os.path.join(out, "old.md"), "w", encoding="utf-8") as f:
                f.write("old")

            with patch.object(build_catalog, "ROOT", root), patch.object(build_catalog, "OUT", out):
                build_catalog.publish({"_index.md": "index", "new.md": "new"})

            self.assertEqual(sorted(os.listdir(out)), ["_index.md", "new.md"])
            with open(os.path.join(out, "new.md"), encoding="utf-8") as f:
                self.assertEqual(f.read(), "new")

    def test_staging_failure_keeps_previous_catalog(self):
        with tempfile.TemporaryDirectory() as root:
            out = os.path.join(root, "catalog")
            os.mkdir(out)
            old = os.path.join(out, "old.md")
            with open(old, "w", encoding="utf-8") as f:
                f.write("still usable")

            with patch.object(build_catalog, "ROOT", root), patch.object(build_catalog, "OUT", out), \
                    patch("builtins.open", side_effect=OSError("disk full")):
                with self.assertRaisesRegex(OSError, "disk full"):
                    build_catalog.publish({"new.md": "new"})

            with open(old, encoding="utf-8") as f:
                self.assertEqual(f.read(), "still usable")


if __name__ == "__main__":
    unittest.main()
