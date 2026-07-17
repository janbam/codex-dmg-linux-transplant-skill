#!/usr/bin/env python3
"""Locate the primary Electron app inside a Codex/ChatGPT DMG."""

import re
import subprocess
from dataclasses import dataclass
from pathlib import PurePosixPath


@dataclass(frozen=True)
class DmgAppLayout:
    """Brand-independent paths rooted at an Electron app's Contents directory."""

    contents: str

    @property
    def resources(self) -> str:
        return f'{self.contents}/Resources'

    @property
    def info_plist(self) -> str:
        return f'{self.contents}/Info.plist'

    @property
    def app_name(self) -> str:
        return PurePosixPath(self.contents).parts[-2].removesuffix('.app')


def find_app_layout(dmg: str) -> DmgAppLayout:
    """Find the single shallowest Electron app bundle carried by a DMG."""
    # Identify app candidates by their portable payload instead of a mutable product name.
    listing = subprocess.run(
        ['7z', 'l', '-slt', dmg],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    candidates = []
    for line in listing.splitlines():
        if not line.startswith('Path = '):
            continue
        path = line.removeprefix('Path = ')
        match = re.fullmatch(r'(.+\.app/Contents)/Resources/app\.asar', path)
        if match:
            candidates.append(match.group(1))

    # Ignore nested helper apps when one unambiguous top-level bundle exists.
    if candidates:
        shallowest_depth = min(len(PurePosixPath(path).parts) for path in candidates)
        candidates = [
            path for path in candidates
            if len(PurePosixPath(path).parts) == shallowest_depth
        ]
    # Fail closed rather than transplanting an arbitrary app from an ambiguous image.
    if len(candidates) != 1:
        found = ', '.join(candidates) if candidates else 'none'
        raise SystemExit(f'expected one top-level Electron app in dmg; found: {found}')
    return DmgAppLayout(candidates[0])
