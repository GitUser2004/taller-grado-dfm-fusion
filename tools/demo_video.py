"""Demo grabable de la primera etapa: diseño -> procedencia/mediciones -> defectos -> reporte.

    python tools/demo_video.py          (en su propia ventana de consola, al lado de Fusion)

Usa el Edge Clamp (models/edge_clamp.py) en un documento NUEVO etiquetado 'demo_edge_clamp'.
La consola narra cada paso; Fusion muestra el modelo. Cada paso deja pausas para que se vea.
Escribe los reportes en models/metrics/demo_*.json y abre el final al terminar.
"""
import json
import os
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fusion_bridge import send  # noqa: E402

ROOT = r'C:\taller\taller-grado-dfm-fusion'
TAG = 'demo_edge_clamp'
PAUSE = 2.5

PRELUDE = r'''
import sys, importlib
sys.path.insert(0, r'C:\taller\taller-grado-dfm-fusion\src')
import dfm.analysis, dfm.provenance, dfm.catalog, dfm.metrics
def _design():
    for doc in app.documents:
        d = adsk.fusion.Design.cast(doc.products.itemByProductType('DesignProductType'))
        a = d and d.attributes.itemByName('ClaudeBridge', 'model')
        if a and a.value == %r:
            doc.activate()
            return d
def _view(fit=True):
    vp = app.activeViewport
    vp.viewOrientation = adsk.core.ViewOrientations.IsoTopRightViewOrientation
    if fit:
        vp.fit()
    vp.refresh()
    adsk.doEvents()
''' % TAG


def fusion(code, timeout=300):
    r = send(PRELUDE + code, timeout=timeout)
    if not r.get('ok'):
        print('\n[ERROR en Fusion]\n', r.get('error'))
        sys.exit(1)
    return r.get('result')


def say(title, *lines):
    print('\n' + '=' * 70)
    print('  ' + title)
    print('=' * 70)
    for ln in lines:
        print('   ' + ln)
    sys.stdout.flush()


FAST = os.environ.get('DEMO_FAST') == '1'  # prueba sin pausas ni notepad


def wait(s=PAUSE):
    if not FAST:
        time.sleep(s)


def measure(label):
    """Mide la pieza, guarda el reporte y devuelve un resumen."""
    out = os.path.join(ROOT, 'models', 'metrics', 'demo_{}.json'.format(label))
    res = fusion(r'''
import json
d = _design()
rep = dfm.metrics.measure(d)
json.dump(rep, open(%r, 'w', encoding='utf-8'), indent=2, ensure_ascii=False, default=str)
result = {'summary': rep['summary'], 'min_wall_mm': rep['min_wall_mm'], 'faces': rep['body']['faces'],
          'volume_mm3': rep['body']['volume_mm3'], 'setups': [s['direction'] for s in rep['setups']],
          'cavities': [(c.get('kind'), c.get('depth_mm'), c.get('hole_d_mm') or c.get('min_internal_radius_mm')) for c in rep['cavities']],
          'findings': [(f['rule'], f['severity'], f['value'], f['threshold'],
                        (f['trace'][0]['origin'] if f['trace'] else None),
                        sorted({p['expr'] for t in f['trace'] for p in t['parameters'] if 'deg' not in p['expr']})) for f in rep['findings']],
          'time': rep['timing_s']}
''' % out)
    return res, out


def show_findings(res):
    print('   Errores: {error}  Advertencias: {warning}'.format(**res['summary']))
    print('   Pared mínima: {} mm   Montajes: {}'.format(res['min_wall_mm'], ', '.join(res['setups'])))
    for rule, sev, val, th, origin, params in res['findings']:
        print('   -> [{}] {} = {} (umbral {})'.format(sev.upper(), rule, val, th))
        print('        origen: "{}"   parámetros: {}'.format(origin, ', '.join(params) or '-'))
    print('   Tiempo: procedencia {provenance_s} s + análisis {analysis_s} s'.format(**res['time']))


def highlight(kind):
    """Selecciona (resalta en azul) las caras del defecto."""
    return fusion(r'''
d = _design()
ui.activeSelections.clear()
body = max(d.rootComponent.bRepBodies, key=lambda b: b.volume)
n = 0
if %r == 'wall':
    th = dfm.analysis.thickness(d.rootComponent, body)
    for f in body.faces:
        if th.get(f.tempId, 99) < 0.8:
            ui.activeSelections.add(f); n += 1
else:
    for f in body.faces:
        g = f.geometry
        if g.objectType.endswith('Cylinder') and g.radius * 10 < 1.0:
            ui.activeSelections.add(f); n += 1
_view(fit=False)
result = n
''' % kind)


