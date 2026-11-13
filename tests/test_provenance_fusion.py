# Integration test for src/dfm/provenance.py. Runs INSIDE Fusion via ClaudeBridge:
#   python tools/fusion_bridge.py tests/test_provenance_fusion.py --timeout 300
# Creates a new unsaved document. Result: {'checks': [...], 'passed': n, 'failed': n, ...}
import importlib
import sys
import time
import traceback

SRC = r'C:\taller\taller-grado-dfm-fusion\src'
if SRC not in sys.path:
    sys.path.insert(0, SRC)
import dfm.provenance as prov
importlib.reload(prov)

V = adsk.core.ValueInput.createByString
P = adsk.core.Point3D.create
F = adsk.fusion
OUT = {'checks': [], 'modes': [], 'errors': [], 'traces': {}}


def check(name, cond, detail=None):
    OUT['checks'].append({'check': name, 'ok': bool(cond), 'detail': detail})


def short(o):
    return o.objectType.split('::')[-1] if o else None


# ------------------------------------------------------------- build part
app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
design = F.Design.cast(app.activeProduct)
design.designType = F.DesignTypes.ParametricDesignType
root = design.rootComponent
tracker = prov.ProvenanceTracker(design)


def upd(label):
    t = time.perf_counter()
    mode = tracker.update()
    OUT['modes'].append({'after': label, 'mode': mode, 'steps': tracker.last_update['steps'],
                         'ms': round((time.perf_counter() - t) * 1000, 1)})
    return mode


for n, v in [('blk_L', '100 mm'), ('blk_W', '60 mm'), ('blk_H', '30 mm'), ('p1_L', '40 mm'),
             ('p1_W', '20 mm'), ('p1_D', '25 mm'), ('p1_r', '1 mm'), ('p2_D', '10 mm'),
             ('p3_D', '8 mm'), ('hole_d', '6 mm'), ('hole_depth', '20 mm')]:
    design.userParameters.add(n, V(v), 'mm', '')
upd('user parameters')

ext = root.features.extrudeFeatures
D = F.DimensionOrientations
sk = root.sketches.add(root.xYConstructionPlane); sk.name = 'Block sketch'
ln = sk.sketchCurves.sketchLines.addTwoPointRectangle(P(0, 0, 0), P(10, 6, 0))
sk.geometricConstraints.addCoincident(ln.item(0).startSketchPoint, sk.originPoint)
sk.sketchDimensions.addDistanceDimension(ln.item(0).startSketchPoint, ln.item(0).endSketchPoint,
    D.HorizontalDimensionOrientation, P(5, -1, 0)).parameter.expression = 'blk_L'
sk.sketchDimensions.addDistanceDimension(ln.item(1).startSketchPoint, ln.item(1).endSketchPoint,
    D.VerticalDimensionOrientation, P(11, 3, 0)).parameter.expression = 'blk_W'
upd('Block sketch')
ei = ext.createInput(sk.profiles.item(0), F.FeatureOperations.NewBodyFeatureOperation)
ei.setDistanceExtent(False, V('blk_H'))
block = ext.add(ei); block.name = 'Block'
upd('Block')

pi = root.constructionPlanes.createInput()
pi.setByOffset(root.xYConstructionPlane, V('blk_H'))
top_plane = root.constructionPlanes.add(pi); top_plane.name = 'Top plane'
upd('Top plane')


def cut(sketch, depth, name, profile=None):
    ci = ext.createInput(profile or sketch.profiles.item(0), F.FeatureOperations.CutFeatureOperation)
    ci.setOneSideExtent(F.DistanceExtentDefinition.create(V(depth)),
                        F.ExtentDirections.NegativeExtentDirection)
    feat = ext.add(ci); feat.name = name
    upd(name)
    return feat


s1 = root.sketches.add(top_plane); s1.name = 'Pocket1 sketch'
r1 = s1.sketchCurves.sketchLines.addCenterPointRectangle(P(3, 3, 0), P(5, 4, 0))
s1.sketchDimensions.addDistanceDimension(r1.item(0).startSketchPoint, r1.item(0).endSketchPoint,
    D.HorizontalDimensionOrientation, P(3, 4.5, 0)).parameter.expression = 'p1_L'
s1.sketchDimensions.addDistanceDimension(r1.item(1).startSketchPoint, r1.item(1).endSketchPoint,
    D.VerticalDimensionOrientation, P(5.5, 3, 0)).parameter.expression = 'p1_W'
