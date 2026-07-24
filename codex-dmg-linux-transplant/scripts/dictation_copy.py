#!/usr/bin/env python3
"""Clarify the distinction between global and in-app dictation on Linux."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


MESSAGE_ID = "settings.voice.dictation.unsupported"
UPSTREAM_MESSAGE = "Dictation is not available on this device"
LINUX_MESSAGE = (
    "Global dictation shortcuts are unavailable on this device. "
    "In-app dictation still works from the composer."
)

_DESCRIPTOR = re.compile(
    r"\{(?P<body>[^{}]{0,1000})\}",
    re.DOTALL,
)
_ID_LITERAL = re.compile(rf"[`'\"]{re.escape(MESSAGE_ID)}[`'\"]")
_UPSTREAM_DEFAULT = re.compile(
    rf"(?P<prefix>\bdefaultMessage\s*:\s*)"
    rf"(?P<quote>[`'\"]){re.escape(UPSTREAM_MESSAGE)}(?P=quote)"
)
_LINUX_DEFAULT = re.compile(
    rf"\bdefaultMessage\s*:\s*([`'\"]){re.escape(LINUX_MESSAGE)}\1"
)


class DictationCopyPatchError(ValueError):
    """Report dictation copy that cannot be rewritten without guessing."""


@dataclass(frozen=True)
class DictationCopyPatch:
    """Describe the files and semantic message descriptors rewritten in one app."""

    files: tuple[Path, ...]
    descriptors: int


def patch_dictation_copy(root: Path) -> DictationCopyPatch:
    """Rewrite every descriptor that pairs the known message ID and upstream copy."""
    candidates: list[tuple[Path, str, int]] = []
    descriptor_count = 0

    # Stage every semantic candidate in memory so ambiguity cannot cause partial writes.
    for path in root.rglob("*.js"):
        text = path.read_text(errors="surrogateescape")
        if not _semantic_descriptors(text):
            continue
        rewritten, patched = _patch_descriptors(text)
        candidates.append((path, rewritten, patched))

    if not candidates:
        return DictationCopyPatch(files=(), descriptors=0)

    # Validate every staged descriptor before committing any bundle to disk.
    for path, rewritten, _ in candidates:
        for body in _semantic_descriptors(rewritten):
            if _UPSTREAM_DEFAULT.search(body) is not None:
                raise DictationCopyPatchError(
                    f"dictation message remained ambiguous in {path}"
                )
            if _LINUX_DEFAULT.search(body) is None:
                raise DictationCopyPatchError(
                    f"dictation message identifier had unknown copy in {path}"
                )

    # Commit the validated rewrite set as one logical patch operation.
    patched_files: list[Path] = []
    for path, rewritten, patched in candidates:
        if not patched:
            continue
        path.write_text(rewritten, errors="surrogateescape")
        patched_files.append(path)
        descriptor_count += patched

    return DictationCopyPatch(
        files=tuple(patched_files), descriptors=descriptor_count
    )


def _patch_descriptors(text: str) -> tuple[str, int]:
    """Rewrite matching message literals inside flat translation descriptors."""
    count = 0

    def replace_descriptor(match: re.Match[str]) -> str:
        """Preserve one descriptor unless its ID and upstream message form a pair."""
        nonlocal count
        body = match.group("body")
        if _ID_LITERAL.search(body) is None or _UPSTREAM_DEFAULT.search(body) is None:
            return match.group(0)

        # Replace only defaultMessage while preserving its property spacing and quotes.
        rewritten, replacements = _UPSTREAM_DEFAULT.subn(
            lambda message: (
                message.group("prefix")
                + message.group("quote")
                + LINUX_MESSAGE
                + message.group("quote")
            ),
            body,
        )
        count += replacements
        return "{" + rewritten + "}"

    return _DESCRIPTOR.sub(replace_descriptor, text), count


def _semantic_descriptors(text: str) -> tuple[str, ...]:
    """Return flat default-message descriptors carrying the dictation message ID."""
    descriptors: list[str] = []
    for match in _DESCRIPTOR.finditer(text):
        body = match.group("body")
        if _ID_LITERAL.search(body) is not None and "defaultMessage" in body:
            descriptors.append(body)
    return tuple(descriptors)


def main(argv: list[str]) -> int:
    """Patch extracted renderer bundles below the root named on the command line."""
    if len(argv) != 2:
        raise SystemExit("usage: dictation_copy.py <extracted-app-root>")

    patch = patch_dictation_copy(Path(argv[1]))
    if patch.descriptors == 0:
        print(
            "dictation copy patch skipped: message descriptor was not found",
            file=sys.stderr,
        )
    else:
        print(
            f"patched {patch.descriptors} dictation message descriptors in "
            f"{len(patch.files)} bundles",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
