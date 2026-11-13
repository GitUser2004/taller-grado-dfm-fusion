# Bibliografía del proyecto

Actualizada: 2026-11-12. Reúne todas las fuentes citadas en `docs/`, en `src/dfm/catalog.json` y en
el perfil de tesis. Las entradas en BibTeX están en [`referencias.bib`](referencias.bib).

## Organización

| Carpeta o archivo | Contenido |
|---|---|
| `README.md` | Este índice: cada fuente con su identificador, enlace, fecha de consulta y dónde se usa |
| `referencias.bib` | Las fuentes técnicas de las secciones 1 a 6 en BibTeX (las 43 del perfil viven en el `.bib` de la tesis) |

**Identificadores.** Las fuentes del catálogo de reglas conservan el `id` de `src/dfm/catalog.json` (por ejemplo `HUBS`,
`GUPTA1997`); las nuevas usan el mismo estilo. Las del perfil se citan con su número, `[1]` a `[43]`.

**Uso y licencia.** Los planos de Make It From Metal dicen "Proprietary and confidential" y los documentos de Haas y Harvey
son comerciales: se usaron con fines educativos, citando la fuente, y **no se incluyen en este repositorio**. Todos se
obtienen desde los enlaces de abajo.

## 1. Máquina: Haas VF-2 y Mini Mill

