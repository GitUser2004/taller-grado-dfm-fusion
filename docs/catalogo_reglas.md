# Catálogo de reglas geométricas para fresado de 3 ejes (objetivo 1)

Versión 0.1 · 2026-11-04 · Datos: [`src/dfm/catalog.json`](../src/dfm/catalog.json) · Cargador: [`src/dfm/catalog.py`](../src/dfm/catalog.py)
· Lo aplica: [`src/dfm/metrics.py`](../src/dfm/metrics.py) · Fuentes: [`bibliografia/`](../bibliografia/README.md)

El catálogo reemplaza los umbrales provisionales (`DEFAULT_THRESHOLDS`). Desde ahora el motor no tiene ningún número de
regla escrito en el código: todos los umbrales, severidades, categorías y fuentes se leen de `catalog.json`. Así los umbrales
se configuran **cambiando valores del catálogo**, dentro de un rango permitido por regla, y no editando código.

## Cómo se lee

**Dos categorías**, como pide el alcance del objetivo 1:

| Categoría | Qué es | Depende del proceso |
|---|---|---|
| `diseno_preliminar` | Errores del modelo: sólido inválido, operaciones con error, parámetros que no mueven la geometría. Se corrigen modelando. | No |
| `proceso` | Violaciones de restricciones geométricas del fresado de 3 ejes. **Son las que atiende el sistema.** | Sí (material, taller) |

**Tres severidades**, con un criterio fijo para todas las reglas de proceso:

| Severidad | Significado | Se fija con |
|---|---|---|
| `error` | Fuera del límite **factible** con herramienta estándar: exige otro proceso (electroerosión), herramienta especial, o no se puede fabricar | el valor "factible" o "mínimo absoluto" de las fuentes |
| `warning` | Factible, pero fuera del valor **recomendado** (más costo, vibración, riesgo) | el valor "recomendado" de las fuentes |
| `info` | No es restricción del proceso: describe la intención de diseño | — |

Así una regla con dos números en las fuentes (recomendado y factible) tiene dos niveles, y cada nivel queda justificado
por separado.

## Reglas

| # | Regla (`id`) | Categoría | Alcance en la tesis | Medición | Advertencia | Error | Fuentes |
|---|---|---|---|---|---|---|---|
| 1 | Validez topológica (`topological_validity`) | diseño preliminar, **bloqueante** | comprometida | sólido cerrado, 1 lump, 1 cuerpo, 0 aristas abiertas o no variedad, aristas < 0,01 mm, caras < 0,001 mm² | — | cualquier falla | [38] Requicha; sondeo 02 (T3) |
| 2 | Operaciones con error (`feature_health`) | diseño preliminar | adicional | `healthState ≠ 0` | — | cualquiera | API de Fusion |
| 3 | Parámetro sin efecto (`unused_parameter`) | diseño preliminar | adicional | `dependentParameters = 0` | info | — | [1] Camba; inyección E2 |
| 4 | Radio interno mínimo (`internal_radius`) | proceso | comprometida | radio mínimo de las aristas cóncavas **paralelas al eje de la herramienta** | — | r < **0,5 mm** | Protolabs (fresas desde 1 mm); JLCCNC (R0,5 solo hasta 3 mm de profundidad); DFMXpress (esquina viva → EDM) |
| 5 | Radio respecto de la profundidad (`internal_radius_depth`) | proceso | comprometida | r / profundidad | r < **prof./3** | — | Hubs |
| 6 | Profundidad / diámetro de fresa (`cavity_aspect_tool`) | proceso | comprometida | prof. / (2 r_mín) | > **6** | > **10** | Five Flute (6 máx., 10 difícil); Protolabs (fresa 1 mm → 9,52 mm); JLCCNC; DFMXpress (3); Mitsubishi (deflexión ∝ L³) |
| 7 | Profundidad / ancho (`cavity_aspect_opening`) | proceso | comprometida | prof. / **menor** extensión de la abertura | > **4** | — | Hubs (4 × ancho); Protolabs (< 6 × ancho); JLCCNC (5 × mayor medida) |
| 8 | L/D de agujero (`hole_aspect`) | proceso | comprometida (la relación de aspecto de cavidades incluye agujeros) | largo / diámetro | > **4** | > **10** | Hubs (4 recom., 10 típico, 40 factible); Sandvik (> 10 D = agujero profundo); Protolabs (> 6 es un desafío); DFMXpress (2,75) |
| 9 | Diámetro mínimo de agujero (`hole_diameter`) | proceso | adicional | diámetro | < **2,5 mm** | < **1,0 mm** | Hubs; DFMXpress (< 3 mm difícil) |
| 10 | Espesor de pared (`wall_thickness`) | proceso | deseable | rayos + distancia exacta entre caras no adyacentes | < **0,8 mm** | < **0,5 mm** | Hubs; JLCCNC; Protolabs (0,51 y 0,5 mm) |
| 11 | Accesibilidad (`accessibility`) | proceso | deseable | caras que ninguna de ±X, ±Y, ±Z alcanza (≥ 95 % de muestras libres) | — | cualquiera | Gupta et al. 1997; DFMXpress (operaciones inaccesibles) |

