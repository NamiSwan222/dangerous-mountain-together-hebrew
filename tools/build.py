"""Build the Hebrew pack data for Dangerous Mountain Together.

    python tools/build.py

work/pack/files/DMT/Binaries/Win64/:
  dsound.dll                          launcher-only proxy (tools/proxy, generic Tirgumim proxy)
  tirgumim/he/redirect.cfg            adds our pak to the game's Paks folder listing (only for the launcher)
  tirgumim/he/zzz_tirgumim_he_P.pak   (made with UnrealPak) Game.locres (en) in Hebrew, and the Tango Sans /
                                      Akira fonts with Hebrew letters from Rubik (OFL)
UE5 does bidi and shaping itself: the Hebrew stays in logical order.
"""
import hashlib, json, os, shutil, struct, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.append(os.path.join(ROOT, '..', 'dispatch', 'tools'))
import extract, fonts, locres, pak_v11  # noqa: E402

FONTS = {
    'DMT/Content/UI/Assets/Fonts/Tango/TangoSans.ufont': 'Rubik-Regular.ttf',
    'DMT/Content/UI/Assets/Fonts/Tango/TangoSans_Bold.ufont': 'Rubik-Bold.ttf',
    'DMT/Content/UI/Assets/Fonts/Akira/Akira_Expanded_Demo.ufont': 'Rubik-Black.ttf',
}
FONT_SRC = os.path.join(ROOT, '..', 'tomb-raider-2013', 'tools', 'bin', 'fonts')
PAK_NAME = 'zzz_tirgumim_he_P.pak'
UTOC_NAME = PAK_NAME[:-4] + '.utoc'


def empty_utoc(path):
    """An IoStore TOC with no chunks (version 8 like the game's). The game uses IoStore, and UE 5.6 then
    refuses to mount a .pak without a .utoc of the same name ("IoStore container not found"), so the pak
    alone was silently skipped. No chunks: no .ucas (PartitionCount 0, as UE writes empty containers)."""
    cid = struct.unpack('<Q', hashlib.sha1(UTOC_NAME.encode()).digest()[:8])[0]
    h = b'-==--==--==--==-' + struct.pack('<BBHIIIIIIIII', 8, 0, 0, 144, 0, 0, 12, 0, 32, 65536, 0, 0)
    h += struct.pack('<Q', cid) + bytes(16) + struct.pack('<BBHIQII', 0, 0, 0, 0, 2**64 - 1, 0, 0) + bytes(40)
    assert len(h) == 144
    open(path, 'wb').write(h)


def main():
    work = os.path.join(ROOT, 'work')
    ex = os.path.join(work, 'extract')
    stage = os.path.join(work, 'stage')
    shutil.rmtree(stage, ignore_errors=True)
    he = json.load(open(os.path.join(ROOT, 'translation', 'he', 'strings.json'), encoding='utf-8'))
    ver, ents = locres.read(os.path.join(ex, extract.LOCRES))
    out = [(ns, nsh, key, kh, sh, he.get(f'{ns}|{key}', text)) for ns, nsh, key, kh, sh, text in ents]
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
    empty_utoc(os.path.join(data, UTOC_NAME))
    with open(os.path.join(data, 'redirect.cfg'), 'w', newline='\n') as f:
        f.write('root=..\\..\\..\n')
        f.write(f'add=DMT\\Content\\Paks\\{PAK_NAME}\n')
        f.write(f'add=DMT\\Content\\Paks\\{UTOC_NAME}\n')
    shutil.copy(os.path.join(ROOT, 'tools', 'proxy', 'target', 'release', 'tirgumim_proxy.dll'), os.path.join(win, 'dsound.dll'))
    print('pak', os.path.getsize(pak), 'bytes')


if __name__ == '__main__':
    main()
