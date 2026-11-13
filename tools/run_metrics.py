# Metrics for one modelled part. Runs INSIDE Fusion via ClaudeBridge:
#   python tools/fusion_bridge.py -c "TAG='vise_base'; exec(open(r'C:\taller\taller-grado-dfm-fusion\tools\run_metrics.py', encoding='utf-8').read())" --timeout 300
# Finds the document tagged ClaudeBridge/model == TAG (models/*.py tag their design),
# measures it with src/dfm/metrics.py and writes models/metrics/<TAG>.json.
import importlib
import json
import os
import sys

ROOT_DIR = r'C:\taller\taller-grado-dfm-fusion'
if os.path.join(ROOT_DIR, 'src') not in sys.path:
    sys.path.insert(0, os.path.join(ROOT_DIR, 'src'))
import dfm.analysis
import dfm.provenance
import dfm.metrics
for _m in (dfm.analysis, dfm.provenance, dfm.metrics):
    importlib.reload(_m)


def find_design(tag):
    for doc in app.documents:
        d = adsk.fusion.Design.cast(doc.products.itemByProductType('DesignProductType'))
        a = d and d.attributes.itemByName('ClaudeBridge', 'model')
        if a and a.value == tag:
            return doc, d
    return None, None


TAG = globals().get('TAG')
doc, design = find_design(TAG)
if not design:
    raise RuntimeError('No open document tagged ClaudeBridge/model = {!r}. Run models/{}.py first.'.format(TAG, TAG))
doc.activate()
report = dict(tag=TAG, document=doc.name, units=design.unitsManager.defaultLengthUnits,
              **dfm.metrics.measure(design))
os.makedirs(os.path.join(ROOT_DIR, 'models', 'metrics'), exist_ok=True)
with open(os.path.join(ROOT_DIR, 'models', 'metrics', TAG + '.json'), 'w', encoding='utf-8') as fh:
    json.dump(report, fh, indent=2, ensure_ascii=False, default=str)
result = {k: report[k] for k in ('tag', 'body', 'setups', 'unreachable_faces', 'min_wall_mm', 'summary', 'timing_s')}
