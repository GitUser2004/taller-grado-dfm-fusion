"""Provenance tracker: for every B-Rep face and edge, which timeline feature
created it, which later features modified it, and which parameters control it.

Why it is needed (see probes/02_limites_y_tecnicas.md):
  * Feature.faces only tells the feature that CREATED a face, not the ones that
    modified it later (a pocket cut into the top face, a fillet trimming a wall).
  * tempId changes on every recompute; entityToken survives, so state is keyed
    by entityToken and re-keyed after every step.

One core operation, `_step(feature)`, carries provenance from the previous model
state to the current one and attributes every change to `feature`:
  * token of an old face resolves to 0 faces  -> the face was consumed
  * resolves to >1 faces                       -> split   (counts as modified)
  * two old faces resolve to the same face     -> merged  (counts as modified)
  * fingerprint (area, edges, loops, bbox) changed -> modified
  * face not reachable from any old token      -> created by `feature`

Two ways to drive it:
  * update()  - call after each user command. If the only change is one new
                feature at the end of the timeline it runs ONE step
                (incremental); anything else (editing an old feature, changing a
                parameter, deleting, reordering, moving the marker) triggers
  * rebuild() - replays the timeline up to the marker with rollTo, one step per
                feature, then restores the user's marker position.

Scope: Design workspace, bodies of the root component (the thesis works on a
single solid body, but nothing here assumes only one).
"""

import json

import adsk.core
import adsk.fusion

ATTR_GROUP = 'dfm'
ATTR_NAME = 'provenance'
# Timeline entities that can never change B-Rep geometry: skipped during replay.
NON_GEOMETRIC = {'Sketch', 'ConstructionPlane', 'ConstructionAxis', 'ConstructionPoint',
                 'Occurrence', 'Joint', 'AsBuiltJoint', 'JointOrigin'}
TOL = 1e-6  # cm


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def _short(obj):
    return obj.objectType.split('::')[-1] if obj else None


def _bbox(entity):
    bb = entity.boundingBox
    return [round(v * 10, 5) for v in (bb.minPoint.x, bb.minPoint.y, bb.minPoint.z,
                                       bb.maxPoint.x, bb.maxPoint.y, bb.maxPoint.z)]


def face_fingerprint(f):
    return [round(f.area * 100, 6), f.edges.count, f.loops.count] + _bbox(f)


def edge_fingerprint(e):
    return [round(e.length * 10, 6)] + _bbox(e)


class _Kind:
    """Per-entity-type plumbing so faces and edges share the same step logic."""
    def __init__(self, name, collection, fingerprint):
        self.name, self.collection, self.fingerprint = name, collection, fingerprint


FACES = _Kind('faces', lambda body: body.faces, face_fingerprint)
EDGES = _Kind('edges', lambda body: body.edges, edge_fingerprint)


