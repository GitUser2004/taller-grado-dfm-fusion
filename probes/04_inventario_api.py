# Sondeo 04 - Inventario: qué datos entrega la API de Fusion 360 DURANTE el diseño.
# Se ejecuta dentro de Fusion con ClaudeBridge:
#   python tools/fusion_bridge.py probes/04_inventario_api.py --timeout 600
#
# Construye la pieza de prueba operación por operación, como lo haría el diseñador:
#   0 parámetros -> 1 bloque -> 2 cajera (esquinas vivas) -> 3 redondeo r = 1 -> 4 agujero
#   -> 5 edición: r_corner 1 -> 3 mm
# y después de cada paso registra cada dato disponible con la llamada de la API que lo da,
# ordenado por las capas de la matriz de trazabilidad:
#   operación -> parámetros -> entidades B-Rep -> mediciones -> reglas (catálogo)
# Al final, la sensibilidad: qué parámetro mueve cada cara clave.
# Resultado: probes/04_inventario_fusion.result.json
import importlib
import json
import os
import sys
import time

ROOT_DIR = r'C:\taller\taller-grado-dfm-fusion'
if os.path.join(ROOT_DIR, 'src') not in sys.path:
    sys.path.insert(0, os.path.join(ROOT_DIR, 'src'))
import dfm.analysis
import dfm.catalog
import dfm.provenance
import dfm.metrics
for _m in (dfm.analysis, dfm.catalog, dfm.provenance, dfm.metrics):
    importlib.reload(_m)
an, prov, metrics = dfm.analysis, dfm.provenance, dfm.metrics

V = adsk.core.ValueInput.createByString
P = adsk.core.Point3D.create
F = adsk.fusion


def safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def short(obj):
    return obj.objectType.split('::')[-1] if obj else None


mm = lambda cm: round(cm * 10, 4)

# ------------------------------------------------------------------ documento
app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
design = F.Design.cast(app.activeProduct)
design.designType = F.DesignTypes.ParametricDesignType
design.attributes.add('ClaudeBridge', 'model', 'inventario04')
root = design.rootComponent
ext = root.features.extrudeFeatures
tracker = prov.ProvenanceTracker(design)
OUT = {'cad': 'Fusion 360 ' + app.version, 'pieza': 'bloque 80x50x30, cajera 40x20x25, redondeo r_corner, agujero 6x20',
       'pasos': []}


def command_done():
    """Lo que haría el complemento en ui.commandTerminated: actualizar la procedencia."""
    return tracker.update()


