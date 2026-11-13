"""Toolmaker's Vise - Base (Make It From Metal, DWG 002, sheet 2 of 4).

Parametric single-body model for the traceability prototypes (objective 2).
Every drawing dimension is a user parameter (prefix vb_), and every sketch
dimension / feature value references one of them, so each face can be traced
to a feature and from there to a parameter.

Runs two ways:
  * through ClaudeBridge (tools/fusion_bridge.py models/vise_base.py)
  * from Fusion: Shift+S > Scripts > + (add this file) > Run
It always creates a NEW unsaved document; it never touches open designs.

Axes: X = length (6.000), Y = width (2.450, centred on Y=0), Z = height.
Assumptions where the drawing is not explicit are listed in ASSUMPTIONS.
"""

import traceback

import adsk.core
import adsk.fusion

F = adsk.fusion
P = adsk.core.Point3D.create
V = adsk.core.ValueInput.createByString
HORIZ = F.DimensionOrientations.HorizontalDimensionOrientation
VERT = F.DimensionOrientations.VerticalDimensionOrientation
CUT = F.FeatureOperations.CutFeatureOperation
X_AX, Y_AX, Z_AX = (1, 0, 0), (0, 1, 0), (0, 0, 1)

# name, expression, units, comment (drawing reference)
PARAMS = [
    ('vb_L', '6.000 in', 'in', 'Largo total (vista superior 6.000)'),
    ('vb_W', '2.450 in', 'in', 'Ancho total (vista superior 2.450)'),
    ('vb_base_H', '1.250 in', 'in', 'Altura de la base (.875 + .375, vista lateral)'),
    ('vb_up_L', '1.375 in', 'in', 'Largo del montante fijo (1.375)'),
    ('vb_up_H', '1.200 in', 'in', 'Altura del montante sobre la base (1.200)'),
    ('vb_way_W', '2.075 in', 'in', 'Ancho de las guias (2.075 +.000/-.001)'),
    ('vb_way_H', '0.375 in', 'in', 'Altura de las guias / rebaje lateral (.375)'),
    ('vb_ucut_d', '0.125 in', 'in', 'Alivio 1/8 U-cut (detalle A)'),
    ('vb_slot_x', '0.734 in', 'in', 'Inicio de ranura y cajera desde el extremo (.734)'),
    ('vb_slot_L', '4.531 in', 'in', 'Largo total de ranura y cajera (4.531)'),
    ('vb_slot_W', '0.531 in', 'in', 'Ancho de la ranura pasante (.531)'),
    ('vb_cb_W', '1.063 in', 'in', 'Ancho de la cajera inferior (1.063)'),
    ('vb_cb_D', '0.688 in', 'in', 'Profundidad de la cajera inferior (.688, linea oculta)'),
    ('vb_cb_R', '0.250 in', 'in', 'Radio de esquina de la cajera inferior (R.250 TYP)'),
    ('vb_pin_d', '0.375 in', 'in', 'Agujeros pasantes 8X (.375 THRU ALL)'),
    ('vb_pin_x', '1.500 in', 'in', 'Primer agujero desde el extremo (1.500)'),
    ('vb_pin_p', '0.438 in', 'in', 'Paso entre agujeros (.438 TYP)'),
    ('vb_pin_n', '8', '', 'Cantidad de agujeros pasantes (8X)'),
    ('vb_pin_z', '0.625 in', 'in', 'Altura del eje de los agujeros (.625)'),
    ('vb_tap_x', 'vb_up_L - 0.375 in', 'in', 'Roscado 1/4-20: .375 desde la cara del montante'),
    ('vb_tap_z', 'vb_base_H + vb_up_H - 0.375 in', 'in', 'Roscado 1/4-20: .375 bajo la cara superior'),
    ('vb_tap_depth', '0.500 in', 'in', 'Profundidad del roscado (.500, ambos lados)'),
    ('vb_tap_drill', '0.201 in', 'in', 'Broca de roscado 1/4-20 (#7)'),
]

