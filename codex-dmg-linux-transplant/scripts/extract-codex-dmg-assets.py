#!/usr/bin/env python3
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


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


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: extract-codex-dmg-assets.py /path/to/Codex.dmg /path/to/stage-dir')

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
        run(['7z', 'x', str(dmg), '-ir!Codex Installer/Codex.app/Contents/Resources/app.asar', '-y', f'-o{out}'])
        run(['7z', 'x', str(dmg), '-ir!Codex Installer/Codex.app/Contents/Resources/app.asar.unpacked', '-y', f'-o{out}'])
        run(['7z', 'x', str(dmg), '-ir!Codex Installer/Codex.app/Contents/Resources/electron.icns', '-y', f'-o{out}'])

        app_asar = out / 'Codex Installer' / 'Codex.app' / 'Contents' / 'Resources' / 'app.asar'
        app_asar_unpacked = out / 'Codex Installer' / 'Codex.app' / 'Contents' / 'Resources' / 'app.asar.unpacked'
        icns = out / 'Codex Installer' / 'Codex.app' / 'Contents' / 'Resources' / 'electron.icns'
        if not app_asar.exists():
            raise SystemExit('failed to extract app.asar from dmg')
        if not app_asar_unpacked.is_dir():
            raise SystemExit('failed to extract app.asar.unpacked from dmg')
        if not icns.exists():
            raise SystemExit('failed to extract default icon from dmg')

        shutil.copy2(app_asar, stage / 'resources' / 'app.asar')
        stage_app_asar_unpacked = stage / 'resources' / 'app.asar.unpacked'
        shutil.rmtree(stage_app_asar_unpacked, ignore_errors=True)
        shutil.copytree(app_asar_unpacked, stage_app_asar_unpacked)
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