def main():
    say('DEMO: verificación progresiva de fresado en Fusion 360',
        'Pieza: cuerpo del Edge Clamp (Make It From Metal, DWG 002)',
        'Etapas: 1) diseño paramétrico  2) procedencia y mediciones',
        '        3) inyección de defectos  4) reporte final')
    if not FAST:
        input('\n   Empieza a grabar (Win+Shift+R) y presiona ENTER para comenzar... ')

    # ---------------------------------------------------------------- 1. diseño
    say('1. DISEÑO PARAMÉTRICO', 'Se construye la pieza por script con parámetros de usuario y línea de tiempo.')
    fusion(r'''
for doc in list(app.documents):
    d = adsk.fusion.Design.cast(doc.products.itemByProductType('DesignProductType'))
    a = d and d.attributes.itemByName('ClaudeBridge', 'model')
    if a and a.value == %r:
        doc.close(False)
src = open(r'C:\taller\taller-grado-dfm-fusion\models\edge_clamp.py', encoding='utf-8').read()
src = src.replace("mlib.new_design(app, 'edge_clamp')", "mlib.new_design(app, %r)")
exec(src)
d = _design()
d.timeline.markerPosition = 0
_view()
result = [(t.name) for t in d.timeline]
''' % (TAG, TAG), timeout=180)
    items = fusion("d = _design(); result = [t.name for t in d.timeline]")
    params = fusion("d = _design(); result = [(p.name, p.expression, p.comment) for p in d.userParameters]")
    print('   Parámetros de usuario:')
    for n, e, c in params:
        print('     {:<10} {:<12} {}'.format(n, e, c))
    wait()
    print('\n   Línea de tiempo, operación por operación:')
    for i, name in enumerate(items, 1):
        print('     {:>2}. {}'.format(i, name))
        fusion('d = _design(); d.timeline.markerPosition = %d; _view(fit=%s)' % (i, 'True' if i <= 2 else 'False'))
        wait(1.2)
    wait()

    # ------------------------------------------------- 2. procedencia + mediciones
    say('2. PROCEDENCIA Y MEDICIONES (pieza sana)',
        'Se repite la línea de tiempo cara por cara (rollTo + entityToken) y se mide:',
        'validez, aristas, accesibilidad por rayos, espesor y cavidades.')
    base, base_file = measure('1_base')
    print('   Caras: {}   Volumen: {} mm3'.format(base['faces'], base['volume_mm3']))
    print('   Cavidades (tipo, profundidad mm, Ø o radio mm):')
    for c in base['cavities']:
        print('     ', c)
    show_findings(base)
    print('   Reporte: ' + base_file)
    wait(4)

    # ------------------------------------------------------ 3. defectos
    say('3a. DEFECTO: caja de la ranura .800 -> 1.200 in',
        'Se cambia el parámetro ec_cb_w; las paredes laterales quedan de 0,64 mm.')
    fusion("d = _design(); d.userParameters.itemByName('ec_cb_w').expression = '1.200 in'; _view(fit=False)")
    wait()
    r1, f1 = measure('2_pared_delgada')
    show_findings(r1)
    print('   Caras delgadas resaltadas en Fusion: {}'.format(highlight('wall')))
    wait(5)

    say('3b. DEFECTO: agujero roscado 27/64 -> .035 in',
        'Se cambia ec_tap: un agujero de 0,89 mm que atraviesa 25 mm (L/D ≈ 29).')
    fusion("d = _design(); ui.activeSelections.clear(); d.userParameters.itemByName('ec_tap').expression = '0.035 in'; _view(fit=False)")
    wait()
    r2, f2 = measure('3_agujero_fino')
    show_findings(r2)
    print('   Agujero resaltado en Fusion: {}'.format(highlight('hole')))
    wait(5)

    # ------------------------------------------------------ 4. revertir + reporte
    say('4. CORRECCIÓN Y REPORTE FINAL',
        'Se restauran los parámetros y se vuelve a verificar: los hallazgos deben desaparecer.')
    fusion("d = _design(); ui.activeSelections.clear(); "
           "d.userParameters.itemByName('ec_cb_w').expression = '0.800 in'; "
           "d.userParameters.itemByName('ec_tap').expression = '0.4219 in'; _view()")
    wait()
    r3, f3 = measure('4_corregida')
    show_findings(r3)
    ok = r3['summary'] == base['summary']
    print('\n   Revertir restaura la pieza sana: {}'.format('SÍ' if ok else 'NO'))
    print('   Reportes generados:')
    for f in (base_file, f1, f2, f3):
        print('     ' + f)
    wait(3)
    say('Abriendo el reporte del defecto 3a (JSON con medición, umbral y traza)...')
    if not FAST:
        subprocess.Popen(['notepad.exe', f1])
    print('\n   Fin de la demo. Ya puedes detener la grabación.')


if __name__ == '__main__':
    main()
