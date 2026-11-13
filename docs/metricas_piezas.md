# Métricas de las piezas de prueba modeladas desde planos

Fecha: 2026-11-04 · Fusion 2706.1.17 · Planos: Make It From Metal (no incluidos en el repositorio; uso educativo, ver `docs/piezas_de_prueba.md`).

Cómo se obtienen: cada `models/<pieza>.py` construye la pieza con historial y parámetros. Después
`tools/run_metrics.py` (dentro de Fusion vía ClaudeBridge) reconstruye la procedencia (`src/dfm/provenance.py`),
mide con `src/dfm/analysis.py`, aplica **umbrales provisionales** y traza cada hallazgo hasta su operación y parámetro.
El detalle completo por pieza está en `models/metrics/<pieza>.json`.

```
python tools/fusion_bridge.py models/tap_guide.py --timeout 120
python tools/fusion_bridge.py -c "TAG='tap_guide'; exec(open(r'C:\taller\taller-grado-dfm-fusion\tools\run_metrics.py', encoding='utf-8').read())" --timeout 300
```

## Tabla comparativa

| Pieza | Línea de tiempo / ops. con geometría | Parám. de usuario | Caras / aristas | Aristas cóncavas/convexas/tangentes | Cavidades | Montajes (direcciones) | Caras inalcanzables | Pared mín. (mm) | Caras modificadas tras crearse / máx. modificadores | Errores / advertencias | Tiempo s (procedencia + análisis) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Base de la prensa (DWG 002)¹ | 23 / 11 | 23 (1 sin uso) | 68 / 209 | 35/160/12 | 15 (11 agujeros) | 3 (−Z, +Y, −Y) | 0 | 1,59 | 24 / 4 | **1** / **8** | 2,15 + 1,34 |
| Tap Guide (DWG 001) | 20 / 10 | 13 (2 sin uso) | 17 / 53 | 9/44/0 | 9 (8 agujeros) | 2 (+Z, −Z) | 0 | 5,00 | 7 / 8 | 0 / **1** | 0,55 + 0,27 |
| Vee Block (DWG 002) | 14 / 7 | 9 (8 sin uso) | 26 / 72 | 8/64/0 | 4 | 2 (+Y, +Z) | 0 | 8,52 | 14 / 6 | 0 / 0 | 0,49 + 0,26 |
| 123 Superblock (DWG 001) | 23 / 10 | 9 (1 sin uso) | 120 / 284 | 23/261/0 | 46 (46 agujeros) | 6 (todas) | 0 | 2,25 | 79 / 2 | 0 / **8** | 2,99 + 4,12 |
| Edge Clamp, cuerpo (control) | 9 / 4 | 10 (3 sin uso) | 16 / 38 | 4/26/8 | 3 (1 agujero) | 2 (+Z, −Z) | 0 | 5,71 | 3 / 2 | 0 / 0 | 0,19 + 0,18 |

¹ Modelada en una etapa anterior (`models/vise_base.py`); aquí solo se midió.

Cifras de la última medición (después de las correcciones 3 y 4 de abajo). La pared mínima se mide con el
método exacto: la de la base bajó de 1,84 a 1,59 mm y la del Superblock de 6,35 a 2,25 mm, porque los rayos la sobrestimaban.

**Parámetros sin uso** (ningún elemento depende de ellos, así que cambiarlos no modifica la pieza):
- Base: `vb_slot_W`: **el ancho de la ranura pasante no está ligado a su parámetro**.
- Tap Guide: `tg_v_open` y `tg_v_angle`.
- Vee Block: 8 de 9.
- Superblock: `sb_pitch`.
- Edge Clamp: `ec_c1`, `ec_c2` y `ec_hole_x`.

En mis modelos, la V, las muescas y las posiciones se dibujaron con puntos fijos. Es un **defecto de intención de diseño**,
no de mecanizado, y el catálogo debería distinguirlo como "error de diseño preliminar".

Todas las piezas nuevas salen **sanas en la primera construcción** y su volumen coincide con el cálculo a mano
(Vee Block 5,31396 in³; Edge Clamp 3,23953 in³; las cajas del Superblock en Z quitan exactamente 8 × y 7 × 0,0828 in³).

## Hallazgos y trazas

