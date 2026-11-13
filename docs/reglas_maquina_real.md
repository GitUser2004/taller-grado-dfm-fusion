# Reglas de fabricabilidad derivadas de una máquina y herramientas reales

Fecha: 2026-11-12 · Máquina: **Haas VF-2** (y Mini Mill para comparar) · Material: **aluminio 6061** (ISO N, forjado)
· Herramientas: **Sandvik Coromant** (brocas), **Harvey Tool** y **Haas Tooling** (fresas) · Estado: **propuesta**, todavía no implementada.

## 1. Por qué replantear

El catálogo v0.1 ([`catalogo_reglas.md`](catalogo_reglas.md)) usa razones fijas tomadas de guías de proveedores de mecanizado
(Hubs, Protolabs, JLCCNC): 4 × ancho, r ≥ prof./3, L/D 4 y 10. Esas razones resumen lo que pasa en un taller, pero no
dicen **por qué**. Al leer los documentos de la máquina y de las herramientas aparece la causa real:

- **La máquina** fija el tamaño de la pieza, la altura disponible, la velocidad del husillo y la cantidad de herramientas.
- **El catálogo de herramientas** fija el radio mínimo posible, la profundidad que alcanza cada fresa y la profundidad que perfora cada broca.
- **Una cavidad es fabricable si existe una herramienta de catálogo que quepa en ella y llegue al fondo**, y la máquina puede usarla.

La propuesta es cambiar las razones fijas por esa pregunta. Cada umbral pasa a ser un dato verificable de un catálogo y
el taller puede reemplazarlo por su inventario real, cambiando la biblioteca de herramientas sin tocar las reglas.

## 2. Datos de la máquina (fuente: Haas)

| Especificación | Haas VF-2 | Haas Mini Mill (2023) | Para qué sirve |
|---|---|---|---|
| Recorridos X / Y / Z | 762 / 406 / 508 mm | 406 / 356 / 381 mm | Tamaño máximo de pieza |
| Husillo a mesa (máx. / mín.) | 610 / 102 mm | 483 / 102 mm | Altura de pieza + sujeción + portaherramienta + herramienta |
| Mesa | 914 × 356 mm, 3 ranuras T de 16 mm | — | Sujeción |
| Carga máxima en la mesa | 1361 kg | — | No limita piezas chicas |
| Husillo | 8100 rpm, 22,4 kW, cono CT40/BT40 | 8000 rpm, 7,5 kW, cono 40 | Herramienta mínima útil (sección 4) |
| Cambiador de herramientas | Carrusel de 20, Ø máx. 89 mm, 5,4 kg | Carrusel de 10 (20 opcional) | Cantidad de herramientas distintas |
| Ejes | 3 (4.º y 5.º opcionales) | 3 | Direcciones de acceso: la herramienta siempre en Z |

**El largo máximo de herramienta no está publicado.** El manual remite al plano de cada máquina, y el plano de la VF-2
no lo trae en texto. El catálogo de prensas de Haas es una imagen sin texto, así que la apertura de mordaza tampoco quedó registrada.

## 3. Datos de las herramientas (aluminio)

### Fresas de punta plana

| Dato | Valor | Fuente |
|---|---|---|
| Diámetros en catálogo (miniatura, alcance largo) | desde **0,005 in (0,13 mm)** hasta 1/4 in | Harvey Tool, *Miniature End Mills – Square – Long Reach, Stub Flute* |
| Alcance disponible | **5×D y 8×D en todos los diámetros**; hasta 12, 18, 22 y **30×D** solo en algunos (0,010, 0,015, 0,020, 1/8 y 3/16 in) | misma tabla (144 filas leídas) |
| Largo de corte de esas fresas | 1,5 × D (filo corto para rigidez, cuello rebajado para no rozar) | misma página |
| Profundidad de corte estándar (fresas Haas HM42 3FL, 6–25 mm) | lateral: ap 1,5 D, ae 0,5 D; ranurado: ap 0,5 D, ae 1 D | Haas Tooling, hoja de velocidades HM42-3FL |
| Penalización por alcance largo | "**reducir la profundidad y el avance un 50 %** con herramientas de filo largo o alcance largo" | misma hoja de Haas |
| Velocidad de corte recomendada | Haas: ~136–180 m/min (6–12 mm) · Harvey: 1000 SFM ≈ 305 m/min en forjado | Haas HM42; Harvey SF_739900 |
| Flexión | proporcional al **cubo del voladizo** y a **1/D⁴** (doble largo → 8 veces; doble diámetro → 16 veces menos) | Harvey (*In The Loupe*); Mitsubishi Materials |

