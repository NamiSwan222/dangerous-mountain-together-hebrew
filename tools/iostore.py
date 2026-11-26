"""A minimal IoStore container (.utoc + .ucas) for UE 5.6 and helpers to patch a cooked (zen) package.

The game is IoStore: its widgets live in DMT-Windows.ucas. A chunk with the same id in a container
mounted with a higher order (our zzz_..._P pak) is read instead of the game's one, so a patched copy
of a package overrides it. The game's package store entry (exports, imports) stays valid as long as
the package keeps the same exports and imports, which is the case for a changed text in an export.

Container: TOC version 8 like the game's, no compression (method index 0), 64 KiB blocks, no
perfect hash (the reader falls back to a plain map), not indexed, not signed or encrypted.
"""
import hashlib, struct

BLOCK = 0x10000
MAGIC = b'-==--==--==--==-'
EXPORT_BUNDLE_DATA = 1


def chunk_id(package_id, chunk_type=EXPORT_BUNDLE_DATA, index=0):
    return struct.pack('<QHBB', package_id, index, 0, chunk_type)


def write_container(utoc, ucas, chunks, name):
    """chunks: [(12-byte chunk id, bytes)]; every chunk starts on a block boundary."""
    ids, offlens, blocks, data = b'', b'', b'', bytearray()
    for cid, buf in chunks:
        start = len(data)
        ids += cid
        offlens += start.to_bytes(5, 'big') + len(buf).to_bytes(5, 'big')
        for i in range(0, len(buf), BLOCK):
            part = buf[i:i + BLOCK]
            n = len(part)
            blocks += (len(data)).to_bytes(5, 'little') + n.to_bytes(3, 'little') + n.to_bytes(3, 'little') + b'\0'
            data += part
        data += bytes(-len(data) % BLOCK)
    n_blocks = len(blocks) // 12
    cid = struct.unpack('<Q', hashlib.sha1(name.encode()).digest()[:8])[0]
    h = MAGIC + struct.pack('<BBHIIIIIIIII', 8, 0, 0, 144, len(chunks), n_blocks, 12, 0, 32, BLOCK, 0, 1)
    h += struct.pack('<Q', cid) + bytes(16) + struct.pack('<BBHIQII', 0, 0, 0, 0, 2**64 - 1, 0, 0) + bytes(40)
    assert len(h) == 144
    meta = bytes(24) * len(chunks)  # FIoStoreTocEntryMeta (hash + flags), not checked at run time
    open(utoc, 'wb').write(h + ids + offlens + blocks + meta)
    open(ucas, 'wb').write(bytes(data))


def fstring(s):
    try:
        raw = s.encode('ascii') + b'\0'
        return struct.pack('<i', len(raw)) + raw
    except UnicodeEncodeError:
        raw = (s + '\0').encode('utf-16-le')
        return struct.pack('<i', -(len(raw) // 2)) + raw


def replace_in_package(header, exports, old, new):
    """Replace the FString `old` by `new` inside the export data of a zen package and fix the export map
    (CookedSerialOffset is relative to the export data, CookedSerialSize per export). Returns the chunk."""
    hs, = struct.unpack_from('<I', header, 4)
    assert hs == len(header)
    exm, ebe = struct.unpack_from('<ii', header, 32)  # ExportMapOffset, ExportBundleEntriesOffset
    a, b = fstring(old), fstring(new)
    pos = exports.find(a)
    if pos < 0 or exports.find(a, pos + 1) >= 0:
        raise ValueError(f'{old!r} not found exactly once')
    delta = len(b) - len(a)
    header = bytearray(header)
    hit = 0
    for i in range((ebe - exm) // 72):
        at = exm + 72 * i
        off, size = struct.unpack_from('<QQ', header, at)
        if off <= pos < off + size:
            struct.pack_into('<Q', header, at + 8, size + delta)
            hit += 1
        elif off > pos:
            struct.pack_into('<Q', header, at, off + delta)
    if hit != 1:
        raise ValueError('text is not inside one export')
    return bytes(header) + exports[:pos] + b + exports[pos + len(a):]
