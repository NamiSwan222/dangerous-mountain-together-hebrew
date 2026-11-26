"""Adds the Hebrew block from an OFL TrueType font to a cooked UE5 .ufont (u32 length, TTF, 4 zero bytes).

Glyphs are drawn through a scaling pen into the target's glyf table (simple glyphs), with matching hmtx
and cmap entries; the source is scaled so its 'H' height matches the target's.
"""
import io, struct
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen

HEBREW = list(range(0x05D0, 0x05EB)) + [0x05BE, 0x05F3, 0x05F4]


def unpack(ufont):
    n = struct.unpack_from('<I', ufont, 0)[0]
    return ufont[4:4 + n], ufont[4 + n:]


def pack(ttf, tail):
    return struct.pack('<I', len(ttf)) + ttf + tail


def cap(font, ch='H'):
    gs = font.getGlyphSet()
    bp = BoundsPen(gs)
    gs[font.getBestCmap()[ord(ch)]].draw(bp)
    return bp.bounds[3]


def to_truetype(t):
    """CFF -> glyf (quadratic) in place, as fontTools' otf2ttf snippet does."""
    from fontTools.pens.cu2quPen import Cu2QuPen
    from fontTools.ttLib import newTable
    gs = t.getGlyphSet()
    glyf = newTable('glyf')
    glyf.glyphOrder = t.getGlyphOrder()
    glyf.glyphs = {}
    for name in glyf.glyphOrder:
        pen = TTGlyphPen(gs)
        gs[name].draw(Cu2QuPen(pen, 1.0, reverse_direction=True))
        glyf[name] = pen.glyph()
    t['loca'] = newTable('loca')
    t['glyf'] = glyf
    del t['CFF ']
    t['maxp'] = newTable('maxp')
    m = t['maxp']
    m.tableVersion = 0x00010000
    for attr in ('maxZones', 'maxTwilightPoints', 'maxStorage', 'maxFunctionDefs', 'maxInstructionDefs',
                 'maxStackElements', 'maxSizeOfInstructions', 'maxComponentElements'):
        setattr(m, attr, 0)
    m.maxZones = 1
    m.numGlyphs = len(glyf.glyphOrder)
    t['head'].glyphDataFormat = 0
    post = t['post']
    post.formatType = 2.0
    post.extraNames = []
    post.mapping = {}
    post.glyphOrder = glyf.glyphOrder
    t.sfntVersion = '\x00\x01\x00\x00'


def add_hebrew(ttf, src_path, codes=HEBREW):
    t = TTFont(io.BytesIO(ttf))
    if 'CFF ' in t:
        to_truetype(t)
    s = TTFont(src_path)
    scale = cap(t) / cap(s)
    scmap, sgs = s.getBestCmap(), s.getGlyphSet()
    order = t.getGlyphOrder()
    cmap_tables = [c for c in t['cmap'].tables if c.isUnicode()]
    have = t.getBestCmap()
    added = 0
    for code in codes:
        if code in have or code not in scmap:
            continue
        name = f'tirgumim_uni{code:04X}'
        pen = TTGlyphPen(None)
        sgs[scmap[code]].draw(TransformPen(pen, (scale, 0, 0, scale, 0, 0)))
        g = pen.glyph()
        t['glyf'][name] = g
        adv = round(s['hmtx'][scmap[code]][0] * scale)
        g.recalcBounds(t['glyf'])
        t['hmtx'][name] = (adv, getattr(g, 'xMin', 0))
        if 'vmtx' in t:  # CJK fonts (ZenMaru) have vertical metrics: every glyph needs one
            t['vmtx'][name] = (t['head'].unitsPerEm, 0)
        if name not in order:
            order.append(name)
        for c in cmap_tables:
            c.cmap[code] = name
        added += 1
    t['maxp'].numGlyphs = len(t.getGlyphOrder())
    if 'post' in t and t['post'].formatType == 2.0:
        t['post'].extraNames = []
        t['post'].mapping = {}
    out = io.BytesIO()
    t.save(out)
    return out.getvalue(), added