upd('Pocket1 sketch')
pocket1 = cut(s1, 'p1_D', 'Pocket1')
edges = adsk.core.ObjectCollection.create(); seen = set()
for face in pocket1.sideFaces:
    for e in face.edges:
        a, b = e.startVertex.geometry, e.endVertex.geometry
        if abs(a.x - b.x) < 1e-6 and abs(a.y - b.y) < 1e-6 and e.tempId not in seen:
            seen.add(e.tempId); edges.add(e)
fi = root.features.filletFeatures.createInput()
fi.edgeSetInputs.addConstantRadiusEdgeSet(edges, V('p1_r'), True)
fillet = root.features.filletFeatures.add(fi); fillet.name = 'Pocket1 corners'
upd('Pocket1 corners')

s2 = root.sketches.add(top_plane); s2.name = 'Pocket2 sketch'
s2.sketchCurves.sketchLines.addTwoPointRectangle(P(7.5, 2, 0), P(9.85, 4, 0))
upd('Pocket2 sketch')
pocket2 = cut(s2, 'p2_D', 'Pocket2')

s3 = root.sketches.add(top_plane); s3.name = 'Pocket3 sketch'
r3 = s3.sketchCurves.sketchLines.addTwoPointRectangle(P(1, 4.6, 0), P(5, 5.6, 0))
L3 = [r3.item(i) for i in range(4)]
for i in range(4):
    s3.sketchCurves.sketchArcs.addFillet(L3[i], L3[i].endSketchPoint.geometry,
                                         L3[(i + 1) % 4], L3[(i + 1) % 4].startSketchPoint.geometry, 0.2)
upd('Pocket3 sketch')
pocket3 = cut(s3, 'p3_D', 'Pocket3', min(s3.profiles, key=lambda p: p.areaProperties().area))

body = lambda: root.bRepBodies.item(0)
top = lambda: max((f for f in body().faces if short(f.geometry) == 'Plane'),
                  key=lambda f: (round(f.centroid.z, 6), f.area))
hi = root.features.holeFeatures.createSimpleInput(V('hole_d'))
hi.setPositionByPoint(top(), P(7, 0.8, top().centroid.z))
hi.setDistanceExtent(V('hole_depth'))
hole = root.features.holeFeatures.add(hi); hole.name = 'Hole'
upd('Hole')
app.activeViewport.fit()


# ------------------------------------------------------------- helpers
def key(ent):
    """Geometry-based key, independent of tempId/token (which change on recompute)."""
    if short(ent) == 'BRepFace':
        c = ent.centroid
        return ('F', short(ent.geometry), round(c.x * 10, 3), round(c.y * 10, 3), round(c.z * 10, 3))
    p = ent.pointOnEdge
    return ('E', short(ent.geometry), round(p.x * 10, 3), round(p.y * 10, 3), round(p.z * 10, 3))


def snapshot():
    snap = {}
    for kind, coll in (('faces', body().faces), ('edges', body().edges)):
        for ent in coll:
            rec = tracker.record(ent)
            snap[str(key(ent))] = None if rec is None else (rec['origin'], tuple(rec['modified_by']))
    return snap


def api_owner():
    own = {}
    for it in design.timeline:
        for f in (prov._safe(lambda: list(it.entity.faces), []) or []):
            own.setdefault(f.tempId, it.name)
    return own


def find_face(pred):
    return next((f for f in body().faces if pred(f)), None)


def run(name, fn):
    try:
        fn()
    except Exception:
        OUT['errors'].append({'scenario': name, 'error': traceback.format_exc()[-1500:]})


# ---------------------------------------------- S0: incremental while building
def s0():
    modes = [m['mode'] for m in OUT['modes']]
    check('S0 first update is a rebuild, the rest are appends',
          modes[0] == 'rebuild' and all(m == 'append' for m in modes[1:]), modes)
    missing = [str(key(f)) for f in body().faces if tracker.record(f) is None] + \
              [str(key(e)) for e in body().edges if tracker.record(e) is None]
    check('S0 every face and edge has a record', not missing, missing[:5])
    own = api_owner()
    bad = [(str(key(f)), tracker.record(f)['origin'], own.get(f.tempId)) for f in body().faces
           if tracker.record(f)['origin'] != own.get(f.tempId)]
    check('S0 origin == Feature.faces owner for every face', not bad, bad[:5])
run('S0', s0)

INCREMENTAL = snapshot()


