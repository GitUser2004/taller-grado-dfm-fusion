# Vee Block - Make It From Metal, DWG 002 (VEE-BLOCKS.pdf, not included in this repo, sheet 2).
# Educational use only; see docs/piezas_de_prueba.md.
#   python tools/fusion_bridge.py models/vee_block.py --timeout 120
# Orientation: cube 1.9375 in; front view = XZ plane, the vees and notches run
# through along Y. Top vee 90 deg (edges .234 from the sides) with a .250 relief
# slot down to .770; bottom vee 90 deg (edges .484 from the sides) with a .250
# relief slot up to .520; side notches .375 high, starting .750 from the bottom.
# ASSUMPTION: notch depth is not dimensioned on the drawing; measured ~.25 in on
# the rendered sheet, so .250 is used (parameter vk_notch_d).
import importlib
import sys

sys.path.insert(0, r'C:\taller\taller-grado-dfm-fusion\models')
import mlib
importlib.reload(mlib)


def build(app):
    log = []
    design = mlib.new_design(app, 'vee_block')
    root = design.rootComponent
    mlib.params(design, [
        ('vk_S', '1.9375 in', 'Arista del cubo (1.9375 +/- .0005)'),
        ('vk_top_edge', '0.234 in', 'V superior: distancia del borde'),
        ('vk_top_depth', '0.770 in', 'V superior: profundidad hasta el fondo del alivio'),
        ('vk_bot_edge', '0.484 in', 'V inferior: distancia del borde'),
        ('vk_bot_depth', '0.520 in', 'V inferior: altura hasta el fondo del alivio'),
        ('vk_relief_w', '0.250 in', 'Ancho de las ranuras de alivio'),
        ('vk_notch_h', '0.375 in', 'Alto de las muescas laterales'),
        ('vk_notch_z', '0.750 in', 'Altura de la muesca desde la base'),
        ('vk_notch_d', '0.250 in', 'SUPUESTO: profundidad de la muesca (no acotada)'),
    ])
    g = lambda n: mlib.p(design, n)
    S, rw = g('vk_S'), g('vk_relief_w')
    mlib.box(root, design, 'vk_S', 'vk_S', 'vk_S', 'Cubo')
    e = 0.1
    xz = root.xZConstructionPlane

    def through_y(name, pts):
        sk = mlib.sketch(root, xz, name + ' - perfil')
        mlib.polygon(sk, pts)
        return mlib.cut(root, mlib.all_profiles(sk), 'vk_S', name, log)

    a1 = S / 2 - g('vk_top_edge')          # half opening of the top vee
    through_y('V superior 90', [(S / 2, 0, S - a1), (S / 2 + a1 + e, 0, S + e), (S / 2 - a1 - e, 0, S + e)])
    through_y('Alivio V superior', [(S / 2 - rw / 2, 0, S - g('vk_top_depth')), (S / 2 + rw / 2, 0, S - g('vk_top_depth')),
                                    (S / 2 + rw / 2, 0, S - a1 + rw / 2 + 0.01), (S / 2 - rw / 2, 0, S - a1 + rw / 2 + 0.01)])
    a2 = S / 2 - g('vk_bot_edge')
    through_y('V inferior 90', [(S / 2, 0, a2), (S / 2 + a2 + e, 0, -e), (S / 2 - a2 - e, 0, -e)])
    through_y('Alivio V inferior', [(S / 2 - rw / 2, 0, g('vk_bot_depth')), (S / 2 + rw / 2, 0, g('vk_bot_depth')),
                                    (S / 2 + rw / 2, 0, a2 - rw / 2 - 0.01), (S / 2 - rw / 2, 0, a2 - rw / 2 - 0.01)])
    z0, z1, nd = g('vk_notch_z'), g('vk_notch_z') + g('vk_notch_h'), g('vk_notch_d')
    through_y('Muesca izquierda', [(-e, 0, z0), (nd, 0, z0), (nd, 0, z1), (-e, 0, z1)])
    through_y('Muesca derecha', [(S - nd, 0, z0), (S + e, 0, z0), (S + e, 0, z1), (S - nd, 0, z1)])

    app.activeViewport.fit()
    # hand check: cube - top vee (a1^2) - bottom vee (a2^2) - 2 notches - relief slots below the vee apexes
    vee = a1 ** 2 + a2 ** 2
    relief = rw * (g('vk_top_depth') - (a1 - rw / 2)) + rw * (g('vk_bot_depth') - (a2 - rw / 2))
    relief -= 2 * (rw / 2) ** 2  # the small triangles above/below each apex were already removed by the vee
    expected = (S ** 2 - vee - relief - 2 * nd * g('vk_notch_h')) * S
    return mlib.report(design, log, round(expected, 5))


result = build(app)  # noqa: F821
