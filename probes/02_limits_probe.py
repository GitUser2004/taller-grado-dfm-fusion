# Probe 02 - API limitations and the techniques that can work around them.
# Runs inside Fusion through ClaudeBridge. Creates a NEW unsaved document.
#
# Test part (one body, 3-axis milling from +Z), each feature carries a defect:
#   Pocket1      40x20x25 mm, fillet corners r=1 mm   -> deep cavity, small internal radius
#   Pocket2      sharp internal corners, 1.5 mm wall  -> radius 0 + thin wall, NO sketch dims
#   Pocket3      corners from sketch fillets r=2 mm   -> radius that is NOT a parameter
#   Hole         vertical, d6 x 20                    -> ok from +Z
#   SideHole     horizontal from the X- face, d5      -> undercut: not reachable from +Z
#
# Techniques probed (T1..T11), each answers a limitation found in probe 01.
import json
import math
import os
import sys
import time
import traceback

R = {'errors': {}, 'timing_ms': {}}
V = adsk.core.ValueInput.createByString
P = adsk.core.Point3D.create
Vec = adsk.core.Vector3D.create
F = adsk.fusion
C = adsk.core
OUT = os.path.join(os.path.expanduser('~'), 'Documents', 'ClaudeBridge', 'artifacts')
os.makedirs(OUT, exist_ok=True)
Z = Vec(0, 0, 1)
FACE = F.BRepEntityTypes.BRepFaceEntityType


class section:
    def __init__(self, key):
        self.key = key
    def __enter__(self):
        self.t = time.perf_counter()
    def __exit__(self, *exc):
        R['timing_ms'][self.key] = round((time.perf_counter() - self.t) * 1000, 1)
        if exc[0]:
            R['errors'][self.key] = ''.join(traceback.format_exception(*exc))[-1500:]
        return True


def safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def short(obj):
    return obj.objectType.split('::')[-1] if obj else None


mm = lambda cm: round(cm * 10, 4)


def body():
    return root.bRepBodies.item(0)


# ---------------------------------------------------------------- T1 helper
# Technique T1: tag faces with attributes after every feature. 'origin' = first
# feature that produced the face; 'modified_by' = later features that changed its area.
def tag(feature_name):
    for f in body().faces:
        a = f.attributes
        if a.itemByName('dfm', 'origin') is None:
            a.add('dfm', 'origin', feature_name)
            a.add('dfm', 'area', repr(f.area))
            a.add('dfm', 'modified_by', '')
        else:
            old = float(a.itemByName('dfm', 'area').value)
            if abs(old - f.area) > 1e-9:
                mb = a.itemByName('dfm', 'modified_by')
                mb.value = (mb.value + ',' + feature_name).strip(',')
                a.itemByName('dfm', 'area').value = repr(f.area)


def top_face():
    return max((f for f in body().faces if short(f.geometry) == 'Plane'),
               key=lambda f: (round(f.centroid.z, 6), f.area))


