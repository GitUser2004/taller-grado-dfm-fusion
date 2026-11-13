# Edge Clamp body - Make It From Metal, DWG 002 (EDGE-CLAMP.pdf, not included in this repo, sheet 2).
# Educational use only; see docs/piezas_de_prueba.md. CONTROL PART: with the
# default thresholds it should produce no findings.
#   python tools/fusion_bridge.py models/edge_clamp.py --timeout 120
# Block 4.000 (X) x 1.250 (Y) x 1.000 (Z). Through slot .531 wide with a .800 wide
# counterbore slot, both with end centres at x = 1.625 and 3.375 (1.750 apart,
# .625 from the right edge); 1/2-13 UNC THRU at x = .625, modelled as the 27/64 tap drill.
# ASSUMPTION: the counterbore depth is not dimensioned; the side view measures
# ~.61 in, so .625 is used (parameter ec_cb_d).
import importlib
import sys

sys.path.insert(0, r'C:\taller\taller-grado-dfm-fusion\models')
import mlib
importlib.reload(mlib)


def build(app):
    log = []
    design = mlib.new_design(app, 'edge_clamp')
    root = design.rootComponent
    mlib.params(design, [
        ('ec_L', '4.000 in', 'Largo'), ('ec_W', '1.250 in', 'Ancho'), ('ec_T', '1.000 in', 'Espesor (1.0000 +/- .0005)'),
        ('ec_slot_w', '0.531 in', 'Ranura pasante'), ('ec_cb_w', '0.800 in', 'Caja de la ranura'),
        ('ec_cb_d', '0.625 in', 'SUPUESTO: profundidad de la caja (no acotada)'),
        ('ec_c1', '1.625 in', 'Centro izquierdo de la ranura'), ('ec_c2', '3.375 in', 'Centro derecho (.625 del borde)'),
        ('ec_hole_x', '0.625 in', 'Posicion del 1/2-13'), ('ec_tap', '0.4219 in', 'Broca 27/64 para 1/2-13 UNC'),
    ])
    g = lambda n: mlib.p(design, n)
    L, W, T = g('ec_L'), g('ec_W'), g('ec_T')
    mlib.box(root, design, 'ec_L', 'ec_W', 'ec_T', 'Cuerpo')
    top = mlib.plane_at(root, root.xYConstructionPlane, 'ec_T', 2, T, 'Cara superior')

    sk = mlib.sketch(root, top, 'Caja de la ranura - perfil')
    mlib.slot(sk, (g('ec_c1'), W / 2, T), (g('ec_c2'), W / 2, T), 'ec_cb_w')
    mlib.cut(root, mlib.all_profiles(sk), 'ec_cb_d', 'Caja de la ranura .800', log)

    sk = mlib.sketch(root, root.xYConstructionPlane, 'Ranura pasante - perfil')
    mlib.slot(sk, (g('ec_c1'), W / 2, 0), (g('ec_c2'), W / 2, 0), 'ec_slot_w')
    mlib.cut(root, mlib.all_profiles(sk), 'all', 'Ranura pasante .531', log)

    sk = mlib.sketch(root, root.xYConstructionPlane, 'Rosca 1/2-13 - centro')
    mlib.circles(sk, [(g('ec_hole_x'), W / 2, 0)], 'ec_tap')
    mlib.cut(root, mlib.all_profiles(sk), 'all', 'Rosca 1/2-13 THRU', log)

    app.activeViewport.fit()
    import math
    cbw, sw, span = g('ec_cb_w'), g('ec_slot_w'), g('ec_c2') - g('ec_c1')
    stadium = lambda w: w * span + math.pi * (w / 2) ** 2
    expected = L * W * T - stadium(cbw) * g('ec_cb_d') - stadium(sw) * (T - g('ec_cb_d')) \
        - math.pi * (g('ec_tap') / 2) ** 2 * T
    return mlib.report(design, log, round(expected, 5))


result = build(app)  # noqa: F821
