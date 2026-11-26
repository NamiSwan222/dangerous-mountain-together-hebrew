"""Turn an UnrealPak 5.7+ pak (version 12, Utf8PakDirectory) into version 11 (Fnv64BugFix) for UE 5.6.

    python tools/pak_v11.py <file.pak>

The game is UE 5.6, whose runtime only reads pak versions up to 11 and stops at start with a
LowLevelFatalError in PakFile.cpp on a version 12 pak. Versions 11 and 12 differ only in the full
directory index: version 12 stores file names as UTF-8 strings (length without terminator),
version 11 as FString (length with the terminating NUL). This rewrites that index, its SHA-1 in the
primary index, the primary index SHA-1 and the version in the footer. Unencrypted paks only.
"""
import hashlib, struct, sys

MAGIC = 0x5A6F12E1
FOOTER = 16 + 1 + 4 + 4 + 8 + 8 + 20 + 5 * 32  # guid, encrypted index, magic, version, offset, size, hash, methods


def _fstring(b, i):
    n, = struct.unpack_from('<i', b, i)
    i += 4
    if n < 0:
        return b[i:i - 2 * n].decode('utf-16-le').rstrip('\0'), i - 2 * n
    return b[i:i + n].rstrip(b'\0').decode('latin-1'), i + n


def _put_fstring(s):
    try:
        raw = s.encode('ascii') + b'\0'
        return struct.pack('<i', len(raw)) + raw
    except UnicodeEncodeError:
        raw = (s + '\0').encode('utf-16-le')
        return struct.pack('<i', -(len(raw) // 2)) + raw


def convert(path):
    d = bytearray(open(path, 'rb').read())
    f = len(d) - FOOTER
    if struct.unpack_from('<I', d, f + 17)[0] != MAGIC:
        sys.exit(f'{path}: no pak footer')
    if d[f + 16]:
        sys.exit(f'{path}: encrypted index not supported')
    ver, io, isz = struct.unpack_from('<IQQ', d, f + 21)
    if ver == 11:
        return False
    if ver != 12:
        sys.exit(f'{path}: pak version {ver}, expected 12')
    idx = bytes(d[io:io + isz])
    # primary index: mount point, entry count, path hash seed, then the two optional sub-indexes
    _, i = _fstring(idx, 0)
    i += 4 + 8
    has_phi, = struct.unpack_from('<i', idx, i)
    i += 4
    if has_phi:
        i += 8 + 8 + 20
    has_fdi, = struct.unpack_from('<i', idx, i)
    if not has_fdi:
        sys.exit(f'{path}: no full directory index')
    fdi_at = i + 4
    fo, fs = struct.unpack_from('<QQ', idx, fdi_at)
    fdi = bytes(d[fo:fo + fs])
    # full directory index: dirs { FString dir, files { utf8 name, int32 location } }
    out = bytearray()
    n, = struct.unpack_from('<i', fdi, 0)
    out += struct.pack('<i', n)
    j = 4
    for _ in range(n):
        name, j = _fstring(fdi, j)
        out += _put_fstring(name)
        nf, = struct.unpack_from('<i', fdi, j)
        j += 4
        out += struct.pack('<i', nf)
        for _ in range(nf):
            ln, = struct.unpack_from('<i', fdi, j)
            j += 4
            fname = fdi[j:j + ln].decode('utf-8')
            j += ln
            out += _put_fstring(fname) + fdi[j:j + 4]
            j += 4
    if j != len(fdi):
        sys.exit(f'{path}: directory index parse error')
    # the indexes are the last thing before the footer: rewrite them in the same order
    if fo < io + isz or fo + fs != f:
        sys.exit(f'{path}: unexpected index layout')
    new_idx = bytearray(idx)
    struct.pack_into('<QQ', new_idx, fdi_at, fo, len(out))
    new_idx[fdi_at + 16:fdi_at + 36] = hashlib.sha1(out).digest()
    between = bytes(d[io + isz:fo])  # path hash index
    footer = bytearray(d[f:])
    struct.pack_into('<IQQ', footer, 21, 11, io, isz)
    footer[41:61] = hashlib.sha1(new_idx).digest()
    data = bytes(d[:io]) + bytes(new_idx) + between + bytes(out) + bytes(footer)
    open(path, 'wb').write(data)
    return True


if __name__ == '__main__':
    for p in sys.argv[1:]:
        print(p, 'converted to v11' if convert(p) else 'already v11')