# ---------------------------------------------------------------- build part
with section('build_part'):
    app.documents.add(C.DocumentTypes.FusionDesignDocumentType)
    design = F.Design.cast(app.activeProduct)
    design.designType = F.DesignTypes.ParametricDesignType
    root = design.rootComponent
    for n, v in [('blk_L', '100 mm'), ('blk_W', '60 mm'), ('blk_H', '30 mm'),
                 ('p1_L', '40 mm'), ('p1_W', '20 mm'), ('p1_D', '25 mm'), ('p1_r', '1 mm'),
                 ('p2_D', '10 mm'), ('p3_D', '8 mm'), ('hole_d', '6 mm'),
                 ('hole_depth', '20 mm'), ('side_d', '5 mm'), ('side_depth', '30 mm')]:
        design.userParameters.add(n, V(v), 'mm', '')
    ext = root.features.extrudeFeatures
    dims = F.DimensionOrientations

    sk = root.sketches.add(root.xYConstructionPlane); sk.name = 'Block sketch'
    ln = sk.sketchCurves.sketchLines.addTwoPointRectangle(P(0, 0, 0), P(10, 6, 0))
    sk.geometricConstraints.addCoincident(ln.item(0).startSketchPoint, sk.originPoint)
    sk.sketchDimensions.addDistanceDimension(ln.item(0).startSketchPoint, ln.item(0).endSketchPoint,
        dims.HorizontalDimensionOrientation, P(5, -1, 0)).parameter.expression = 'blk_L'
    sk.sketchDimensions.addDistanceDimension(ln.item(1).startSketchPoint, ln.item(1).endSketchPoint,
        dims.VerticalDimensionOrientation, P(11, 3, 0)).parameter.expression = 'blk_W'
    ei = ext.createInput(sk.profiles.item(0), F.FeatureOperations.NewBodyFeatureOperation)
    ei.setDistanceExtent(False, V('blk_H'))
    block = ext.add(ei); block.name = 'Block'
    tag('Block')

    pi = root.constructionPlanes.createInput()
    pi.setByOffset(root.xYConstructionPlane, V('blk_H'))
    top_plane = root.constructionPlanes.add(pi); top_plane.name = 'Top plane'

    def cut(sketch, depth_expr, name, profile=None):
        prof = profile or sketch.profiles.item(0)
        ci = ext.createInput(prof, F.FeatureOperations.CutFeatureOperation)
        ci.setOneSideExtent(F.DistanceExtentDefinition.create(V(depth_expr)),
                            F.ExtentDirections.NegativeExtentDirection)
        feat = ext.add(ci); feat.name = name
        tag(name)
        return feat

    # Pocket1 - dimensioned, corners filleted later
    s1 = root.sketches.add(top_plane); s1.name = 'Pocket1 sketch'
    r1 = s1.sketchCurves.sketchLines.addCenterPointRectangle(P(3, 3, 0), P(5, 4, 0))
    s1.sketchDimensions.addDistanceDimension(r1.item(0).startSketchPoint, r1.item(0).endSketchPoint,
        dims.HorizontalDimensionOrientation, P(3, 4.5, 0)).parameter.expression = 'p1_L'
    s1.sketchDimensions.addDistanceDimension(r1.item(1).startSketchPoint, r1.item(1).endSketchPoint,
        dims.VerticalDimensionOrientation, P(5.5, 3, 0)).parameter.expression = 'p1_W'
    pocket1 = cut(s1, 'p1_D', 'Pocket1')
    edges = C.ObjectCollection.create(); seen = set()
    for face in pocket1.sideFaces:
        for e in face.edges:
            a, b = e.startVertex.geometry, e.endVertex.geometry
            if abs(a.x - b.x) < 1e-6 and abs(a.y - b.y) < 1e-6 and e.tempId not in seen:
                seen.add(e.tempId); edges.add(e)
    fi = root.features.filletFeatures.createInput()
    fi.edgeSetInputs.addConstantRadiusEdgeSet(edges, V('p1_r'), True)
    fillet = root.features.filletFeatures.add(fi); fillet.name = 'Pocket1 corners'
    tag('Pocket1 corners')

    # Pocket2 - sharp corners, 1.5 mm wall to the X+ side, no sketch dimensions
    s2 = root.sketches.add(top_plane); s2.name = 'Pocket2 sketch'
    s2.sketchCurves.sketchLines.addTwoPointRectangle(P(7.5, 2, 0), P(9.85, 4, 0))
    pocket2 = cut(s2, 'p2_D', 'Pocket2')

    # Pocket3 - corner radii drawn as sketch fillets (no radius parameter)
    s3 = root.sketches.add(top_plane); s3.name = 'Pocket3 sketch'
    r3 = s3.sketchCurves.sketchLines.addTwoPointRectangle(P(1, 4.6, 0), P(5, 5.6, 0))
    lines3 = [r3.item(i) for i in range(4)]
    for i in range(4):
        l1, l2 = lines3[i], lines3[(i + 1) % 4]
        s3.sketchCurves.sketchArcs.addFillet(l1, l1.endSketchPoint.geometry,
                                             l2, l2.startSketchPoint.geometry, 0.2)
    prof3 = min(s3.profiles, key=lambda p: p.areaProperties().area)
    pocket3 = cut(s3, 'p3_D', 'Pocket3', prof3)

    # Vertical hole
    holes = root.features.holeFeatures
    hi = holes.createSimpleInput(V('hole_d'))
    hi.setPositionByPoint(top_face(), P(7, 0.8, top_face().centroid.z))
    hi.setDistanceExtent(V('hole_depth'))
    hole = holes.add(hi); hole.name = 'Hole'
    tag('Hole')

    # Horizontal hole from the X- face (undercut for a +Z setup)
    xface = min((f for f in body().faces if short(f.geometry) == 'Plane'),
                key=lambda f: f.centroid.x)
    hs = holes.createSimpleInput(V('side_d'))
    hs.setPositionByPoint(xface, P(0, 1.0, 1.5))
    hs.setDistanceExtent(V('side_depth'))
    side = holes.add(hs); side.name = 'SideHole'
    tag('SideHole')
    app.activeViewport.fit()