ASSUMPTIONS = [
    'Altura de base 1.250 = .875 + .375 (vista lateral); el montante sube 1.200 sobre ella (total 2.450).',
    'Las guias (2.075 de ancho, .375 de alto) recorren todo el largo, tambien bajo el montante '
    '(linea oculta en la vista superior); el montante sobresale .1875 a cada lado.',
    'El alivio 1/8 U-cut es un cilindro de 1/8 a lo largo de Y, centrado en la arista montante/guias.',
    'La cajera inferior llega a .688 desde abajo (linea oculta de la vista frontal) y R.250 TYP '
    'son sus 4 esquinas verticales.',
    'La ranura de .531 atraviesa toda la base (0 a 1.250), no el montante.',
    'Los agujeros .375 THRU ALL tienen el eje en Y (se ven como circulos en la vista frontal).',
]


# ----------------------------------------------------------------- helpers
def to_sk(sk, xyz):
    return sk.modelToSketchSpace(P(*xyz))


def axis_orient(sk, axis):
    """Horizontal if the model axis maps to sketch X, vertical if to sketch Y."""
    o, a = to_sk(sk, (0, 0, 0)), to_sk(sk, axis)
    return HORIZ if abs(a.x - o.x) >= abs(a.y - o.y) else VERT


def text_pt(p, q, d=0.5):
    g1, g2 = p.geometry, q.geometry
    return P((g1.x + g2.x) / 2 + d, (g1.y + g2.y) / 2 + d, 0)


def dim(sk, p, q, axis, expr):
    """Distance between two sketch points along a model axis, driven by expr."""
    d = sk.sketchDimensions.addDistanceDimension(p, q, axis_orient(sk, axis), text_pt(p, q))
    d.parameter.expression = expr
    return d


def align(sk, p, q, shared_axis):
    """Make p and q share their coordinate along a model axis."""
    if axis_orient(sk, shared_axis) == HORIZ:
        sk.geometricConstraints.addVerticalPoints(p, q)
    else:
        sk.geometricConstraints.addHorizontalPoints(p, q)


def rect(sk, c0, c1):
    """Rectangle from two opposite model-space corners; returns a corner finder."""
    lines = sk.sketchCurves.sketchLines.addTwoPointRectangle(to_sk(sk, c0), to_sk(sk, c1))
    # In this API version the rectangle comes with no constraints at all.
    gc = sk.geometricConstraints
    for ln in lines:
        a, b = ln.startSketchPoint.geometry, ln.endSketchPoint.geometry
        (gc.addHorizontal if abs(a.y - b.y) < abs(a.x - b.x) else gc.addVertical)(ln)
    pts = []
    for ln in lines:
        for sp in (ln.startSketchPoint, ln.endSketchPoint):
            if all(sp.geometry.distanceTo(q.geometry) > 1e-9 for q in pts):
                pts.append(sp)

    def at(xyz):
        t = to_sk(sk, xyz)
        return min(pts, key=lambda sp: sp.geometry.distanceTo(t))
    return at


def origin_point(sk, root):
    """The sketch's own origin: the model origin projected onto the sketch plane.

    Do NOT use sk.include(root.originConstructionPoint) here: the included
    point keeps its 3D position, so on an offset plane it sits off the plane,
    and constraints to it silently drag the profile off-plane. The features
    stay 'healthy' but start at the wrong height (found 2026-11-04)."""
    return sk.originPoint


def healthy(feature):
    return feature.healthState == F.FeatureHealthStates.HealthyFeatureHealthState


