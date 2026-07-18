#!/usr/bin/env python3
"""Behavior tests for Desktop and bundled-CLI release discovery."""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


# Load the repository scripts directly without requiring a package installation.
SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from codex_version import read_bundled_codex_version


def load_update_checker():
    """Load the hyphenated update-check command as a testable Python module."""
    spec = importlib.util.spec_from_file_location(
        "check_desktop_update", SCRIPTS / "check-desktop-update.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# Keep one module instance so dataclass identity remains stable throughout the test process.
CHECKER = load_update_checker()


class BundledCodexVersionTests(unittest.TestCase):
    """Prove extraction stays tied to Codex's product marker."""

    def test_reads_the_nearest_prerelease_version(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "codex"
            binary.write_bytes(
                b"dependency-9.9.9\0noise\0"
                b"0.145.0-alpha.18codex-appcodex-climacos"
            )

            self.assertEqual(read_bundled_codex_version(binary), "0.145.0-alpha.18")

    def test_rejects_a_binary_without_the_product_version(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "codex"
            binary.write_bytes(b"dependency-9.9.9\0codex-appcodex-climacos")

            with self.assertRaisesRegex(ValueError, "found none"):
                read_bundled_codex_version(binary)

    def test_rejects_conflicting_product_versions(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "codex"
            binary.write_bytes(
                b"0.145.0-alpha.18codex-appcodex-climacos\0"
                b"0.146.0-alpha.1codex-appcodex-climacos"
            )

            with self.assertRaisesRegex(ValueError, "0.145.0-alpha.18, 0.146.0-alpha.1"):
                read_bundled_codex_version(binary)


class DesktopReleaseTests(unittest.TestCase):
    """Prove the checker uses the appcast's first numerical build."""

    def test_reads_the_first_appcast_item(self):
        appcast = b"""<?xml version="1.0"?>
        <rss xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle">
          <channel>
            <item>
              <title>26.715.31925</title>
              <pubDate>Sat, 18 Jul 2026 05:09:45 +0000</pubDate>
              <sparkle:version>5551</sparkle:version>
              <sparkle:shortVersionString>26.715.31925</sparkle:shortVersionString>
            </item>
            <item>
              <title>26.715.31251</title>
              <sparkle:version>5538</sparkle:version>
            </item>
          </channel>
        </rss>"""

        release = CHECKER.parse_latest_release(appcast)

        self.assertEqual(release.version, "26.715.31925")
        self.assertEqual(release.build, 5551)
        self.assertEqual(release.published_at, "Sat, 18 Jul 2026 05:09:45 +0000")


if __name__ == "__main__":
    unittest.main()
