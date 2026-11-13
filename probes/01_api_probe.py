# Probe 01 - what the Fusion API can do for this project (objective 2).
# Runs inside Fusion through ClaudeBridge. Creates a NEW unsaved document with
# a test part (block + pocket with internal corner radii + hole) and checks:
#   A. face -> feature -> parameter traceability
#   B. B-Rep measurements needed by the rules (radius, concavity, depth, distance)
#   C. stability of entityTokens after a parameter change
#   D. timeline rollback, health states, topology checks
#   E. timing of every step (latency budget for "check after each operation")
import time

R = {'errors': {}, 'timing_ms': {}}
V = adsk.core.ValueInput.createByString
P = adsk.core.Point3D.create
F = adsk.fusion


def timed(key):
    class _T:
        def __enter__(self):
            self.t = time.perf_counter()
        def __exit__(self, *exc):
            R['timing_ms'][key] = round((time.perf_counter() - self.t) * 1000, 3)
            if exc[0]:
                import traceback
                R['errors'][key] = ''.join(traceback.format_exception(*exc))
            return True  # keep going with the next section
    return _T()


def safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def short(obj):
    return obj.objectType.split('::')[-1] if obj else None


# ---------------------------------------------------------------- build part
with timed('build_part'):
    app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    design = F.Design.cast(app.activeProduct)
    design.designType = F.DesignTypes.ParametricDesignType
    root = design.rootComponent
    for n, v in [('block_L', '80 mm'), ('block_W', '50 mm'), ('block_H', '30 mm'), ('pocket_L', '40 mm'),
                 ('pocket_W', '20 mm'), ('pocket_D', '25 mm'), ('r_corner', '1 mm'),
                 ('hole_d', '6 mm'), ('hole_depth', '20 mm')]:
        design.userParameters.add(n, V(v), 'mm', '')

    # Block
    sk = root.sketches.add(root.xYConstructionPlane)
    sk.name = 'Block sketch'
    lines = sk.sketchCurves.sketchLines.addTwoPointRectangle(P(0, 0, 0), P(8, 5, 0))
    sk.geometricConstraints.addCoincident(lines.item(0).startSketchPoint, sk.originPoint)
    d = sk.sketchDimensions
    d.addDistanceDimension(lines.item(0).startSketchPoint, lines.item(0).endSketchPoint,
                           F.DimensionOrientations.HorizontalDimensionOrientation,
                           P(4, -1, 0)).parameter.expression = 'block_L'
    d.addDistanceDimension(lines.item(1).startSketchPoint, lines.item(1).endSketchPoint,
                           F.DimensionOrientations.VerticalDimensionOrientation,
                           P(9, 2.5, 0)).parameter.expression = 'block_W'
    ext = root.features.extrudeFeatures
    ei = ext.createInput(sk.profiles.item(0), F.FeatureOperations.NewBodyFeatureOperation)
    ei.setDistanceExtent(False, V('block_H'))
    block = ext.add(ei)
    block.name = 'Block'
    body = block.bodies.item(0)

    # Pocket (cut from top plane, depth pocket_D)
    pl_in = root.constructionPlanes.createInput()
    pl_in.setByOffset(root.xYConstructionPlane, V('block_H'))
    top_plane = root.constructionPlanes.add(pl_in)
    sk2 = root.sketches.add(top_plane)
    sk2.name = 'Pocket sketch'
    rect = sk2.sketchCurves.sketchLines.addCenterPointRectangle(P(4, 2.5, 0), P(6, 3.5, 0))
    d2 = sk2.sketchDimensions
    d2.addDistanceDimension(rect.item(0).startSketchPoint, rect.item(0).endSketchPoint,
                            F.DimensionOrientations.HorizontalDimensionOrientation,
                            P(4, 4.5, 0)).parameter.expression = 'pocket_L'
    d2.addDistanceDimension(rect.item(1).startSketchPoint, rect.item(1).endSketchPoint,
                            F.DimensionOrientations.VerticalDimensionOrientation,
                            P(7, 2.5, 0)).parameter.expression = 'pocket_W'
    ci = ext.createInput(sk2.profiles.item(0), F.FeatureOperations.CutFeatureOperation)
    ci.setOneSideExtent(F.DistanceExtentDefinition.create(V('pocket_D')),
                        F.ExtentDirections.NegativeExtentDirection)
    pocket = ext.add(ci)
    pocket.name = 'Pocket'

    # Internal corner fillets on the 4 vertical pocket edges
    edges = adsk.core.ObjectCollection.create()
    seen = set()
    for face in pocket.sideFaces:
        for e in face.edges:
            a, b = e.startVertex.geometry, e.endVertex.geometry
            if abs(a.x - b.x) < 1e-6 and abs(a.y - b.y) < 1e-6 and e.tempId not in seen:
                seen.add(e.tempId)
                edges.add(e)
    fi = root.features.filletFeatures.createInput()
    try:
        fi.edgeSetInputs.addConstantRadiusEdgeSet(edges, V('r_corner'), True)
    except Exception:
        fi.addConstantRadiusEdgeSet(edges, V('r_corner'), True)
    fillet = root.features.filletFeatures.add(fi)
    fillet.name = 'Pocket corners'

    # Simple hole on the top face
    top_face = max(body.faces, key=lambda f: f.centroid.z if short(f.geometry) == 'Plane' else -1e9)
    hi = root.features.holeFeatures.createSimpleInput(V('hole_d'))
    hi.setPositionByPoint(top_face, P(1.2, 1.2, top_face.centroid.z))
    hi.setDistanceExtent(V('hole_depth'))
    hole = root.features.holeFeatures.add(hi)
    hole.name = 'Hole'
    app.activeViewport.fit()

