# Sondeo 01 — Capacidades de la API de Fusion 360 (Fase 1, objetivo 2)

Fecha: 2026-11-04 · Fusion / API 2706.1.17 · Script: `probes/01_api_probe.py` · Datos crudos: `probes/01_api_probe.result.json`

Pieza de prueba (generada por script, un solo cuerpo): bloque 80×50×30 mm, cajera 40×20×25 mm
con radios internos `r_corner = 1 mm`, agujero simple Ø6×20 mm. Línea de tiempo: 7 elementos, 17 caras.

## A. Trazabilidad cara → operación → parámetro

| Hallazgo | Evidencia |
|---|---|
| `Feature.faces` asigna **cada cara del cuerpo a exactamente una operación** | 17/17 caras con dueño, 0 con varios dueños |
| El dueño es la operación que **creó** la cara, no las que la modificaron | La cara superior (3172,6 mm², recortada por la cajera y el agujero) sigue atribuida solo a `Block` |
| `ModelParameter.createdBy` + `role` + `dependencyParameters` cierran la cadena hasta el parámetro de usuario | `Pocket corners` → `d21` (role `Radius`) → `r_corner` |
| No existe una propiedad cara→operación en `BRepFace`: la relación se reconstruye recorriendo la línea de tiempo | Lista de miembros de `BRepFace` |

Implicación para la matriz: hay que registrar dos relaciones distintas, **operación de origen** (la que da `Feature.faces`)
y **operaciones que modificaron la cara** (que habrá que obtener comparando estados con `rollTo`).

## B. Mediciones para las reglas

| Medición | Resultado | Tiempo |
|---|---|---|
| Tipo de superficie y radio de cada cara | Plano / Cilindro / Cono; radios 1,0 mm (esquinas) y 3,0 mm (agujero) | 3,9 ms (17 caras) |
| Concavidad de cilindros (normal vs. eje) | Las 4 esquinas y el agujero salen cóncavos, como corresponde | incluido arriba |
| Profundidad de la cajera (`measureMinimumDistance` fondo↔tapa) | 25,0 mm, exacto | 3,6 ms |
| Relación de aspecto profundidad / Ø herramienta (Ø = 2·r mín.) | 25 / 2 = **12,5**, lo que daría una violación con cualquier umbral razonable | — |
| `concaveEdges` / `convexEdges` del cuerpo | 9 / 30; la suma da las 39 aristas, así que las **aristas tangentes caen dentro de "convexas"**: no conviene usarlas como único criterio | — |

## C. Estabilidad tras un cambio de parámetro

- `r_corner` de 1 → 3 mm: el modelo se recalcula en **143 ms**.
- Los 4 `entityToken` de las caras de radio se resolvieron con `findEntityByToken` (4/4) y ya devuelven el radio nuevo (3,0 mm).
  Esto permite seguir una violación a través de los cambios.

## D. Línea de tiempo, estado de salud y topología

- `rollTo(True)` antes del redondeo → 11 caras; `moveToEnd()` → 17 caras. 21 ms ida y vuelta.
- Topología consultable: `isSolid`, lumps (1), shells (1), caras/aristas/vértices, caras degeneradas (0).
- **No existe un "Check body" en la API** (el único miembro relacionado es `isValid`, que solo indica si la referencia al objeto sigue viva).
  La regla de validez topológica tiene que componerse con las consultas anteriores más el estado de salud de cada operación.
- Defecto inducido: con `hole_depth = 0` el agujero queda en **advertencia (1), no en error (2)**, con el mensaje
  "Can't create hole toolbody… Zero distance". Hay que tratar las advertencias también como hallazgos.

## E. Eventos disponibles para la verificación progresiva

- `ui.commandTerminated`, el mismo que ya usa ParamTracker, es el gancho natural para disparar "verificar tras cada operación".
- Otros: `commandStarting`, `activeSelectionChanged`, `documentOpened/Saved/Activated`, y eventos personalizados (`fireCustomEvent`).

## Presupuesto de latencia (17 caras)

Mapeo completo (~3 ms) + mediciones (~7 ms) + topología (~3 ms) ≈ **13 ms**, frente a 143 ms que tarda el propio
recálculo de Fusion. La verificación tras cada operación es viable sin bloquear al usuario. Falta medir piezas más grandes.

## Pendientes para la Fase 3 (matriz de trazabilidad)

1. Obtener las operaciones que modifican una cara (diferencias entre estados con `rollTo`).
2. Medir el espesor de pared (alcance deseable): distancia mínima entre caras opuestas.
3. Medir la escalabilidad del tiempo con piezas de 100 a 1000 caras.
4. Probar la robustez de los tokens ante reordenar, suprimir y borrar operaciones.