# --------------------------------------------------------------- inventario
def snapshot(n, accion, feature=None, edited=None):
    t0 = time.perf_counter()
    rows = []

    def D(capa, dato, valor, api):
        rows.append({'capa': capa, 'dato': dato, 'valor': valor, 'api': api})

    mode = command_done()
    body = root.bRepBodies.item(0) if root.bRepBodies.count else None

    # 1. Operación
    if feature is not None:
        item = feature.timelineObject
        D('operacion', 'op.nombre', item.name, 'TimelineObject.name')
        D('operacion', 'op.tipo', short(feature), 'TimelineObject.entity.objectType')
        D('operacion', 'op.indice', item.index, 'TimelineObject.index')
        D('operacion', 'op.estado', {'health': item.healthState,
                                     'mensaje': safe(lambda: item.errorOrWarningMessage) or ''},
          'TimelineObject.healthState / errorOrWarningMessage')
    if edited:
        D('operacion', 'op.edicion', edited, 'UserParameter.expression (asignación)')
    D('operacion', 'op.evento', 'ui.commandTerminated (solo comandos de la interfaz; desde un script no hay evento: '
      'el complemento compara la firma de la línea de tiempo)', 'UserInterface.commandTerminated')
    D('operacion', 'op.modo_procedencia', mode, 'derivado: firma de la línea de tiempo (ítems, marcador, parámetros)')

    # 2. Parámetros
    D('parametros', 'par.usuario',
      [{'nombre': p.name, 'expresion': p.expression, 'valor_mm': mm(p.value),
        'lo_usan': [q.name for q in p.dependentParameters]} for p in design.userParameters],
      'Design.userParameters -> name, expression, value, dependentParameters')
    if feature is not None:
        own = prov.feature_parameters(design, feature)
        D('parametros', 'par.operacion',
          [{'nombre': p['name'], 'rol': p['role'], 'expresion': p['expression'], 'depende_de': p['drives']}
           for p in own],
          'ModelParameter.createdBy == operación -> name, role, expression, dependencyParameters')
        prof = safe(lambda: feature.profile)
        sk = safe(lambda: prof.parentSketch) if prof is not None and short(prof) == 'Profile' else None
        if sk is not None:
            D('parametros', 'par.cotas_croquis',
              {'croquis': sk.name, 'totalmente_definido': safe(lambda: sk.isFullyConstrained),
               'cotas': [{'nombre': d.parameter.name, 'expresion': d.parameter.expression, 'tipo': short(d)}
                         for d in sk.sketchDimensions if safe(lambda: d.parameter)]},
              'Profile.parentSketch.sketchDimensions[].parameter; Sketch.isFullyConstrained')

    # 3. Entidades B-Rep
    if body is not None:
        D('brep', 'brep.cuerpo', {'caras': body.faces.count, 'aristas': body.edges.count,
                                  'vertices': body.vertices.count, 'volumen_mm3': round(body.volume * 1000, 3)},
          'BRepBody.faces/edges/vertices.count, volume')
    if feature is not None and body is not None:
        native = safe(lambda: list(feature.faces), [])
        D('brep', 'brep.caras_de_la_operacion', len(native), 'Feature.faces (solo las que la operación CREÓ)')
        created, modified = [], []
        for f in body.faces:
            rec = tracker.record(f)
            if not rec:
                continue
            if rec['origin'] == feature.timelineObject.name:
                created.append(f)
            elif feature.timelineObject.name in rec['modified_by']:
                modified.append((f, rec))
        D('brep', 'brep.caras_creadas', len(created), 'rastreador de procedencia (entityToken entre estados)')
        D('brep', 'brep.caras_modificadas',
          [{'tipo': short(f.geometry), 'creada_por': r['origin'], 'area_mm2': round(f.area * 100, 3)}
           for f, r in modified],
          'NO hay API: rastreador (findEntityByToken + huella de área, aristas, bucles y caja)')
        geo = []
        for f in created[:12]:
            g = f.geometry
            info = {'tipo': short(g), 'area_mm2': round(f.area * 100, 3)}
            if short(g) == 'Cylinder':
                info.update({'radio_mm': mm(g.radius), 'concava': an._concave_cylinder(f)})
            elif short(g) == 'Plane':
                info['normal'] = [round(c, 3) for c in g.normal.asArray()]
            role = prov._face_role(feature, f)
            info['rol'] = role
            geo.append(info)
        D('brep', 'brep.geometria_caras', geo,
          'BRepFace.geometry (Plane/Cylinder/Cone), area, evaluator.getNormalAtPoint; '
          'Feature.startFaces/endFaces/sideFaces')
        if created:
            tok = created[0].entityToken
            D('brep', 'brep.id_persistente', {'longitud_token': len(tok),
                                              'resuelve': len(design.findEntityByToken(tok)),
                                              'tempId_estable': False},
              'BRepFace.entityToken / Design.findEntityByToken (tempId cambia al recalcular)')

    # 4 y 5. Mediciones y reglas (motor + catálogo)
    if body is not None:
        rep = metrics.measure(design, tracker, trace_limit=2)
        D('mediciones', 'med.validez', dict(rep['topology'], valido=rep['topology_valid']),
          'BRepBody.isSolid, lumps, shells.isClosed/isVoid, BRepEdge.faces.count (sin verificador nativo)')
        D('mediciones', 'med.aristas', dict(rep['edges'], api_concavas=body.concaveEdges.count,
                                            api_convexas=body.convexEdges.count),
          'propio: ángulo diedro con evaluator.getNormalAtPoint; nativo: BRepBody.concaveEdges/convexEdges')
        D('mediciones', 'med.cavidades',
          [{k: c.get(k) for k in ('kind', 'axis', 'depth_mm', 'opening_min_mm', 'min_internal_radius_mm',
                                  'sharp_internal_edges', 'depth_over_tool_d', 'depth_over_opening',
                                  'hole_d_mm', 'hole_L_over_D', 'origins')} for c in rep['cavities']],
          'grafo de adyacencia (BRepEdge.faces) + Cylinder.radius + MeasureManager.measureMinimumDistance')
        D('mediciones', 'med.pared_min_mm', rep['min_wall_mm'],
          'findBRepUsingRay (rayos) + measureMinimumDistance + BRepBody.pointContainment')
        D('mediciones', 'med.accesibilidad', {'montajes': rep['setups'], 'caras_inalcanzables': rep['unreachable_faces']},
          'Component.findBRepUsingRay desde ±X, ±Y, ±Z')
        D('reglas', 'regla.hallazgos',
          [{'regla': f['rule_id'], 'severidad': f['severity'], 'valor': f['value'], 'umbral': f['threshold'],
            'categoria': f['category'],
            'origen': f['trace'][0]['origin'] if f['trace'] else None,
            'parametros': sorted({p['expr'] for t in f['trace'] for p in t['parameters']})}
           for f in rep['findings']],
          'catalog.json + metrics.measure (traza: rastreador + ModelParameter.createdBy)')
        D('reglas', 'regla.resumen', rep['summary'], '')

    OUT['pasos'].append({'paso': n, 'accion': accion, 'tiempo_ms': round((time.perf_counter() - t0) * 1000, 1),
                         'datos': rows})


