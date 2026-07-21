#!/usr/bin/env python3
"""Behavior tests for semantic desktop-feature patching."""

import sys
import tempfile
import unittest
from pathlib import Path


# Load the repository transformer directly without requiring a package installation.
SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from desktop_flags import (
    DesktopFlagPatchError,
    find_desktop_feature_bundle,
    patch_desktop_flags,
)


CURRENT_RENDERER_SHAPE = """function ple() {
  let e = o(q),
    t = Kp(),
    n = Yp(),
    r = (0, X8.useRef)({ entries: [t.key], index: 0 }),
    i = mle(r.current, t.key, n);
  return i;
}
function unrelatedGate() {
  return qo(`459748632`) && Yp();
}
function xde() {
  let ambient = qo(`2425897452`),
    browser = p(jv),
    computerUse = platformCapability(),
    multiWindow = qo(`459748632`),
    projectlessThreads = false;
  (0, V7.useEffect)(() => {
    Kt.dispatchMessage(`electron-desktop-features-changed`, {
      ambientSuggestions: ambient,
      browserPane: browser,
      computerUse,
      diagnostics: {
        note: `}`,
        projectlessThreads,
      },
      multiWindow,
    });
  }, []);
  return null;
}
initializeRenderer();
"""


class DesktopFlagPatchTests(unittest.TestCase):
    """Prove patch discovery follows semantics and stays inside its function."""

    def test_forces_supported_current_features_without_touching_navigation(self):
        patch = patch_desktop_flags(CURRENT_RENDERER_SHAPE)

        self.assertEqual(
            patch.features,
            ("ambientSuggestions", "browserPane", "multiWindow"),
        )
        self.assertIn("n = Yp()", patch.text)
        self.assertIn("return qo(`459748632`) && Yp()", patch.text)
        self.assertIn("initializeRenderer();", patch.text)
        self.assertIn("ambientSuggestions: enabled", patch.text)
        self.assertIn("browserPane: enabled", patch.text)
        self.assertIn("multiWindow: enabled", patch.text)
        self.assertNotIn("projectlessThreads: enabled", patch.text)
        self.assertNotIn("computerUse: enabled", patch.text)

    def test_discovers_changed_minified_identifiers(self):
        renderer = CURRENT_RENDERER_SHAPE.replace("function xde()", "function $r()")
        renderer = renderer.replace("V7.useEffect", "_R.useEffect")
        renderer = renderer.replace("Kt.dispatchMessage", "$b.dispatchMessage")

        patch = patch_desktop_flags(renderer)

        self.assertEqual(patch.function_name, "$r")
        self.assertIn("(0, _R.useEffect)", patch.text)
        self.assertIn("$b.dispatchMessage", patch.text)

    def test_rejects_ambiguous_dispatches_instead_of_guessing(self):
        renderer = CURRENT_RENDERER_SHAPE + CURRENT_RENDERER_SHAPE.replace(
            "function xde()", "function duplicate()"
        )

        with self.assertRaisesRegex(DesktopFlagPatchError, "expected one .* found 2"):
            patch_desktop_flags(renderer)

    def test_rejects_a_dispatch_without_the_required_browser_feature(self):
        renderer = CURRENT_RENDERER_SHAPE.replace("      browserPane: browser,\n", "")

        with self.assertRaisesRegex(DesktopFlagPatchError, "does not expose browserPane"):
            patch_desktop_flags(renderer)

    def test_ignores_property_shaped_text_inside_a_template(self):
        renderer = CURRENT_RENDERER_SHAPE.replace("      browserPane: browser,\n", "")
        renderer = renderer.replace(
            "        note: `}`,",
            "        note: `\nbrowserPane: imaginary\n`,",
        )

        with self.assertRaisesRegex(DesktopFlagPatchError, "does not expose browserPane"):
            patch_desktop_flags(renderer)

    def test_rejects_an_object_boundary_the_lexer_cannot_prove(self):
        renderer = CURRENT_RENDERER_SHAPE.replace(
            "      ambientSuggestions: ambient,",
            "      ambientSuggestions: /}/,",
        )

        with self.assertRaisesRegex(DesktopFlagPatchError, "boundary is ambiguous"):
            patch_desktop_flags(renderer)

    def test_bundle_discovery_ignores_a_main_process_event_handler(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            main_bundle = root / "main.js"
            renderer_bundle = root / "renderer.js"
            main_bundle.write_text(
                "switch (message.type) { case `electron-desktop-features-changed`: "
                "consume(message.browserPane); }"
            )
            renderer_bundle.write_text(CURRENT_RENDERER_SHAPE)

            self.assertEqual(find_desktop_feature_bundle(root), renderer_bundle)

    def test_bundle_discovery_rejects_multiple_publishers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "first.js").write_text(CURRENT_RENDERER_SHAPE)
            (root / "second.js").write_text(CURRENT_RENDERER_SHAPE)

            with self.assertRaisesRegex(
                DesktopFlagPatchError, "multiple desktop feature renderer candidates"
            ):
                find_desktop_feature_bundle(root)


if __name__ == "__main__":
    unittest.main()
