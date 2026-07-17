#!/usr/bin/env python3
import plistlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from dmg_layout import find_app_layout


def run(cmd):
    subprocess.run(cmd, check=True)


def ensure_pillow(target_dir: Path):
    try:
        from PIL import Image  # type: ignore
        return Image
    except Exception:
        run([sys.executable, '-m', 'ensurepip', '--upgrade'])
        run([sys.executable, '-m', 'pip', 'install', '--quiet', '--target', str(target_dir), 'Pillow'])
        sys.path.insert(0, str(target_dir))
        from PIL import Image  # type: ignore
        return Image


def remove_macos_payloads(root: Path):
    """Keep cross-platform plugin data without carrying unusable Mach-O binaries."""
    macho_magics = {
        b'\xfe\xed\xfa\xce', b'\xce\xfa\xed\xfe',
        b'\xfe\xed\xfa\xcf', b'\xcf\xfa\xed\xfe',
        b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca',
        b'\xca\xfe\xba\xbf', b'\xbf\xba\xfe\xca',
    }
    for app_bundle in root.rglob('*.app'):
        if app_bundle.is_dir():
            shutil.rmtree(app_bundle)
    for debug_bundle in root.rglob('*.dSYM'):
        if debug_bundle.is_dir():
            shutil.rmtree(debug_bundle)
    for path in root.rglob('*'):
        if not path.is_file():
            continue
        try:
            with path.open('rb') as file:
                magic = file.read(4)
        except OSError:
            continue
        if magic in macho_magics:
            path.unlink()


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: extract-codex-dmg-assets.py /path/to/ChatGPT.dmg /path/to/stage-dir')

    dmg = Path(sys.argv[1]).expanduser().resolve()
    stage = Path(sys.argv[2]).expanduser().resolve()
    if not dmg.exists():
        raise SystemExit(f'dmg not found: {dmg}')
    if shutil.which('7z') is None:
        raise SystemExit('7z is required')

    stage.mkdir(parents=True, exist_ok=True)
    (stage / 'resources').mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        # Discover the bundle and its declared icon without coupling extraction to either brand name.
        layout = find_app_layout(str(dmg))
        run(['7z', 'x', str(dmg), f'-ir!{layout.info_plist}', '-y', f'-o{out}'])
        info_path = out / Path(layout.info_plist)
        info = plistlib.load(info_path.open('rb'))
        icon_name = info.get('CFBundleIconFile') or 'electron.icns'
        if not Path(icon_name).suffix:
            icon_name += '.icns'

        includes = [
            f'{layout.resources}/app.asar',
            f'{layout.resources}/app.asar.unpacked',
            f'{layout.resources}/{icon_name}',
            f'{layout.resources}/plugins',
            f'{layout.resources}/skills',
        ]
        run(['7z', 'x', str(dmg), *(f'-ir!{path}' for path in includes), '-y', f'-o{out}'])

        resources = out / Path(layout.resources)
        app_asar = resources / 'app.asar'
        app_asar_unpacked = resources / 'app.asar.unpacked'
        icns = resources / icon_name
        if not app_asar.exists():
            raise SystemExit('failed to extract app.asar from dmg')
        if not app_asar_unpacked.is_dir():
            raise SystemExit('failed to extract app.asar.unpacked from dmg')
        if not icns.exists():
            raise SystemExit('failed to extract default icon from dmg')

        shutil.copy2(app_asar, stage / 'resources' / 'app.asar')
        # Replace the DMG payload so interrupted or older stages cannot leak stale files.
        stage_app_asar_unpacked = stage / 'resources' / 'app.asar.unpacked'
        shutil.rmtree(stage_app_asar_unpacked, ignore_errors=True)
        shutil.copytree(app_asar_unpacked, stage_app_asar_unpacked)

        # Keep portable external resources while stripping binaries that cannot execute on Linux.
        for resource_dir in ('plugins', 'skills'):
            source = resources / resource_dir
            if source.is_dir():
                target = stage / 'resources' / resource_dir
                shutil.rmtree(target, ignore_errors=True)
                shutil.copytree(source, target)
                remove_macos_payloads(target)
        shutil.copy2(icns, stage / 'icon.icns')

        Image = ensure_pillow(stage / '.python-deps')
        img = Image.open(icns)
        img.load()
        if img.mode not in ('RGBA', 'RGB'):
            img = img.convert('RGBA')
        img.thumbnail((512, 512))
        img.save(stage / 'icon.png')

    print(stage / 'resources' / 'app.asar')
    print(stage / 'icon.png')


if __name__ == '__main__':
    main()