if 'build_part' in R['errors']:
    raise RuntimeError('build failed:\n' + R['errors']['build_part'])

FEATURES = [design.timeline.item(i) for i in range(design.timeline.count)]


def feature_owner_map():
    owner = {}
    for item in design.timeline:
        for f in safe(lambda: list(item.entity.faces), []) or []:
            owner.setdefault(f.tempId, item.name)
    return owner


OWNER = feature_owner_map()


def describe(f):
    g = f.geometry
    d = {'tempId': f.tempId, 'type': short(g), 'owner': OWNER.get(f.tempId),
         'area_mm2': round(f.area * 100, 2),
         'centroid_mm': [mm(f.centroid.x), mm(f.centroid.y), mm(f.centroid.z)]}
    if d['type'] == 'Cylinder':
        d['radius_mm'] = mm(g.radius)
    return d


# -------------------------------------------- T1. attributes as provenance tags
with section('T1_attribute_provenance'):
    rows = []
    for f in body().faces:
        a = f.attributes
        rows.append({'tempId': f.tempId, 'owner_api': OWNER.get(f.tempId),
                     'origin_attr': safe(lambda: a.itemByName('dfm', 'origin').value),
                     'modified_by_attr': safe(lambda: a.itemByName('dfm', 'modified_by').value)})
    R['T1'] = {'faces': rows,
               'agree_with_feature_faces': sum(1 for r in rows if r['origin_attr'] == r['owner_api']),
               'total': len(rows),
               'faces_with_modified_by': [r for r in rows if r['modified_by_attr']]}

with section('T1_attributes_survive_recompute'):
    design.userParameters.itemByName('p1_r').expression = '2 mm'
    design.userParameters.itemByName('p1_D').expression = '20 mm'
    adsk.doEvents()
    tagged = sum(1 for f in body().faces if f.attributes.itemByName('dfm', 'origin'))
    R['T1']['after_recompute'] = {'faces': body().faces.count, 'still_tagged': tagged}
    design.userParameters.itemByName('p1_r').expression = '1 mm'
    design.userParameters.itemByName('p1_D').expression = '25 mm'
    adsk.doEvents()
    R['T1']['after_revert'] = {'faces': body().faces.count, 'still_tagged': sum(
        1 for f in body().faces if f.attributes.itemByName('dfm', 'origin'))}