**Perfil `plastico`:** cambia solo la pared, con advertencia por debajo de 1,5 mm y error por debajo de 1,0 mm (Hubs y JLCCNC).
El perfil por defecto es `metal`.

### Notas por regla

- **1. Validez topológica.** Es una **precondición**: si falla, las mediciones de proceso no son confiables, y el
  reporte lo indica con `topology_valid: false`. Los límites de arista corta y cara diminuta son **criterio propio**, sin
  fuente externa (quedan configurables). Las aristas degeneradas del ápice de los conos no se cuentan, porque son legales.
- **4 y 5. Radio interno.** Solo cuentan las aristas cóncavas **paralelas al eje de la herramienta**. Las horizontales
  (el fondo de una V, los alivios) las deja el flanco o una fresa de forma. Por eso el Vee Block da 0 hallazgos. La regla 5 se evalúa solo si se cumple la 4, para no reportar dos veces el mismo radio.
- **6. Profundidad / diámetro de fresa.** El radio mínimo fija la fresa más grande posible (D = 2 r). Hubs admite hasta
  30:1 con herramienta especial. El error a 10 marca el punto donde dos fuentes (Five Flute y Protolabs) dicen que deja de
  ser fresado estándar.
- **7. Profundidad / ancho.** Ahora se mide sobre el **ancho**, que es la menor extensión de la abertura. Hubs pide 4
  veces el ancho y Protolabs 6 veces. Antes se medía sobre la mayor extensión, como propone JLCCNC; con el ancho la regla
  queda más estricta y más fiel a la fuente principal. No tiene nivel de error, porque ninguna fuente da un límite factible.
- **8. Agujeros.** Las cajas del Superblock se clasifican como agujeros (un cilindro coaxial) y se les aplica esta regla,
  no la de cajera.

## Dónde discrepan las fuentes y qué se eligió

| Tema | Valores en las fuentes | Elegido | Por qué |
|---|---|---|---|
| L/D de agujero | DFMXpress 2,75 · Hubs 4 / 10 / 40 · Protolabs 6 · Five Flute 20 · Sandvik > 10 es profundo | 4 / 10 | Hubs da los niveles recomendado y típico; Sandvik coincide en 10 como frontera de técnica especial. DFMXpress queda como alternativa estricta |
| Prof. / D de fresa | DFMXpress 3 · JLCCNC 2–3 (mejor) y ≥ 5 (especial) · Five Flute 6 y 10 · Protolabs ≈ 9,5 · Hubs 30 (especial) | 6 / 10 | Five Flute da los dos niveles; Protolabs confirma el orden de 10 |
| Prof. / abertura | Hubs 4 × ancho · Protolabs 6 × ancho · JLCCNC 5 × mayor medida | 4 × ancho | Fuente principal y más estricta; las otras dos son alternativas |
| Radio vs. profundidad | Hubs r ≥ prof./3 · JLCCNC R ≥ prof./10 + 0,5 · un proveedor secundario prof./8 | prof./3 (advertencia) | Hubs es recomendación; JLCCNC es factibilidad y queda cubierta por la regla 6 (D = H/5) |
| Pared en metal | Hubs 0,8 / 0,5 · JLCCNC 0,8 / 0,5 · Protolabs 0,51 y 0,5 | 0,8 / 0,5 | Las tres coinciden |

Las alternativas están en `catalog.json`, en `fuentes[].valor` de cada regla. Si el diseñador quiere aplicar
otro criterio (por ejemplo, el de DFMXpress), alcanza con cambiar el umbral dentro de su rango.

## Configuración

```python
from dfm import catalog, metrics
cat = catalog.Catalog(profile='metal', overrides={'hole_aspect.warning': 2.75})  # criterio de DFMXpress
report = metrics.measure(design, tracker, catalog=cat)
```

