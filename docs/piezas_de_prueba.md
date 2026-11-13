# Piezas de prueba para fresado de 3 ejes

Borrador del conjunto de piezas de prueba (Objetivos 2 y 5). Fecha: 2026-11-04.

## Criterio de selección

El objetivo 2 pide trazar **cara → operación → parámetro**. Eso solo es posible si la pieza
se modela en Fusion con historial. Por eso las fuentes se separan en dos usos:

| Uso | Necesita | Fuente adecuada |
|---|---|---|
| Trazabilidad (cara → operación → parámetro) | Plano totalmente acotado para remodelar con historial | Proyectos de taller (sección A), piezas sintéticas (D) |
| Exactitud de la medición (radio, profundidad, espesor) | Geometría exacta de referencia | STEP de NIST (sección B) |
| Escala y variedad de features | Muchos modelos etiquetados por cara | MFCAD++ (sección C) |

Un STEP importado llega a Fusion como cuerpo sin historial, así que sirve para validar
mediciones pero no para trazar el parámetro de origen.

## A. Proyectos de taller con planos (remodelar con historial)

Fuente: Make It From Metal, 13 proyectos con planos PDF gratuitos, también enlazados por el
Design Lab de la University of Florida como piezas de entrenamiento. Planos descargados el
2026-11-04; **no se incluyen en este repositorio** (se obtienen desde el enlace de `bibliografia/README.md`).

**Licencia:** cada plano dice "Proprietary and confidential" y prohíbe la reproducción
**no educativa** sin permiso escrito. Una tesis es uso educativo, pero hay que citar la fuente
y no redistribuir los PDF. Por eso este repositorio incluye los scripts que remodelan las piezas, pero no los planos.

Todos los planos están en **pulgadas** (tamaño A). Se revisaron hoja por
hoja; solo entran piezas de un solo cuerpo fresadas en 3 ejes.

### Seleccionadas

| Prioridad | Pieza (plano) | Features de fresado | Qué pone a prueba | Defecto a inyectar |
|---|---|---|---|---|
| 1 ✅ modelada (`models/vise_base.py`) | Toolmaker's Vise, **base** (DWG 002) | Ranura pasante con cajera escalonada (R.250 típ.), 8× Ø.375 pasantes, 2× 1/4-20, escalón, **ranura de alivio "1/8 U-cut"** (detalle A) | Radio interno, aspecto de ranura, **accesibilidad**: el U-cut es un socavado que no se alcanza desde +Z | Bajar R.250 por debajo del radio de herramienta; profundizar la ranura |
| 1 | Toolmaker's Vise, **mordaza** (DWG 003) | Cara a 45°, caja Ø1.000 ↓.250 + Ø.500 pasante **perpendicular a la cara a 45°**, escalón de .120 | Accesibilidad y número de montajes (la caja exige inclinar la pieza) | Mover la caja a una cara no accesible |
| 1 | 123 Superblock (DWG 001) | 23 agujeros 1/4-20 con caja Ø.375 en 3 caras, alternando lados; cajas de .75, 1.75 y **2.75 de profundidad** | **Relación de aspecto**: la caja Ø.375 ↓2.75 tiene L/D ≈ 7,3, por encima de 6×D. Es intencional en la pieza real, así que prueba si el motor distingue taladrado de cajera fresada | Reducir la separación .500 hasta dejar pared < 0,8 mm entre agujeros |
| 1 | Vee Block (DWG 002) | Dos V a 90°, **ranuras de alivio de .250 con esquinas vivas** en el fondo de cada V, muescas laterales de .375 | Radio interno: las esquinas vivas son horizontales (las hace el costado de la fresa), no verticales; prueba que la regla dependa de la dirección de la herramienta | Eliminar la ranura de alivio → arista interna viva en el fondo de la V |
| 1 | Tap Guide Block (DWG 001) | V de 90° **sin alivio**, 8 agujeros pasantes Ø.136 a Ø.500 | Arista interna viva legítima (se hace con fresa en V): el motor no debería marcarla si la operación es un chaflán o fresa en V. Agujero Ø.136 con L/D ≈ 4 | Reemplazar la V por una cajera recta de fondo vivo |
| 2 | Vee Block **Clamp** (DWG 003) | Perfil en U, R.500 exterior, **pared de .219** | Espesor de pared, radio interno de la U | Adelgazar la pared por debajo del umbral |
| 2 | Micrometer Stand **block** (DWG 002) | Ranura inclinada a 45° de .590, chaflanes .750×45° y .500×45°, ranura vertical de .250, 3/8-16 pasante | Accesibilidad de caras inclinadas, aspecto de ranura angosta (.250) | Ranura vertical más profunda que 4× su ancho |
| Control | Edge Clamp **body** (DWG 002) | Ranura pasante .531 con caja .800, 1/2-13 pasante, bloque 1×1.25×4 | Pieza limpia: con umbrales por defecto debería dar 0 violaciones | — |

### Descartadas

- Machinist's Hammer: el mango es de torno y la cabeza es cilíndrica con conos de 20°;
  no es una pieza de fresado de 3 ejes.
- Toolmaker's Vise **nut**, 123 Block **cap screw**: piezas de torno.
- Micrometer Stand **jaw**, Edge Clamp **jaw**: prismas triviales (un chaflán o un avellanado);
  sirven solo como casos mínimos de humo.

