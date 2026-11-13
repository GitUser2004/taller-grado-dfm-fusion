"""Measure a part and apply the rule catalogue, tracing every finding.

measure(design, tracker=None, profile='metal', overrides=None) -> report dict (no file I/O).
Used by tools/run_metrics.py (one part) and tools/inject_defects.py (defect cases).
Thresholds, severities, categories and sources come from catalog.json
(docs/catalogo_reglas.md); nothing numeric about the rules is hard-coded here.
"""

import time

from . import analysis as an
from . import catalog as catmod
from . import provenance as prov

# Flat view of the default (metal) profile, kept for scripts that only print thresholds.
DEFAULT_THRESHOLDS = catmod.Catalog('metal').values


def trace_summary(tracker, face):
    t = tracker.trace(face) or {}
    c = t.get('controls', {})
    params = [{'name': p['name'], 'expr': p['expression'], 'role': p['role']} for p in c.get('parameters', [])]
    for cur in c.get('sketch_curves', []):
        for d in cur['dimensions']:
            params.append({'name': d['name'], 'expr': d['expression'], 'role': d['dimension'],
                           'sketch': cur['sketch']})
    return {'origin': t.get('origin'), 'modified_by': t.get('modified_by'),
            'face_role': c.get('face_role'), 'parametric': c.get('parametric'), 'parameters': params,
            'sketch_curves_without_dims': [cur['curve'] for cur in c.get('sketch_curves', []) if not cur['dimensions']]}


def main_body(design):
    return max(design.rootComponent.bRepBodies, key=lambda b: b.volume)


def _exceeds(value, op, limit):
    if limit is None or value is None:
        return False
    return value < limit if op == '<' else value > limit


