"""Geometric measurements for 3-axis milling rules (runs inside Fusion).

Techniques validated in probes/02_limites_y_tecnicas.md, generalised here:
  topology()      composed validity check (Fusion has no "Check body")
  classify_edges  own dihedral classification (API puts tangent edges in convex)
  accessibility() ray casting from the 6 axis directions -> reachable directions
                  per face, unreachable faces (undercuts), greedy setup count
  thickness()     ray casting along -normal -> local wall thickness per face
  cavities()      attributed adjacency graph (concave + tangent edges) -> cavities,
                  each measured along its own machining direction

All lengths returned in mm.
"""

import math

import adsk.core
import adsk.fusion

C = adsk.core
F = adsk.fusion
FACE = F.BRepEntityTypes.BRepFaceEntityType
DIRS = {'+Z': (0, 0, 1), '-Z': (0, 0, -1), '+X': (1, 0, 0),
        '-X': (-1, 0, 0), '+Y': (0, 1, 0), '-Y': (0, -1, 0)}
AXIS_INDEX = {'X': 0, 'Y': 1, 'Z': 2}


def short(obj):
    return obj.objectType.split('::')[-1] if obj else None


def mm(cm):
    return round(cm * 10, 4)


def vec(t):
    return C.Vector3D.create(*t)


def _bb(face):
    b = face.boundingBox
    return (b.minPoint.x, b.minPoint.y, b.minPoint.z), (b.maxPoint.x, b.maxPoint.y, b.maxPoint.z)


# ------------------------------------------------------------------ topology
def topology(body, short_edge_mm=0.01, tiny_face_mm2=0.001):
    degenerate = [e for e in body.edges if e.length < 1e-7]  # cone apex: legal
    real = [e for e in body.edges if e.length >= 1e-7]
    nfaces = [e.faces.count for e in real]
    return {
        'is_solid': body.isSolid, 'lumps': body.lumps.count,
        'shells': sum(l.shells.count for l in body.lumps),
        'open_shells': sum(1 for l in body.lumps for s in l.shells if not s.isClosed),
        'void_shells': sum(1 for l in body.lumps for s in l.shells if s.isVoid),
        'faces': body.faces.count, 'edges': body.edges.count,
        'degenerate_edges': len(degenerate),
        'open_edges': nfaces.count(1),
        'non_manifold_edges': sum(1 for n in nfaces if n > 2),
        'short_edges': sum(1 for e in real if e.length * 10 < short_edge_mm),
        'tiny_faces': sum(1 for f in body.faces if f.area * 100 < tiny_face_mm2),
    }


# ------------------------------------------------------------------ edges
def classify_edges(body):
    """tempId -> {kind: concave|convex|tangent, f1, f2, line, dir}."""
    out = {}
    for e in body.edges:
        if e.faces.count != 2 or e.length < 1e-7:
            continue
        ok, t0, t1 = e.evaluator.getParameterExtents()
        tm = (t0 + t1) / 2
        ok, pt = e.evaluator.getPointAtParameter(tm)
        ok, tan = e.evaluator.getTangent(tm)
        tan.normalize()
        co = list(e.coEdges)
        f1, f2 = co[0].loop.face, co[1].loop.face
        _, n1 = f1.evaluator.getNormalAtPoint(pt)
        _, n2 = f2.evaluator.getNormalAtPoint(pt)
        t1v = tan.copy()
        if co[0].isOpposedToEdge:
            t1v.scaleBy(-1)
        inward1 = n1.crossProduct(t1v)  # material of f1 lies left of its coedge
        angle = math.degrees(math.acos(max(-1.0, min(1.0, n1.dotProduct(n2)))))
        kind = 'tangent' if angle < 0.5 else ('concave' if inward1.dotProduct(n2) > 0 else 'convex')
        out[e.tempId] = {'kind': kind, 'f1': f1.tempId, 'f2': f2.tempId,
                         'line': short(e.geometry) == 'Line3D',
                         'dir': (tan.x, tan.y, tan.z), 'angle_deg': round(angle, 2)}
    return out