class ProvenanceTracker:
    def __init__(self, design):
        self.design = design
        self.records = {'faces': {}, 'edges': {}}  # current entityToken -> record
        self.signature = None
        self.last_update = None  # {'mode': ..., 'steps': n}

    # ------------------------------------------------------------ model access
    def _bodies(self):
        return list(self.design.rootComponent.bRepBodies)

    def _entities(self, kind):
        for body in self._bodies():
            for ent in kind.collection(body):
                yield ent

    # --------------------------------------------------------------- core step
    def _step_kind(self, kind, feature_name):
        old = self.records[kind.name]
        carried = {}  # current tempId -> record under construction
        for token, rec in old.items():
            found = _safe(lambda: self.design.findEntityByToken(token), []) or []
            split = len(found) > 1
            for ent in found:
                if _short(ent) not in ('BRepFace', 'BRepEdge'):
                    continue
                cur = carried.get(ent.tempId)
                if cur is None:
                    carried[ent.tempId] = {'origin': rec['origin'],
                                           'modified_by': list(rec['modified_by']),
                                           'old_fp': rec['fp'], 'split': split, 'merged': False}
                else:  # two old entities ended up as one: keep the earliest origin
                    cur['merged'] = True
                    for m in rec['modified_by'] + [rec['origin']]:
                        if m != cur['origin'] and m not in cur['modified_by']:
                            cur['modified_by'].append(m)

        new_records = {}
        for ent in self._entities(kind):
            fp = kind.fingerprint(ent)
            cur = carried.get(ent.tempId)
            if cur is None:
                rec = {'origin': feature_name, 'modified_by': [], 'fp': fp}
            else:
                changed = cur['split'] or cur['merged'] or cur['old_fp'] != fp
                mods = cur['modified_by']
                if changed and feature_name != cur['origin'] and feature_name not in mods:
                    mods = mods + [feature_name]
                rec = {'origin': cur['origin'], 'modified_by': mods, 'fp': fp}
            new_records[ent.entityToken] = rec
        self.records[kind.name] = new_records

    def _step(self, feature_name):
        self._step_kind(FACES, feature_name)
        self._step_kind(EDGES, feature_name)

    # ------------------------------------------------------- change detection
    def _signature(self):
        tl = self.design.timeline
        items = []
        for i in range(tl.count):
            it = tl.item(i)
            ent = _safe(lambda: it.entity)
            items.append([it.name, _short(ent), bool(_safe(lambda: it.isSuppressed, False)),
                          _safe(lambda: ent.entityToken)])
        params = sorted([p.name, p.expression] for p in self.design.allParameters)
        return {'items': items, 'marker': tl.markerPosition, 'params': params}

    @staticmethod
    def _classify(old, new):
        if old is None:
            return 'rebuild'
        if old == new:
            return 'noop'
        old_params = dict(map(tuple, old['params']))
        new_params = dict(map(tuple, new['params']))
        params_kept = all(new_params.get(k) == v for k, v in old_params.items())
        if new['items'] == old['items'] and new['marker'] == old['marker'] and params_kept:
            return 'noop'  # e.g. only a new user parameter was added
        appended = (len(new['items']) == len(old['items']) + 1
                    and new['items'][:-1] == old['items']
                    and old['marker'] == len(old['items'])
                    and new['marker'] == len(new['items'])
                    and params_kept)
        return 'append' if appended else 'rebuild'

    # -------------------------------------------------------------- public API
    def update(self):
        """Call after every user command. Returns the mode that was used."""
        sig = self._signature()
        mode = self._classify(self.signature, sig)
        if mode == 'append':
            item = self.design.timeline.item(self.design.timeline.count - 1)
            self._step(item.name)
            self.last_update = {'mode': 'append', 'steps': 1}
        elif mode == 'rebuild':
            self.rebuild()
        else:
            self.last_update = {'mode': 'noop', 'steps': 0}
        self.signature = self._signature()
        return self.last_update['mode']

    def rebuild(self):
        """Replay the timeline up to the user's marker, one step per feature."""
        tl = self.design.timeline
        marker = tl.markerPosition
        self.records = {'faces': {}, 'edges': {}}
        steps = 0
        try:
            for i in range(marker):
                item = tl.item(i)
                if _safe(lambda: item.isGroup, False) or _safe(lambda: item.isSuppressed, False):
                    continue
                if _short(_safe(lambda: item.entity)) in NON_GEOMETRIC:
                    continue
                item.rollTo(False)
                self._step(item.name)
                steps += 1
        finally:
            if tl.markerPosition != marker:
                tl.markerPosition = marker
        self.signature = self._signature()
        self.last_update = {'mode': 'rebuild', 'steps': steps}

    def record(self, entity):
        kind = 'faces' if _short(entity) == 'BRepFace' else 'edges'
        return self.records[kind].get(entity.entityToken)

    def owner_feature(self, name):
        tl = self.design.timeline
        for i in range(tl.count):
            if tl.item(i).name == name:
                return _safe(lambda: tl.item(i).entity)
        return None

    def trace(self, entity):
        """Full trace for a face or edge: origin, modifiers and controlling parameters."""
        rec = self.record(entity)
        if rec is None:
            return None
        out = {'entity': _short(entity), 'geometry': _short(entity.geometry),
               'origin': rec['origin'], 'modified_by': rec['modified_by']}
        if _short(entity) == 'BRepFace':
            out['controls'] = face_controls(self.design, entity, self.owner_feature(rec['origin']))
            out['modifier_parameters'] = {
                m: [p['name'] for p in feature_parameters(self.design, self.owner_feature(m))]
                for m in rec['modified_by']}
        else:
            out['faces'] = [self.trace(f) for f in entity.faces]
        return out

    # ------------------------------------------------------------ persistence
    def save(self):
        """Store the provenance inside the document (survives save/reopen)."""
        data = json.dumps({'records': self.records, 'signature': self.signature})
        attrs = self.design.attributes
        a = attrs.itemByName(ATTR_GROUP, ATTR_NAME)
        if a:
            a.value = data
        else:
            attrs.add(ATTR_GROUP, ATTR_NAME, data)
        return len(data)

    def load(self):
        a = self.design.attributes.itemByName(ATTR_GROUP, ATTR_NAME)
        if not a:
            return False
        data = json.loads(a.value)
        self.records, self.signature = data['records'], data['signature']
        return True


