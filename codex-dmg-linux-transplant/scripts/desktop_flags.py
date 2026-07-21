#!/usr/bin/env python3
"""Rewrite the renderer's semantic desktop-feature dispatch without alias guesses."""

from __future__ import annotations

import mmap
import re
import sys
from dataclasses import dataclass
from pathlib import Path


# Stable Electron message used to publish renderer feature availability.
DESKTOP_FEATURE_EVENT = "electron-desktop-features-changed"

# Portable desktop features that the Linux transplant may advertise.
FORCED_DESKTOP_FEATURES = (
    "avatarOverlay",
    "ambientSuggestions",
    "artifactsPane",
    "browserPane",
    "multiWindow",
    "projectlessThreads",
)

_IDENTIFIER = r"[A-Za-z_$][A-Za-z0-9_$]*"
_EVENT_BYTES = DESKTOP_FEATURE_EVENT.encode()
_DISPATCH = re.compile(
    rf"(?P<bridge>{_IDENTIFIER})\.dispatchMessage\(\s*`{DESKTOP_FEATURE_EVENT}`,\s*\{{"
)
_DISPATCH_BYTES = re.compile(
    rb"[A-Za-z_$][A-Za-z0-9_$]*\.dispatchMessage\(\s*`"
    + _EVENT_BYTES
    + rb"`,\s*\{"
)
_FUNCTION_START = re.compile(
    rf"^function (?P<name>{_IDENTIFIER})\([^{{}}]*\) \{{$"
)
_USE_EFFECT = re.compile(rf"\(0,\s*(?P<react>{_IDENTIFIER})\.useEffect\)\(")


class DesktopFlagPatchError(ValueError):
    """Report a renderer shape that cannot be patched without guessing."""


@dataclass(frozen=True)
class DesktopFlagPatch:
    """Describe the rewritten bundle text and the features it now forces."""

    text: str
    function_name: str
    features: tuple[str, ...]


def find_desktop_feature_bundle(root: Path) -> Path | None:
    """Find the sole JavaScript bundle that semantically publishes desktop features."""
    # Memory-map large bundles so semantic discovery does not decode the entire app.
    candidates: list[Path] = []
    for path in root.rglob("*.js"):
        if path.stat().st_size == 0:
            continue
        with path.open("rb") as file:
            with mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as contents:
                if (
                    contents.find(_EVENT_BYTES) != -1
                    and _DISPATCH_BYTES.search(contents) is not None
                ):
                    candidates.append(path)

    if len(candidates) > 1:
        paths = "\n".join(f"  {path}" for path in sorted(candidates))
        raise DesktopFlagPatchError(
            f"found multiple desktop feature renderer candidates:\n{paths}"
        )
    return candidates[0] if candidates else None


def patch_desktop_flags(text: str) -> DesktopFlagPatch:
    """Replace only the function that publishes supported desktop features."""
    # Anchor discovery in the stable Electron protocol instead of release-local aliases.
    dispatches = list(_DISPATCH.finditer(text))
    if len(dispatches) != 1:
        raise DesktopFlagPatchError(
            f"expected one {DESKTOP_FEATURE_EVENT} dispatch, found {len(dispatches)}"
        )
    dispatch = dispatches[0]

    # Use Prettier's top-level indentation to isolate the owning function exactly.
    lines = text.splitlines(keepends=True)
    offsets = _line_offsets(lines)
    dispatch_line = _line_containing(offsets, lines, dispatch.start())
    function_start, function_name = _find_enclosing_function(lines, dispatch_line)
    function_end = _find_function_end(lines, function_start)
    original_function = "".join(lines[function_start:function_end])

    function_offset = offsets[function_start]
    function_limit = function_offset + len(original_function)
    if not function_offset <= dispatch.start() < function_limit:
        raise DesktopFlagPatchError("desktop feature dispatch escaped its owning function")

    # Discover current feature keys and React aliases from the semantic dispatch.
    dispatch_end = _find_matching_brace(text, dispatch.end() - 1)
    if re.match(r"\s*\)", text[dispatch_end + 1 :]) is None:
        raise DesktopFlagPatchError("desktop feature object boundary is ambiguous")
    features = _find_dispatched_features(text[dispatch.end() : dispatch_end])
    if "browserPane" not in features:
        raise DesktopFlagPatchError("desktop feature dispatch does not expose browserPane")

    react_aliases = {match.group("react") for match in _USE_EFFECT.finditer(original_function)}
    if len(react_aliases) != 1:
        raise DesktopFlagPatchError(
            f"expected one React useEffect alias, found {len(react_aliases)}"
        )
    react_alias = react_aliases.pop()

    replacement = _render_forced_dispatch(
        function_name=function_name,
        bridge_alias=dispatch.group("bridge"),
        react_alias=react_alias,
        features=features,
    )
    return DesktopFlagPatch(
        text="".join(lines[:function_start]) + replacement + "".join(lines[function_end:]),
        function_name=function_name,
        features=features,
    )


def patch_desktop_flags_file(path: Path) -> DesktopFlagPatch:
    """Patch one Prettier-formatted renderer bundle in place."""
    patch = patch_desktop_flags(path.read_text())
    path.write_text(patch.text)
    return patch


