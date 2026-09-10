#!/usr/bin/env python3
"""
Metis Icons Font Generator
Converte os assets de ícones do Metis em uma fonte TrueType (.ttf) monoespaçada,
mapeando os glifos para caracteres na Private Use Area (PUA) do Unicode:
  - U+E900 / U+E00B: Metis Silhouette (Ícone principal)
  - U+E901 / U+E00C: Metis Glyph (Variante de traço)
  - U+E902 / U+E00D: Metis Circle (Variante circular)
"""

import os
import sys
import time
import tempfile
import xml.etree.ElementTree as ET
from PIL import Image

try:
    import vtracer
    from fontTools.ttLib import TTFont, newTable
    from fontTools.ttLib.tables._g_l_y_f import Glyph
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.svgLib.path import parse_path
    from fontTools.ttLib.tables.O_S_2f_2 import Panose
    from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
except ImportError:
    print('Dependências ausentes. Instalando automaticamente...')
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'fonttools', 'pillow', 'vtracer'])
    import vtracer
    from fontTools.ttLib import TTFont, newTable
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.svgLib.path import parse_path
    from fontTools.ttLib.tables.O_S_2f_2 import Panose
    from fontTools.ttLib.tables._c_m_a_p import CmapSubtable

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICONS_DIR = os.path.join(BASE_DIR, 'assets', 'icons')
OUTPUT_FONT_DIR = os.path.expanduser('~/.local/share/fonts')
OUTPUT_TTF = os.path.join(OUTPUT_FONT_DIR, 'MetisIcons.ttf')

ICONS_DEF = [
    {
        'name': 'metis_silhouette',
        'src': os.path.join(ICONS_DIR, 'metis_dark_silhouette.png'),
        'codepoints': [0xE900, 0xE00B],
        'threshold_alpha': 80,
    },
    {
        'name': 'metis_glyph',
        'src': os.path.join(ICONS_DIR, 'metis_glyph_transparent.png'),
        'codepoints': [0xE901, 0xE00C],
        'threshold_alpha': 80,
    },
    {
        'name': 'metis_circle',
        'src': os.path.join(ICONS_DIR, 'metis_circle.png'),
        'codepoints': [0xE902, 0xE00D],
        'threshold_alpha': 80,
    },
]

