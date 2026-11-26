"""Build the Hebrew pack data for Dangerous Mountain Together.

    python tools/build.py

work/pack/files/DMT/Binaries/Win64/:
  dsound.dll                          launcher-only proxy (tools/proxy, generic Tirgumim proxy)
  tirgumim/he/redirect.cfg            adds our pak to the game's Paks folder listing (only for the launcher)
  tirgumim/he/zzz_tirgumim_he_P.pak   (made with UnrealPak) Game.locres (en) in Hebrew, and the Tango Sans /
                                      Akira fonts with Hebrew letters from Rubik (OFL)
UE5 does bidi and shaping itself: the Hebrew stays in logical order.
"""
import json, os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.append(os.path.join(ROOT, '..', 'dispatch', 'tools'))
import extract, fonts, iostore, locres, make_translation, pak_v11, ue_hash  # noqa: E402

FONTS = {
    'DMT/Content/UI/Assets/Fonts/Tango/TangoSans.ufont': 'Rubik-Regular.ttf',
    'DMT/Content/UI/Assets/Fonts/Tango/TangoSans_Bold.ufont': 'Rubik-Bold.ttf',
    'DMT/Content/UI/Assets/Fonts/Akira/Akira_Expanded_Demo.ufont': 'Rubik-Black.ttf',
    # WB_Text (the input hints next to the key icons, ...) uses ZenMaru, a composite font with no fallback
    'DMT/Content/UI/Assets/Fonts/ZenMaru/ZenMaruGothic-Black.ufont': 'Rubik-Black.ttf',
    'DMT/Content/UI/Assets/Fonts/ZenMaru/ZenMaruGothic-Bold.ufont': 'Rubik-Bold.ttf',
}
FONT_SRC = os.path.join(ROOT, '..', 'tomb-raider-2013', 'tools', 'bin', 'fonts')
PAK_NAME = 'zzz_tirgumim_he_P.pak'
UTOC_NAME = PAK_NAME[:-4] + '.utoc'
UCAS_NAME = PAK_NAME[:-4] + '.ucas'
# Culture-invariant texts in cooked widgets (Game.locres cannot reach them): package path, package id
# (from `UnrealPak IoStore -List`), English, Hebrew. RLM first so the line is right-to-left.
WIDGET_TEXT = [
    ('DMT/Content/UI/Sections/WB_Options', 0x5E0DFC7A7DF10C61, 'Max FPS', '‏FPS מקסימלי'),
]


def main():
    work = os.path.join(ROOT, 'work')
    ex = os.path.join(work, 'extract')
    stage = os.path.join(work, 'stage')
    shutil.rmtree(stage, ignore_errors=True)
    he = json.load(open(os.path.join(ROOT, 'translation', 'he', 'strings.json'), encoding='utf-8'))
    ver, ents = locres.read(os.path.join(ex, extract.LOCRES))
    out = [(ns, nsh, key, kh, sh, he.get(f'{ns}|{key}', text)) for ns, nsh, key, kh, sh, text in ents]
    nsh = {ns: h for ns, h, *_ in ents}
    for sid, src in make_translation.EXTRA.items():
        ns, key = sid.split('|', 1)
        if sid in he and not any(e[0] == ns and e[2] == key for e in ents):
            out.append((ns, nsh.get(ns, ue_hash.key_hash(ns)), key, ue_hash.key_hash(key), ue_hash.source_hash(src), he[sid]))
    dst = os.path.join(stage, extract.LOCRES)
    os.makedirs(os.path.dirname(dst))
    locres.write(dst, ver, out)
    for path, src in FONTS.items():
        ttf, tail = fonts.unpack(open(os.path.join(ex, path), 'rb').read())
        new, n = fonts.add_hebrew(ttf, os.path.join(FONT_SRC, src))
        d = os.path.join(stage, path)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        open(d, 'wb').write(fonts.pack(new, tail))
        print(path, '+', n, 'glyphs from', src)
    # pak (mount point ../../../ like the game's)
    lst = os.path.join(work, 'paklist.txt')
    with open(lst, 'w', encoding='utf-8') as f:
        for dirpath, _, files in os.walk(stage):
            for fn in files:
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, stage).replace('\\', '/')
                f.write(f'"{full}" "../../../{rel}"\n')
    pack = os.path.join(work, 'pack')
    shutil.rmtree(pack, ignore_errors=True)
    win = os.path.join(pack, 'files', 'DMT', 'Binaries', 'Win64')
    data = os.path.join(win, 'tirgumim', 'he')
    os.makedirs(data)
    pak = os.path.join(data, PAK_NAME)
    r = subprocess.run([extract.UNREALPAK, pak, f'-Create={lst}'], capture_output=True, text=True)
    if r.returncode or not os.path.exists(pak):
        sys.exit(r.stdout[-2000:] + r.stderr[-2000:])
    pak_v11.convert(pak)  # the game is UE 5.6: it stops at start on a 5.7+ (v12) pak
    # IoStore container next to the pak (UE 5.6 skips a pak without one); it also carries patched widgets
    chunks = []
    for path, pid, en, he_text in WIDGET_TEXT:
        base = os.path.join(ex, 'iostore', path)
        chunk = iostore.replace_in_package(open(base + '.uheader', 'rb').read(), open(base + '.uexp', 'rb').read(), en, he_text)
        chunks.append((iostore.chunk_id(pid), chunk))
    iostore.write_container(os.path.join(data, UTOC_NAME), os.path.join(data, UCAS_NAME), chunks, UTOC_NAME)
    with open(os.path.join(data, 'redirect.cfg'), 'w', newline='\n') as f:
        f.write('root=..\\..\\..\n')
        f.write(f'add=DMT\\Content\\Paks\\{PAK_NAME}\n')
        f.write(f'add=DMT\\Content\\Paks\\{UTOC_NAME}\n')
        f.write(f'add=DMT\\Content\\Paks\\{UCAS_NAME}\n')
    shutil.copy(os.path.join(ROOT, 'tools', 'proxy', 'target', 'release', 'tirgumim_proxy.dll'), os.path.join(win, 'dsound.dll'))
    print('pak', os.path.getsize(pak), 'bytes')


if __name__ == '__main__':
    main()