### Brocas (Sandvik Coromant)

| Familia | Diámetros | Profundidad | Notas |
|---|---|---|---|
| CoroDrill 860-NM (no ferrosos: aluminio) | 3–20 mm | **3–8 × D** estándar | refrigeración interna |
| CoroDrill 862 (micro) | 0,3–3,0 mm | **9 × D**; 12 y 16 × D (1–3 mm) **con broca piloto** | refrigeración interna desde 1 mm |
| CoroDrill 861 (agujero profundo, incluye no ferrosos) | 12 × D: 3–20 mm · 15 y 20 × D: 3–12 mm · 30 × D: 3–8 mm | **12–30 × D** | **incluye broca piloto**, sin picoteo |

### Base académica

- **Mecánica de la herramienta:** se modela como una viga en voladizo, δ = F·L³ / (3·E·I), con I = π·d_e⁴/64. El diámetro
  equivalente d_e ≈ 0,7–0,8 D (Mitsubishi Materials). Esto justifica medir la profundidad en múltiplos de D y que el
  costo crezca muy rápido con el alcance.
- **Paredes delgadas:** en un estudio de fresado de paredes delgadas de aluminio con fresas de disco, la deformación depende sobre todo de la **altura**
  de la pared, y el espesor tiene el efecto más bajo de los parámetros estudiados (Micromachines 14(2):341, 2023, doi:10.3390/mi14020341). La pared, entonces, debería
  evaluarse por su relación altura/espesor y no solo por el espesor.
- **Accesibilidad por direcciones de aproximación:** Gupta, Das, Regli y Nau (1997), ya en el catálogo v0.1.
- **Pendiente:** libros de texto, como Kalpakjian y Schmid (*Manufacturing Engineering and Technology*), Groover y
  Boothroyd-Dewhurst. No están accesibles en línea; los resultados de búsqueda solo muestran diapositivas sin las reglas.

## 4. Lo que cambia con estos datos

1. **El radio mínimo no lo fija la existencia de la herramienta, sino el husillo.** Hay fresas de 0,13 mm, pero con
   8100 rpm una fresa de 1 mm gira a 25 m/min, el **8 %** de los 305 m/min que recomienda Harvey, y una de 0,13 mm al 1 %.
   Haas lo admite: su hoja trae una fórmula para escalar el avance "si el taller no tiene las rpm". Con el husillo
   estándar, la fresa más chica que trabaja a la velocidad recomendada mide **5,3 mm** con los datos de Haas y **12 mm** con
   los de Harvey. Por debajo de eso el mecanizado es más lento, y bajo ~1 mm deja de ser práctico.
2. **La profundidad tiene tres niveles reales:**
   - **≤ 3×D:** herramienta estándar con parámetros completos.
   - **Hasta 8×D:** alcance largo disponible en todos los diámetros, pero con la mitad de profundidad y avance (Haas).
   - **Más de 8×D:** solo algunos diámetros en catálogo, hasta 30×D. Después de eso no hay herramienta de catálogo.

   Esto reemplaza las tres reglas de aspecto del catálogo v0.1 y explica de dónde salen las razones de Hubs (4 × ancho) y
   de Five Flute (6 y 10 D).
3. **La profundidad de un agujero depende de su diámetro.** No hay un único L/D: hasta 8×D es estándar (860-NM); hasta
   16 o 30×D se hace con broca piloto (862 y 861), según el diámetro; más allá no hay broca de catálogo. Con estos datos, el L/D de
   19,6 del alivio U-cut de la base de la prensa (Ø3,17) es factible con piloto (861 de 20×D) y deja de ser error.
4. **Un criterio de severidad más claro** para todas las reglas de proceso:

| Severidad | Criterio |
|---|---|
| sin hallazgo | Una herramienta estándar de catálogo, con parámetros completos |
| `warning` | Hace falta una herramienta de catálogo **con parámetros reducidos o una operación extra** (alcance largo, broca piloto, más de una sujeción) |
| `error` | **Ninguna herramienta de catálogo** lo hace, o no entra en la máquina: exige herramienta a medida, electroerosión, otra máquina o más ejes |

## 5. Reglas candidatas

Se agregan al catálogo dos bloques de datos: el **perfil de máquina** (sección 2) y la **biblioteca de herramientas**
(sección 3). Las reglas consultan esos bloques.