def build_font():
    os.makedirs(OUTPUT_FONT_DIR, exist_ok=True)
    glyph_set = {}
    cmap_mapping = {}
    hmetrics = {}
    glyph_order = ['.notdef']

    # 1. .notdef glyph
    notdef_pen = TTGlyphPen(glyph_set)
    notdef_pen.moveTo((100, 0))
    notdef_pen.lineTo((100, 700))
    notdef_pen.lineTo((500, 700))
    notdef_pen.lineTo((500, 0))
    notdef_pen.closePath()
    notdef_pen.moveTo((150, 50))
    notdef_pen.lineTo((450, 50))
    notdef_pen.lineTo((450, 650))
    notdef_pen.lineTo((150, 650))
    notdef_pen.closePath()
    glyph_set['.notdef'] = notdef_pen.glyph()
    hmetrics['.notdef'] = (600, 100)

    with tempfile.TemporaryDirectory() as tmpdir:
        for icon in ICONS_DEF:
            gname = icon['name']
            if not os.path.exists(icon['src']):
                print(f'Aviso: Arquivo de imagem não encontrado: {icon["src"]}')
                continue

            glyph_order.append(gname)
            for cp in icon['codepoints']:
                cmap_mapping[cp] = gname

            im = Image.open(icon['src']).convert('RGBA')
            mask = Image.new('L', im.size, 255)
            for x in range(im.width):
                for y in range(im.height):
                    r, g, b, a = im.getpixel((x, y))
                    if a > icon['threshold_alpha'] and not (r > 240 and g > 240 and b > 240):
                        mask.putpixel((x, y), 0)

            mask_file = os.path.join(tmpdir, f'{gname}_mask.png')
            mask.save(mask_file)
            svg_file = os.path.join(tmpdir, f'{gname}.svg')

            vtracer.convert_image_to_svg_py(mask_file, svg_file)

            tree = ET.parse(svg_file)
            root = tree.getroot()
            black_paths = [
                p for p in root.findall('{http://www.w3.org/2000/svg}path')
                if p.get('fill', '').upper() in ('#000000', '#010101', '#020202', 'BLACK')
            ]

            bounds_pen = BoundsPen(None)
            for p in black_paths:
                parse_path(p.get('d'), bounds_pen)

            svg_bounds = bounds_pen.bounds
            svg_w = svg_bounds[2] - svg_bounds[0]
            svg_h = svg_bounds[3] - svg_bounds[1]

            scale = 800.0 / max(svg_w, svg_h)
            svg_center_x = (svg_bounds[0] + svg_bounds[2]) / 2.0
            svg_center_y = (svg_bounds[1] + svg_bounds[3]) / 2.0

            dx = 500.0 - (scale * svg_center_x)
            dy = 350.0 + (scale * svg_center_y)
            t_matrix = (scale, 0, 0, -scale, dx, dy)

            pen = TTGlyphPen(glyph_set)
            t_pen = TransformPen(pen, t_matrix)
            for p in black_paths:
                parse_path(p.get('d'), t_pen)

            glyph_set[gname] = pen.glyph()
            hmetrics[gname] = (1000, int(dx))
            print(f'✓ Glifo "{gname}" gerado com {glyph_set[gname].numberOfContours} contornos.')

    font = TTFont()
    font.setGlyphOrder(glyph_order)

    glyf_table = newTable('glyf')
    glyf_table.glyphs = glyph_set
    font['glyf'] = glyf_table

    head_table = newTable('head')
    head_table.tableVersion = 1.0
    head_table.fontRevision = 1.0
    head_table.checkSumAdjustment = 0
    head_table.magicNumber = 0x5F0F3CF5
    head_table.flags = 0x000B
    head_table.unitsPerEm = 1000
    now = int(time.time() + 2082844800)
    head_table.created = now
    head_table.modified = now
    head_table.xMin = 0
    head_table.yMin = -150
    head_table.xMax = 1000
    head_table.yMax = 850
    head_table.macStyle = 0
    head_table.lowestRecPPEM = 6
    head_table.fontDirectionHint = 2
    head_table.indexToLocFormat = 0
    head_table.glyphDataFormat = 0
    font['head'] = head_table

    hhea_table = newTable('hhea')
    hhea_table.tableVersion = 0x00010000
    hhea_table.ascent = 850
    hhea_table.descent = -150
    hhea_table.lineGap = 0
    hhea_table.advanceWidthMax = 1000
    hhea_table.minLeftSideBearing = 0
    hhea_table.minRightSideBearing = 0
    hhea_table.xMaxExtent = 1000
    hhea_table.caretSlopeRise = 1
    hhea_table.caretSlopeRun = 0
    hhea_table.caretOffset = 0
    hhea_table.reserved0 = 0
    hhea_table.reserved1 = 0
    hhea_table.reserved2 = 0
    hhea_table.reserved3 = 0
    hhea_table.metricDataFormat = 0
    hhea_table.numberOfHMetrics = len(glyph_order)
    font['hhea'] = hhea_table

    maxp_table = newTable('maxp')
    maxp_table.tableVersion = 0x00010000
    maxp_table.numGlyphs = len(glyph_order)
    maxp_table.maxPoints = 0
    maxp_table.maxContours = 0
    maxp_table.maxCompositePoints = 0
    maxp_table.maxCompositeContours = 0
    maxp_table.maxZones = 2
    maxp_table.maxTwilightPoints = 0
    maxp_table.maxStorage = 0
    maxp_table.maxFunctionDefs = 0
    maxp_table.maxInstructionDefs = 0
    maxp_table.maxStackElements = 0
    maxp_table.maxSizeOfInstructions = 0
    maxp_table.maxComponentElements = 0
    maxp_table.maxComponentDepth = 0
    font['maxp'] = maxp_table

    os2_table = newTable('OS/2')
    os2_table.version = 4
    os2_table.xAvgCharWidth = 1000
    os2_table.usWeightClass = 400
    os2_table.usWidthClass = 5
    os2_table.fsType = 0
    os2_table.ySubscriptXSize = 650
    os2_table.ySubscriptYSize = 600
    os2_table.ySubscriptXOffset = 0
    os2_table.ySubscriptYOffset = 75
    os2_table.ySuperscriptXSize = 650
    os2_table.ySuperscriptYSize = 600
    os2_table.ySuperscriptXOffset = 0
    os2_table.ySuperscriptYOffset = 350
    os2_table.yStrikeoutSize = 50
    os2_table.yStrikeoutPosition = 300
    os2_table.sFamilyClass = 0
    os2_table.panose = Panose()
    os2_table.ulUnicodeRange1 = 0
    os2_table.ulUnicodeRange2 = 0
    os2_table.ulUnicodeRange3 = 0
    os2_table.ulUnicodeRange4 = 0
    os2_table.achVendID = b'METI'
    os2_table.fsSelection = 0x0040
    os2_table.usFirstCharIndex = min(cmap_mapping.keys()) if cmap_mapping else 0x20
    os2_table.usLastCharIndex = max(cmap_mapping.keys()) if cmap_mapping else 0x20
    os2_table.sTypoAscender = 850
    os2_table.sTypoDescender = -150
    os2_table.sTypoLineGap = 0
    os2_table.usWinAscent = 850
    os2_table.usWinDescent = 150
    os2_table.ulCodePageRange1 = 1
    os2_table.ulCodePageRange2 = 0
    os2_table.sxHeight = 500
    os2_table.sCapHeight = 700
    os2_table.usDefaultChar = 0
    os2_table.usBreakChar = 32
    os2_table.usMaxContext = 0
    font['OS/2'] = os2_table

    hmtx_table = newTable('hmtx')
    hmtx_table.metrics = hmetrics
    font['hmtx'] = hmtx_table

    cmap_table = newTable('cmap')
    cmap_table.tableVersion = 0

    cmap_subtable_win = CmapSubtable.newSubtable(4)
    cmap_subtable_win.platformID = 3
    cmap_subtable_win.platEncID = 1
    cmap_subtable_win.language = 0
    cmap_subtable_win.cmap = cmap_mapping

    cmap_subtable_mac = CmapSubtable.newSubtable(4)
    cmap_subtable_mac.platformID = 1
    cmap_subtable_mac.platEncID = 0
    cmap_subtable_mac.language = 0
    cmap_subtable_mac.cmap = cmap_mapping

    cmap_table.tables = [cmap_subtable_win, cmap_subtable_mac]
    font['cmap'] = cmap_table

    loca_table = newTable('loca')
    font['loca'] = loca_table

    post_table = newTable('post')
    post_table.formatType = 2.0
    post_table.extraNames = []
    post_table.mapping = {}
    post_table.italicAngle = 0.0
    post_table.underlinePosition = -100
    post_table.underlineThickness = 50
    post_table.isFixedPitch = 1
    post_table.minMemType42 = 0
    post_table.maxMemType42 = 0
    post_table.minMemType1 = 0
    post_table.maxMemType1 = 0
    font['post'] = post_table

    name_table = newTable('name')
    name_entries = [
        (1, 'Metis Icons'),
        (2, 'Regular'),
        (3, 'Metis Icons Regular:1.0'),
        (4, 'Metis Icons Regular'),
        (5, 'Version 1.000'),
        (6, 'MetisIcons-Regular'),
    ]
    for nid, val in name_entries:
        name_table.setName(val, nid, 3, 1, 0x409)
        name_table.setName(val, nid, 1, 0, 0)
    font['name'] = name_table

    font.save(OUTPUT_TTF)
    print(f'✓ Fonte instalada com sucesso em: {OUTPUT_TTF}')

    try:
        import subprocess
        subprocess.run(['fc-cache', '-f', OUTPUT_FONT_DIR], check=False)
        print('✓ Cache do fontconfig atualizado.')
    except Exception:
        pass

if __name__ == '__main__':
    build_font()