# --------------------------------- T2. timeline replay diff (who modified a face)
with section('T2_rollback_diff'):
    tl = design.timeline
    per_feature = []
    touched = {}  # token at that state -> feature name that modified/split it
    prev = None
    for i in range(tl.count):
        tl.item(i).rollTo(False)
        if root.bRepBodies.count == 0:
            prev = None
            continue
        b = root.bRepBodies.item(0)
        cur = {f.entityToken: f.area for f in b.faces}
        if prev is not None:
            stats = {'feature': tl.item(i).name, 'deleted': 0, 'split': 0, 'modified': 0,
                     'unchanged': 0, 'new': 0}
            matched = set()
            for tok, area in prev.items():
                found = design.findEntityByToken(tok)
                if not found:
                    stats['deleted'] += 1
                    continue
                matched.update(x.tempId for x in found)
                if len(found) > 1:
                    stats['split'] += 1
                elif abs(found[0].area - area) > 1e-9:
                    stats['modified'] += 1
                else:
                    stats['unchanged'] += 1
                    continue
                for x in found:
                    touched.setdefault(x.entityToken, []).append(tl.item(i).name)
            stats['new'] = sum(1 for f in b.faces if f.tempId not in matched)
            per_feature.append(stats)
        prev = cur
    tl.moveToEnd()
    final = {}
    for tok, names in touched.items():
        for x in design.findEntityByToken(tok):
            final.setdefault(x.tempId, set()).update(names)
    R['T2'] = {'per_feature': per_feature,
               'final_faces_modified_by': {str(k): sorted(v) for k, v in final.items()}}

# tempIds are NOT stable across recomputes (T1 changed parameters, T2 rolled the
# timeline), so the face -> feature map has to be rebuilt from here on.
OWNER.clear(); OWNER.update(feature_owner_map())
R['tempId_note'] = 'tempIds changed after recompute/rollback: owner map rebuilt'

# ------------------------------------------- T3. composed topology validity
with section('T3_topology_checks'):
    b = body()
    # A zero-length edge with one face is the apex of a cone (drill tip): legal, not a defect.
    degenerate = [e for e in b.edges if e.length < 1e-7]
    real = [e for e in b.edges if e.length >= 1e-7]
    edge_faces = [e.faces.count for e in real]
    short_edges = [mm(e.length) for e in real if e.length * 10 < 0.01]
    R['T3'] = {
        'isSolid': b.isSolid, 'lumps': b.lumps.count,
        'shells': [{'faces': s.faces.count, 'isVoid': s.isVoid, 'isClosed': s.isClosed}
                   for l in b.lumps for s in l.shells],
        'degenerate_edges(cone apex)': [{'faces': [short(f.geometry) for f in e.faces]} for e in degenerate],
        'open_edges(1 face)': edge_faces.count(1),
        'non_manifold_edges(>2 faces)': sum(1 for n in edge_faces if n > 2),
        'short_edges(<0.01mm)': short_edges,
        'tiny_faces(<0.001mm2)': sum(1 for f in b.faces if f.area * 100 < 1e-3),
        'feature_health': {t.name: t.healthState for t in design.timeline},
    }

with section('T3_text_commands'):
    found = {}
    for cmd in ('TextCommands.List', 'TextCommands.List /hidden'):
        out = safe(lambda: app.executeTextCommand(cmd), None)
        if out:
            lines = out.splitlines()
            found[cmd] = {'lines': len(lines),
                          'matches': [l.strip() for l in lines if any(
                              k in l.lower() for k in ('check', 'valid', 'heal', 'brep', 'geometry'))][:60]}
        else:
            found[cmd] = None
    R['T3']['text_commands'] = found