if 'build_part' in R['errors']:
    raise RuntimeError('build failed:\n' + R['errors']['build_part'])
body = root.bRepBodies.item(0)
um = design.unitsManager
mm = lambda cm: round(cm * 10, 4)

# ------------------------------------------------- A. face -> feature -> param
with timed('A_face_to_feature_map'):
    owner = {}
    feats = []
    tl = design.timeline
    for i in range(tl.count):
        item = tl.item(i)
        ent = item.entity
        faces = safe(lambda: list(ent.faces), None)
        feats.append({'index': i, 'name': item.name, 'type': short(ent),
                      'n_faces': None if faces is None else len(faces),
                      'health': safe(lambda: item.healthState)})
        for f in faces or []:
            owner.setdefault(f.tempId, []).append(item.name)
    unowned = [f.tempId for f in body.faces if f.tempId not in owner]
    R['A'] = {'features': feats, 'body_faces': body.faces.count,
              'faces_with_owner': body.faces.count - len(unowned),
              'faces_without_owner': len(unowned),
              'faces_with_multiple_owners': sum(1 for v in owner.values() if len(v) > 1)}

with timed('A_feature_to_parameter'):
    by_feature = {}
    for p in design.allParameters:
        mp = F.ModelParameter.cast(p)
        if not mp:
            continue
        cb = safe(lambda: mp.createdBy)
        key = safe(lambda: cb.name) or short(cb)
        by_feature.setdefault(key, []).append({
            'param': mp.name, 'role': mp.role, 'expression': mp.expression,
            'depends_on': safe(lambda: [q.name for q in mp.dependencyParameters], 'n/a')})
    R['A']['params_by_feature'] = by_feature