# ------------------------------------------------------------------ sampling
def face_samples(face, n=5):
    ev = face.evaluator
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
    if not pts:  # very thin faces: fall back to the API's own point
        p = face.pointOnFace
        ok, nrm = ev.getNormalAtPoint(p)
        if ok:
            pts.append((p, nrm))
    return pts


def offset(p, v, d):
    w = v.copy()
    w.normalize()
    w.scaleBy(d)
    q = p.copy()
    q.translateBy(w)
    return q


# ------------------------------------------------------------- accessibility
def accessibility(component, body, n=5, min_free=0.95):
    """For every face, the axis directions from which a tool can reach it.
    A sample is reachable from d when its normal does not face away from d and a
    ray from the point towards d leaves the body without hitting another face."""
    faces = {}
    for f in body.faces:
        pts = face_samples(f, n)
        reach = {}
        for name, t in DIRS.items():
            d = vec(t)
            free = 0
            for p, nrm in pts:
                if nrm.dotProduct(d) < -1e-6:
                    continue
                start = offset(offset(p, nrm, 0.002), d, 0.002)
                hits = [h for h in component.findBRepUsingRay(start, d, FACE) if h.tempId != f.tempId]
                if not hits:
                    free += 1
            reach[name] = round(free / len(pts), 3) if pts else 0.0
        faces[f.tempId] = {'reach': reach, 'dirs': [k for k, v in reach.items() if v >= min_free],
                           'partial': [k for k, v in reach.items() if 0 < v < min_free]}
    # greedy set cover: fewest directions (setups) that reach every reachable face
    todo = {k for k, v in faces.items() if v['dirs']}
    setups = []
    while todo:
        best = max(DIRS, key=lambda d: sum(1 for k in todo if d in faces[k]['dirs']))
        covered = {k for k in todo if best in faces[k]['dirs']}
        if not covered:
            break
        setups.append({'direction': best, 'faces': len(covered)})
        todo -= covered
    unreachable = [k for k, v in faces.items() if not v['dirs']]
    return {'faces': faces, 'setups': setups, 'unreachable': unreachable}


# ------------------------------------------------------------------ thickness
def thickness(component, body, n=4, window_mm=3.0):
    """Local wall thickness per face (mm), min of two methods:
    1. rays along -normal from sampled points (cheap, but a sample grid can miss
       the thinnest spot: two neighbouring counterbores are closest along the line
       between their axes, where no sample may lie - injection case E);
    2. exact minimum distance between non-adjacent face pairs whose bounding boxes
       are closer than `window_mm`; it counts as a wall only if the midpoint of the
       closest-point segment lies INSIDE the material (otherwise it is a gap, e.g.
       the width of a slot)."""
    out = _thickness_rays(component, body, n)
    mm_ = adsk.core.Application.get().measureManager
    inside = adsk.fusion.PointContainment.PointInsidePointContainment
    win = window_mm / 10
    fl = list(body.faces)
    verts = {f.tempId: {v.tempId for v in f.vertices} for f in fl}
    boxes = {f.tempId: _bb(f) for f in fl}
    for a in range(len(fl)):
        for b in range(a + 1, len(fl)):
            fa, fb = fl[a], fl[b]
            (a0, a1), (b0, b1) = boxes[fa.tempId], boxes[fb.tempId]
            if any(a0[i] - b1[i] > win or b0[i] - a1[i] > win for i in range(3)):
                continue
            if verts[fa.tempId] & verts[fb.tempId]:
                continue  # touching faces: distance 0 at the shared vertex/edge
            try:
                res = mm_.measureMinimumDistance(fa, fb)
            except Exception:
                continue
            d = res.value
            if d * 10 > window_mm or d < 1e-7:
                continue
            p, q = res.positionOne, res.positionTwo
            mid = C.Point3D.create((p.x + q.x) / 2, (p.y + q.y) / 2, (p.z + q.z) / 2)
            if body.pointContainment(mid) != inside:
                continue
            for f in (fa, fb):
                out[f.tempId] = min(out.get(f.tempId, 1e9), mm(d))
    return out


