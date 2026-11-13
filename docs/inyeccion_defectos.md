# Inyección de defectos controlados

Fecha: 2026-11-04 · Arnés: `tools/inject_defects.py` (dentro de Fusion vía ClaudeBridge) · Datos: `models/metrics/injection_results.json`
· Resultado: **8/8 casos aprobados** (6 detecciones y 2 controles negativos).

> **Actualización (catálogo v0.1):** se volvió a correr con los umbrales del catálogo y siguen aprobados 8/8. Cambian
> severidades: en C y F la pared de 0,635 mm pasa a advertencia (está entre el factible, 0,5, y el recomendado, 0,8); en A el
> aspecto de 22,9 pasa a error; en D aparece además la advertencia de diámetro mínimo. Detalle en
> [`catalogo_reglas.md`](catalogo_reglas.md#validación). La tabla de abajo es la corrida con umbrales provisionales.

```
python tools/fusion_bridge.py tools/inject_defects.py --timeout 1200
```

## Protocolo

En cada caso: **medir → inyectar** (cambiar un parámetro o suprimir una operación) **→ medir → revertir → medir**.
Un caso se aprueba cuando:

1. la regla esperada aparece **solo** después de la inyección (se compara con la medición base);
2. la traza del hallazgo llega al parámetro o a la operación inyectada;
3. al revertir, los hallazgos vuelven a ser idénticos a los de la base.

En los casos de control (E2 y H) se aprueba si **no** aparece ningún hallazgo nuevo.

## Resultados

| Caso | Pieza | Inyección | Hallazgo nuevo | Traza | Revertir restaura | Tiempo de detección |
|---|---|---|---|---|---|---|
| A | Base de la prensa | `vb_cb_R` .250 → .015 in | **error** radio interno 0,381 mm (< 0,5); + advertencia de aspecto 22,9 | `Cajera inferior - radios R.250` → `vb_cb_R` | Sí | 3,2 s |
| B | Base de la prensa | Se suprime `Cajera inferior - radios R.250` | **error** radio interno **0** (aristas verticales vivas) | `Cajera inferior` (el radio deja de ser un parámetro: hay que restaurar la operación) | Sí | 3,6 s |
| C | Base de la prensa | `vb_cb_D` .688 → 1.225 in | **error** pared 0,635 mm (< 0,8); + advertencia r < profundidad/3 | parámetros de las caras delgadas, incluido `vb_cb_D` | Sí | 3,1 s |
| D | Tap Guide | `tg_d1` .136 → .040 in | **error** L/D 14,6 (> 10); la advertencia previa de L/D 4,6 desaparece | `Agujero 1 D0.136 THRU` → `tg_d1` | Sí | 0,8 s |
| E | 123 Superblock | `sb_cb` .375 → .480 in | **error** pared 0,36 mm, en 69 caras | `15X Z cajas lado +` → `sb_cb` | Sí | 8,0 s |
| E2 | 123 Superblock | `sb_pitch` .500 → .400 in (control) | Ninguno. **La geometría no cambia** (mismo volumen) | — | Sí | 7,7 s |
| F | Edge Clamp | `ec_cb_w` .800 → 1.200 in | **error** pared 0,635 mm (exacto: (1.250 − 1.200)/2) | parámetros de la caja, incluido `ec_cb_w` | Sí | 0,4 s |
| H | Vee Block | Se suprime `Alivio V superior` (control) | Ninguno: la arista viva del fondo de la V es **horizontal** y la hace una fresa en V | — | Sí | 0,6 s |

El tiempo de detección incluye la reconstrucción completa de la procedencia (el cambio de un parámetro anterior la exige) y todo el análisis.

## Lo que encontró la inyección

- **Un fallo real del análisis (caso E, primera corrida).** Con el espesor solo por rayos, la pared de 0,51 mm entre cajas vecinas **no se detectó**:
  la grilla de muestras no lanza ningún rayo por la línea que une los dos ejes. Se agregó la distancia mínima exacta entre caras no
  adyacentes, validada con `pointContainment` para no confundir una ranura con una pared. Con eso E pasó, y el espesor de F pasó de 0,676 (rayos) a 0,635 mm, el valor exacto.
- **Parámetros desconectados (E2).** `sb_pitch` existe, pero las posiciones se dibujaron fijas: cambiarlo no hace nada. Ahora
  `metrics.measure` reporta los `unused_user_parameters`. Así apareció también `vb_slot_W` en la base de la prensa: el ancho de la ranura no está ligado a su parámetro.
- **Una traza que no es un parámetro (B).** Si el defecto viene de suprimir o borrar una operación, la traza apunta a la operación de
  origen (`Cajera inferior`) y sus parámetros no arreglan el radio. La corrección propuesta tiene que ser "restaurar el redondeo", no "cambiar un valor".
- **Las consecuencias secundarias también se detectan.** Profundizar la cajera (C) adelgaza la pared y además deja el radio por debajo
  de profundidad/3. Achicar el radio (A) dispara también la relación de aspecto de la herramienta.

## Límites del experimento

- Los defectos inyectados son "limpios" (un parámetro, un valor). Falta probar combinaciones y defectos que aparecen al editar el boceto.
- Solo se probaron los parámetros que de verdad controlan la geometría. En el Vee Block no hay ninguno inyectable más allá del tamaño
  del cubo, porque sus perfiles están dibujados con puntos fijos (ver `docs/metricas_piezas.md`).
- La regla de espesor usa una ventana de 3 mm para los pares de caras. Una pared más gruesa no se mide con el método exacto (no hace falta para el umbral de 0,8 mm).
- Los umbrales siguen siendo provisionales. Lo que se validó es la **cadena** medición → regla → traza → reversión, no los valores del catálogo.
