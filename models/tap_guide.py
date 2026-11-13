# Tap Guide Block - Make It From Metal, DWG 001 (TAP-GUIDE.pdf, not included in this repo).
# Educational use only; see docs/piezas_de_prueba.md.
#   python tools/fusion_bridge.py models/tap_guide.py --timeout 120
# Orientation: block 4.000 (X) x .875 (Y) x .875 (Z); the 90 deg vee runs along X on
# the top face (+Z); the 8 holes go along Z from the bottom face into the vee.
import importlib
import math
import sys

sys.path.insert(0, r'C:\taller\taller-grado-dfm-fusion\models')
import mlib
importlib.reload(mlib)

HOLES = [  # (x position, diameter) from the drawing, inches
    (0.250, 0.136), (0.581, 0.164), (0.940, 0.190), (1.342, 0.250),
    (1.805, 0.313), (2.330, 0.375), (2.918, 0.438), (3.568, 0.500)]


def build(app):
    log = []
    design = mlib.new_design(app, 'tap_guide')
    root = design.rootComponent
    rows = [('tg_L', '4.000 in', 'Largo (DWG 001)'), ('tg_W', '0.875 in', 'Ancho'),
            ('tg_H', '0.875 in', 'Alto'), ('tg_v_open', '0.625 in', 'Abertura de la V'),
            ('tg_v_angle', '90 deg', 'Angulo de la V')]
    rows += [('tg_d{}'.format(i + 1), '{:.3f} in'.format(d), 'Agujero {} THRU'.format(i + 1)) for i, (x, d) in enumerate(HOLES)]
    mlib.params(design, rows)
    L, W, H, vo = (mlib.p(design, n) for n in ('tg_L', 'tg_W', 'tg_H', 'tg_v_open'))

    mlib.box(root, design, 'tg_L', 'tg_W', 'tg_H', 'Bloque')

    # Vee: triangle in the YZ plane, cut along X over the whole length
    depth = (vo / 2) / math.tan(math.radians(45))
    e = 0.1  # extend above the top face so the cut is not coplanar
    sk = mlib.sketch(root, root.yZConstructionPlane, 'V 90 - perfil')
    mlib.polygon(sk, [(0, W / 2, H - depth), (0, W / 2 + depth + e, H + e), (0, W / 2 - depth - e, H + e)])
    mlib.cut(root, mlib.all_profiles(sk), 'tg_L', 'V 90', log)

    # Holes: one sketch per hole so each is its own feature (traceable to its diameter)
    for i, (x, d) in enumerate(HOLES):
        sk = mlib.sketch(root, root.xYConstructionPlane, 'Agujero {} - centro'.format(i + 1))
        mlib.circles(sk, [(x, W / 2, 0)], 'tg_d{}'.format(i + 1))
        mlib.cut(root, mlib.all_profiles(sk), 'all', 'Agujero {} D{:.3f} THRU'.format(i + 1, d), log)

    app.activeViewport.fit()
    return mlib.report(design, log)


result = build(app)  # noqa: F821