def _thickness_rays(component, body, n=4):
    out = {}
    for f in body.faces:
        best = None
        for p, nrm in face_samples(f, n):
            inward = nrm.copy()
            inward.scaleBy(-1)
            hp = C.ObjectCollection.create()
            hits = component.findBRepUsingRay(offset(p, inward, 0.0005), inward, FACE, -1, True, hp)
            for k in range(hits.count):
                if hits.item(k).tempId == f.tempId:
                    continue
                d = p.distanceTo(hp.item(k))
                best = d if best is None else min(best, d)
                break
        if best is not None:
            out[f.tempId] = mm(best)
    return out


# ------------------------------------------------------------------ cavities
def _concave_cylinder(f):
    g = f.geometry
    if short(g) != 'Cylinder':
        return False
    p = f.pointOnFace
    ok, n = f.evaluator.getNormalAtPoint(p)
    v = g.origin.vectorTo(p)
    ax = g.axis.copy()
    ax.normalize()
    ax.scaleBy(v.dotProduct(ax))
    v.subtract(ax)
    return n.dotProduct(v) < 0


def _parallel(a, b, tol=1e-6):
    return abs(abs(a[0] * b[0] + a[1] * b[1] + a[2] * b[2]) - 1) < tol


def cavities(body, edges, access):
    """Group faces joined by concave/tangent edges (plus isolated concave cylinders)
    into cavities and measure each one along the direction it is machined from."""
    faces = {f.tempId: f for f in body.faces}
    adj = {k: set() for k in faces}
    for c in edges.values():
        if c['kind'] in ('concave', 'tangent'):
            adj[c['f1']].add(c['f2'])
            adj[c['f2']].add(c['f1'])
    comps, seen = [], set()
    for k in faces:
        if k in seen:
            continue
        if not adj[k] and not _concave_cylinder(faces[k]):
            continue
        stack, comp = [k], set()
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            comp.add(x)
            stack.extend(adj[x] - seen)
        comps.append(comp)

    # Holes that cross other holes are split into several cylinder faces that are
    # not joined by concave edges (the crossing edges are convex). Merge components
    # whose concave cylinders are coaxial with the same radius: one drilled hole.
    def cyl_key(f):
        g = f.geometry
        ax = g.axis.copy()
        ax.normalize()
        if (ax.x, ax.y, ax.z) < (0, 0, 0):
            ax.scaleBy(-1)
        o = g.origin
        # project the origin onto the plane through 0 normal to the axis
        s = o.x * ax.x + o.y * ax.y + o.z * ax.z
        p = (o.x - s * ax.x, o.y - s * ax.y, o.z - s * ax.z)
        return (round(ax.x, 5), round(ax.y, 5), round(ax.z, 5),
                round(p[0], 4), round(p[1], 4), round(p[2], 4), round(g.radius, 5))

    # Only when the stretch between the two segments is void (a crossing hole, a
    # pocket): two blind holes drilled from opposite faces on the same axis are
    # coaxial too, but solid material separates them.
    def interval(comp, key):
        ax = C.Vector3D.create(*key[:3])
        o = C.Point3D.create(*key[3:6])
        ts = [o.vectorTo(v.geometry).dotProduct(ax) for i in comp
              if _concave_cylinder(faces[i]) and cyl_key(faces[i]) == key for v in faces[i].vertices]
        return (min(ts), max(ts)) if ts else None

    def void_between(key, ia, ib):
        lo, hi = (ia, ib) if ia[1] <= ib[0] else (ib, ia)
        if lo[1] >= hi[0] - 1e-6:
            return True  # segments touch or overlap
        ax, o = key[:3], key[3:6]
        inside = adsk.fusion.PointContainment.PointInsidePointContainment
        for k in range(1, 6):
            t = lo[1] + (hi[0] - lo[1]) * k / 6
            q = C.Point3D.create(o[0] + ax[0] * t, o[1] + ax[1] * t, o[2] + ax[2] * t)
            if body.pointContainment(q) == inside:
                return False
        return True

    merged = True
    while merged:
        merged = False
        keys = [{cyl_key(faces[i]) for i in c if _concave_cylinder(faces[i])} for c in comps]
        for a in range(len(comps)):
            for b in range(a + 1, len(comps)):
                shared = keys[a] & keys[b]
                if any(void_between(k, interval(comps[a], k), interval(comps[b], k)) for k in shared):
                    comps[a] |= comps.pop(b)
                    merged = True
                    break
            if merged:
                break

    out = []
    for comp in comps:
        fs = [faces[i] for i in comp]
        # Machining direction. Reaching the faces is not enough: an open step that
        # runs the whole part length is "reachable" looking down its length (+X),
        # but it is machined from the side that sees its floor. Rank directions by
        # (1) faces reached, (2) a planar floor facing the tool (normal == d),
        # (3) smallest depth along d, (4) +Z first.
        order = ['+Z', '-Z', '+X', '-X', '+Y', '-Y']
        score = {d: sum(1 for i in comp if d in access['faces'][i]['dirs']) for d in order}

        def has_floor(d):
            t = DIRS[d]
            for f in fs:
                if short(f.geometry) == 'Plane':
                    _, n = f.evaluator.getNormalAtPoint(f.pointOnFace)
                    if n.x * t[0] + n.y * t[1] + n.z * t[2] > 1 - 1e-6:
                        return True
            return False

        def extent(d):
            idx = AXIS_INDEX[d[1]]
            return max(_bb(f)[1][idx] for f in fs) - min(_bb(f)[0][idx] for f in fs)

        axis = max(order, key=lambda d: (score[d], has_floor(d), -round(extent(d), 6), -order.index(d)))
        reach_all = score[axis] == len(comp)
        if score[axis] == 0:
            axis = None
        cav = {'faces': sorted(comp), 'n_faces': len(comp), 'axis': axis,
               'all_faces_reachable_from_axis': reach_all}
        if axis:
            t = DIRS[axis]
            idx = AXIS_INDEX[axis[1]]
            sign = 1 if axis[0] == '+' else -1
            body_faces = [f for f in fs if short(f.geometry) != 'Cone']
            lo = min(_bb(f)[0][idx] for f in body_faces or fs)
            hi = max(_bb(f)[1][idx] for f in body_faces or fs)
            lo_all = min(_bb(f)[0][idx] for f in fs)
            hi_all = max(_bb(f)[1][idx] for f in fs)
            others = [i for i in range(3) if i != idx]
            ext = [max(_bb(f)[1][i] for f in fs) - min(_bb(f)[0][i] for f in fs) for i in others]
            cyl = [f for f in fs if _concave_cylinder(f) and _parallel(
                (f.geometry.axis.x, f.geometry.axis.y, f.geometry.axis.z), t)]
            radii = sorted({round(f.geometry.radius * 10, 4) for f in cyl})
            sharp = [c for c in edges.values() if c['f1'] in comp and c['f2'] in comp
                     and c['kind'] == 'concave' and c['line'] and _parallel(c['dir'], t)]
            floor = [f for f in fs if short(f.geometry) == 'Plane'
                     and _parallel((f.geometry.normal.x, f.geometry.normal.y, f.geometry.normal.z), t)]
            is_hole = (len({cyl_key(f) for f in cyl}) == 1 and abs(max(ext) - 2 * cyl[0].geometry.radius) < 1e-4
                       and all(short(f.geometry) in ('Cylinder', 'Cone', 'Plane') for f in fs))
            r_min = 0.0 if sharp else (radii[0] if radii else None)
            depth = mm(hi - lo)
            cav.update({
                'kind': 'hole' if is_hole else 'pocket/slot/step',
                'through': not floor and not any(short(f.geometry) == 'Cone' for f in fs),
                'depth_mm': depth, 'depth_with_tip_mm': mm(hi_all - lo_all),
                'opening_min_mm': mm(min(ext)), 'opening_max_mm': mm(max(ext)),
                'internal_radii_mm': radii, 'sharp_internal_edges': len(sharp),
                'min_internal_radius_mm': r_min,
                'depth_over_tool_d': round(depth / (2 * r_min), 2) if r_min else None,
                'depth_over_opening': round(depth / mm(min(ext)), 2) if min(ext) > 1e-9 else None,
                'hole_d_mm': round(2 * cyl[0].geometry.radius * 10, 4) if is_hole else None,
                'hole_L_over_D': round(depth / (2 * cyl[0].geometry.radius * 10), 2) if is_hole else None,
            })
        out.append(cav)
    return out