# ------------------------------------------------------------------- build
def build(app):
    app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    design = F.Design.cast(app.activeProduct)
    design.designType = F.DesignTypes.ParametricDesignType
    design.fusionUnitsManager.distanceDisplayUnits = F.DistanceUnits.InchDistanceUnits
    # Tag so later scripts can find this design without relying on the active document.
    design.attributes.add('ClaudeBridge', 'model', 'vise_base')
    root = design.rootComponent
    for name, expr, unit, comment in PARAMS:
        design.userParameters.add(name, V(expr), unit, comment)

    g = lambda n: design.userParameters.itemByName(n).value  # internal units (cm)
    L, W, BH, UL = g('vb_L'), g('vb_W'), g('vb_base_H'), g('vb_up_L')
    WW, SX, SL, CW = g('vb_way_W'), g('vb_slot_x'), g('vb_slot_L'), g('vb_cb_W')
    ext = root.features.extrudeFeatures
    holes = root.features.holeFeatures
    planes = root.constructionPlanes
    log = []

    def new_sketch(plane, name):
        sk = root.sketches.add(plane)
        sk.name = name
        return sk, origin_point(sk, root)

    def offset_plane(base, expr, name):
        pi = planes.createInput()
        pi.setByOffset(base, V(expr))
        pl = planes.add(pi)
        pl.name = name
        return pl

    def body_volume():
        return root.bRepBodies.item(0).volume if root.bRepBodies.count else 0.0

    def add_checked(name, attempts, min_removed, adding=False):
        """Try each (label, make_input) until the feature is healthy and removes
        (or, with adding=True, adds) at least min_removed cm^3 of material.
        Fusion does not always extrude toward the side the API direction
        suggests, so the volume change is the check. Returns (feature, change)."""
        for label, make in attempts:
            before = body_volume()
            feat = None
            try:
                feat = make()
                removed = (body_volume() - before) if adding else (before - body_volume())
                if healthy(feat) and removed >= min_removed:
                    feat.name = name
                    log.append('{}: ok ({}), {:.4f} in^3 {}'.format(
                        name, label, removed / 16.387064, 'agregados' if adding else 'removidos'))
                    return feat, removed
                log.append('{}: descartado ({}), sano={}, cambio={:.4f} cm^3'.format(
                    name, label, healthy(feat), removed))
            except Exception as e:
                log.append('{}: fallo ({}): {}'.format(name, label, str(e).splitlines()[0]))
            if feat:
                try:
                    feat.deleteMe()
                except Exception:
                    pass
        raise RuntimeError('No se pudo crear "{}":\n{}'.format(name, '\n'.join(log)))

    def extrude_checked(name, profiles, operation, expr, min_change):
        """One-side distance extrude, trying both directions."""
        def attempt(direction):
            def make():
                ei = ext.createInput(profiles, operation)
                ei.setOneSideExtent(F.DistanceExtentDefinition.create(V(expr)), direction)
                return ext.add(ei)
            return make
        return add_checked(name, [
            ('sentido +', attempt(F.ExtentDirections.PositiveExtentDirection)),
            ('sentido -', attempt(F.ExtentDirections.NegativeExtentDirection)),
        ], min_change, adding=(operation == F.FeatureOperations.JoinFeatureOperation))

    # 1. Base block --------------------------------------------------------
    sk, o = new_sketch(root.xYConstructionPlane, 'Base - perfil')
    at = rect(sk, (0, -W / 2, 0), (L, W / 2, 0))
    c = at((0, -W / 2, 0))
    align(sk, o, c, X_AX)
    dim(sk, o, c, Y_AX, 'vb_W / 2')
    dim(sk, c, at((L, -W / 2, 0)), X_AX, 'vb_L')
    dim(sk, c, at((0, W / 2, 0)), Y_AX, 'vb_W')
    ei = ext.createInput(sk.profiles.item(0), F.FeatureOperations.NewBodyFeatureOperation)
    ei.setDistanceExtent(False, V('vb_base_H'))
    base = ext.add(ei)
    base.name = 'Base'
    base.bodies.item(0).name = 'Toolmaker vise base'

    top = offset_plane(root.xYConstructionPlane, 'vb_base_H', 'Plano superior de la base')

    # 2. Fixed upright -----------------------------------------------------
    sk, o = new_sketch(top, 'Montante - perfil')
    at = rect(sk, (0, -W / 2, BH), (UL, W / 2, BH))
    c = at((0, -W / 2, BH))
    align(sk, o, c, X_AX)
    dim(sk, o, c, Y_AX, 'vb_W / 2')
    dim(sk, c, at((UL, -W / 2, BH)), X_AX, 'vb_up_L')
    dim(sk, c, at((0, W / 2, BH)), Y_AX, 'vb_W')
    extrude_checked('Montante fijo', sk.profiles.item(0), F.FeatureOperations.JoinFeatureOperation,
                    'vb_up_H', 0.95 * UL * W * g('vb_up_H'))

    # 3. Ways: side rebates cut down from the top of the base -------------
    sk, o = new_sketch(top, 'Guias - perfil')
    at = rect(sk, (0, -W / 2, BH), (L, -WW / 2, BH))
    c = at((0, -W / 2, BH))
    align(sk, o, c, X_AX)
    dim(sk, o, c, Y_AX, 'vb_W / 2')
    dim(sk, c, at((L, -W / 2, BH)), X_AX, 'vb_L')
    dim(sk, c, at((0, -WW / 2, BH)), Y_AX, '(vb_W - vb_way_W) / 2')
    at = rect(sk, (0, WW / 2, BH), (L, W / 2, BH))
    c = at((0, WW / 2, BH))
    align(sk, o, c, X_AX)
    dim(sk, o, c, Y_AX, 'vb_way_W / 2')
    dim(sk, c, at((L, WW / 2, BH)), X_AX, 'vb_L')
    dim(sk, c, at((0, W / 2, BH)), Y_AX, '(vb_W - vb_way_W) / 2')
    profiles = adsk.core.ObjectCollection.create()
    for p in sk.profiles:
        profiles.add(p)
    extrude_checked('Guias (rebaje lateral)', profiles, CUT, 'vb_way_H',
                    0.95 * 2 * L * (W - WW) / 2 * g('vb_way_H'))

    # 4. 1/8 U-cut relief along Y at the upright / ways corner -------------
    sk, o = new_sketch(root.xZConstructionPlane, 'Alivio U-cut - perfil')
    cp = sk.sketchPoints.add(to_sk(sk, (UL, 0, BH)))
    dim(sk, o, cp, X_AX, 'vb_up_L')
    dim(sk, o, cp, Z_AX, 'vb_base_H')
    circle = sk.sketchCurves.sketchCircles.addByCenterRadius(cp, g('vb_ucut_d') / 2)
    sk.sketchDimensions.addDiameterDimension(
        circle, P(cp.geometry.x + 0.5, cp.geometry.y + 0.5, 0)).parameter.expression = 'vb_ucut_d'
    ci = ext.createInput(sk.profiles.item(0), CUT)
    ci.setTwoSidesExtent(F.ThroughAllExtentDefinition.create(), F.ThroughAllExtentDefinition.create())
    ext.add(ci).name = 'Alivio U-cut 1/8'

    # 5. Bottom pocket (counterbore of the slot) + R.250 corners -----------
    sk, o = new_sketch(root.xYConstructionPlane, 'Cajera inferior - perfil')
    at = rect(sk, (SX, -CW / 2, 0), (SX + SL, CW / 2, 0))
    c = at((SX, -CW / 2, 0))
    dim(sk, o, c, X_AX, 'vb_slot_x')
    dim(sk, o, c, Y_AX, 'vb_cb_W / 2')
    dim(sk, c, at((SX + SL, -CW / 2, 0)), X_AX, 'vb_slot_L')
    dim(sk, c, at((SX, CW / 2, 0)), Y_AX, 'vb_cb_W')
    pocket, _ = extrude_checked('Cajera inferior', sk.profiles.item(0), CUT, 'vb_cb_D',
                                0.9 * SL * CW * g('vb_cb_D'))

    edges, seen = adsk.core.ObjectCollection.create(), set()
    for face in pocket.sideFaces:
        for e in face.edges:
            a, b = e.startVertex.geometry, e.endVertex.geometry
            if abs(a.x - b.x) < 1e-6 and abs(a.y - b.y) < 1e-6 and e.tempId not in seen:
                seen.add(e.tempId)
                edges.add(e)
    log.append('Cajera inferior: {} aristas verticales para R.250 (se esperan 4)'.format(edges.count))
    fi = root.features.filletFeatures.createInput()
    try:
        fi.edgeSetInputs.addConstantRadiusEdgeSet(edges, V('vb_cb_R'), True)
    except Exception:
        fi.addConstantRadiusEdgeSet(edges, V('vb_cb_R'), True)
    root.features.filletFeatures.add(fi).name = 'Cajera inferior - radios R.250'

    # 6. Through slot .531 with full-radius ends ---------------------------
    sk, o = new_sketch(root.xYConstructionPlane, 'Ranura pasante - perfil')
    p1 = sk.sketchPoints.add(to_sk(sk, (SX, 0, 0)))
    p2 = sk.sketchPoints.add(to_sk(sk, (SX + SL, 0, 0)))
    align(sk, o, p1, Y_AX)
    align(sk, o, p2, Y_AX)
    dim(sk, o, p1, X_AX, 'vb_slot_x')
    dim(sk, p1, p2, X_AX, 'vb_slot_L')
    slot_curves = sk.addOverallSlot(p1, p2, V('vb_slot_W'), True)
    log.append('Ranura: addOverallSlot devolvio {} objetos'.format(len(slot_curves)))
    extrude_checked('Ranura pasante', sk.profiles.item(0), CUT, 'vb_base_H',
                    0.5 * SL * g('vb_slot_W') * (BH - g('vb_cb_D')))

    # 7. 8X .375 through holes along Y (one hole + rectangular pattern) ---
    side_a = offset_plane(root.xZConstructionPlane, 'vb_W / 2', 'Plano cara lateral A')
    side_b = offset_plane(root.xZConstructionPlane, '-vb_W / 2', 'Plano cara lateral B')
    ya, yb = side_a.geometry.origin.y, side_b.geometry.origin.y
    log.append('Plano A en y={:.4f} in, plano B en y={:.4f} in'.format(ya / 2.54, yb / 2.54))

    sk, o = new_sketch(side_a, 'Agujeros pasantes - centro')
    pin_pt = sk.sketchPoints.add(to_sk(sk, (g('vb_pin_x'), ya, g('vb_pin_z'))))
    dim(sk, o, pin_pt, X_AX, 'vb_pin_x')
    dim(sk, o, pin_pt, Z_AX, 'vb_pin_z')

    def pin_input(direction):
        def make():
            hi = holes.createSimpleInput(V('vb_pin_d'))
            hi.setPositionBySketchPoint(pin_pt)
            hi.setAllExtent(direction)
            return holes.add(hi)
        return make
    pin, pin_removed = add_checked('Agujero pasante .375', [
        ('todo, sentido negativo', pin_input(F.ExtentDirections.NegativeExtentDirection)),
        ('todo, sentido positivo', pin_input(F.ExtentDirections.PositiveExtentDirection)),
    ], min_removed=1e-4)

    def pattern_input(spacing):
        def make():
            ents = adsk.core.ObjectCollection.create()
            ents.add(pin)
            pi = root.features.rectangularPatternFeatures.createInput(
                ents, root.xConstructionAxis, V('vb_pin_n'), V(spacing),
                F.PatternDistanceType.SpacingPatternDistanceType)
            return root.features.rectangularPatternFeatures.add(pi)
        return make
    # All 7 copies cross the same pocket and slot, so each removes the same
    # volume as the first hole; a pattern going the wrong way removes less.
    copies = int(round(g('vb_pin_n'))) - 1
    add_checked('Agujeros pasantes 8X (patron)', [
        ('paso +X', pattern_input('vb_pin_p')),
        ('paso -X', pattern_input('-vb_pin_p')),
    ], min_removed=0.95 * copies * pin_removed)

    # 8. 1/4-20 tapped holes, depth .500, both sides ------------------------
    def tap_input(sk_point, default_dir, threaded):
        def make():
            hi = holes.createSimpleInput(V('vb_tap_drill'))
            if threaded:
                ti = F.ThreadInfo.create(False, True, 'ANSI Unified Screw Threads', '1/4-20 UNC', '2B', True)
                if not ti or not hi.setToTappedHole(ti):
                    raise RuntimeError('ThreadInfo 1/4-20 UNC 2B no aceptado')
            hi.setPositionBySketchPoint(sk_point)
            hi.setDistanceExtent(V('vb_tap_depth'))
            hi.isDefaultDirection = default_dir
            return holes.add(hi)
        return make

    for side, plane, y in (('A', side_a, ya), ('B', side_b, yb)):
        sk, o = new_sketch(plane, 'Roscado 1/4-20 lado {} - centro'.format(side))
        tp = sk.sketchPoints.add(to_sk(sk, (g('vb_tap_x'), y, g('vb_tap_z'))))  # noqa
        dim(sk, o, tp, X_AX, 'vb_tap_x')
        dim(sk, o, tp, Z_AX, 'vb_tap_z')
        add_checked('Roscado 1/4-20 lado {}'.format(side), [
            ('roscado, sentido natural', tap_input(tp, True, True)),
            ('roscado, sentido invertido', tap_input(tp, False, True)),
            ('simple Ø.201, sentido natural', tap_input(tp, True, False)),
            ('simple Ø.201, sentido invertido', tap_input(tp, False, False)),
        ], min_removed=1e-5)

    app.activeViewport.fit()
    return report(design, log)


