# Rastreador de procedencia (herramienta intermediaria n.º 1)

Código: `src/dfm/provenance.py` · Prueba: `tests/test_provenance_fusion.py` (se ejecuta dentro de Fusion vía ClaudeBridge)
· Resultado: `tests/test_provenance_fusion.result.json`, con **25/25 comprobaciones aprobadas** (2026-11-04).

## Qué responde

Para cada cara y arista del cuerpo:

1. **Operación de origen**: la que la creó.
2. **Operaciones que la modificaron**, en el orden de la línea de tiempo: la API no da esta información.
3. **Qué la controla**: los parámetros de su operación según el rol de la cara (fondo → distancia, pared → curva del boceto
   y sus cotas, redondeo → radio, agujero → diámetro o profundidad) y, para la respuesta exacta, un **análisis de sensibilidad**.

Ejemplo real (cara superior del bloque): `origin = Block`, `modified_by = [Pocket1, Pocket1 corners, Pocket2, Pocket3, Hole]`.

## Diseño

Una sola operación, `_step(operación)`, lleva la procedencia del estado anterior del modelo al estado actual:

| Lo que le pasa al `entityToken` de una cara anterior | Interpretación |
|---|---|
| Ya no resuelve a ninguna cara | La cara fue consumida |
| Resuelve a más de una cara | Se dividió: cuenta como modificada |
| Dos caras anteriores resuelven a la misma | Se fusionaron: cuenta como modificada |
| La huella (área, aristas, lazos, caja envolvente) cambió | Modificada |
| Una cara actual no viene de ningún token anterior | Creada por esta operación |

Esa operación se usa de dos formas:

- **`update()`** se llama tras cada comando del usuario y compara una firma (operaciones, supresión, marcador, expresiones de todos los parámetros):
  - **noop**: nada cambió en la geometría (por ejemplo, solo se creó un parámetro de usuario).
  - **append**: hay una operación nueva al final, así que basta con **un paso**.
  - **rebuild**: cualquier otro cambio (editar un parámetro, mover el marcador, insertar a mitad de la línea de tiempo, suprimir, borrar).
- **`rebuild()`** repite la línea de tiempo hasta el marcador con `rollTo`, un paso por operación con geometría (salta bocetos y planos),
  y **devuelve el marcador a donde lo tenía el usuario**.

El estado se indexa por `entityToken` y se reindexa en cada paso, porque los `tempId` cambian con cada recálculo.
`save()` y `load()` lo guardan en los atributos del documento, así que sobrevive a guardar y reabrir.

## Escenarios probados

| Escenario | Resultado |
|---|---|
| Construir la pieza llamando a `update()` tras cada operación | Todo en modo *append*. El origen coincide con `Feature.faces` en el 100 % de las caras |
| Incremental vs. repetición completa | **Idénticos** en caras y aristas |
| Editar `p1_D` (operación anterior) | *rebuild*. La procedencia no cambia |
| Mover el marcador antes del agujero | *rebuild*. El estado retrocedido no contiene caras del agujero |
| Insertar Pocket4 a mitad de la línea de tiempo | *rebuild* (no se confunde con *append*). Los modificadores salen en el orden correcto: `…Pocket3, Pocket4, Hole` |
| Suprimir Pocket2 | Desaparece de toda la procedencia |
| Borrar Pocket3 | Desaparece de los modificadores de la cara superior |
| Guardar → instancia nueva → cargar | Registros idénticos. El siguiente `update()` da *noop* |

## Trazado hasta el parámetro: heurística vs. sensibilidad

**Heurística** (`face_controls`, inmediata): empareja la pared con su curva del boceto (`profileCurves`) y busca las cotas que tocan
la curva o sus puntos. Funciona para fondos, redondeos y agujeros. Para paredes es **incompleta**: en la pared larga de Pocket1 encontró
`p1_W` pero no `p1_L`, porque esa cota está en la línea opuesta y llega a esta pared por las restricciones del rectángulo.
**La API no expone el grafo de restricciones del solver del boceto.**

**Sensibilidad** (`sensitivity`, exacta): mueve cada parámetro independiente un 1 %, recalcula, mide el efecto sobre la entidad
(radio, desplazamiento del plano, área, movimiento) y restaura el valor. Resultados:

| Entidad | Parámetros con efecto |
|---|---|
| Pared larga de Pocket1 | `p1_W` → desplaza el plano · `p1_L`, `p1_D`, `p1_r` → área · `blk_H` → solo la mueve (**dependencia indirecta** a través del plano superior) |
| Radio de esquina de Pocket1 | Solo `p1_r` cambia el **radio**. `p1_D` y `blk_H` cambian el área o la posición |
| Radio de esquina de Pocket3 | **Ninguno** de los 13 parámetros cambia el radio, así que el radio no es paramétrico: la corrección tiene que ser "acotar el arco" |

Hallazgo de paso: cambiar `p1_L` desplaza la pared 0,2 mm, cuando un rectángulo centrado debería crecer simétricamente. El centro del
boceto no está fijado (el rastreador lo reporta como `fully_constrained: false`). Es un **defecto de diseño preliminar**, el tipo de
error que el catálogo debe distinguir de una violación de proceso.

Costo de la sensibilidad: un recálculo por parámetro (≈100–150 ms cada uno). Conviene **bajo demanda**, solo para las entidades con una violación.
Cada recálculo agrega pasos al historial de deshacer (el valor se restaura).

## Limitaciones conocidas

- El tiempo de *append* crece con el tamaño del modelo (de 1 a 120 ms en esta pieza), porque cada registro se resuelve con
  `findEntityByToken`. Se puede optimizar resolviendo solo las caras vecinas a la operación nueva.
- La repetición completa tarda entre 0,3 y 0,7 s en esta pieza y crece con la línea de tiempo. Habrá que medirla en piezas reales.
- Las operaciones agrupadas (`TimelineGroup`) y los componentes que no son la raíz no se probaron.
- La sensibilidad con un 1 % puede cruzar un límite topológico (la cara se divide o desaparece). En ese caso lo reporta como `split` o `consumed`, no como error.
- Falta conectarlo al evento `ui.commandTerminated` y probarlo con operaciones manuales, incluidos deshacer y rehacer.
