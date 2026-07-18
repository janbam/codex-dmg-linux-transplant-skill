#!/usr/bin/env python3
"""Recover the Codex CLI package version embedded in a bundled native binary."""

import re
from pathlib import Path


# Unified ChatGPT builds place the package semver immediately before these compile-time Codex target names.
_PRODUCT_MARKER = b"codex-appcodex-cli"
_VERSION_PATTERN = re.compile(
    rb"(?<![0-9A-Za-z.-])"
    rb"([0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z]+(?:\.[0-9A-Za-z]+)*)?)"
    + rb"(?=" + re.escape(_PRODUCT_MARKER) + rb")"
)


def read_bundled_codex_version(path: Path) -> str:
    """Return the CLI semver stored beside Codex's compile-time product markers."""
    binary = path.read_bytes()
    versions: set[str] = set()

    # Bind the version to Codex's own product markers so unrelated dependency versions cannot masquerade as the CLI version.
    for match in _VERSION_PATTERN.finditer(binary):
        versions.add(match.group(1).decode("ascii"))

    # Refuse to guess when upstream changes the binary layout or exposes conflicting product versions.
    if len(versions) != 1:
        found = ", ".join(sorted(versions)) or "none"
        raise ValueError(
            f"expected exactly one unified ChatGPT Codex CLI version in {path}; found {found}"
        )
    return versions.pop()