| # | Regla | Qué se mide | Criterio propuesto | Fuente | Respecto del catálogo v0.1 |
|---|---|---|---|---|---|
| P1 | **Envolvente de máquina** | Caja envolvente de la pieza en cada orientación de montaje | `error` si no entra en X × Y en ninguna orientación, o si altura + sujeción + portaherramienta + herramienta > husillo-mesa máx. (VF-2: 762 × 406 mm, 610 mm) | Haas VF-2 | Nueva |
| P2 | **Herramienta mínima** (radio interno) | Radio de las aristas cóncavas paralelas a la herramienta | `error` si 2r < D_min del perfil. Valor por defecto **D_min = 1 mm** (r ≥ 0,5) para un husillo de 8100 rpm (punto 1 de la sección 4); configurable a 0,25 mm con un husillo de alta velocidad | Harvey (diámetros), Haas (rpm), Harvey (velocidad de corte) | Mismo umbral (0,5 mm), ahora **justificado por la máquina** |
| P3 | **Alcance de fresa en cavidades** | m = profundidad / D_max, con D_max = min(2·r_mín, ancho de la abertura) | sin hallazgo si m ≤ 3 · `warning` si 3 < m ≤ alcance máximo de catálogo para ese D (8×D para todos; hasta 30×D en algunos) · `error` si m supera todo el catálogo | Harvey (alcances), Haas (−50 %), Mitsubishi y Harvey (flexión) | **Reemplaza** `internal_radius_depth`, `cavity_aspect_tool` y `cavity_aspect_opening` |
| P4 | **Taladrado por familia de broca** | Ø y L/D del agujero | Ø < 0,3 mm `error`. 0,3–3 mm: L/D ≤ 9 sin hallazgo, ≤ 16 `warning` (piloto), > 16 `error`. 3–20 mm: ≤ 8 sin hallazgo, hasta el máximo de la 861 para ese Ø (30 / 20 / 12) `warning` (piloto), después `error`. Ø > 20 mm: `info`, se interpola con fresa y se evalúa como cavidad (P3) | Sandvik 860-NM, 862 y 861 | **Reemplaza** `hole_aspect` y `hole_diameter` |
| P5 | **Pared delgada** | Espesor (ya se mide) y, nuevo, altura de la pared sobre el fondo | Se mantiene 0,5 / 0,8 mm (proveedores). Se agrega una regla candidata de **altura/espesor**: δ ∝ (h/t)³ por la mecánica de viga, y la deformación depende sobre todo de la altura (Micromachines 2023). **El umbral numérico falta**: ningún catálogo lo da y hay que calibrarlo | proveedores (v0.1), mecánica de viga, Micromachines 2023 | Se amplía |
| P6 | **Accesibilidad en 3 ejes** | Caras alcanzables desde ±X, ±Y, ±Z | Igual que v0.1. Con el 4.º eje opcional de la VF-2 se podría reevaluar | Haas (3 ejes), Gupta 1997 | Sin cambio |
| P7 | **Herramientas distintas frente al cambiador** | Cantidad de diámetros de fresa y broca que exige la geometría | `info` si supera la capacidad del cambiador (VF-2 20, Mini Mill 10). Más herramientas exige cambios manuales | Haas | Nueva (informativa) |
| P8 | **Velocidad de husillo** | D de la herramienta exigida frente a D_lim = Vc / (π·n_máx) | `info`: herramienta que trabaja por debajo de la velocidad recomendada (más tiempo de ciclo) | Haas (fórmula de escalado), Harvey y Haas (Vc) | Nueva (informativa; el costo está fuera de alcance) |

Sin cambio: validez topológica, operaciones con error y parámetros sin uso (diseño preliminar).

## 6. Efecto estimado en las piezas de prueba

Calculado a mano con las mediciones ya guardadas (`models/metrics/*.json`), sin volver a medir:

| Pieza | Hoy (v0.1) | Con P3 + P4 | Motivo |
|---|---|---|---|
| Base de la prensa | 1 error / 8 advertencias | **0 / 1** | U-cut Ø3,17 L/D 19,6 → `warning` (861 de 20×D con piloto); los 8 pasantes Ø9,53 L/D 6,53 → sin hallazgo (≤ 8×D, 860-NM); cajeras m = 1,1 y 1,4 → sin hallazgo |
| Tap Guide | 0 / 1 | **0 / 0** | Ø3,45 L/D 4,64 ≤ 8 |
| Vee Block | 0 / 0 | 0 / 0 | ranuras abiertas, m ≤ 1 |
| 123 Superblock | 0 / 8 | **0 / 0** | cajas Ø9,53 con L/D 7,33 y 4,67, ambas ≤ 8 |
| Edge Clamp | 0 / 0 | 0 / 0 | m = 0,7 y 0,8 |

