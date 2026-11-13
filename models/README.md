# Modelos paramétricos de prueba

Cada script crea un documento nuevo sin guardar en Fusion y no toca los diseños abiertos.

```
python tools/fusion_bridge.py models/vise_base.py --timeout 120
```

Sin el puente también se pueden correr desde Fusion: Shift+S > Scripts > + > Run.

## Toolmaker's Vise — base (`vise_base.py`)

Fuente: Make It From Metal, plano DWG 002, hoja 2 de 4 (`TOOLMAKER-VISE-PROJECT.pdf`, no incluido en el repositorio).
Uso educativo; ver la nota de licencia en `docs/piezas_de_prueba.md`.

| | |
|---|---|
| Estado | Generada y verificada en Fusion (versión 2706.1.17), 2026-11-04 |
| Cuerpo | 1 sólido, 68 caras, 209 aristas, 6.000 × 2.450 × 2.450 in |
| Volumen | 15.5667 in³ en Fusion contra 15.5669 in³ calculados a mano a partir del plano |
| Línea de tiempo | 23 elementos, todos sanos; los 10 bocetos completamente restringidos |
| Parámetros | 23 parámetros de usuario `vb_*`, uno por cota del plano |
| Tiempo de generación | ~2,6 s a través del puente |

Las operaciones con nombre (Base, Montante fijo, Guías, Alivio U-cut 1/8, Cajera inferior,
Cajera inferior - radios R.250, Ranura pasante, Agujero pasante .375 + patrón 8X, Roscado 1/4-20
A y B) son la columna "operación" de la matriz de trazabilidad. `vise_base_report.json` lista
los parámetros, las operaciones y el registro de la generación.

Vistas: `img/vise_iso_top.png`, `img/vise_iso_bottom.png`.

### Supuestos de interpretación del plano

1. Altura de la base 1.250 = .875 + .375 (vista lateral); el montante sube 1.200 sobre ella.
2. Las guías (2.075 × .375) recorren todo el largo, también bajo el montante (línea oculta en la
   vista superior), así que el montante sobresale .1875 por lado.
3. El alivio "1/8 U-cut" es un cilindro de Ø1/8 a lo largo de Y, centrado en la arista
   montante/guías.
4. La cajera inferior llega a .688 desde abajo (línea oculta de la vista frontal), y R.250 TYP son
   sus cuatro esquinas verticales.
5. La ranura de .531 atraviesa la base (0 a 1.250), no el montante.
6. Los 8 agujeros de .375 son pasantes en Y, a .625 de altura; cruzan la cajera inferior.

### Casos que ya trae la pieza para las reglas

- **Accesibilidad:** el U-cut y las guías bajo el montante no se alcanzan desde +Z; hacen falta
  montajes laterales.
- **Radio interno:** R.250 en la cajera inferior, extremos de ranura R.2655, y U-cut de Ø.125
  (radio .0625, una herramienta muy chica).
- **Relación de aspecto:** el U-cut tiene Ø.125 y atraviesa 2.450 (L/D ≈ 20).

## Otras piezas (`tap_guide.py`, `vee_block.py`, `superblock_123.py`, `edge_clamp.py`)

Usan los ayudantes de `mlib.py`: coordenadas en pulgadas con `modelToSketchSpace`, cortes que prueban
los dos sentidos y verifican el volumen quitado, y `plane_at` para ubicar planos desplazados.
Cada script devuelve su reporte; sus métricas están en `metrics/` y la comparación en
`docs/metricas_piezas.md`.

| Pieza | Etiqueta | Caras | Volumen (in³) | Supuestos |
|---|---|---|---|---|
| Tap Guide Block (DWG 001) | `tap_guide` | 17 | 2,25401 | V hacia +Z, agujeros a lo largo de Z |
| Vee Block (DWG 002) | `vee_block` | 26 | 5,31396 (= cálculo a mano) | Profundidad de las muescas 0,250 (no acotada) |
| 123 Superblock (DWG 001) | `superblock_123` | 120 | 3,81610 | Rosca 1/4-20 modelada como broca de 0,201 |
| Edge Clamp, cuerpo (DWG 002) | `edge_clamp` | 16 | 3,23953 (= cálculo a mano) | Profundidad de la caja 0,625 (no acotada); rosca como broca de 27/64 |

## Lecciones de la API (Fusion 2706)

- `sketch.include(origen)` sobre un plano desplazado **conserva la posición 3D del punto**: las
  restricciones a ese punto sacan el perfil del plano, y las operaciones quedan "sanas" pero a la
  altura equivocada. Hay que usar `sketch.originPoint`. Es un ejemplo de que "sano" en la línea de
  tiempo no garantiza geometría correcta.
- `addTwoPointRectangle` no agrega restricciones de horizontal/vertical; hay que agregarlas.
- El sentido de una extrusión no siempre coincide con lo que sugiere `PositiveExtentDirection`:
  el script prueba los dos sentidos y verifica el cambio de volumen.
- Los agujeros pasantes desde un plano lateral funcionaron con `setAllExtent(Positive)`; el
  roscado del lado B necesitó `isDefaultDirection = False`.
- Varias sesiones comparten el documento activo de Fusion: los scripts etiquetan su diseño con
  `design.attributes.add('ClaudeBridge', 'model', ...)` y lo buscan por esa etiqueta.
