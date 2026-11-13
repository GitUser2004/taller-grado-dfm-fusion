# Taller de grado: reglas de fresado verificadas en Fusion 360

Avance del proyecto de grado *Prevención de la propagación de defectos en el modelado paramétrico mediante verificación
progresiva asistida por modelos de lenguaje en Fusion 360* (Ingeniería Mecatrónica, IMT353).

Este repositorio reúne **solo los dos primeros objetivos específicos**:

1. **Recopilación de material para las reglas.** *Elaborar un catálogo de reglas geométricas para fresado de 3 ejes, con
   umbrales configurables y las fuentes que los respaldan.*
2. **Exploración de la API de Fusion 360.** *Establecer, mediante la API de Fusion 360, la correspondencia entre entidades
   B-Rep, mediciones y reglas, validándola con prototipos.*

Las etapas siguientes (motor de reglas por tipo de operación, complemento, asistencia con modelo de lenguaje y
verificación final) no forman parte de este avance.

## Resultados principales

| Resultado | Dónde |
|---|---|
| Catálogo v0.1: 11 reglas en dos categorías (diseño preliminar y proceso), con umbrales de advertencia y error y sus fuentes | [`docs/catalogo_reglas.md`](docs/catalogo_reglas.md), [`src/dfm/catalog.json`](src/dfm/catalog.json) |
| Límites de la API de Fusion y técnicas para suplirlos (T1–T11) | [`probes/02_limites_y_tecnicas.md`](probes/02_limites_y_tecnicas.md) |
| Rastreador de procedencia: cada cara con su operación de origen, las operaciones que la modificaron y los parámetros que la controlan; **25/25 comprobaciones aprobadas** | [`probes/03_rastreador_procedencia.md`](probes/03_rastreador_procedencia.md) |
| Cinco piezas de prueba modeladas con historial y parámetros; en las que se calculó a mano, el volumen coincide | [`models/README.md`](models/README.md), [`docs/metricas_piezas.md`](docs/metricas_piezas.md) |
| Inyección de defectos: **8/8 casos aprobados** (6 detecciones y 2 controles), con traza al parámetro y reversión exacta | [`docs/inyeccion_defectos.md`](docs/inyeccion_defectos.md) |

## Mapa del repositorio

### Objetivo 1: material para las reglas

| Ruta | Contenido |
|---|---|
| [`bibliografia/`](bibliografia/README.md) | Todas las fuentes, con enlace, fecha de consulta y dónde se usan; entradas BibTeX en `referencias.bib` |
| [`docs/catalogo_reglas.md`](docs/catalogo_reglas.md) | Catálogo v0.1: reglas, categorías, severidades, umbrales y por qué se eligió cada uno |
| [`src/dfm/catalog.json`](src/dfm/catalog.json), [`catalog.py`](src/dfm/catalog.py) | Datos del catálogo y cargador con validación de rangos |
| [`docs/reglas_maquina_real.md`](docs/reglas_maquina_real.md) | Propuesta (no implementada) para ligar los umbrales a una máquina (Haas VF-2) y a catálogos de herramientas |
| [`docs/piezas_de_prueba.md`](docs/piezas_de_prueba.md) | Selección de piezas de prueba y conjuntos de datos |

### Objetivo 2: exploración de la API

| Ruta | Contenido |
|---|---|
| [`probes/01_*`](probes/01_api_probe_hallazgos.md) | Sondeo inicial: cara → operación, mediciones, estabilidad tras un cambio de parámetro, eventos |
| [`probes/02_*`](probes/02_limites_y_tecnicas.md) | Límites de la API y técnicas para suplirlos |
| [`probes/03_rastreador_procedencia.md`](probes/03_rastreador_procedencia.md), [`src/dfm/provenance.py`](src/dfm/provenance.py), [`tests/`](tests/) | Rastreador de procedencia y su prueba |
| [`probes/04_inventario_api.py`](probes/04_inventario_api.py) | Inventario de los datos que entrega la API en cada paso del diseño |
| [`src/dfm/analysis.py`](src/dfm/analysis.py), [`metrics.py`](src/dfm/metrics.py) | Mediciones sobre la B-Rep (topología, aristas, cavidades, espesor, accesibilidad) y aplicación del catálogo con traza |
| [`models/`](models/README.md) | Scripts que construyen las cinco piezas de prueba, sus reportes y métricas (`models/metrics/`) |
| [`tools/`](tools/) | Medición de una pieza (`run_metrics.py`), inyección de defectos (`inject_defects.py`), verificación externa con OpenCASCADE (`occ_check.py`), demostración (`demo_video.py`) y cliente del puente (`fusion_bridge.py`) |

## Cómo se ejecuta

- Requiere **Autodesk Fusion 360** (Windows o macOS). Todo el código de `src/`, `probes/`, `models/` y `tests/` corre
  **dentro de Fusion** con su Python embebido, que no trae numpy.
- Durante el desarrollo, los scripts se enviaron a Fusion con un complemento puente local (ClaudeBridge) y su cliente
  `tools/fusion_bridge.py`. **El complemento no está en este repositorio.** Los modelos también se pueden correr desde
  Fusion: Shift+S > Scripts > + > Run.
- Varios scripts usan la ruta fija `C:\taller\taller-grado-dfm-fusion` (`ROOT_DIR`, `sys.path`). Si el repositorio se
  clona en otra ubicación, hay que ajustarla.
- `tools/occ_check.py` corre fuera de Fusion y necesita `pip install cadquery-ocp`.

## Material de terceros

Los planos PDF de Make It From Metal y los documentos de Haas y Harvey se usaron con fines educativos y **no se incluyen**
(los planos dicen "Proprietary and confidential"). Los enlaces a cada fuente están en
[`bibliografia/README.md`](bibliografia/README.md).