# ---------------------------------------------------------------- parameters
def _param_info(p):
    return {'name': p.name, 'role': _safe(lambda: adsk.fusion.ModelParameter.cast(p).role),
            'expression': p.expression,
            'drives': _safe(lambda: [q.name for q in p.dependencyParameters], [])}


def feature_parameters(design, feature):
    """Model parameters created by a feature (its own dimensions)."""
    if feature is None:
        return []
    token = _safe(lambda: feature.entityToken)
    out = []
    for p in design.allParameters:
        mp = adsk.fusion.ModelParameter.cast(p)
        if mp and _safe(lambda: mp.createdBy.entityToken) == token:
            out.append(_param_info(mp))
    return out


def _profiles(feature):
    prof = _safe(lambda: feature.profile)
    if prof is None:
        return []
    if _short(prof) == 'ObjectCollection':
        return [prof.item(i) for i in range(prof.count)]
    return [prof]


def _curve_matches_face(curve, face):
    g = face.geometry
    kind = _short(g)
    if kind == 'Plane' and _short(curve) == 'SketchLine':
        n = g.normal
        for sp in (curve.startSketchPoint, curve.endSketchPoint):
            if abs(g.origin.vectorTo(sp.worldGeometry).dotProduct(n)) > TOL:
                return False
        return True
    if kind == 'Cylinder' and _short(curve) in ('SketchArc', 'SketchCircle'):
        if abs(curve.radius - g.radius) > TOL:
            return False
        c = curve.centerSketchPoint.worldGeometry
        v = g.origin.vectorTo(c)
        axis = g.axis.copy()
        axis.normalize()
        return v.crossProduct(axis).length < TOL  # center lies on the cylinder axis
    return False


DIM_REFS = ('entity', 'entityOne', 'entityTwo', 'line', 'lineOne', 'lineTwo', 'circleOne', 'circleTwo')


def curve_dimensions(curve):
    """Sketch dimensions that reference a curve or one of its points."""
    sketch = curve.parentSketch
    tokens = {curve.entityToken}
    for attr in ('startSketchPoint', 'endSketchPoint', 'centerSketchPoint'):
        pt = _safe(lambda: getattr(curve, attr))
        if pt:
            tokens.add(pt.entityToken)
    dims = []
    for d in sketch.sketchDimensions:
        refs = {_safe(lambda: getattr(d, a).entityToken) for a in DIM_REFS}
        if refs & tokens:
            p = _safe(lambda: d.parameter)
            if p:
                dims.append(dict(_param_info(p), dimension=_short(d)))
    return dims


def _face_role(feature, face):
    for role in ('endFaces', 'sideFaces', 'startFaces'):
        faces = _safe(lambda: list(getattr(feature, role)), None)
        if faces and any(f.tempId == face.tempId for f in faces):
            return role
    return 'faces'