| ID | Referencia | Archivo local | Usada en |
|---|---|---|---|
| HAAS_VF2 | Haas Automation, [VF-2: especificaciones](https://www.haascnc.com/machines/vertical-mills/vf-series/models/small/vf-2.html). Consultada 2026-11-12 | — | Recorridos, husillo-mesa, rpm, cambiador (`reglas_maquina_real.md` §2, P1, P7, P8) |
| HAAS_VF2_MLD | Haas Automation, [VF-2/VF-2SS/VF-2TR, plano de instalación](https://pub-aem.haascnc.com/content/dam/haascnc/pdp_feed/mld/vf-2_mld__1_2023.pdf), 2023-01-17 | no incluido | Búsqueda del largo máximo de herramienta (no figura) |
| HAAS_MINI | Haas Automation, [Mini Mill, folleto 2023](https://www.haascnc.com/content/dam/haascnc/assets/seriesflyers/mini-mill-reboot/23_12_MiniMill_4Pager.pdf) | no incluido | Comparación con la VF-2 (§2) |
| HAAS_ATC | Haas Automation, [Manual del operador: cambiador tipo paraguas](https://www.haascnc.com/service/online-operator-s-manuals/mill-operator-s-manual/mill---umbrella-tool-changer.html) | — | Capacidad y límites de herramienta (P7) |
| HAAS_MANUAL | Haas Automation, [Mill NGC Operator's Manual](https://www.haascnc.com/content/dam/haascnc/en/service/manual/operator/english---mill-ngc---operator's-manual---2020.pdf), 2020 | — | Remite al plano de cada máquina para el largo de herramienta |
| HAAS_VISE | Haas Automation, [Vise options and configurations](https://pub-aem.haascnc.com/content/dam/haascnc/assets/printdocuments/ViseOptionsAndConfigurations.pdf) | — (PDF de imagen, sin texto) | Apertura de mordaza: **dato no obtenido** |
| HAAS_TORQUE | Haas Automation, [VF 40-taper series: curvas de par y potencia](https://pub-aem.haascnc.com/content/dam/haascnc/productivity/spindles/torque-chart-jpg/torque-chart-machine-pdp-binder-/VF-40T%20Series%20Binder.pdf) | — | Consultada; no se usa en las reglas |

## 2. Herramientas de corte (aluminio 6061)

| ID | Referencia | Archivo local | Usada en |
|---|---|---|---|
| HAAS_HM42 | Haas Tooling, [Speeds and Feeds HM42 3FL](https://haascnc.com/content/dam/haascnc/ecommerce-assets/linedrawings/milling/end_mills/speeds-and-feeds/Speeds%20and%20Feeds_HM42-3FL.pdf) | no incluido | ap/ae estándar, regla del −50 % en alcance largo, Vc (P3, P8) |
| HARVEY_LR | Harvey Tool, [Miniature End Mills – Square – Long Reach, Stub Flute](https://www.harveytool.com/products/miniature-end-mills---square---long-reach-stub-flute). Tabla leída en parte (144 filas) | — | Diámetros desde 0,13 mm, alcances 5–30×D (P2, P3) |
| HARVEY_SF | Harvey Tool, [hoja de velocidades SF_739900](https://harveyperformance.widen.net/content/34je46ewxv/original/SF_739900.pdf) | no incluido | Vc de 1000 SFM en aluminio forjado (P2, P8) |
| HARVEY_LOUPE | Harvey Performance, [In The Loupe: tool breakage](https://www.harveyperformance.com/in-the-loupe/tag/tool-breakage/) | — | Escalado de la flexión con largo y diámetro (P3) |
| SANDVIK_860 | Sandvik Coromant, [CoroDrill 860](https://www.sandvik.coromant.com/en-gb/tools/drilling-tools/solid-carbide-drills/corodrill-860) | — | Broca de aluminio Ø3–20, 3–8×D (P4) |
| SANDVIK_862 | Sandvik Coromant, [CoroDrill 862](https://www.sandvik.coromant.com/en-gb/tools/drilling-tools/solid-carbide-drills/corodrill-862) | — | Microbroca Ø0,3–3, 9×D; 16×D con piloto (P4) |
| SANDVIK_861 | Sandvik Coromant, [CoroDrill 861](https://www.sandvik.coromant.com/en-gb/tools/drilling-tools/solid-carbide-drills/corodrill-861) | — | Agujero profundo 12–30×D con piloto (P4) |
| SANDVIK | Sandvik Coromant, guía de aplicación de taladrado profundo. **Edición y enlace pendientes** (la reemplaza en parte SANDVIK_861) | — | `hole_aspect` del catálogo v0.1 |
| MMC | Mitsubishi Materials, [Length of cut](https://www.mmc-carbide.com/permanent/courses/70/length-of-cut.html) | — | Flexión ∝ voladizo³ (v0.1 y P3) |
| MMC_EDGE | Mitsubishi Materials, [Cutting edge classification](https://www.mmc-carbide.com/permanent/courses/70/cutting-edge-classification.html) | — | Diámetro equivalente 0,7–0,8 D |

## 3. Guías de diseño para mecanizado (proveedores y CAD)

Consultadas el 2026-11-04. Son la base de los umbrales del catálogo v0.1 ([`docs/catalogo_reglas.md`](../docs/catalogo_reglas.md)).

| ID | Referencia |
|---|---|
| HUBS | Protolabs Network (Hubs), [How to design parts for CNC machining](https://www.hubs.com/knowledge-base/how-design-parts-cnc-machining/) |
| PL_GUIDE | Protolabs, [Design Guidelines: CNC Milling](https://www.protolabs.com/services/cnc-machining/cnc-milling/design-guidelines/) |
| PL_COMPLEX | Protolabs, [Mastering complex features on machined parts](https://www.protolabs.com/resources/design-tips/mastering-complex-features-on-machined-parts/) |
| PL_6WAYS | Protolabs, [6 Ways to Optimize Part Design for CNC Machining](https://www.protolabs.com/resources/design-tips/6-ways-to-optimize-part-design-for-cnc-machining/) |
| JLC | JLCCNC, [CNC Machining Design Guideline](https://jlccnc.com/help/article/CNC-Machining-Design-Guideline), actualizada 2025-08-20 |
| FIVEFLUTE | Five Flute, [CNC Machining DFM: Design Guidelines for Milled Parts](https://www.fiveflute.com/guide/cnc-machining-dfm-design-guidelines-for-milled-parts) |
| DFMX | Dassault Systèmes, ayuda de DFMXpress, SOLIDWORKS 2026 (`lang\spanish\dfmxpress.chm`, instalada) y [versión en línea, regla de cajeras profundas](https://help.solidworks.com/2019/English/SolidWorks/dfmxpress/c_rules_mill_deep_pockets_slots.htm) |

## 4. Artículos sobre fabricabilidad, modelado sólido y mecánica

| ID | Referencia | Usada en |
|---|---|---|
| GUPTA1997 | S. K. Gupta, D. Das, W. C. Regli, D. S. Nau, "Automated manufacturability analysis: A survey", *Research in Engineering Design*, 9(3), 168–190, 1997. doi:10.1007/BF01596601. [PDF del autor](https://www.cs.umd.edu/~nau/papers/gupta1997automated.pdf) | Accesibilidad (P6) y marco general |
| MICROMACH2023 | "Evaluation of Thin Wall Milling Ability Using Disc Cutters", *Micromachines*, 14(2), 341, 2023. doi:10.3390/mi14020341. [Texto en PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9958652/). Autores por completar | Pared: la altura pesa más que el espesor (P5) |
| REQUICHA1980 | A. A. G. Requicha, "Representations for rigid solids: Theory, methods, and systems", *ACM Computing Surveys*, 12(4), 437–464, 1980. Es [38] del perfil | Validez topológica |
| CAMBA2016 | J. D. Camba, M. Contero, P. Company, "Parametric CAD modeling: An analysis of strategies for design reusability", *Computer-Aided Design*, 74, 18–31, 2016. Es [1] del perfil | Parámetros sin uso |

## 5. Piezas de prueba y conjuntos de datos

Consultados el 2026-11-04 (ver [`docs/piezas_de_prueba.md`](../docs/piezas_de_prueba.md)).

| ID | Referencia | Archivo local |
|---|---|---|
| MIFM | Make It From Metal, [13 practical machining projects](https://makeitfrommetal.com/13-practical-machining-projects-for-students-and-beginners/) | no incluido (7 PDF) |
| UFL | University of Florida Design Lab, [Training Parts](https://web.mae.ufl.edu/designlab/Advanced%20Manufacturing/Training%20Parts/Training%20Parts.htm) | — |
| NIST_PMI | NIST, [MBE PMI Validation and Conformance Testing](https://www.nist.gov/el/systems-integration-division-73400/mbe-pmi-validation-and-conformance-testing-project); [descargas](https://www.nist.gov/el/systems-integration-division-73400/mbe-pmi-validation-and-conformance-testing/download-free-cad); [STEP de los casos](https://www.nist.gov/document/nist-pmi-step-files); [navegador de modelos](https://pages.nist.gov/CAD-PMI-Testing/models.html) | — |
| MFCADPP | MFCAD++, [conjunto de datos (QUB)](https://pure.qub.ac.uk/en/datasets/mfcad-dataset-dataset-for-paper-hierarchical-cadnet-learning-from/) y [espejo en Hugging Face](https://huggingface.co/datasets/AI4Manufacturing/mfcadpp). Acompaña a [6] del perfil | — |
| ISO10791_7 | ISO 10791-7:2020, *Test conditions for machining centres — Part 7: Accuracy of finished test pieces* ([ficha AFNOR](https://www.boutique.afnor.org/en-gb/standard/iso-1079172020/test-conditions-for-machining-centres-part-7-accuracy-of-finished-test-piec/xs132627/130204), de pago) | — |

## 6. Documentación de software

| ID | Referencia | Usada en |
|---|---|---|
| FUSIONAPI | Autodesk, *Fusion API Reference Manual* (ayuda en línea): `TimelineObject.healthState`, `entityToken`, `findBRepUsingRay`, `Attributes`. **Enlace exacto pendiente** | `probes/`, `src/dfm/` |

## 7. Estado del arte (perfil de tesis)

Copiadas de la bibliografía del perfil de tesis. Las marcadas con ★ también se usan en el trabajo técnico.

**CAD paramétrico y calidad de modelos**
- ★ [1] J. D. Camba, M. Contero, P. Company, "Parametric CAD modeling: An analysis of strategies for design reusability", *Computer-Aided Design*, 74, 18–31, 2016.
- [2] K. Cheng, A. Olechowski, S. Zhou, "It's a complete haystack: Understanding dependency management needs in computer-aided design", *Proc. ACM HCI*, 9(7), CSCW436, 2025. arXiv:2508.05940.
- [20] P. Company, M. Contero, J. D. Camba, A. Aranburu, D. Justel, "A hierarchical multilevel modeling framework for the creation of high-quality solid models in parametric feature-based CAD systems", *Computer-Aided Design & Applications*, 22(2), 229–244, 2025.
- [21] J. D. Camba, M. Contero, P. Company, N. Hartman, "The cost of change in parametric modeling: A roadmap", *Computer-Aided Design & Applications*, 18(3), 634–643, 2021.
- [22] B. Ekins, "Understanding geometry and B-Rep in Inventor and Fusion 360", Autodesk University, Las Vegas, 2018, clase SD224080.
- [23] X. Dong et al., "HistCAD: A constraint-aware parametric history-based CAD representation, dataset, and benchmark with industrial complexity", arXiv:2602.19171, 2026.
- [24] P. Burggräf, J. Wagner, T. Saßmannshausen, T. Weißer, O. Radisic-Aberger, "AI-artifacts in engineering change management: A systematic literature review", *Research in Engineering Design*, 35(2), 215–237, 2024.
- [25] M. Contero, D. Pérez-López, P. Company, J. D. Camba, "A quantitative analysis of parametric CAD model complexity and its relationship to perceived modeling complexity", *Advanced Engineering Informatics*, 56, 101970, 2023.
- [26] A. Aranburu, D. Justel, M. Contero, P. Company, J. D. Camba, "Are we using effective modeling strategies in parametric associative CAD?", Proc. CAD'24, Eger, 115–120, 2024.
- [27] C. González-Lluch, R. Plumed, P. Company, "From negative knowledge to best practices for enhancing reusability of sketches in procedural 3D CAD models", *Designs*, 9(6), 132, 2025.
- ★ [38] A. A. G. Requicha, "Representations for rigid solids: Theory, methods, and systems", *ACM Computing Surveys*, 12(4), 437–464, 1980.

**Verificación de fabricabilidad y reconocimiento de features**
- [3] S. Baltadouros, J. R. Duflou, "Process-aware thickness analysis in CAD models using hybrid geometric methods", arXiv:2609.15245, 2026.
- [4] H. Lee, C. Yeo, S. Lim, B. C. Kim, K. C. Bae, D. Mun, "Rule-based design verification for mechanical parts with dynamic rule subset selection", *Scientific Reports*, 15, 17153, 2025.
- [5] M. Ballegeer, D. F. Benoit, "BenDFM: A taxonomy and synthetic CAD dataset for manufacturability assessment in sheet metal bending", arXiv:2603.13102, 2026.
- ★ [6] A. R. Colligan, T. T. Robinson, D. C. Nolan, Y. Hua, W. Cao, "Hierarchical CADNet: Learning from B-Reps for machining feature recognition", *Computer-Aided Design*, 147, 103226, 2022.
- [28] J. Lee, C. Yeo, S.-U. Cheon, J. H. Park, D. Mun, "BRepGAT: Graph neural network to segment machining feature faces in a B-rep model", *J. Computational Design and Engineering*, 10(6), 2384–2400, 2023.
- [29] N. Heidari, A. Iosifidis, "Geometric deep learning for computer-aided design: A survey", arXiv:2402.17695, 2024.

**LLM y agentes para CAD y DFM**
- [7] L. Zhang, B. Le, N. Akhtar, S.-K. Lam, T. Ngo, "Large language models for computer-aided design: A survey", *ACM Computing Surveys*, 2026. arXiv:2505.08137.
- [8] W. Wu et al., "AI-driven generation of 3D CAD models: A survey", *Computational Visual Media*, 12(3), 575–614, 2026.
- [9] K. Welbeck, X. Shi, Z. Sadeghi, Q. Zhu, P. Guo, "LLM-aided design for manufacturing: A multi-agent system for intent-preserving redesign of CAD for improved manufacturability", arXiv:2609.05559, 2026.
- [10] E. George, C. Keefe, P. Pak, A. Barati Farimani, "AgentsCAD: Automated design for manufacturing of FDM parts via multi-agent LLM reasoning and geometric feature recognition", arXiv:2607.02448, 2026.
- [11] D. Mallis et al., "CAD-Assistant: Tool-augmented VLLMs as generic CAD task solvers", ICCV 2025, 7284–7294.
- [12] J. Li et al., "CAD-Llama: Leveraging large language models for computer-aided design parametric 3D model generation", CVPR 2025, 18563–18573.
- [13] Y. Guan et al., "CAD-Coder: Text-to-CAD generation with chain-of-thought and geometric reward", NeurIPS 2025. arXiv:2505.19713.
- [14] Y. Gong, X. Wu, W. Liu, K. Tu, "ToolCAD: Exploring tool-using large language models in text-to-CAD generation with reinforcement learning", arXiv:2604.07960, 2026.
- [15] F. Fan et al., "CADDesigner: Conceptual design of CAD models based on a general-purpose agent", *Computer-Aided Design*, 198, 104087, 2026. arXiv:2508.01031.
- [16] H. Singh, A. Dubey, J. A. Amador Herrera, "CADEngBench: It looks like CAD, but does it work? Evaluating parametric design, assembly reasoning, and physics simulation", arXiv:2608.09296, 2026.
- [17] A. Haag, A. Kaćan, B. Fuchs, O. Lohse, "Test-time scaling for CAD generation via verifier-free consensus selection", arXiv:2608.09706, 2026.
- [18] J. Barkley, R. Loghmani, A. Barati Farimani, "CADSmith: Multi-agent CAD generation with programmatic geometric validation", arXiv:2603.26512, 2026.
- [19] E. Berger, M. Usama, J. Mehlstäubl, B. Saske, K. Paetzold-Byhain, "Physics-in-the-loop: A hybrid agentic architecture for validated CAD engineering design", arXiv:2605.19717, 2026.
- [30] F. Ocker, S. Menzel, A. Sadik, T. Rios, "From idea to CAD: A language model-driven multi-agent system for collaborative design", arXiv:2503.04417, 2025.
- [31] A. Schüpbach, R. San Miguel, J. Ferchow, M. Meboldt, "From text to design: A framework to leverage LLM agents for automated CAD generation", *Proc. Design Society*, 5, 1893–1902, 2025 (ICED25).
- [32] L. Wang et al., "Text2CAD-Bench: A benchmark for LLM-based text-to-parametric CAD generation", arXiv:2605.18430, 2026.
- [33] K. Alrashedy et al., "Generating CAD code with vision-language models for 3D designs", ICLR 2025. arXiv:2410.05340.
- [34] F. Chiarello, S. Barandoni, M. M. Škec, G. Fantoni, "Generative large language models in engineering design: Opportunities and challenges", *Proc. Design Society*, 4, 1959–1968, 2024 (DESIGN 2024).
- [35] E. Berger et al., "Challenges and opportunities in the integration of generative AI with computer-aided design", *Proc. Design Society*, 5, 881–890, 2025 (ICED25).
- [36] Y. Lu et al., "Proactive agent: Shifting LLM agents from reactive responses to active assistance", arXiv:2410.12361, 2024.
- [37] M. Adler, M. Russo, M. Cafarella, "Agent-aided design for dynamic CAD models", Proc. CAIS '26, San Jose, 2026.
- [39] B. T. Jones et al., "A solver-aided hierarchical language for LLM-driven CAD design", *Computer Graphics Forum*, 44(7), e70250, 2025.
- [40] D. Rukhovich et al., "CAD-Recode: Reverse engineering CAD code from point clouds", ICCV 2025, 9801–9811.
- [41] J. Xu et al., "CAD-MLLM: Unifying multimodality-conditioned CAD generation with MLLM", arXiv:2411.04954, 2024.
- [42] X. Xu, J. G. Lambourne, P. K. Jayaraman, Z. Wang, K. D. D. Willis, Y. Furukawa, "BrepGen: A B-rep generative diffusion model with structured latent geometry", *ACM Trans. Graphics*, 43(4), 120, 2024.
- [43] O. Peckham et al., "Artificial intelligence in generative design: A structured review of trends and opportunities in techniques and applications", *Designs*, 9(4), 79, 2025.

## 8. Pendientes

- **Libros de texto (biblioteca):** Kalpakjian y Schmid, *Manufacturing Engineering and Technology*; Groover, *Fundamentals of
  Modern Manufacturing*; Boothroyd, Dewhurst y Knight, *Product Design for Manufacture and Assembly*. Falta confirmar la
  edición disponible y extraer las reglas de fresado y taladrado.
- **Sandvik, taladrado profundo (`SANDVIK`):** ubicar la guía de aplicación vigente.
- **Micromachines 2023:** completar los autores.
- **Fusion API:** registrar el enlace exacto de cada página citada.
- **PDF originales:** no se incluyen; los de Haas, Harvey y Sandvik se descargan desde los enlaces.