### Cotas faltantes (hay que asumirlas al modelar)

- Vee Block: no está acotada la profundidad horizontal de las muescas laterales.
- Micrometer Stand block: confirmar la profundidad de la ranura vertical de .250 en las
  hojas 4 y 5.

Las piezas se terminan con rectificado y tratamiento térmico; el sistema solo evalúa la etapa
de fresado.

## B. Modelos NIST MBE/PMI (validar la exactitud de las mediciones)

Fuente: [NIST MBE PMI Validation and Conformance Testing](https://www.nist.gov/el/systems-integration-division-73400/mbe-pmi-validation-and-conformance-testing-project).
NIST declara que los casos de prueba, modelos CAD y STEP pueden usarse sin restricciones y
pide reconocimiento.

- **FTC 6, 8 y 9** (Fully-Toleranced Test Cases): piezas mecanizadas con agujeros, cajeras y
  chaflanes, en pulgadas, ASME Y14.5. Se usan como referencia exacta para comparar lo que mide
  el complemento contra la geometría real.
- Los planos PDF no bastan para remodelar: indican que el modelo CAD es necesario para completar
  la definición del producto (es MBD). Por eso estas piezas entran como STEP, no como plano.
- Descargas: [STEP AP242/AP203 de todos los casos](https://www.nist.gov/document/nist-pmi-step-files)
  (zip de más de 10 MB) y planos individuales `nist-cad-model-ftc-06` … `ftc-11`.
- FTC 7, 10 y 11 no se modelaron en ningún CAD dentro del proyecto; se descartan.

## C. MFCAD++ (escala, trabajo futuro o validación adicional)

[MFCAD++](https://pure.qub.ac.uk/en/datasets/mfcad-dataset-dataset-for-paper-hierarchical-cadnet-learning-from/):
59 665 modelos STEP con una etiqueta de feature de mecanizado por cara (25 clases), licencia
CC BY. Es el conjunto de Hierarchical CADNet, ya citado en el perfil como [6].
Sirve para medir cuántas caras clasifica bien el motor a nivel de entidad, pero no tiene
historial. El espejo de Hugging Face exige solicitud de acceso.

## D. Piezas sintéticas paramétricas (generadas por script)

Piezas generadas con la API, con cada defecto controlado por un único parámetro de usuario.
Son las que dan la matriz de trazabilidad más limpia:

1. Bloque con cajera rectangular: `pocket_D`, `pocket_W`, `r_corner`.
2. Bloque con ranura pasante: `slot_W`, `slot_L`.
3. Placa con agujeros ciegos: `hole_D`, `hole_depth`.
4. Pared delgada entre dos cajeras: `wall_t`.
5. Pieza de prueba tipo círculo-diamante-cuadrado: la forma es habitual en pruebas de máquinas
   (NAS 979, ISO 10791-7), pero esas normas son de pago, así que se modela una versión propia
   inspirada en ellas, sin reclamar sus cotas.

## Umbrales iniciales (para el objetivo 1, a confirmar con más fuentes)

Valores de guías DFM de proveedores ([Hubs](https://hubs.com/knowledge-base/how-design-parts-cnc-machining)
y otras); son punto de partida, no la referencia definitiva del catálogo:

| Regla | Umbral recomendado | Nota |
|---|---|---|
| Radio interno vertical | ≥ 1/3 de la profundidad de la cavidad | Otras guías: ≥ 1,3 × radio de herramienta |
| Profundidad de cavidad | ≤ 4 × mayor dimensión en XY | Más de 6 × D de herramienta exige herramienta especial |
| Radio de fondo | 0,5 mm, 1 mm o sin radio | |
| Espesor de pared | 0,8 mm metal / 1,5 mm plástico | Factible: 0,5 mm / 1,0 mm |

Las guías no coinciden del todo (por ejemplo, la fórmula R = H/10 + 0,5 mm de JLC da radios
menores), lo que respalda tener umbrales configurables por proceso y máquina.

## Fuentes

- NIST, MBE PMI Validation and Conformance Testing: https://www.nist.gov/el/systems-integration-division-73400/mbe-pmi-validation-and-conformance-testing-project
- NIST, descargas: https://www.nist.gov/el/systems-integration-division-73400/mbe-pmi-validation-and-conformance-testing/download-free-cad
- NIST, navegador de modelos: https://pages.nist.gov/CAD-PMI-Testing/models.html
- Make It From Metal, 13 proyectos: https://makeitfrommetal.com/13-practical-machining-projects-for-students-and-beginners/
- UF Design Lab, Training Parts: https://web.mae.ufl.edu/designlab/Advanced%20Manufacturing/Training%20Parts/Training%20Parts.htm
- MFCAD++ (QUB): https://pure.qub.ac.uk/en/datasets/mfcad-dataset-dataset-for-paper-hierarchical-cadnet-learning-from/
- MFCAD++ (Hugging Face): https://huggingface.co/datasets/AI4Manufacturing/mfcadpp
- Hubs, diseño para mecanizado CNC: https://hubs.com/knowledge-base/how-design-parts-cnc-machining
- JLCCNC, guía de diseño: https://jlccnc.com/help/article/CNC-Machining-Design-Guideline
- ISO 10791-7:2020 (de pago): https://www.boutique.afnor.org/en-gb/standard/iso-1079172020/test-conditions-for-machining-centres-part-7-accuracy-of-finished-test-piec/xs132627/130204
