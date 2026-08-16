#!/usr/bin/env python3

import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import usage_stats


class UsageStatsTest(unittest.TestCase):
    def test_records_and_discovers_zero_usage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "usage-stats.json"
            skills = root / "skills"
            skills.mkdir()
            (skills / "sample.md").write_text(
                "<!-- usage-stats: skill used -->\n# usage-stats: hook unused\n",
                encoding="utf-8",
            )

            usage_stats.record(data, "skill", "used", "2026-08-16T00:00:00Z")
            usage_stats.record(data, "skill", "used", "2026-08-16T00:01:00Z")
            items = usage_stats.rows(data, skills)

            self.assertEqual(2, items[0]["count"])
            self.assertEqual("used", items[0]["name"])
            self.assertEqual(0, items[1]["count"])
            self.assertEqual("unused", items[1]["name"])


if __name__ == "__main__":
    unittest.main()
