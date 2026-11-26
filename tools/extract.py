"""Dangerous Mountain Together (UE5): English text and font files from DMT-Windows.pak.

    python tools/extract.py      -> work/extract/... (UnrealPak), work/en/strings.json [{id, en}]

id = "<namespace>|<key>" of DMT/Content/Localization/Game/en/Game.locres.
Needs Unreal Engine's UnrealPak (D:\\UE\\UE_5.8 here, or set UNREALPAK).
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(ROOT, '..', 'dispatch', 'tools'))
import locres  # noqa: E402

GAME = r'D:\SteamLibrary\steamapps\common\Dangerous Mountain Together'
PAK = os.path.join(GAME, 'DMT', 'Content', 'Paks', 'DMT-Windows.pak')
UNREALPAK = os.environ.get('UNREALPAK', r'D:\UE\UE_5.8\Engine\Binaries\Win64\UnrealPak.exe')
LOCRES = 'DMT/Content/Localization/Game/en/Game.locres'
FILTERS = ['*Localization/Game/*', '*UI/Assets/Fonts/*']
UTOC = os.path.join(GAME, 'DMT', 'Content', 'Paks', 'DMT-Windows.utoc')
# cooked widgets with culture-invariant text (not in Game.locres), patched by tools/build.py
PACKAGES = ['*/UI/Sections/WB_Options.*']


def main():
    out = os.path.join(ROOT, 'work', 'extract')
    for f in FILTERS:
        subprocess.run([UNREALPAK, PAK, '-Extract', out, f'-Filter={f}'], check=True, capture_output=True)
    for f in PACKAGES:  # zen packages: <name>.uheader + <name>.uexp
        subprocess.run([UNREALPAK, 'IoStore', f'-FindAndExtract={UTOC}', f'-PackageFilter={f}',
                        f'-OutPath={os.path.join(out, "iostore")}'], check=True, capture_output=True)
    ver, ents = locres.read(os.path.join(out, LOCRES))
    rows = [{'id': f'{ns}|{key}', 'en': text} for ns, _, key, _, _, text in ents]
    os.makedirs(os.path.join(ROOT, 'work', 'en'), exist_ok=True)
    json.dump(rows, open(os.path.join(ROOT, 'work', 'en', 'strings.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print('locres v%d' % ver, len(rows), 'strings')


if __name__ == '__main__':
    main()