# ----------------------------------- T4. own edge convexity (dihedral angle)
def classify_edge(e):
    if e.faces.count != 2:
        return None
    ok, t0, t1 = e.evaluator.getParameterExtents()
    tm = (t0 + t1) / 2
    ok, pt = e.evaluator.getPointAtParameter(tm)
    ok, tan = e.evaluator.getTangent(tm)
    tan.normalize()
    co = [c for c in e.coEdges]
    f1, f2 = co[0].loop.face, co[1].loop.face
    ok1, n1 = f1.evaluator.getNormalAtPoint(pt)
    ok2, n2 = f2.evaluator.getNormalAtPoint(pt)
    t1v = tan.copy()
    if co[0].isOpposedToEdge:
        t1v.scaleBy(-1)
    inward1 = n1.crossProduct(t1v)  # face material lies left of the coedge
    cos = max(-1.0, min(1.0, n1.dotProduct(n2)))
    angle = math.degrees(math.acos(cos))  # angle between normals; 0 = tangent
    if angle < 0.5:
        kind = 'tangent'
    else:
        kind = 'concave' if inward1.dotProduct(n2) > 0 else 'convex'
    return {'kind': kind, 'normal_angle_deg': round(angle, 2), 'f1': f1.tempId, 'f2': f2.tempId,
            'is_line': short(e.geometry) == 'Line3D', 'length_mm': mm(e.length),
            'vertical': abs(abs(tan.z) - 1) < 1e-6}


with section('T4_edge_convexity'):
    b = body()
    api_concave = {e.tempId for e in b.concaveEdges}
    api_convex = {e.tempId for e in b.convexEdges}
    EDGE = {}
    agree = disagree = 0
    detail = []
    for e in b.edges:
        c = classify_edge(e)
        if not c:
            continue
        EDGE[e.tempId] = c
        api = 'concave' if e.tempId in api_concave else 'convex' if e.tempId in api_convex else 'none'
        if c['kind'] == 'tangent':
            detail.append({'edge': e.tempId, 'ours': 'tangent', 'api': api})
        elif c['kind'] == api:
            agree += 1
        else:
            disagree += 1
            detail.append({'edge': e.tempId, 'ours': c['kind'], 'api': api})
    R['T4'] = {'edges': b.edges.count,
               'ours': {k: sum(1 for c in EDGE.values() if c['kind'] == k)
                        for k in ('concave', 'convex', 'tangent')},
               'api': {'concave': len(api_concave), 'convex': len(api_convex)},
               'agree_on_non_tangent': agree, 'disagree': disagree, 'detail': detail}

# ------------- T5. attributed adjacency graph -> depressions (cavity recognition)
with section('T5_aag_depressions'):
    b = body()
    faces = {f.tempId: f for f in b.faces}
    adj = {k: set() for k in faces}
    for c in EDGE.values():
        if c['kind'] in ('concave', 'tangent'):
            adj[c['f1']].add(c['f2']); adj[c['f2']].add(c['f1'])
    comps, seen = [], set()
    for k in faces:
        if k in seen or not adj[k]:
            continue
        stack, comp = [k], set()
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x); comp.add(x); stack.extend(adj[x] - seen)
        comps.append(comp)

    edge_by_pair = {}
    for e in b.edges:
        if e.tempId in EDGE:
            c = EDGE[e.tempId]
            edge_by_pair.setdefault(frozenset((c['f1'], c['f2'])), []).append(c)

    cavities = []
    for comp in comps:
        fs = [faces[i] for i in comp]
        zmin = min(f.boundingBox.minPoint.z for f in fs)
        zmax = max(f.boundingBox.maxPoint.z for f in fs)
        xs = [f.boundingBox.minPoint.x for f in fs] + [f.boundingBox.maxPoint.x for f in fs]
        ys = [f.boundingBox.minPoint.y for f in fs] + [f.boundingBox.maxPoint.y for f in fs]
        vert_cyl_r = [f.geometry.radius for f in fs if short(f.geometry) == 'Cylinder'
                      and abs(abs(f.geometry.axis.z) - 1) < 1e-6]
        sharp_vertical = [c for pair, cs in edge_by_pair.items() if pair <= comp
                          for c in cs if c['kind'] == 'concave' and c['vertical'] and c['is_line']]
        r_min = 0.0 if sharp_vertical else (min(vert_cyl_r) if vert_cyl_r else None)
        depth = zmax - zmin
        width = min(max(xs) - min(xs), max(ys) - min(ys))
        cavities.append({
            'faces': len(comp),
            'owners': sorted({OWNER.get(i) for i in comp if OWNER.get(i)}),
            'depth_mm': mm(depth), 'min_opening_mm': mm(width),
            'min_vertical_internal_radius_mm': None if r_min is None else mm(r_min),
            'sharp_vertical_concave_edges': len(sharp_vertical),
            'aspect_depth/tool_d': None if not r_min else round(depth / (2 * r_min), 2),
            'aspect_depth/opening': round(depth / width, 2) if width > 0 else None,
            'axis_horizontal_cylinders': sum(1 for f in fs if short(f.geometry) == 'Cylinder'
                                             and abs(f.geometry.axis.z) < 1e-6),
        })
    R['T5'] = {'components': len(comps), 'cavities': cavities}