# --------------------------------------------------------- B. measurements
with timed('B_face_measurements'):
    faces_out = []
    for f in body.faces:
        g = f.geometry
        info = {'tempId': f.tempId, 'type': short(g), 'area_mm2': round(f.area * 100, 3),
                'owner': owner.get(f.tempId)}
        if info['type'] == 'Cylinder':
            ok, n = f.evaluator.getNormalAtPoint(f.pointOnFace)
            pt = f.pointOnFace
            v = g.origin.vectorTo(pt)
            ax = g.axis.copy(); ax.normalize()
            ax.scaleBy(v.dotProduct(ax)); v.subtract(ax)  # radial component
            info['radius_mm'] = mm(g.radius)
            info['concave'] = n.dotProduct(v) < 0  # normal toward the axis = internal radius
        faces_out.append(info)
    R['B'] = {'faces': faces_out,
              'concave_edges': safe(lambda: body.concaveEdges.count),
              'convex_edges': safe(lambda: body.convexEdges.count)}

with timed('B_pocket_depth_and_aspect'):
    floor = [f for f in pocket.endFaces][0]
    top = [f for f in block.endFaces][0]
    dist = app.measureManager.measureMinimumDistance(floor, top).value
    concave_r = [x['radius_mm'] for x in faces_out
                 if x.get('concave') and 'Pocket corners' in (x['owner'] or [])]
    R['B']['pocket'] = {'depth_mm_measured': mm(dist),
                        'min_internal_radius_mm': min(concave_r) if concave_r else None,
                        'aspect_depth_over_tool_d': round(mm(dist) / (2 * min(concave_r)), 2)
                        if concave_r else None}

# ------------------------------------------- C. token stability after change
with timed('C_tokens_before'):
    tokens = {f.tempId: f.entityToken for f in fillet.faces}
with timed('C_recompute_r_corner_1_to_3mm'):
    design.userParameters.itemByName('r_corner').expression = '3 mm'
    adsk.doEvents()
with timed('C_tokens_after'):
    resolved = []
    for tid, tok in tokens.items():
        found = design.findEntityByToken(tok)
        resolved.append({'old_tempId': tid, 'found': len(found),
                         'new_radius_mm': mm(found[0].geometry.radius) if found and short(found[0].geometry) == 'Cylinder' else None})
    R['C'] = {'tokens': len(tokens), 'resolved': resolved}

# ------------------------------------------ D. timeline, health, topology
with timed('D_rollback_before_fillet'):
    fillet.timelineObject.rollTo(True)
    R['D'] = {'faces_when_rolled_before_fillet': root.bRepBodies.item(0).faces.count}
    design.timeline.moveToEnd()
    R['D']['faces_at_end'] = root.bRepBodies.item(0).faces.count

with timed('D_topology'):
    b = root.bRepBodies.item(0)
    R['D']['topology'] = {
        'isSolid': b.isSolid, 'lumps': b.lumps.count,
        'shells': sum(l.shells.count for l in b.lumps),
        'faces': b.faces.count, 'edges': b.edges.count, 'vertices': b.vertices.count,
        'tiny_faces(<1e-4 mm2)': sum(1 for f in b.faces if f.area * 100 < 1e-4),
        'health': [(design.timeline.item(i).name, design.timeline.item(i).healthState)
                   for i in range(design.timeline.count)]}
    R['D']['body_methods_with_check_or_valid'] = [n for n in dir(b)
                                                  if 'check' in n.lower() or 'valid' in n.lower()]

with timed('D_break_feature_on_purpose'):
    # A pocket deeper than the block must cut through; a 0-length hole must fail.
    design.userParameters.itemByName('hole_depth').expression = '0 mm'
    adsk.doEvents()
    R['D']['after_bad_param'] = [(design.timeline.item(i).name, design.timeline.item(i).healthState,
                                  safe(lambda: design.timeline.item(i).errorOrWarningMessage))
                                 for i in range(design.timeline.count)]
    design.userParameters.itemByName('hole_depth').expression = '20 mm'

# ------------------------------------------------------- E. events available
R['E_ui_events'] = [n for n in dir(ui) if n[0].islower() and any(
    k in n for k in ('command', 'Command', 'activ', 'select', 'Select', 'marking'))]
R['E_app_events'] = [n for n in dir(app) if any(k in n for k in ('document', 'Document', 'Event', 'Started', 'Opened'))]

result = R
