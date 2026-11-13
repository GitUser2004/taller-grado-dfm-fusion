# Defect injection on the modelled parts. Runs INSIDE Fusion via ClaudeBridge:
#   python tools/fusion_bridge.py tools/inject_defects.py --timeout 900
# For every case: measure -> inject (parameter change or suppressed feature) ->
# measure -> revert -> measure. A case passes when the expected rule appears only
# after the injection, its trace reaches the injected parameter/feature, and the
# revert brings the findings back to the baseline.
# Parts must be open (models/*.py). Writes models/metrics/injection_results.json.
import importlib
import json
import os
import sys
import time

ROOT_DIR = r'C:\taller\taller-grado-dfm-fusion'
if os.path.join(ROOT_DIR, 'src') not in sys.path:
    sys.path.insert(0, os.path.join(ROOT_DIR, 'src'))
import dfm.analysis
import dfm.provenance
import dfm.metrics
for _m in (dfm.analysis, dfm.provenance, dfm.metrics):
    importlib.reload(_m)
prov, metrics = dfm.provenance, dfm.metrics

# (id, part tag, kind, target, new value, expected rule or None, expected severity, trace key, description)
CASES = [
    ('A', 'vise_base', 'param', 'vb_cb_R', '0.015 in', 'internal_radius', 'error', 'vb_cb_R',
     'Radio de la cajera inferior R.250 -> R.015 (0,38 mm, menor que cualquier fresa comun)'),
    ('B', 'vise_base', 'suppress', 'Cajera inferior - radios R.250', None, 'internal_radius', 'error', 'Cajera inferior',
     'Se suprime el redondeo: la cajera queda con esquinas verticales vivas (r = 0)'),
    # C and F leave 0,64 mm: between the catalogue's feasible (0,5) and recommended (0,8) wall -> warning
    ('C', 'vise_base', 'param', 'vb_cb_D', '1.225 in', 'wall_thickness', 'warning', 'vb_cb_D',
     'Cajera inferior .688 -> 1.225 de profundidad: deja 0,64 mm hasta la cara superior'),
    ('D', 'tap_guide', 'param', 'tg_d1', '0.040 in', 'hole_aspect', 'error', 'tg_d1',
     'Agujero 1 de .136 a .040 (1 mm): L/D = 16'),
    ('E', 'superblock_123', 'param', 'sb_cb', '0.480 in', 'wall_thickness', 'error', 'sb_cb',
     'Cajas de .375 a .480 con paso .500: pared de 0,51 mm entre cajas vecinas'),
    ('E2', 'superblock_123', 'param', 'sb_pitch', '0.400 in', None, None, None,
     'Control: sb_pitch existe pero las posiciones se dibujaron fijas; no debe cambiar nada'),
    ('F', 'edge_clamp', 'param', 'ec_cb_w', '1.200 in', 'wall_thickness', 'warning', 'ec_cb_w',
     'Caja de la ranura .800 -> 1.200 en un cuerpo de 1.250: paredes de 0,64 mm'),
    ('H', 'vee_block', 'suppress', 'Alivio V superior', None, None, None, None,
     'Control: sin la ranura de alivio la V queda con arista viva HORIZONTAL (la hace una fresa en V)'),
]


def find_design(tag):
    for doc in app.documents:
        d = adsk.fusion.Design.cast(doc.products.itemByProductType('DesignProductType'))
        a = d and d.attributes.itemByName('ClaudeBridge', 'model')
        if a and a.value == tag:
            return doc, d
    return None, None


def key(f):
    origin = f['trace'][0]['origin'] if f.get('trace') else None
    return (f['rule'], f['severity'], origin)


def findings_keys(report):
    return sorted(key(f) for f in report['findings'])


def traced_to(finding, target):
    for t in finding.get('trace', []):
        if target in (t.get('origin') or '') or any(target in m for m in (t.get('modified_by') or [])):
            return True
        if any(target in (p.get('expr') or '') for p in t.get('parameters', [])):
            return True
    return False


def short_finding(f):
    t = f['trace'][0] if f.get('trace') else {}
    return {'rule': f['rule'], 'severity': f['severity'], 'value': f['value'], 'threshold': f.get('threshold'),
            'faces': f['faces'], 'origin': t.get('origin'), 'modified_by': t.get('modified_by'),
            'parameters': sorted({p['expr'] for tr in f.get('trace', []) for p in tr.get('parameters', [])})}


results = []
for cid, tag, kind, target, value, rule, severity, trace_key, desc in CASES:
    out = {'case': cid, 'part': tag, 'kind': kind, 'target': target, 'value': value, 'description': desc}
    try:
        doc, design = find_design(tag)
        if not design:
            raise RuntimeError('part {} not open'.format(tag))
        doc.activate()
        tracker = prov.ProvenanceTracker(design)
        base = metrics.measure(design, tracker, trace_limit=10)

        if kind == 'param':
            p = design.userParameters.itemByName(target)
            old = p.expression
            p.expression = value
            undo = lambda: setattr(p, 'expression', old)
        else:
            item = next(t for t in design.timeline if t.name == target)
            item.isSuppressed = True
            undo = lambda: setattr(item, 'isSuppressed', False)
        t0 = time.perf_counter()
        inj = metrics.measure(design, tracker, trace_limit=10)
        detect_s = round(time.perf_counter() - t0, 2)
        undo()
        rev = metrics.measure(design, tracker, trace_limit=10)

        base_keys = findings_keys(base)
        pool = list(base_keys)
        new = []
        for f in inj['findings']:
            k = key(f)
            if k in pool:
                pool.remove(k)
            else:
                new.append(f)
        if rule:
            hits = [f for f in new if f['rule'] == rule and f['severity'] == severity]
            detected = bool(hits)
            traced = any(traced_to(f, trace_key) for f in hits)
        else:
            hits, detected, traced = [], not new, None  # controls pass when nothing new appears
        out.update({
            'baseline': base['summary'], 'injected': inj['summary'], 'reverted': rev['summary'],
            'new_findings': [short_finding(f) for f in new],
            'expected': '{} {}'.format(severity, rule) if rule else 'no new findings',
            'detected': detected, 'traced_to_target': traced,
            'revert_restores_baseline': findings_keys(rev) == base_keys,
            'geometry_changed': (base['body']['volume_mm3'] != inj['body']['volume_mm3']
                                 or base['body']['faces'] != inj['body']['faces']),
            'volume_mm3': [base['body']['volume_mm3'], inj['body']['volume_mm3']],
            'detection': {'provenance_mode': inj['timing_s']['provenance_mode'],
                          'provenance_s': inj['timing_s']['provenance_s'],
                          'analysis_s': inj['timing_s']['analysis_s'], 'total_s': detect_s},
        })
        out['passed'] = bool(detected and (traced is not False) and out['revert_restores_baseline'])
    except Exception:
        import traceback
        out['error'] = traceback.format_exc()[-1500:]
        out['passed'] = False
    results.append(out)

os.makedirs(os.path.join(ROOT_DIR, 'models', 'metrics'), exist_ok=True)
with open(os.path.join(ROOT_DIR, 'models', 'metrics', 'injection_results.json'), 'w', encoding='utf-8') as fh:
    json.dump(results, fh, indent=2, ensure_ascii=False, default=str)
result = {'passed': sum(r['passed'] for r in results), 'total': len(results),
          'cases': [(r['case'], r['passed'], r.get('error', '')[-300:]) for r in results]}