# ------------------------------------------------------------- 0. parámetros
for n, v in [('block_L', '80 mm'), ('block_W', '50 mm'), ('block_H', '30 mm'), ('pocket_L', '40 mm'),
             ('pocket_W', '20 mm'), ('pocket_D', '25 mm'), ('r_corner', '1 mm'),
             ('hole_d', '6 mm'), ('hole_depth', '20 mm')]:
    design.userParameters.add(n, V(v), 'mm', '')
snapshot(0, 'Parámetros de usuario creados (sin geometría)')

# ------------------------------------------------------------------ 1. bloque
sk = root.sketches.add(root.xYConstructionPlane)
sk.name = 'Block sketch'
lines = sk.sketchCurves.sketchLines.addTwoPointRectangle(P(0, 0, 0), P(8, 5, 0))
sk.geometricConstraints.addCoincident(lines.item(0).startSketchPoint, sk.originPoint)
sk.sketchDimensions.addDistanceDimension(lines.item(0).startSketchPoint, lines.item(0).endSketchPoint,
                                         F.DimensionOrientations.HorizontalDimensionOrientation,
                                         P(4, -1, 0)).parameter.expression = 'block_L'
sk.sketchDimensions.addDistanceDimension(lines.item(1).startSketchPoint, lines.item(1).endSketchPoint,
                                         F.DimensionOrientations.VerticalDimensionOrientation,
                                         P(9, 2.5, 0)).parameter.expression = 'block_W'
command_done()
ei = ext.createInput(sk.profiles.item(0), F.FeatureOperations.NewBodyFeatureOperation)
ei.setDistanceExtent(False, V('block_H'))
block = ext.add(ei)
block.name = 'Block'
snapshot(1, 'Operación nueva: bloque (croquis + extrusión)', block)

# ------------------------------------------------------------------ 2. cajera
pl_in = root.constructionPlanes.createInput()
pl_in.setByOffset(root.xYConstructionPlane, V('block_H'))
top_plane = root.constructionPlanes.add(pl_in)
command_done()
sk2 = root.sketches.add(top_plane)
sk2.name = 'Pocket sketch'
rect = sk2.sketchCurves.sketchLines.addTwoPointRectangle(P(2, 1.5, 0), P(6, 3.5, 0))
d2 = sk2.sketchDimensions
d2.addDistanceDimension(rect.item(0).startSketchPoint, rect.item(0).endSketchPoint,
                        F.DimensionOrientations.HorizontalDimensionOrientation, P(4, 0.8, 0)).parameter.expression = 'pocket_L'
d2.addDistanceDimension(rect.item(1).startSketchPoint, rect.item(1).endSketchPoint,
                        F.DimensionOrientations.VerticalDimensionOrientation, P(6.8, 2.5, 0)).parameter.expression = 'pocket_W'
proj = sk2.project(root.originConstructionPoint).item(0)
d2.addDistanceDimension(proj, rect.item(0).startSketchPoint, F.DimensionOrientations.HorizontalDimensionOrientation,
                        P(1, 0.5, 0)).parameter.expression = '(block_L - pocket_L) / 2'
