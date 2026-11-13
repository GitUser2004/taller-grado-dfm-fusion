# 123 Superblock - Make It From Metal, DWG 001 (123-SUPERBLOCK.pdf, not included in this repo).
# Educational use only; see docs/piezas_de_prueba.md.
#   python tools/fusion_bridge.py models/superblock_123.py --timeout 180
# Block 3.000 (X) x 2.000 (Y) x 1.000 (Z), .500 pitch, 1/4-20 tapped THRU holes
# (modelled as the .201 tap drill) with dia .375 counterbores on alternating sides:
#   15X along Z, c-bore depth .75  (front view: c-bore on +Z where col+row is even)
#    5X along Y, c-bore depth 1.75 (top view:   c-bore on +Y for the 2nd and 4th)
#    3X along X, c-bore depth 2.75 (side view:  c-bore on +X for the middle one)
# The three families cross each other, as in the real part.
import importlib
import sys

sys.path.insert(0, r'C:\taller\taller-grado-dfm-fusion\models')
import mlib
importlib.reload(mlib)


def plane_at(root, base, expr, axis, target_in, name):
    """Offset plane that really sits at coordinate `target_in` on `axis` (0=X,1=Y,2=Z)."""
    for e in (expr, '-(' + expr + ')'):
        pl = mlib.offset_plane(root, base, e, name)
        o = pl.geometry.origin
        if abs((o.x, o.y, o.z)[axis] / mlib.IN - target_in) < 1e-6:
            return pl
        pl.deleteMe()
    raise RuntimeError('could not place plane ' + name)


def build(app):
    log = []
    design = mlib.new_design(app, 'superblock_123')
    root = design.rootComponent
    mlib.params(design, [
        ('sb_L', '3.000 in', 'Largo (3.0000 +/- .0002)'), ('sb_W', '2.000 in', 'Ancho (2.0000 +/- .0002)'),
        ('sb_T', '1.000 in', 'Espesor (1.0000 +/- .0002)'), ('sb_pitch', '0.500 in', 'Paso TYP'),
        ('sb_tap', '0.201 in', 'Broca de roscado 1/4-20 (H11), THRU'),
        ('sb_cb', '0.375 in', 'Diametro de caja'),
        ('sb_cbZ', '0.75 in', '15X caja, eje Z'), ('sb_cbY', '1.75 in', '5X caja, eje Y'),
        ('sb_cbX', '2.75 in', '3X caja, eje X'),
    ])
    g = lambda n: mlib.p(design, n)
    L, W, T, pit = g('sb_L'), g('sb_W'), g('sb_T'), g('sb_pitch')
    mlib.box(root, design, 'sb_L', 'sb_W', 'sb_T', 'Bloque')
    cols = [L / 2 + k * pit for k in (-2, -1, 0, 1, 2)]
    rows = [W / 2 + k * pit for k in (-1, 0, 1)]
    zc = T / 2

    def family(name, plane_lo, plane_hi, centers_lo, centers_hi, centers_all, depth):
        if centers_hi:
            sk = mlib.sketch(root, plane_hi, name + ' cajas lado + - centros')
            mlib.circles(sk, centers_hi, 'sb_cb')
            mlib.cut(root, mlib.all_profiles(sk), depth, name + ' cajas lado +', log)
        if centers_lo:
            sk = mlib.sketch(root, plane_lo, name + ' cajas lado - - centros')
            mlib.circles(sk, centers_lo, 'sb_cb')
            mlib.cut(root, mlib.all_profiles(sk), depth, name + ' cajas lado -', log)
        sk = mlib.sketch(root, plane_lo, name + ' broca - centros')
        mlib.circles(sk, centers_all, 'sb_tap')
        mlib.cut(root, mlib.all_profiles(sk), 'all', name + ' broca THRU', log)

    # 15X along Z
    top = plane_at(root, root.xYConstructionPlane, 'sb_T', 2, T, 'Cara +Z')
    cells = [(c, r, (i + j) % 2 == 0) for j, r in enumerate(rows) for i, c in enumerate(cols)]
    family('15X Z', root.xYConstructionPlane, top,
           [(c, r, 0) for c, r, big in cells if not big], [(c, r, T) for c, r, big in cells if big],
           [(c, r, 0) for c, r, big in cells], 'sb_cbZ')

    # 5X along Y
    yhi = plane_at(root, root.xZConstructionPlane, 'sb_W', 1, W, 'Cara +Y')
    family('5X Y', root.xZConstructionPlane, yhi,
           [(c, 0, zc) for i, c in enumerate(cols) if i % 2 == 0], [(c, W, zc) for i, c in enumerate(cols) if i % 2 == 1],
           [(c, 0, zc) for c in cols], 'sb_cbY')

    # 3X along X
    xhi = plane_at(root, root.yZConstructionPlane, 'sb_L', 0, L, 'Cara +X')
    family('3X X', root.yZConstructionPlane, xhi,
           [(0, r, zc) for j, r in enumerate(rows) if j != 1], [(L, rows[1], zc)],
           [(0, r, zc) for r in rows], 'sb_cbX')

    app.activeViewport.fit()
    return mlib.report(design, log)


result = build(app)  # noqa: F821