# ---------------------------- sampling helper for T6/T7 (points on a face)
def face_samples(f, n=5):
    ev = f.evaluator
    rng = ev.parametricRange()
    u0, v0, u1, v1 = rng.minPoint.x, rng.minPoint.y, rng.maxPoint.x, rng.maxPoint.y
    pts = []
    for i in range(n):
        for j in range(n):
            uv = C.Point2D.create(u0 + (u1 - u0) * (i + 0.5) / n, v0 + (v1 - v0) * (j + 0.5) / n)
            if not ev.isParameterOnFace(uv):
                continue
            ok, p = ev.getPointAtParameter(uv)
            ok2, nrm = ev.getNormalAtParameter(uv)
            if ok and ok2:
                pts.append((p, nrm))
    return pts


def offset(p, v, d):
    w = v.copy(); w.normalize(); w.scaleBy(d)
    q = p.copy(); q.translateBy(w)
    return q


# ----------------------- T6. accessibility from +Z by ray casting (undercuts)
with section('T6_accessibility_rays'):
    b = body()
    res = []
    zmin_stock = b.boundingBox.minPoint.z
    fixture = []
    for f in b.faces:
        # The face lying on the stock bottom is the fixture face of a +Z setup, not a defect.
        if short(f.geometry) == 'Plane' and abs(f.boundingBox.maxPoint.z - zmin_stock) < 1e-6:
            fixture.append(f.tempId)
            continue
        pts = face_samples(f)
        if not pts:
            continue
        down = blocked = free = 0
        for p, n in pts:
            if n.dotProduct(Z) < -1e-6:
                down += 1          # faces the -Z side: a tool from +Z can never touch it
                continue
            start = offset(offset(p, n, 0.002), Z, 0.002)
            hits = root.findBRepUsingRay(start, Z, FACE)
            hits = [h for h in hits if h.tempId != f.tempId]
            if hits:
                blocked += 1
            else:
                free += 1
        if down or blocked:
            d = describe(f); d.update(samples=len(pts), facing_down=down, occluded=blocked, free=free)
            res.append(d)
    R['T6'] = {'faces_not_fully_reachable_from_+Z': res, 'fixture_faces_skipped': fixture}

# ------------------------------ T7. wall thickness by ray casting along -normal
with section('T7_wall_thickness_rays'):
    b = body()
    out = []
    for f in b.faces:
        best = None
        for p, n in face_samples(f, 4):
            inward = n.copy(); inward.scaleBy(-1)
            start = offset(p, inward, 0.0005)
            hp = C.ObjectCollection.create()
            hits = root.findBRepUsingRay(start, inward, FACE, -1, True, hp)
            for k in range(hits.count):
                if hits.item(k).tempId == f.tempId:
                    continue
                d = p.distanceTo(hp.item(k))
                best = d if best is None else min(best, d)
                break
        if best is not None:
            d = describe(f); d['min_thickness_mm'] = mm(best); out.append(d)
    out.sort(key=lambda x: x['min_thickness_mm'])
    R['T7'] = {'thinnest_faces': out[:6]}

