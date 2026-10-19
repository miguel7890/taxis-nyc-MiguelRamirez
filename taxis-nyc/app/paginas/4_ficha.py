"""Página 4: ficha técnica del modelo."""

import pandas as pd
import plotly.express as px
import streamlit as st

from utils import cargar_metricas

st.title("Ficha técnica del modelo")
m = cargar_metricas()
t, d, mod = m["test"], m["datos"], m["modelo"]

st.subheader("Desempeño en test (25–31 ene 2024)")
c1, c2, c3, c4 = st.columns(4)
c1.metric("MAE p50 (viajes/h)", f"{t['mae_p50']:.2f}",
          delta=f"{t['mae_p50'] - t['mae_baseline_lag168']:+.2f} vs lag 168", delta_color="inverse", border=True)
c2.metric("WAPE p50", f"{t['wape_p50']:.1%}", border=True)
c3.metric("Cobertura p10–p90", f"{t['cobertura_p10_p90']:.1%}", delta="objetivo 80%", delta_color="off",
          border=True)
c4.metric("Pinball loss promedio", f"{t['pinball_promedio']:.2f}", border=True)

col_a, col_b = st.columns(2)
with col_a:
    calib = pd.DataFrame({"Cuantil nominal": [float(q) for q in m["cobertura_por_cuantil"]],
                          "Cobertura empírica": list(m["cobertura_por_cuantil"].values())})
    fig = px.line(calib, x="Cuantil nominal", y="Cobertura empírica", markers=True, title="Calibración de cuantiles")
    fig.add_shape(type="line", x0=0.1, y0=0.1, x1=0.9, y1=0.9, line=dict(dash="dot", color="gray"))
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, width="stretch")
with col_b:
    imp = pd.Series(mod["importancia_gain"]).sort_values()
    fig = px.bar(x=imp.values, y=imp.index, orientation="h", title="Importancia de variables (gain)",
                 labels={"x": "Proporción", "y": ""}, color_discrete_sequence=["#F7B500"])
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, width="stretch")

st.subheader("Especificación")
st.markdown(f"""
| Elemento | Detalle |
|---|---|
| Algoritmo | {mod['algoritmo']} · `objective="{mod['objective']}"` · {len(mod['cuantiles'])} cuantiles (0.1–0.9) |
| Hiperparámetros | `n_estimators={mod['n_estimators']}`, `max_depth={mod['max_depth']}`, `learning_rate={mod['learning_rate']}`, `enable_categorical=True` |
| Variables | {', '.join(f'`{f}`' for f in mod['features'])} |
| Datos | Yellow Taxi NYC enero 2024 · {d['viajes_validos_enero']:,} viajes válidos · zonas Unknown (264, 265) excluidas |
| Zonas | {d['zonas_pronostico']} zonas con ≥ 3,000 viajes (pronóstico) · {d['zonas_segmentacion']} con ≥ 500 (segmentación) |
| Partición temporal | Entrenamiento {d['train'][0]} a {d['train'][1]} · Test {d['test'][0]} a {d['test'][1]} · Pronóstico {d['futuro']} |
| Anti-fuga | Solo lags ≥ 24 h (24, 48, 167, 168, 169) y media del día anterior; sin `train_test_split` |
| Post-proceso | `np.sort(..., axis=1)` para evitar cuantiles cruzados y recorte a ≥ 0 |
""")

st.subheader("Limitaciones")
st.markdown(f"""
- **Un solo mes de historia:** no captura estacionalidad anual, feriados (p. ej. MLK Day en el periodo de entrenamiento) ni eventos especiales.
- **Referencia exigente:** en p50 el modelo mejora solo ligeramente a la regla ingenua *hace una semana*
  (MAE {t['mae_p50']:.2f} vs {t['mae_baseline_lag168']:.2f}); su valor añadido principal son las **bandas de incertidumbre calibradas**.
- **Horizonte de 24 h:** pronostica el día siguiente usando datos hasta el día anterior; no sirve para horizontes largos.
- **Sin variables exógenas:** clima, eventos, tráfico o competencia (Uber/Lyft) no están incluidos.
- **Demanda observada ≠ demanda real:** solo se ven viajes realizados; la demanda no atendida queda oculta (censura).
""")

st.subheader("Uso ético y responsable")
st.markdown("""
- **Sesgo contra zonas periféricas:** solo se pronostican zonas con ≥ 3,000 viajes, casi todas en Manhattan y aeropuertos.
  Usar el modelo para reasignar flota puede **reducir aún más el servicio** en barrios del Bronx, Brooklyn y Queens,
  generando un círculo vicioso (menos taxis → menos viajes observados → menos taxis). Se recomienda fijar una
  **cobertura mínima** por distrito independiente del pronóstico.
- **Protección a conductores:** el pronóstico es una herramienta de apoyo, no un mecanismo de control. No debe usarse
  para penalizar, vigilar ni fijar metas individuales a conductores, ni para recortar ingresos en horas de baja demanda.
- **Transparencia:** las recomendaciones deben mostrarse con su incertidumbre (bandas) y con los costos supuestos.
- **Privacidad:** se usan datos públicos agregados por zona y hora; no se identifican personas ni vehículos.
- **Supervisión humana:** monitorear el error diariamente (página *Monitoreo*) y reentrenar ante deriva.
""")

st.divider()
st.subheader("¿Te resultó útil esta ficha?")
calificacion = st.feedback("stars", key="feedback_ficha")
if calificacion is not None:
    estrellas = calificacion + 1
    st.toast(f"¡Gracias por tu calificación de {estrellas} estrella{'s' if estrellas > 1 else ''}!", icon="⭐")
    st.caption(f"Calificación registrada: {'⭐' * estrellas}")