# ---------------------------------------------- S1: rebuild gives the same answer
def s1():
    tracker.rebuild()
    rebuilt = snapshot()
    diff = [(k, INCREMENTAL.get(k), rebuilt.get(k)) for k in set(INCREMENTAL) | set(rebuilt)
            if INCREMENTAL.get(k) != rebuilt.get(k)]
    check('S1 incremental == full replay (faces and edges)', not diff, diff[:5])
    check('S1 replay restored the marker to the end',
          design.timeline.markerPosition == design.timeline.count,
          [design.timeline.markerPosition, design.timeline.count])
run('S1', s1)


# ---------------------------------------------- S2: traces down to parameters
def s2():
    tf = top()
    t = tracker.trace(tf)
    OUT['traces']['top face'] = t
    check('S2 top face: origin Block, modified by every cut',
          t['origin'] == 'Block' and t['modified_by'] == ['Pocket1', 'Pocket1 corners', 'Pocket2', 'Pocket3', 'Hole'],
          t['modified_by'])

    fil = find_face(lambda f: short(f.geometry) == 'Cylinder' and abs(f.geometry.radius - 0.1) < 1e-6)
    t = tracker.trace(fil); OUT['traces']['pocket1 corner radius'] = t
    check('S2 Pocket1 corner -> Pocket1 corners -> p1_r',
          t['origin'] == 'Pocket1 corners' and any('p1_r' in p['drives'] for p in t['controls']['parameters']),
          t['controls'])

    floor = pocket1.endFaces.item(0)
    t = tracker.trace(floor); OUT['traces']['pocket1 floor'] = t
    check('S2 Pocket1 floor -> p1_D, modified by the fillet',
          any('p1_D' in p['drives'] for p in t['controls']['parameters'])
          and t['modified_by'] == ['Pocket1 corners'], t)

    side = max(pocket1.sideFaces, key=lambda f: f.area)
    t = tracker.trace(side); OUT['traces']['pocket1 long wall'] = t
    dims = [d['drives'] for c in t['controls'].get('sketch_curves', []) for d in c['dimensions']]
    check('S2 Pocket1 long wall -> heuristic finds a pocket dimension (p1_L or p1_W)',
          any('p1_L' in d or 'p1_W' in d for d in dims), t['controls'])

    arcs = [f for f in pocket3.faces if short(f.geometry) == 'Cylinder']
    t = tracker.trace(arcs[0]); OUT['traces']['pocket3 corner'] = t
    curves = t['controls'].get('sketch_curves', [])
    check('S2 Pocket3 corner -> undimensioned SketchArc, not parametric',
          curves and curves[0]['curve'] == 'SketchArc' and not curves[0]['dimensions']
          and t['controls']['parametric'] is False, t['controls'])

    sharp = next(e for e in body().edges if short(e.geometry) == 'Line3D'
                 and abs(abs(e.geometry.asInfiniteLine().direction.z) - 1) < 1e-6
                 and all(tracker.record(f)['origin'] == 'Pocket2' for f in e.faces))
    t = tracker.trace(sharp); OUT['traces']['pocket2 sharp corner edge'] = t
    check('S2 Pocket2 sharp edge -> Pocket2, its walls have no dimensions',
          t['origin'] == 'Pocket2' and all(not c['dimensions'] for f in t['faces']
                                           for c in f['controls'].get('sketch_curves', [])), t['origin'])

    hc = next(f for f in hole.sideFaces)
    t = tracker.trace(hc); OUT['traces']['hole wall'] = t
    check('S2 Hole wall -> hole_d', any('hole_d' in p['drives'] for p in t['controls']['parameters']), t['controls'])
run('S2', s2)


# ---------------------------------------------- S2b: sensitivity = exact controls
def eff(res, name):
    for e in res['effects']:
        if e['parameter'] == name:
            return e['effect']
    return {}