def measure(design, tracker=None, profile='metal', overrides=None, trace_limit=3, catalog=None):
    cat = catalog or catmod.Catalog(profile, overrides)
    root = design.rootComponent
    T = {}
    t0 = time.perf_counter()
    if tracker is None:
        tracker = prov.ProvenanceTracker(design)
        tracker.rebuild()
        T['provenance_mode'] = 'rebuild'
    else:
        T['provenance_mode'] = tracker.update()
    T['provenance_s'] = round(time.perf_counter() - t0, 3)

    body = main_body(design)  # rollTo invalidates references: fetch after provenance
    faces = {f.tempId: f for f in body.faces}
    t0 = time.perf_counter()
    topo = an.topology(body, cat.th('topological_validity', 'short_edge_mm'),
                       cat.th('topological_validity', 'tiny_face_mm2'))
    edges = an.classify_edges(body)
    access = an.accessibility(root, body, min_free=cat.th('accessibility', 'min_free'))
    thick = an.thickness(root, body)
    cavs = an.cavities(body, edges, access)
    T['analysis_s'] = round(time.perf_counter() - t0, 3)

    findings = []

    def add(rule_id, severity, value, threshold, face_ids, note='', rule_name=None):
        findings.append(dict({'rule': rule_name or rule_id, 'rule_id': rule_id, 'severity': severity,
                              'value': value, 'threshold': threshold, 'note': note, 'faces': len(face_ids),
                              'trace': [trace_summary(tracker, faces[i]) for i in sorted(face_ids)[:trace_limit]]},
                             **cat.meta(rule_id)))

    def leveled(rule_id, value, face_ids, note='', scale=1.0, rule_name=None):
        """Apply the rule's error level first, then warning. `scale` turns a ratio threshold into a value."""
        for level in ('error', 'warning'):
            spec = cat.rule(rule_id)['niveles'].get(level)
            limit = cat.th(rule_id, level)
            if spec and limit is not None and _exceeds(value, spec['op'], limit * scale):
                add(rule_id, level, value, round(limit * scale, 4), face_ids, note, rule_name)
                return level
        return None

    # --- diseño preliminar ---------------------------------------------------------------
    bad = {k: v for k, v in topo.items() if k in ('open_shells', 'void_shells', 'open_edges', 'non_manifold_edges',
                                                  'short_edges', 'tiny_faces') and v}
    topo_ok = topo['is_solid'] and topo['lumps'] == 1 and not bad and root.bRepBodies.count == 1
    if not topo_ok:
        findings.append(dict({'rule': 'topological_validity', 'rule_id': 'topological_validity', 'severity': 'error',
                              'value': dict(bad, bodies=root.bRepBodies.count, lumps=topo['lumps']),
                              'faces': 0, 'trace': []}, **cat.meta('topological_validity')))
    unhealthy = [(t.name, t.healthState) for t in design.timeline
                 if t.healthState != 0 and not t.isSuppressed]
    if unhealthy:
        findings.append(dict({'rule': 'feature_health', 'rule_id': 'feature_health', 'severity': 'error',
                              'value': unhealthy, 'faces': 0, 'trace': []}, **cat.meta('feature_health')))
    unused = [p.name for p in design.userParameters if p.dependentParameters.count == 0]

    # --- proceso ---------------------------------------------------------------------------
    for i, c in enumerate(cavs):
        c['id'] = i
        c['origins'] = sorted({tracker.record(faces[k])['origin'] for k in c['faces'] if tracker.record(faces[k])})
        if not c['axis']:
            add('accessibility', 'error', 'no axis direction reaches it', '6 axis directions', c['faces'],
                'cavity {} ({})'.format(i, ', '.join(c['origins'])))
            continue
        if c['kind'] == 'hole':
            leveled('hole_aspect', c['hole_L_over_D'], c['faces'], 'cavity {}'.format(i))
            leveled('hole_diameter', c['hole_d_mm'], c['faces'], 'cavity {}'.format(i))
            continue
        r, depth = c['min_internal_radius_mm'], c['depth_mm']
        radius_faces = [k for k in c['faces'] if an._concave_cylinder(faces[k])] or c['faces']
        if r is not None:
            hit = leveled('internal_radius', r, radius_faces,
                          'cavity {} ({}), sharp edges: {}'.format(i, ', '.join(c['origins']), c['sharp_internal_edges']))
            if not hit:  # r/depth is only meaningful once the absolute minimum is met
                leveled('internal_radius_depth', r, radius_faces, 'cavity {} r < depth x {}'.format(
                    i, cat.th('internal_radius_depth', 'warning')), scale=depth, rule_name='internal_radius')
            leveled('cavity_aspect_tool', c['depth_over_tool_d'], radius_faces, 'cavity {} depth / (2 r_min)'.format(i))
        leveled('cavity_aspect_opening', c['depth_over_opening'], c['faces'], 'cavity {} depth / width'.format(i))

    for level in ('error', 'warning'):
        limit = cat.th('wall_thickness', level)
        lower = cat.th('wall_thickness', 'error') if level == 'warning' else None
        thin = [k for k, v in thick.items() if limit is not None and v < limit and (lower is None or v >= lower)]
        if thin:
            add('wall_thickness', level, min(thick[k] for k in thin), limit, thin)

    cav_faces = {k for c in cavs for k in c['faces']}
    lonely = [k for k in access['unreachable'] if k not in cav_faces]
    if lonely:
        add('accessibility', 'error', '{} faces unreachable'.format(len(lonely)), '6 axis directions', lonely)

    timeline = list(design.timeline)
    return {
        'catalog': cat.summary(),
        'topology_valid': topo_ok,
        'unused_user_parameters': unused,
        'timeline_items': len(timeline),
        'features': sum(1 for t in timeline if an.short(prov._safe(lambda: t.entity)) not in prov.NON_GEOMETRIC),
        'user_parameters': design.userParameters.count,
        'body': {'faces': body.faces.count, 'edges': body.edges.count, 'volume_mm3': round(body.volume * 1000, 2)},
        'topology': topo,
        'edges': {k: sum(1 for e in edges.values() if e['kind'] == k) for k in ('concave', 'convex', 'tangent')},
        'setups': access['setups'], 'unreachable_faces': len(access['unreachable']),
        'min_wall_mm': min(thick.values()) if thick else None,
        'cavities': [{k: v for k, v in c.items() if k != 'faces'} for c in cavs],
        'provenance': {
            'faces_modified_after_creation': sum(1 for r in tracker.records['faces'].values() if r['modified_by']),
            'max_modifiers_on_one_face': max((len(r['modified_by']) for r in tracker.records['faces'].values()), default=0),
        },
        'findings': findings,
        'summary': {s: sum(1 for f in findings if f['severity'] == s) for s in ('error', 'warning')},
        'summary_by_category': {cg: {s: sum(1 for f in findings if f['category'] == cg and f['severity'] == s)
                                     for s in ('error', 'warning')} for cg in ('diseno_preliminar', 'proceso')},
        'timing_s': T,
    }