| Pieza | Regla | Valor medido | Umbral | Operación de origen → parámetro | ¿Lo anticipaba la lectura del plano? |
|---|---|---|---|---|---|
| Base de la prensa | L/D de agujero (**error**) | 19,6 | 10 | `Alivio U-cut 1/8`, modificado por `Ranura pasante` → `vb_ucut_d` | Sí: "U-cut Ø.125 atraviesa 2.450 (L/D ≈ 20)" |
| Base de la prensa | L/D de agujero ×8 (advertencia) | 6,53 | 4 | `Agujeros pasantes 8X (patron)` y `Agujero pasante .375` → `vb_pin_d` | No: el pasante de Ø.375 cruza la cajera y se taladra de lado a lado (2.450) |
| Tap Guide | L/D de agujero (advertencia) | 4,64 | 4 | `Agujero 1 D0.136 THRU` → `tg_d1` | Sí: "Agujero Ø.136 con L/D ≈ 4" |
| 123 Superblock | L/D de caja ×3 (advertencia) | 7,33 | 4 | `3X X cajas lado ±` → `sb_cb` | Sí: "caja Ø.375 ↓2.75 tiene L/D ≈ 7,3" |
| 123 Superblock | L/D de caja ×5 (advertencia) | 4,67 | 4 | `5X Y cajas lado ±`, **modificadas por** `3X X cajas` → `sb_cb` | No estaba listado (1.75 / .375) |
| Vee Block | — | 0 hallazgos | — | — | Sí: sus esquinas vivas son horizontales, así que la regla no debía marcarlas |
| Edge Clamp | — | 0 hallazgos | — | — | Sí: es la pieza de control |

Lo que muestran estos casos sobre las reglas:

- **El radio interno depende de la dirección de mecanizado.** Las ranuras de alivio del Vee Block y el fondo de la V del Tap Guide
  tienen aristas cóncavas vivas, pero son perpendiculares a la herramienta (las deja el flanco o una fresa en V), así que no se marcan.
- **Distinguir taladrado de cajera** (pregunta abierta en `piezas_de_prueba.md`): el motor clasifica las cajas del Superblock como
  agujeros (un cilindro coaxial) y les aplica la regla L/D, no la de radio de cajera. Por eso se marcan como advertencia y no como error.
- **La procedencia registra los cruces de agujeros:** las cajas en Y figuran como modificadas por las cajas en X.

## Problemas encontrados y corregidos durante la medición

1. **Falso positivo por la dirección de mecanizado.** El rebaje de las guías de la prensa salió con "radio 0" y "aspecto 16" porque
   se eligió el eje que *alcanza* más caras (+X, mirando a lo largo de 152 mm). Ahora se ordena por: caras alcanzadas → fondo plano
   visto de frente → menor profundidad. El falso positivo desapareció.
2. **Agujeros fragmentados.** Una caja que cruza otros agujeros queda cortada en varias caras cilíndricas unidas por aristas
   *convexas*, y el grafo de adyacencia la veía como varios agujeros cortos. Ahora se fusionan los cilindros cóncavos coaxiales del
   mismo radio: las cajas de 2,75 in del Superblock (7 caras cada una) se miden como una sola de 69,85 mm.
3. **Fusión excesiva de coaxiales.** La corrección 2 unió también los dos roscados de la base, que son ciegos, están en caras opuestas
   y quedan separados por 37 mm de material (L/D falso de 12,2). Ahora solo se fusionan si el tramo entre ellos es hueco
   (`pointContainment` en 5 puntos del eje). Los pasantes que cruzan la cajera sí se unen (62,23 mm).
4. **Espesor subestimado por muestreo.** Lo encontró la inyección de defectos (caso E, `docs/inyeccion_defectos.md`): los rayos de
   una grilla de 5×5 no pasaban por la línea entre dos cajas vecinas. Se agregó la distancia mínima exacta entre caras no adyacentes,
   contada como pared solo si el punto medio del segmento está dentro del material.

## Limitaciones de estas métricas

- **Los montajes son una cota optimista.** Una cara con normal perpendicular a la dirección se cuenta como alcanzable con el flanco
  de la fresa. Por eso el Vee Block sale con 2 montajes. Es válido para perfiles prismáticos, pero no considera el largo de la herramienta ni la sujeción.
- **Umbrales:** desde la versión 0.1 del catálogo ([`catalogo_reglas.md`](catalogo_reglas.md)) salen de `src/dfm/catalog.json`,
  con sus fuentes. Se volvieron a medir las 5 piezas con el catálogo y los hallazgos de la tabla no cambiaron.
- **Cotas supuestas**: la profundidad de las muescas del Vee Block (0,250) y la de la caja del Edge Clamp (0,625) no están en los
  planos. Se midieron sobre la hoja renderizada y quedan como parámetros marcados `SUPUESTO`.
- **Roscas modeladas como broca de roscado** (0,201 y 27/64). Fusion puede modelar la rosca, pero para estas reglas solo importa el diámetro de la broca.
- Las posiciones de agujeros y perfiles quedan **fijadas, no acotadas**. La sensibilidad no las va a ver como parámetros, solo los
  diámetros, profundidades y medidas del bloque.

## Pendientes de la lista de `piezas_de_prueba.md`

Faltan modelar la **mordaza de la prensa** (cara a 45° con caja perpendicular a ella: necesita direcciones fuera de los ejes),
el **Vee Block Clamp** (pared de 0,219, prueba de espesor) y el **bloque del Micrometer Stand** (ranura inclinada a 45°).
También faltan los **defectos inyectados** que propone esa lista (bajar R.250, quitar el alivio de la V, adelgazar paredes).
