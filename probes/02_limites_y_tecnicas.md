# Sondeo 02: límites de la API de Fusion 360 y cómo suplirlos

Fecha: 2026-11-04 · API 2706.1.17 · Script: `probes/02_limits_probe.py` · Datos: `probes/02_limits_probe.result.json`

## Pieza de prueba (un cuerpo, fresado desde +Z)

| Operación | Defecto que se le puso | ¿Se detectó? |
|---|---|---|
| Pocket1 (40×20×25, redondeo r=1 mm) | Cavidad profunda con radio interno chico | Sí: r = 1,0 mm, relación de aspecto 12,5 |
| Pocket2 (esquinas vivas, sin cotas) | Radio interno 0 y pared de 1,5 mm | Sí: 4 aristas verticales vivas y espesor de 1,5 mm |
| Pocket3 (esquinas con *fillet de boceto* r=2) | Radio que no es un parámetro | Sí: se trazó hasta 4 arcos del boceto sin cota |
| Hole (Ø6×20 vertical) | Ninguno (control) | Medido: r = 3, relación 3,63 |
| SideHole (Ø5 horizontal) | Contrasalida: no se alcanza desde +Z | Sí: 0 de 25 puntos alcanzables |

## Límite → técnica → evidencia

| # | Límite de la API | Técnica para suplirlo | Resultado |
|---|---|---|---|
| T1 | `Feature.faces` solo da la operación que **creó** la cara | **Etiquetas con `attributes`**: tras cada operación se marcan las caras nuevas con `origin` y se compara el área de las existentes para llenar `modified_by` | 33/33 coinciden con la API. La cara superior quedó con `modified_by = Pocket1, Pocket1 corners, Pocket2, Pocket3, Hole`. Las etiquetas **sobreviven al recálculo** (33/33 tras cambiar `p1_r` y `p1_D` y revertirlos) |
| T2 | Igual que T1, sin poder instrumentar mientras se modela | **Repetir la línea de tiempo**: `rollTo` en cada operación, y en cada estado se resuelven los tokens del estado anterior para saber qué caras se borraron, dividieron o modificaron | Mismo resultado que T1, sin depender de que el complemento haya estado activo desde el inicio. Sirve como auditoría o para modelos ya existentes |
| — | **Los `tempId` cambian al recalcular o al retroceder la línea de tiempo** (hallazgo nuevo) | Usar siempre `entityToken`; el mapa cara→operación se reconstruye después de cada recálculo | En la primera corrida, T5 y T11 fallaron justamente por usar `tempId` viejos |
| T3 | No existe un "Check body" | **Validez compuesta**: `isSolid`, lumps, capas (`isClosed`, `isVoid`), aristas abiertas o no-manifold, aristas cortas, caras diminutas y estado de las operaciones | Funciona. Hay que excluir las **aristas degeneradas del ápice de los conos** (longitud 0 y una sola cara): sin ese filtro aparecían 2 falsos "bordes abiertos" |
| T3b | Ídem | **Verificador externo con OpenCASCADE**: Fusion exporta STEP y `tools/occ_check.py` lo valida con `BRepCheck_Analyzer` y `ShapeAnalysis_FreeBounds` | valid = true, 1 sólido, 33 caras, 0 bordes libres, volumen 150 968 mm³ (coincide con el cálculo a mano) |
| T4 | `concaveEdges` y `convexEdges` meten las aristas tangentes como convexas | **Ángulo diedro propio**: normales de las dos caras en el punto medio de la arista y orientación del coedge (el material queda a la izquierda) | Coincide 60/60 con la API en las aristas no tangentes y separa las 16 tangentes |
| T5 | No hay reconocimiento de features de mecanizado | **Grafo de adyacencia de caras (AAG)**: componentes conexas por aristas cóncavas o tangentes = cavidades; por cada una se calculan profundidad, abertura, radio mínimo y aristas vivas | 5 cavidades, cada una con su operación de origen y sus métricas correctas |
| T6 | No hay análisis de accesibilidad | **Lanzamiento de rayos** (`findBRepUsingRay`) desde puntos de muestra de cada cara hacia +Z, más el signo de la normal | Solo el agujero lateral sale inaccesible. La cara de apoyo (fondo del stock) se excluye a propósito |
| T7 | No hay análisis de espesor | **Rayos hacia adentro** (−normal) desde cada cara: la distancia al primer impacto es el espesor local | Mínimo 1,5 mm en la pared de Pocket2, exacto |
| T8 | Un radio dibujado en el boceto no tiene parámetro | **Trazado geométrico cara→curva**: `profile.profileLoops.profileCurves.sketchEntity`, emparejando radio y centro | 4/4 caras trazadas a su `SketchArc`, sin cota ni restricción completa. La corrección propuesta sería "agregar una cota", no "cambiar un parámetro" |
| T9 | — | **Exportación** a STEP, STL o SMT y malla por cuerpo o por cara (`meshManager`) | Todo funciona, para alimentar herramientas externas |
| T10 | El Python de Fusion es **3.14 y no trae numpy, scipy ni requests** | Mantener el código del complemento en Python puro y mandar lo pesado (OCC, mallas) a un **proceso externo** | `urllib`, `ssl`, `sqlite3` y `json` sí están disponibles (alcanza para llamadas HTTP) |
| T11 | — | **Retroalimentación al diseñador**: `customGraphics` (copias en rojo de las caras con violaciones), `design.attributes` para guardar la configuración de umbrales dentro del documento, `palettes` y `activeSelections` | 7 caras resaltadas. La configuración se escribe y se lee de vuelta sin pérdida |