# ------------------------------------------------------------------ report
def report(design, log):
    root = design.rootComponent
    to_in = lambda cm: round(cm / 2.54, 4)
    tl = design.timeline
    features = []
    for i in range(tl.count):
        item = tl.item(i)
        ent = item.entity
        features.append({
            'index': i,
            'name': item.name,
            'type': ent.objectType.split('::')[-1] if ent else None,
            'healthy': item.healthState == F.FeatureHealthStates.HealthyFeatureHealthState,
            'message': item.errorOrWarningMessage or None,
            'faces': len(ent.faces) if ent and hasattr(ent, 'faces') else None,
        })
    params = [{'name': p.name, 'expression': p.expression,
               'value_in': to_in(p.value) if p.unit == 'in' else p.value}
              for p in design.userParameters]
    unfixed = [s.name for s in root.sketches if not s.isFullyConstrained]
    bodies = []
    for b in root.bRepBodies:
        bb = b.boundingBox
        bodies.append({
            'name': b.name, 'is_solid': b.isSolid, 'faces': b.faces.count,
            'edges': b.edges.count, 'volume_in3': round(b.volume / 16.387064, 5),
            'bbox_min_in': [to_in(bb.minPoint.x), to_in(bb.minPoint.y), to_in(bb.minPoint.z)],
            'bbox_max_in': [to_in(bb.maxPoint.x), to_in(bb.maxPoint.y), to_in(bb.maxPoint.z)],
        })
    return {'bodies': bodies, 'features': features, 'parameters': params,
            'sketches_not_fully_constrained': unfixed, 'log': log,
            'assumptions': ASSUMPTIONS}


# ------------------------------------------------------------- entry points
if __name__ == '__claude_bridge__':
    result = build(app)  # noqa: F821  (app is injected by ClaudeBridge)


def run(context):
    ui = None
    try:
        app_ = adsk.core.Application.get()
        ui = app_.userInterface
        out = build(app_)
        bad = [f['name'] for f in out['features'] if not f['healthy']]
        ui.messageBox('Base del Toolmaker\'s Vise creada.\nCuerpos: {}\nOperaciones con error: {}'.format(
            len(out['bodies']), ', '.join(bad) or 'ninguna'))
    except Exception:
        if ui:
            ui.messageBox('Fallo:\n{}'.format(traceback.format_exc()))
