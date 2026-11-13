"""Rule catalogue (objective 1): thresholds, severities, categories and sources.

The data lives in catalog.json (documented in docs/catalogo_reglas.md). The rule
engine reads thresholds only through this module, so they can be changed with
`overrides`, which are validated against each level's range.

    cat = Catalog(profile='metal', overrides={'internal_radius.error': 0.3})
    cat.th('internal_radius', 'error')   -> 0.3
    cat.rule('internal_radius')           -> rule dict (name, category, sources...)
"""

import json
import os

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'catalog.json')


def load(path=PATH):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


class Catalog:
    def __init__(self, profile='metal', overrides=None, data=None):
        self.data = data or load()
        if profile not in self.data['perfiles']:
            raise ValueError('unknown profile {!r}; available: {}'.format(profile, list(self.data['perfiles'])))
        self.profile = profile
        self.rules = {r['id']: r for r in self.data['reglas']}
        self.values = {}
        for r in self.data['reglas']:
            for level, spec in r.get('niveles', {}).items():
                self.values['{}.{}'.format(r['id'], level)] = spec['valor']
            for name, spec in r.get('parametros', {}).items():
                self.values['{}.{}'.format(r['id'], name)] = spec['valor']
        self.overrides = {}
        self._apply(self.data['perfiles'][profile], source='profile')
        self._apply(overrides or {}, source='override')

    def _range(self, key):
        rid, name = key.split('.', 1)
        r = self.rules[rid]
        spec = r.get('niveles', {}).get(name) or r.get('parametros', {}).get(name)
        return spec.get('rango') if spec else None

    def _apply(self, mapping, source):
        for key, value in mapping.items():
            if key not in self.values:
                raise KeyError('unknown threshold {!r}'.format(key))
            rng = self._range(key)
            if value is not None and rng and not (rng[0] <= value <= rng[1]):
                raise ValueError('{} = {} outside the allowed range {}'.format(key, value, rng))
            self.values[key] = value
            if source == 'override':
                self.overrides[key] = value

    def th(self, rule_id, level):
        """Threshold value, or None when the level is disabled or not defined."""
        return self.values.get('{}.{}'.format(rule_id, level))

    def rule(self, rule_id):
        return self.rules[rule_id]

    def meta(self, rule_id):
        """Compact metadata attached to every finding."""
        r = self.rules[rule_id]
        return {'rule_name': r['nombre'], 'category': r['categoria'], 'thesis_scope': r['alcance_tesis'],
                'sources': [s['id'] for s in r.get('fuentes', [])]}

    def summary(self):
        return {'version': self.data['version'], 'profile': self.profile, 'overrides': dict(self.overrides),
                'thresholds': dict(self.values)}
