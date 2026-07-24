#!/usr/bin/env python3
"""Behavior tests for Linux dictation copy clarification."""

import sys
import tempfile
import unittest
from pathlib import Path


# Load the repository transformer directly without requiring a package installation.
SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from dictation_copy import (
    LINUX_MESSAGE,
    UPSTREAM_MESSAGE,
    DictationCopyPatchError,
    patch_dictation_copy,
)


class DictationCopyPatchTests(unittest.TestCase):
    """Prove copy changes stay bound to the stable translation descriptor."""

    def test_patches_runtime_and_search_descriptors_in_either_property_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "voice.js").write_text(
                "({id:`settings.voice.dictation.unsupported`,"
                f"defaultMessage:`{UPSTREAM_MESSAGE}`,description:`Unsupported`}})"
            )
            (root / "search.js").write_text(
                f"[{{defaultMessage:'{UPSTREAM_MESSAGE}',"
                "id:'settings.voice.dictation.unsupported'}]"
            )

            patch = patch_dictation_copy(root)

            self.assertEqual(patch.descriptors, 2)
            self.assertEqual(len(patch.files), 2)
            self.assertIn(LINUX_MESSAGE, (root / "voice.js").read_text())
            self.assertIn(LINUX_MESSAGE, (root / "search.js").read_text())

    def test_ignores_the_same_sentence_under_an_unrelated_message_id(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "mixed.js"
            path.write_text(
                f"[{{defaultMessage:`{UPSTREAM_MESSAGE}`,id:`unrelated.message`}},"
                "{defaultMessage:`Already clear`,"
                "id:`settings.voice.dictation.unsupported`}]"
            )

            with self.assertRaisesRegex(
                DictationCopyPatchError, "message identifier had unknown copy"
            ):
                patch_dictation_copy(root)

            self.assertIn(UPSTREAM_MESSAGE, path.read_text())

    def test_rejects_all_candidates_before_writing_any_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid = root / "a-valid.js"
            invalid = root / "b-invalid.js"
            valid.write_text(
                "({id:`settings.voice.dictation.unsupported`,"
                f"defaultMessage:`{UPSTREAM_MESSAGE}`}})"
            )
            invalid.write_text(
                "({id:`settings.voice.dictation.unsupported`,"
                "defaultMessage:`Unexpected upstream copy`})"
            )

            with self.assertRaisesRegex(
                DictationCopyPatchError, "message identifier had unknown copy"
            ):
                patch_dictation_copy(root)

            self.assertIn(UPSTREAM_MESSAGE, valid.read_text())

    def test_does_not_treat_description_copy_as_the_default_message(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "voice.js"
            original = (
                "({id:`settings.voice.dictation.unsupported`,"
                "defaultMessage:`Unexpected upstream copy`,"
                f"description:`{UPSTREAM_MESSAGE}`}})"
            )
            path.write_text(original)

            with self.assertRaisesRegex(
                DictationCopyPatchError, "message identifier had unknown copy"
            ):
                patch_dictation_copy(root)

            self.assertEqual(path.read_text(), original)

    def test_ignores_locale_dictionaries_without_default_message_descriptors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "de-DE.js"
            original = (
                "export default {'settings.voice.dictation.unsupported':"
                "'Diktat ist auf diesem Gerät nicht verfügbar'}"
            )
            path.write_text(original)

            patch = patch_dictation_copy(root)

            self.assertEqual(patch.descriptors, 0)
            self.assertEqual(path.read_text(), original)

    def test_is_idempotent_after_the_copy_has_been_clarified(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "voice.js"
            path.write_text(
                "({id:`settings.voice.dictation.unsupported`,"
                f"defaultMessage:`{LINUX_MESSAGE}`}})"
            )

            patch = patch_dictation_copy(root)

            self.assertEqual(patch.descriptors, 0)
            self.assertEqual(patch.files, ())


if __name__ == "__main__":
    unittest.main()