- Cada umbral tiene un **rango permitido** (`rango` en el JSON). Un valor fuera de rango se rechaza con `ValueError`.
  Por ejemplo, `internal_radius.error = 9` se rechaza porque el rango es 0,1–5 mm. Así ningún ajuste sale del rango que respaldan las fuentes.
- Un nivel en `None` desactiva ese nivel.
- El reporte guarda la versión, el perfil, las sobrescrituras y los umbrales aplicados (`report['catalog']`).
- Cada hallazgo lleva `rule_id`, `category`, `thesis_scope` y `sources`. Lo mismo va en `summary_by_category`.

## Fuera del catálogo

| Tema | Motivo | Fuentes |
|---|---|---|
| Tolerancias | Fuera del alcance de la tesis | Hubs, Protolabs, DFMXpress |
| Número de montajes | Es costo: se reporta como métrica, no como regla | — |
| Roscas | Los modelos usan la broca de roscado | Hubs, JLCCNC, Protolabs |
| Texto grabado | No aparece en las piezas | Hubs, Protolabs |
| Tamaños de broca estándar | Candidata; necesita la tabla de brocas del taller | DFMXpress, Hubs |
| Fondo plano, entrada no perpendicular, agujero parcial | Candidatas de taladrado | DFMXpress |
| Redondeos en aristas externas | Candidata; exigen fresa de forma | DFMXpress |
| Contradesmoldeos (T, cola de milano) | Hoy se reportan como inaccesibles | Hubs |
| Profundidad máxima y tamaño de pieza | Dependen de la máquina | Protolabs |

## Validación

Se volvieron a medir las 5 piezas y a correr los 8 casos de inyección (`tools/run_metrics.py`, `tools/inject_defects.py`):

- **Piezas: los hallazgos son idénticos** a los que daban los umbrales provisionales (base 1/8, Tap Guide 0/1, Vee Block 0/0,
  Superblock 0/8 y Edge Clamp 0/0). Todos son de categoría `proceso`. La regla de profundidad/ancho, que ahora es más
  estricta, no agregó nada.
- **Inyección: 8/8 aprobados**, con estos cambios de severidad que vienen del catálogo:

| Caso | Antes (provisional) | Con el catálogo | Motivo |
|---|---|---|---|
| A `vb_cb_R` → .015 | error r 0,381 + **advertencia** aspecto 22,9 | error r 0,381 + **error** aspecto 22,9 | 22,9 > 10: pasa el límite factible de la regla 6 |
| C `vb_cb_D` → 1.225 | **error** pared 0,635 | **advertencia** pared 0,635 | 0,635 está entre el factible (0,5) y el recomendado (0,8) |
| D `tg_d1` → .040 | error L/D 14,6 | error L/D 14,56 + **advertencia** Ø 1,016 mm | regla nueva de diámetro mínimo |
| E `sb_cb` → .480 | error pared 0,36 | error pared 0,359 + advertencia 0,508 | la pared de 0,51 mm queda en el nivel de advertencia |
| F `ec_cb_w` → 1.200 | **error** pared 0,635 | **advertencia** pared 0,635 | igual que C |
| B, E2, H | — | sin cambios | — |

Las expectativas de C y F en `tools/inject_defects.py` se ajustaron a `warning`.

## Pendientes y límites honestos

- **Las fuentes son, sobre todo, guías de fabricantes** (Hubs/Protolabs, JLCCNC, Five Flute), que no están revisadas por
  pares. Faltan dos manuales de referencia para la tesis: Boothroyd, Dewhurst y Knight, *Product Design for Manufacture
  and Assembly* (3.ª ed., 2010), y Bralla, *Design for Manufacturability Handbook* (2.ª ed., 1999). No se pudieron
  consultar en línea y hay que buscarlos en biblioteca para confirmar o contrastar los valores.
- **Sandvik:** el valor de 10 D se tomó de un resumen de su guía de taladrado profundo. Falta ubicar la edición y la página
  (`pendiente` en el JSON).
- **Criterios propios sin fuente:** aristas cortas (0,01 mm), caras diminutas (0,001 mm²) y la fracción de muestras libres
  de la accesibilidad (0,95). Quedan marcados como tales y son configurables.
- Todos los umbrales son de **taller genérico**. Un perfil del taller real (las fresas y brocas disponibles) haría más
  precisas las reglas 4, 6, 8 y 9.