## Hallazgo extra: Fusion trae un servidor MCP propio

Fusion 2706 incluye un **servidor MCP de Autodesk**, apagado por defecto (`MCP.Server`), en `http://127.0.0.1:27182/mcp`.
Las herramientas habilitadas para clientes externos son `MCP.Read` (documentación de la API, documentos, **captura de pantalla
del viewport** y **lectura del comando activo con sus valores**), `MCP.Execute` (incluye **ejecutar un script de Python**) y `MCP.Update`.
`MCP.Create` y `MCP.Delete` existen, pero vienen deshabilitadas. **No hay ninguna herramienta de manufacturabilidad ni de validación**:
el MCP es un canal para que un modelo de lenguaje opere Fusion, no un verificador. (El volcado completo de herramientas no se incluye en este repositorio.)

Relevancia para etapas posteriores: es un canal **oficial** de comunicación con Fusion, y `activeCommand` permite ver lo que
el diseñador está editando *antes* de que confirme la operación.

## Herramientas intermediarias que conviene construir

1. **Rastreador de procedencia** (T1 durante la sesión y T2 como respaldo): mantiene, por `entityToken`, el origen y
   las modificaciones de cada cara. Se dispara con `ui.commandTerminated`. Es la base de la matriz de trazabilidad.
2. **Biblioteca de análisis geométrico** en Python puro: clasificador de aristas (T4), reconocedor de cavidades por AAG (T5),
   accesibilidad y espesor por rayos (T6, T7) y trazado a boceto (T8). Es la capa de medición del motor de reglas.
3. **Verificador topológico externo** (OCC, T3b): un proceso aparte, porque el Python de Fusion (3.14) no tiene estas
   dependencias. Se invoca con la exportación STEP. La validez compuesta (T3) queda como verificación rápida dentro de Fusion.
4. **Capa de retroalimentación** (T11): resaltado, reporte en una paleta y configuración guardada en el documento.
5. **Canal de ejecución**: un puente local (ClaudeBridge, no incluido) para el desarrollo; el MCP oficial es una alternativa para etapas posteriores.

## Límites que siguen abiertos

- **Muestreo**: T6 y T7 usan una grilla de 5×5 o 4×4 puntos por cara, así que una obstrucción pequeña puede escaparse. Con más puntos aumenta el costo.
- **Eje de la herramienta fijo en +Z**: una pieza con varias preparaciones necesitará probar varias direcciones.
- **Profundidad de agujeros**: el AAG incluye la punta cónica (21,8 mm en vez de 20). La regla debería usar la longitud del cilindro.
- **Abertura de una cavidad**: se aproxima con la caja envolvente, lo que sirve para cavidades rectangulares pero no para formas irregulares.
- **OCC con piezas inválidas**: todavía no se probó con una pieza realmente inválida (todas las de prueba eran válidas).
- **Eventos**: falta probar `commandTerminated` con operaciones reales del usuario, incluidos deshacer y editar una operación antigua.