def _line_offsets(lines: list[str]) -> list[int]:
    """Return the source offset at which each formatted line begins."""
    offsets: list[int] = []
    offset = 0
    for line in lines:
        offsets.append(offset)
        offset += len(line)
    return offsets


def _line_containing(offsets: list[int], lines: list[str], position: int) -> int:
    """Map one source offset to its formatted line index."""
    for index, offset in enumerate(offsets):
        if offset <= position < offset + len(lines[index]):
            return index
    raise DesktopFlagPatchError("failed to map desktop feature dispatch to a line")


def _find_enclosing_function(lines: list[str], dispatch_line: int) -> tuple[int, str]:
    """Find the nearest top-level function declaration above the dispatch."""
    for index in range(dispatch_line, -1, -1):
        match = _FUNCTION_START.fullmatch(lines[index].rstrip("\r\n"))
        if match is not None:
            return index, match.group("name")
    raise DesktopFlagPatchError("failed to locate desktop feature function start")


def _find_function_end(lines: list[str], function_start: int) -> int:
    """Find the first top-level closing brace after a formatted function start."""
    for index in range(function_start + 1, len(lines)):
        if lines[index].rstrip("\r\n") == "}":
            return index + 1
    raise DesktopFlagPatchError("failed to locate desktop feature function end")


def _find_matching_brace(text: str, opening_brace: int) -> int:
    """Find a JavaScript object's closing brace while ignoring quoted content."""
    depth = 0
    quote: str | None = None
    escaped = False
    line_comment = False
    block_comment = False
    index = opening_brace

    # Track only the lexical states that can hide braces in a formatted object.
    while index < len(text):
        char = text[index]
        following = text[index + 1] if index + 1 < len(text) else ""

        if line_comment:
            if char == "\n":
                line_comment = False
        elif block_comment:
            if char == "*" and following == "/":
                block_comment = False
                index += 1
        elif quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char == "/" and following == "/":
            line_comment = True
            index += 1
        elif char == "/" and following == "*":
            block_comment = True
            index += 1
        elif char in "'\"`":
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1

    raise DesktopFlagPatchError("failed to locate desktop feature dispatch end")


def _find_dispatched_features(object_body: str) -> tuple[str, ...]:
    """Read supported top-level keys from one Prettier-formatted object body."""
    # Remove deceptive property-shaped text before indentation reveals object structure.
    code_body = _mask_literals_and_comments(object_body)
    property_pattern = re.compile(
        rf"^(?P<indent>[ \t]*)(?P<key>{_IDENTIFIER})\s*(?::|,|$)", re.MULTILINE
    )
    properties = [
        (len(match.group("indent")), match.group("key"))
        for match in property_pattern.finditer(code_body)
    ]
    if not properties:
        raise DesktopFlagPatchError("desktop feature dispatch has no readable properties")

    top_level_indent = min(indent for indent, _ in properties)
    top_level_keys = {
        key for indent, key in properties if indent == top_level_indent
    }
    return tuple(
        feature for feature in FORCED_DESKTOP_FEATURES if feature in top_level_keys
    )


def _mask_literals_and_comments(text: str) -> str:
    """Blank JavaScript literals and comments while preserving line indentation."""
    masked = list(text)
    quote: str | None = None
    escaped = False
    line_comment = False
    block_comment = False
    index = 0

    # Preserve code and newlines, but make non-code text invisible to property matching.
    while index < len(text):
        char = text[index]
        following = text[index + 1] if index + 1 < len(text) else ""

        if line_comment:
            if char == "\n":
                line_comment = False
            else:
                masked[index] = " "
        elif block_comment:
            if char != "\n":
                masked[index] = " "
            if char == "*" and following == "/":
                masked[index + 1] = " "
                block_comment = False
                index += 1
        elif quote is not None:
            if char != "\n":
                masked[index] = " "
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char == "/" and following == "/":
            masked[index] = masked[index + 1] = " "
            line_comment = True
            index += 1
        elif char == "/" and following == "*":
            masked[index] = masked[index + 1] = " "
            block_comment = True
            index += 1
        elif char in "'\"`":
            masked[index] = " "
            quote = char
        index += 1

    return "".join(masked)


def _render_forced_dispatch(
    *,
    function_name: str,
    bridge_alias: str,
    react_alias: str,
    features: tuple[str, ...],
) -> str:
    """Render the small replacement function using discovered bundle identifiers."""
    feature_lines = "\n".join(f"      {feature}: enabled," for feature in features)
    return f"""function {function_name}() {{
  let enabled = !0;
  (0, {react_alias}.useEffect)(() => {{
    {bridge_alias}.dispatchMessage(`{DESKTOP_FEATURE_EVENT}`, {{
{feature_lines}
    }});
  }}, []);
  return null;
}}
"""


def main(argv: list[str]) -> int:
    """Find or patch the renderer file named on the command line."""
    if len(argv) == 3 and argv[1] == "--find":
        path = find_desktop_feature_bundle(Path(argv[2]))
        if path is not None:
            print(path)
        return 0

    if len(argv) != 2:
        raise SystemExit(
            "usage: desktop_flags.py <prettier-formatted-renderer.js>\n"
            "       desktop_flags.py --find <extracted-app-root>"
        )

    patch = patch_desktop_flags_file(Path(argv[1]))
    print(
        f"patched {patch.function_name}: forced {', '.join(patch.features)}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
