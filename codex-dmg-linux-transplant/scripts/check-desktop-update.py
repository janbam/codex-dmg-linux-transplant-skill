#!/usr/bin/env python3
"""Report whether the installed ChatGPT Desktop transplant is current."""

import json
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


# OpenAI's Sparkle feed is the authoritative ordered list of unified Desktop builds.
APPCAST_URL = "https://persistent.oaistatic.com/codex-app-prod/appcast.xml"
# The transplant records its realized Desktop and CLI versions in this package metadata.
INSTALLED_METADATA = Path.home() / ".local/opt/codex-desktop/package.json"
# Sparkle stores the monotonic build and display version in namespaced elements.
SPARKLE_NAMESPACE = "http://www.andymatuschak.org/xml-namespaces/sparkle"


@dataclass(frozen=True)
class DesktopRelease:
    """A Desktop release identity suitable for monotonic build comparison."""

    version: str
    build: int
    published_at: str | None = None


def parse_latest_release(appcast: bytes) -> DesktopRelease:
    """Read the newest release from the first item in OpenAI's Sparkle feed."""
    root = ET.fromstring(appcast)
    item = root.find("./channel/item")
    if item is None:
        raise ValueError("appcast does not contain a release item")

    # Prefer Sparkle's machine-readable fields while retaining the title as the feed's documented version fallback.
    version = (
        item.findtext(f"{{{SPARKLE_NAMESPACE}}}shortVersionString")
        or item.findtext("title")
    )
    build_text = item.findtext(f"{{{SPARKLE_NAMESPACE}}}version")
    published_at = item.findtext("pubDate")
    if not version or not build_text:
        raise ValueError("latest appcast item is missing its version or build number")
    if not build_text.isdigit():
        raise ValueError(f"latest appcast build is not numeric: {build_text}")

    return DesktopRelease(version=version, build=int(build_text), published_at=published_at)


def read_installed_release(path: Path = INSTALLED_METADATA) -> DesktopRelease | None:
    """Read the installed transplant identity, or return None when it is absent."""
    if not path.is_file():
        return None

    metadata = json.loads(path.read_text())
    version = metadata.get("version")
    build = metadata.get("codexBuildNumber")
    if not isinstance(version, str) or not isinstance(build, str) or not build.isdigit():
        raise ValueError(
            f"installed metadata is missing a valid version or build number: {path}"
        )
    return DesktopRelease(version=version, build=int(build))


def fetch_latest_release(url: str = APPCAST_URL) -> DesktopRelease:
    """Fetch and parse OpenAI's authoritative Desktop release feed."""
    request = urllib.request.Request(
        url, headers={"User-Agent": "codex-dmg-linux-transplant/1"}
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return parse_latest_release(response.read())


def main() -> int:
    """Print installed/latest versions and a plain-language update verdict."""
    try:
        installed = read_installed_release()
        latest = fetch_latest_release()
    except (OSError, ValueError, json.JSONDecodeError, ET.ParseError, urllib.error.URLError) as error:
        print(f"failed to check Desktop version: {error}", file=sys.stderr)
        return 1

    # Always show the release facts before interpreting them so unusual feed or local states remain diagnosable.
    if installed is None:
        print("Installed: not found")
    else:
        print(f"Installed: {installed.version} (build {installed.build})")
    published = f", published {latest.published_at}" if latest.published_at else ""
    print(f"Latest:    {latest.version} (build {latest.build}{published})")

    if installed is None:
        print("Update available: install required")
    elif installed.build < latest.build:
        print("Update available: yes")
    elif installed.build == latest.build:
        print("Update available: no")
    else:
        print("Update available: no (installed build is newer than the current feed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