def face_controls(design, face, feature):
    """Parameters (or bare sketch curves) that directly control a face of `feature`."""
    if feature is None:
        return {'note': 'origin feature not found'}
    ftype = _short(feature)
    params = feature_parameters(design, feature)
    role = _face_role(feature, face)
    out = {'feature_type': ftype, 'face_role': role}

    if ftype == 'ExtrudeFeature':
        if role == 'endFaces':
            out['parameters'] = [p for p in params if 'Distance' in (p['role'] or '')]
        elif role == 'sideFaces':
            out['parameters'] = [p for p in params if 'Taper' in (p['role'] or '')]
            curves = []
            for prof in _profiles(feature):
                for loop in prof.profileLoops:
                    for pc in loop.profileCurves:
                        c = pc.sketchEntity
                        if _curve_matches_face(c, face):
                            curves.append({'sketch': c.parentSketch.name, 'curve': _short(c),
                                           'fully_constrained': _safe(lambda: c.isFullyConstrained),
                                           'dimensions': curve_dimensions(c)})
            out['sketch_curves'] = curves
        else:
            out['parameters'] = []
            out['note'] = 'start face lies on the sketch plane'
    elif ftype == 'FilletFeature':
        out['parameters'] = [p for p in params if p['role'] and 'Radius' in p['role']]
    elif ftype == 'HoleFeature':
        if _short(face.geometry) == 'Cylinder':
            out['parameters'] = [p for p in params if p['role'] == 'HoleDiameter']
        else:
            out['parameters'] = [p for p in params if p['role'] in ('HoleDepth', 'TipAngle')]
    else:
        out['parameters'] = params
    if role == 'sideFaces' and ftype == 'ExtrudeFeature':
        # The taper angle exists on every extrude; it does not make the wall's
        # shape (line position, arc radius) parametric. Only sketch dimensions do.
        out['parametric'] = any(c['dimensions'] for c in out.get('sketch_curves', []))
    else:
        out['parametric'] = bool(out.get('parameters'))
    out['note_heuristic'] = ('dimensions are matched by shared sketch points; constraints '
                             'propagate further, use sensitivity() for the exact answer')
    return out


# --------------------------------------------------------- sensitivity analysis
def _descriptor(entity):
    """Geometric quantities a rule may care about, in mm."""
    g = entity.geometry
    d = {'area' if _short(entity) == 'BRepFace' else 'length':
         round((entity.area * 100) if _short(entity) == 'BRepFace' else entity.length * 10, 6)}
    c = entity.centroid if _short(entity) == 'BRepFace' else entity.pointOnEdge
    d['point'] = (c.x * 10, c.y * 10, c.z * 10)
    kind = _short(g)
    if kind in ('Cylinder', 'Circle3D', 'Arc3D'):
        d['radius'] = round(g.radius * 10, 6)
    elif kind == 'Plane':
        n = g.normal
        d['offset'] = round(n.dotProduct(adsk.core.Vector3D.create(g.origin.x, g.origin.y, g.origin.z)) * 10, 6)
    elif kind == 'Cone':
        d['half_angle_deg'] = round(g.halfAngle * 57.29577951308232, 6)
    return d


def independent_parameters(design):
    """Parameters whose expression does not reference another parameter: the
    values a designer (or a correction) can actually change."""
    out = []
    for p in design.allParameters:
        deps = _safe(lambda: p.dependencyParameters.count, 0)
        if deps == 0 and abs(p.value) > 1e-12:
            out.append(p)
    return out


def sensitivity(design, entity, params=None, rel=0.01):
    """Nudge each parameter by `rel`, recompute, measure the effect on `entity`
    and restore it. Returns the parameters that change the entity and how.
    Each nudge is a real recompute (adds undo steps; the value is restored)."""
    token = entity.entityToken
    base = _descriptor(entity)
    params = params if params is not None else independent_parameters(design)
    effects = []
    for p in params:
        old_expr = p.expression
        status, delta = 'ok', {}
        try:
            p.value = p.value * (1 + rel)
            found = design.findEntityByToken(token)
            if not found:
                status = 'consumed'
            else:
                now = _descriptor(found[0])
                for k, v in base.items():
                    if k == 'point':
                        dist = sum((a - b) ** 2 for a, b in zip(v, now['point'])) ** 0.5
                        if dist > 1e-6:
                            delta['moved_mm'] = round(dist, 6)
                    elif k in now and abs(now[k] - v) > 1e-6:
                        delta[k] = round(now[k] - v, 6)
                if len(found) > 1:
                    status = 'split'
        except Exception as ex:
            status = 'error: {}'.format(ex)[:120]
        finally:
            p.expression = old_expr
        if delta or status != 'ok':
            effects.append({'parameter': p.name, 'expression': old_expr,
                            'role': _safe(lambda: adsk.fusion.ModelParameter.cast(p).role),
                            'status': status, 'effect': delta})
    restored = design.findEntityByToken(token)
    return {'base': base, 'effects': effects, 'tested': len(params),
            'restored': bool(restored) and _descriptor(restored[0]) == base}