# ------------- T8. trace a radius with no parameter back to its sketch curve
with section('T8_sketch_curve_trace'):
    traces = []
    prof = pocket3.profile
    curves = [pc.sketchEntity for loop in prof.profileLoops for pc in loop.profileCurves]
    arcs = [c for c in curves if short(c) == 'SketchArc']
    sk3 = pocket3.profile.parentSketch
    xf = sk3.transform
    for f in pocket3.faces:
        if short(f.geometry) != 'Cylinder':
            continue
        g = f.geometry
        best = None
        for a in arcs:
            cen = a.centerSketchPoint.geometry.copy(); cen.transformBy(xf)
            dxy = math.hypot(cen.x - g.origin.x, cen.y - g.origin.y)
            if abs(a.radius - g.radius) < 1e-6 and dxy < 1e-5:
                best = a
        dim_params = []
        if best:
            for dmn in sk3.sketchDimensions:
                ent = safe(lambda: dmn.entity)
                if ent and ent == best:
                    dim_params.append(dmn.parameter.name)
        traces.append({'face': f.tempId, 'radius_mm': mm(g.radius),
                       'sketch': sk3.name if best else None,
                       'arc_found': bool(best),
                       'arc_fully_constrained': safe(lambda: best.isFullyConstrained),
                       'radius_parameter': dim_params or None})
    R['T8'] = {'pocket3_cylinders': traces,
               'note': 'radius_parameter None => only the sketch curve can be proposed for correction'}

# --------------------- T9. exports for external tools (OCC, mesh analysis)
with section('T9_exports'):
    b = body()
    em = design.exportManager
    step = os.path.join(OUT, 'probe02.step')
    em.execute(em.createSTEPExportOptions(step, root))
    stl = os.path.join(OUT, 'probe02.stl')
    so = em.createSTLExportOptions(b, stl); so.meshRefinement = F.MeshRefinementSettings.MeshRefinementHigh
    em.execute(so)
    smt = os.path.join(OUT, 'probe02.smt')
    smt_ok = F.TemporaryBRepManager.get().exportToFile([b], smt)
    calc = b.meshManager.createMeshCalculator()
    calc.setQuality(F.TriangleMeshQualityOptions.NormalQualityTriangleMesh)
    mesh = calc.calculate()
    face_mesh = body().faces.item(0).meshManager.createMeshCalculator().calculate()
    R['T9'] = {'step': (step, os.path.getsize(step)), 'stl': (stl, os.path.getsize(stl)),
               'smt': (smt, smt_ok and os.path.getsize(smt)),
               'body_mesh': {'nodes': mesh.nodeCount, 'triangles': mesh.triangleCount},
               'per_face_mesh_available': face_mesh.triangleCount > 0}

# -------------------------- T10. python environment inside Fusion
with section('T10_python_env'):
    mods = {}
    for m in ('numpy', 'scipy', 'requests', 'urllib.request', 'ssl', 'sqlite3', 'json'):
        try:
            __import__(m); mods[m] = True
        except Exception as ex:
            mods[m] = repr(ex)[:80]
    R['T10'] = {'python': sys.version, 'executable': sys.executable, 'modules': mods}

# --------------- T11. feedback to the designer: custom graphics + document data
with section('T11_highlight_and_config'):
    tbm = F.TemporaryBRepManager.get()
    group = root.customGraphicsGroups.add()
    red = F.CustomGraphicsSolidColorEffect.create(C.Color.create(230, 30, 30, 255))
    n = 0
    for f in body().faces:
        if OWNER.get(f.tempId) in ('Pocket2', 'SideHole'):
            cg = group.addBRepBody(tbm.copy(f)); cg.color = red; cg.depthPriority = 1; n += 1
    app.activeViewport.refresh()
    design.attributes.add('dfm', 'config', json.dumps({'min_internal_radius_mm': 1.5,
                                                       'max_aspect': 4, 'min_wall_mm': 2}))
    R['T11'] = {'highlighted_faces': n,
                'config_roundtrip': json.loads(design.attributes.itemByName('dfm', 'config').value),
                'palettes_api': hasattr(ui.palettes, 'add'),
                'selection_api': hasattr(ui.activeSelections, 'add')}

result = R
