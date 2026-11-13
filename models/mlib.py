"""Small modelling helpers for the test-part scripts in models/ (run inside Fusion).

Every helper takes model coordinates in INCHES and converts them; sketch points
are placed with sketch.modelToSketchSpace so the plane orientation never matters.
Cuts try both directions and keep the one that actually removes material
(the healthy-but-wrong extrusion trap noted in models/README.md).
"""

import adsk.core
import adsk.fusion

C = adsk.core
F = adsk.fusion
V = C.ValueInput.createByString
IN = 2.54  # cm per inch


def new_design(app, tag):
    app.documents.add(C.DocumentTypes.FusionDesignDocumentType)
    design = F.Design.cast(app.activeProduct)
    design.designType = F.DesignTypes.ParametricDesignType
    design.fusionUnitsManager.distanceDisplayUnits = F.DistanceUnits.InchDistanceUnits
    design.attributes.add('ClaudeBridge', 'model', tag)
    return design


def params(design, rows):
    for name, expr, comment in rows:
        unit = '' if expr.strip().replace('.', '').isdigit() else ('deg' if 'deg' in expr else 'in')
        design.userParameters.add(name, V(expr), unit, comment)


def p(design, name):
    """Parameter value in inches."""
    return design.userParameters.itemByName(name).value / IN


def pt(sk, x, y, z):
    return sk.modelToSketchSpace(C.Point3D.create(x * IN, y * IN, z * IN))


def offset_plane(root, base, expr, name):
    pi = root.constructionPlanes.createInput()
    pi.setByOffset(base, V(expr))
    pl = root.constructionPlanes.add(pi)
    pl.name = name
    return pl


def plane_at(root, base, expr, axis, target_in, name):
    """Offset plane that really sits at coordinate `target_in` on `axis` (0=X,1=Y,2=Z):
    the origin planes' normals do not all point the way one would guess."""
    for e in (expr, '-(' + expr + ')'):
        pl = offset_plane(root, base, e, name)
        o = pl.geometry.origin
        if abs((o.x, o.y, o.z)[axis] / IN - target_in) < 1e-6:
            return pl
        pl.deleteMe()
    raise RuntimeError('could not place plane ' + name)


def slot(sk, a3d, b3d, width_param):
    """Center-to-center slot; its width dimension is linked to `width_param`."""
    sk.addCenterToCenterSlot(pt(sk, *a3d), pt(sk, *b3d), V(width_param), True)
    for d in sk.sketchDimensions:
        if d.parameter.expression != width_param and abs(d.parameter.value - sk.parentComponent.parentDesign.userParameters.itemByName(width_param).value) < 1e-9:
            d.parameter.expression = width_param
    return sk


def sketch(root, plane, name):
    sk = root.sketches.add(plane)
    sk.name = name
    return sk


def polygon(sk, pts3d):
    lines = sk.sketchCurves.sketchLines
    pts = [pt(sk, *q) for q in pts3d]
    first = prev = None
    for i in range(len(pts)):
        a = prev.endSketchPoint if prev else pts[i]
        b = first.startSketchPoint if (i == len(pts) - 1 and first) else pts[(i + 1) % len(pts)]
        ln = lines.addByTwoPoints(a, b)
        first = first or ln
        prev = ln
    for sp in sk.sketchPoints:
        sp.isFixed = True
    return sk


def circles(sk, centers3d, dia_param):
    for c in centers3d:
        circ = sk.sketchCurves.sketchCircles.addByCenterRadius(pt(sk, *c), 0.1)
        circ.centerSketchPoint.isFixed = True
        txt = pt(sk, c[0] + 0.3, c[1] + 0.3, c[2])
        sk.sketchDimensions.addDiameterDimension(circ, txt).parameter.expression = dia_param
    return sk


def all_profiles(sk):
    col = C.ObjectCollection.create()
    for prof in sk.profiles:
        col.add(prof)
    return col


def volume(root):
    return sum(b.volume for b in root.bRepBodies)


def box(root, design, L, W, H, name='Bloque'):
    sk = sketch(root, root.xYConstructionPlane, name + ' - perfil')
    ln = sk.sketchCurves.sketchLines.addTwoPointRectangle(pt(sk, 0, 0, 0), pt(sk, p(design, L), p(design, W), 0))
    gc = sk.geometricConstraints
    gc.addCoincident(ln.item(0).startSketchPoint, sk.originPoint)
    for i in range(4):
        a, b = ln.item(i).startSketchPoint.geometry, ln.item(i).endSketchPoint.geometry
        (gc.addHorizontal if abs(a.y - b.y) < 1e-9 else gc.addVertical)(ln.item(i))
    horiz = [ln.item(i) for i in range(4) if abs(ln.item(i).startSketchPoint.geometry.y - ln.item(i).endSketchPoint.geometry.y) < 1e-9]
    vert = [ln.item(i) for i in range(4) if ln.item(i) not in horiz]
    d = sk.sketchDimensions
    D = F.DimensionOrientations
    d.addDistanceDimension(horiz[0].startSketchPoint, horiz[0].endSketchPoint,
                           D.HorizontalDimensionOrientation, pt(sk, p(design, L) / 2, -0.4, 0)).parameter.expression = L
    d.addDistanceDimension(vert[0].startSketchPoint, vert[0].endSketchPoint,
                           D.VerticalDimensionOrientation, pt(sk, -0.4, p(design, W) / 2, 0)).parameter.expression = W
    ei = root.features.extrudeFeatures.createInput(sk.profiles.item(0), F.FeatureOperations.NewBodyFeatureOperation)
    ei.setDistanceExtent(False, V(H))
    feat = root.features.extrudeFeatures.add(ei)
    feat.name = name
    return feat


def cut(root, profiles, extent, name, log, min_removed_in3=1e-6):
    """extent: a ValueInput expression string, or 'all' for through-all."""
    ext = root.features.extrudeFeatures
    last_err = None
    for direction in (F.ExtentDirections.NegativeExtentDirection, F.ExtentDirections.PositiveExtentDirection):
        before = volume(root)
        try:
            ci = ext.createInput(profiles, F.FeatureOperations.CutFeatureOperation)
            definition = (F.ThroughAllExtentDefinition.create() if extent == 'all'
                          else F.DistanceExtentDefinition.create(V(extent)))
            ci.setOneSideExtent(definition, direction)
            feat = ext.add(ci)
        except Exception as ex:
            last_err = str(ex)[:120]
            continue
        removed = (before - volume(root)) / IN ** 3
        if removed > min_removed_in3 and feat.timelineObject.healthState == 0:
            feat.name = name
            log.append('{}: ok ({}), {:.4f} in^3 removed'.format(name, 'neg' if direction == 1 else 'pos', removed))
            return feat
        feat.deleteMe()
        last_err = 'removed {:.4f} in^3, health {}'.format(removed, feat.timelineObject.healthState if feat.isValid else '?')
    raise RuntimeError('{}: no direction removed material ({})'.format(name, last_err))


def report(design, log, expected_volume_in3=None):
    root = design.rootComponent
    bodies = [{'name': b.name, 'solid': b.isSolid, 'faces': b.faces.count, 'edges': b.edges.count,
               'volume_in3': round(b.volume / IN ** 3, 5)} for b in root.bRepBodies]
    feats = [{'name': t.name, 'health': t.healthState} for t in design.timeline]
    return {'bodies': bodies, 'expected_volume_in3': expected_volume_in3,
            'unhealthy': [f for f in feats if f['health'] != 0],
            'timeline_items': len(feats), 'user_parameters': design.userParameters.count, 'log': log}