d2.addDistanceDimension(proj, rect.item(0).startSketchPoint, F.DimensionOrientations.VerticalDimensionOrientation,
                        P(0.5, 1, 0)).parameter.expression = '(block_W - pocket_W) / 2'
command_done()
ci = ext.createInput(sk2.profiles.item(0), F.FeatureOperations.CutFeatureOperation)
ci.setOneSideExtent(F.DistanceExtentDefinition.create(V('pocket_D')), F.ExtentDirections.NegativeExtentDirection)
pocket = ext.add(ci)
pocket.name = 'Pocket'
snapshot(2, 'Operación nueva: cajera con esquinas vivas', pocket)

# ----------------------------------------------------------------- 3. redondeo
edges = adsk.core.ObjectCollection.create()
seen = set()
for face in pocket.sideFaces:
    for e in face.edges:
        a, b = e.startVertex.geometry, e.endVertex.geometry
        if abs(a.x - b.x) < 1e-6 and abs(a.y - b.y) < 1e-6 and e.tempId not in seen:
            seen.add(e.tempId)
            edges.add(e)
fi = root.features.filletFeatures.createInput()
fi.edgeSetInputs.addConstantRadiusEdgeSet(edges, V('r_corner'), True)
fillet = root.features.filletFeatures.add(fi)
fillet.name = 'Pocket corners'
snapshot(3, 'Operación nueva: redondeo de las 4 esquinas verticales (r_corner = 1 mm)', fillet)

# ------------------------------------------------------------------ 4. agujero
body = root.bRepBodies.item(0)
top_face = max((f for f in body.faces if short(f.geometry) == 'Plane'), key=lambda f: f.centroid.z)
hi = root.features.holeFeatures.createSimpleInput(V('hole_d'))
hi.setPositionByPoint(top_face, P(1.2, 1.2, top_face.centroid.z))
hi.setDistanceExtent(V('hole_depth'))
hole = root.features.holeFeatures.add(hi)
hole.name = 'Hole'
app.activeViewport.fit()
snapshot(4, 'Operación nueva: agujero simple Ø6 x 20', hole)

# ------------------------------------------------------- 5. edición de parámetro
design.userParameters.itemByName('r_corner').expression = '3 mm'
adsk.doEvents()
snapshot(5, 'Edición: r_corner 1 -> 3 mm (cambia una operación anterior)', fillet, edited='r_corner = 3 mm')

# ------------------------------------------------- 6. sensibilidad: parámetro -> cara
t0 = time.perf_counter()
body = root.bRepBodies.item(0)
targets = {}
for f in body.faces:
    rec = tracker.record(f)
    if not rec:
        continue
    if rec['origin'] == 'Pocket corners' and an._concave_cylinder(f) and 'radio_esquina' not in targets:
        targets['radio_esquina'] = f
    elif rec['origin'] == 'Pocket' and prov._face_role(pocket, f) == 'endFaces':
        targets['fondo_cajera'] = f
    elif rec['origin'] == 'Hole' and short(f.geometry) == 'Cylinder':
        targets['pared_agujero'] = f
sens = {}
for key, f in targets.items():
    s = prov.sensitivity(design, f)
    sens[key] = {'probados': s['tested'], 'restaurado': s['restored'],
                 'parametros_que_la_mueven': [{'parametro': e['parameter'], 'expresion': e['expression'],
                                               'rol': e['role'], 'efecto': e['effect'], 'estado': e['status']}
                                              for e in s['effects']]}
OUT['sensibilidad'] = {'api': 'Parameter.value (+1 %) -> recálculo -> findEntityByToken -> medir -> restaurar',
                       'tiempo_ms': round((time.perf_counter() - t0) * 1000, 1), 'caras': sens}

with open(os.path.join(ROOT_DIR, 'probes', '04_inventario_fusion.result.json'), 'w', encoding='utf-8') as fh:
    json.dump(OUT, fh, indent=1, ensure_ascii=False, default=str)
result = {'pasos': [(p['paso'], p['tiempo_ms'],
                     next((d['valor'] for d in p['datos'] if d['dato'] == 'regla.resumen'), None))
                    for p in OUT['pasos']],
          'sensibilidad': {k: [e['parametro'] for e in v['parametros_que_la_mueven']] for k, v in sens.items()}}