def s2b():
    user = list(design.userParameters)
    side = max(pocket1.sideFaces, key=lambda f: f.area)
    r = prov.sensitivity(design, side, user); OUT['traces']['sensitivity pocket1 long wall'] = r
    # blk_H lifts the whole pocket (moves the wall, same area): an indirect dependency
    # through the Top plane that no feature-level lookup would reveal.
    check('S2b long wall: p1_W offsets it, p1_L/p1_D/p1_r change its area, blk_H moves it',
          'offset' in eff(r, 'p1_W') and 'area' in eff(r, 'p1_L') and 'area' in eff(r, 'p1_D')
          and 'area' in eff(r, 'p1_r') and 'moved_mm' in eff(r, 'blk_H')
          and 'area' not in eff(r, 'blk_H') and r['restored'],
          {e['parameter']: e['effect'] for e in r['effects']})

    fil = find_face(lambda f: short(f.geometry) == 'Cylinder' and abs(f.geometry.radius - 0.1) < 1e-6)
    r = prov.sensitivity(design, fil, user); OUT['traces']['sensitivity pocket1 corner'] = r
    radius_params = [e['parameter'] for e in r['effects'] if 'radius' in e['effect']]
    check('S2b Pocket1 corner radius is controlled only by p1_r', radius_params == ['p1_r'] and r['restored'],
          radius_params)

    arc = next(f for f in pocket3.faces if short(f.geometry) == 'Cylinder')
    r = prov.sensitivity(design, arc); OUT['traces']['sensitivity pocket3 corner'] = r
    radius_params = [e['parameter'] for e in r['effects'] if 'radius' in e['effect']]
    check('S2b Pocket3 corner radius: no parameter controls it (all independent params tested)',
          radius_params == [] and r['restored'], {'tested': r['tested'], 'radius_params': radius_params})
run('S2b', s2b)


# ---------------------------------------------- S3: editing an earlier parameter
def s3():
    before = sorted(map(str, INCREMENTAL.values()))
    design.userParameters.itemByName('p1_D').expression = '20 mm'
    mode = upd('edit p1_D 25->20')
    after = sorted(map(str, snapshot().values()))
    check('S3 parameter edit triggers a rebuild', mode == 'rebuild', mode)
    check('S3 provenance unchanged after parameter edit', before == after)
    design.userParameters.itemByName('p1_D').expression = '25 mm'
    upd('revert p1_D')
run('S3', s3)


# ---------------------------------------------- S4: insert a feature mid-timeline
def s4():
    hole.timelineObject.rollTo(True)  # marker before Hole, like dragging the marker
    mode = upd('marker moved before Hole')
    check('S4 moving the marker triggers a rebuild', mode == 'rebuild', mode)
    check('S4 rolled state has no Hole faces',
          all(tracker.record(f)['origin'] != 'Hole' for f in body().faces))
    s4k = root.sketches.add(top_plane); s4k.name = 'Pocket4 sketch'
    s4k.sketchCurves.sketchLines.addTwoPointRectangle(P(6.5, 4.8, 0), P(8.5, 5.5, 0))
    upd('Pocket4 sketch (inserted)')
    ci = ext.createInput(s4k.profiles.item(0), F.FeatureOperations.CutFeatureOperation)
    ci.setOneSideExtent(F.DistanceExtentDefinition.create(V('3 mm')), F.ExtentDirections.NegativeExtentDirection)
    p4 = ext.add(ci); p4.name = 'Pocket4'
    mode = upd('Pocket4 (inserted)')
    check('S4 inserting before the end is not treated as append', mode == 'rebuild', mode)
    design.timeline.moveToEnd()
    upd('marker back to end')
    t = tracker.trace(top())
    check('S4 top face modifiers follow timeline order with Pocket4 inserted',
          t['modified_by'] == ['Pocket1', 'Pocket1 corners', 'Pocket2', 'Pocket3', 'Pocket4', 'Hole'],
          t['modified_by'])
run('S4', s4)


# ---------------------------------------------- S5: suppress and delete
def s5():
    pocket2.timelineObject.isSuppressed = True
    mode = upd('suppress Pocket2')
    check('S5 suppress -> rebuild, no Pocket2 left',
          mode == 'rebuild' and all('Pocket2' not in (tracker.record(f)['origin'], *tracker.record(f)['modified_by'])
                                    for f in body().faces), mode)
    pocket2.timelineObject.isSuppressed = False
    upd('unsuppress Pocket2')
    pocket3.deleteMe()
    mode = upd('delete Pocket3')
    t = tracker.trace(top())
    check('S5 delete Pocket3 -> gone from top face modifiers',
          mode == 'rebuild' and 'Pocket3' not in t['modified_by'], t['modified_by'])
run('S5', s5)


# ---------------------------------------------- S6: persistence in the document
def s6():
    size = tracker.save()
    other = prov.ProvenanceTracker(design)
    ok = other.load()
    check('S6 save/load round trip', ok and other.records == tracker.records, {'bytes': size})
    check('S6 reloaded tracker sees no change (noop)', other.update() == 'noop', other.last_update)
run('S6', s6)

OUT['passed'] = sum(c['ok'] for c in OUT['checks'])
OUT['failed'] = sum(not c['ok'] for c in OUT['checks'])
result = OUT