Casos inyectados afectados:
- **D:** Ø1,016 con L/D 14,6 pasa de `error` a `warning`, porque la 862 de 16×D con piloto lo hace.
- **A:** r 0,381 sigue en `error` por herramienta mínima, y además da m ≈ 23 (`warning` u `error` según el diámetro en catálogo).
- **C, E y F:** paredes, sin cambio.

Las reglas basadas en la máquina son **menos estrictas** que las guías de proveedores. Las guías son conservadoras a
propósito: cotizan para cualquier taller. Con las reglas nuevas, una advertencia significa "hace falta algo
concreto" (una broca piloto, una fresa larga con parámetros a la mitad) y no "supera una razón de referencia".

## 7. Límites y pendientes

- **Datos que faltaron:**
  - El largo máximo de herramienta de la VF-2 no está publicado.
  - La apertura de la prensa Haas está en un PDF de imagen.
  - La tabla de Harvey se leyó en parte (144 filas) antes de que el sitio pidiera una verificación anti-bots, que no se sorteó.
- **Fresas grandes:** la biblioteca de fresas de alcance largo cubre solo hasta 1/4 in (6,35 mm). Para diámetros mayores se
  supone 3×D estándar y 8×D largo, sin dato oficial.
- **Biblioteca de herramientas:** representa un taller "con catálogo completo". El taller real tiene menos herramientas;
  la biblioteca debería poder cargarse desde su inventario.
- **Pared (P5):** la regla de altura/espesor no tiene umbral con fuente; calibrarlo es trabajo pendiente (literatura de paredes delgadas o prueba).
- **Fuera de alcance:** las rpm y el tiempo de ciclo son costo, por eso P7 y P8 son solo `info`.
- **Libros de texto:** faltan Kalpakjian, Groover y Boothroyd-Dewhurst, en biblioteca.

## Fuentes

Índice completo de fuentes, extractos locales y BibTeX: [`bibliografia/`](../bibliografia/README.md).

- Haas Automation, [VF-2: especificaciones](https://www.haascnc.com/machines/vertical-mills/vf-series/models/small/vf-2.html) (leída 2026-11-12).
- Haas Automation, [folleto Mini Mill 2023](https://www.haascnc.com/content/dam/haascnc/assets/seriesflyers/mini-mill-reboot/23_12_MiniMill_4Pager.pdf).
- Haas Automation, [Manual del operador, cambiador tipo paraguas](https://www.haascnc.com/service/online-operator-s-manuals/mill-operator-s-manual/mill---umbrella-tool-changer.html).
- Haas Tooling, [hoja de velocidades y avances HM42 3FL](https://haascnc.com/content/dam/haascnc/ecommerce-assets/linedrawings/milling/end_mills/speeds-and-feeds/Speeds%20and%20Feeds_HM42-3FL.pdf).
- Harvey Tool, [Miniature End Mills – Square – Long Reach, Stub Flute](https://www.harveytool.com/products/miniature-end-mills---square---long-reach-stub-flute) y su hoja de velocidades SF_739900.
- Harvey Performance, [In The Loupe](https://www.harveyperformance.com/in-the-loupe/tag/tool-breakage/) (escalado de flexión).
- Sandvik Coromant, [CoroDrill 860](https://www.sandvik.coromant.com/en-gb/tools/drilling-tools/solid-carbide-drills/corodrill-860), [CoroDrill 862](https://www.sandvik.coromant.com/en-gb/tools/drilling-tools/solid-carbide-drills/corodrill-862), [CoroDrill 861](https://www.sandvik.coromant.com/en-gb/tools/drilling-tools/solid-carbide-drills/corodrill-861).
- Mitsubishi Materials, [Length of cut](https://www.mmc-carbide.com/permanent/courses/70/length-of-cut.html) y [Cutting edge classification](https://www.mmc-carbide.com/permanent/courses/70/cutting-edge-classification.html) (diámetro equivalente 0,7–0,8 D).
- [Evaluation of Thin Wall Milling Ability Using Disc Cutters](https://pmc.ncbi.nlm.nih.gov/articles/PMC9958652/), Micromachines 14(2):341, 2023.
- S. K. Gupta et al., [Automated manufacturability analysis: A survey](https://www.cs.umd.edu/~nau/papers/gupta1997automated.pdf), Research in Engineering Design 9(3), 1997.
