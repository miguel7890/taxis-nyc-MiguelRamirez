"""Página 1: pronóstico horario por cuantiles."""

import plotly.graph_objects as go
import streamlit as st

from utils import COLS_Q, etiqueta_fecha, obtener_pronostico, requiere_info, selector_zona

st.title("Pronóstico de demanda por zona")
st.caption("Viajes por hora con bandas de incertidumbre (cuantiles p10–p90) de un modelo XGBoost.")

url, info = requiere_info()


@st.dialog("¿Cómo leer este pronóstico?", width="large")
def explicar_pronostico():
    st.markdown(
        """
        - **Línea p50 (mediana):** valor central esperado; la demanda real queda por encima o por debajo con igual probabilidad.
        - **Bandas sombreadas:** rangos de incertidumbre. La banda **p10–p90** debería contener la demanda real
          aproximadamente el **80 %** de las horas; la **p30–p70**, el 40 %.
        - **Puntos negros:** demanda real observada (solo días de test, 25–31 ene). El **1 de febrero** es "mañana":
          no hay dato real.
        - **Línea punteada:** demanda de la misma hora hace una semana (`lag_168`), referencia ingenua.
        - Bandas anchas = más incertidumbre → conviene planificar con un cuantil más alto si quedarse sin taxis es caro
          (ver *Decisión de flota*).
        """
    )
    st.info("Los cuantiles se ordenan con `np.sort` en la API para que nunca se crucen (p10 ≤ p20 ≤ … ≤ p90).")


col_zona, col_ayuda = st.columns([4, 1], vertical_alignment="bottom")
with col_zona:
    zona = selector_zona(info, key="zona_pronostico")
with col_ayuda:
    if st.button("¿Cómo leerlo?", icon=":material/help:", width="stretch"):
        explicar_pronostico()

fecha = st.segmented_control(
    "Fecha",
    options=info["fechas"],
    default=info["fecha_futuro"],
    format_func=lambda f: etiqueta_fecha(f, info["fecha_futuro"]),
    key="fecha_pronostico",
)
if fecha is None:
    st.info("Selecciona una fecha.")
    st.stop()

df = obtener_pronostico(url, zona["id"], fecha)
if df is None:
    st.warning("No hay pronóstico disponible para esa zona y fecha.")
    st.stop()

es_futuro = fecha == info["fecha_futuro"]
total_p50 = df["p50"].sum()
total_semana = df["hace_una_semana"].sum()
hora_pico = int(df.loc[df["p50"].idxmax(), "hora"])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Viajes esperados (p50)", f"{total_p50:,.0f}", chart_data=df["p50"].round(1).tolist(),
          chart_type="area", border=True, help="Suma de la mediana de las 24 horas")
if es_futuro:
    c2.metric("Demanda real", "—", help="El 1 de febrero aún no ocurre", border=True)
else:
    total_real = df["real"].sum()
    c2.metric("Demanda real", f"{total_real:,.0f}", delta=f"{total_real - total_p50:+,.0f} vs p50",
              chart_data=df["real"].tolist(), chart_type="area", border=True)
c3.metric("Hace una semana", f"{total_semana:,.0f}",
          delta=f"{(total_p50 / total_semana - 1) * 100:+.1f}% pronóstico" if total_semana else None,
          chart_data=df["hace_una_semana"].tolist(), chart_type="area", border=True)
c4.metric("Hora pico esperada", f"{hora_pico:02d}:00",
          delta=f"rango p10–p90: {df['p10'].sum():,.0f}–{df['p90'].sum():,.0f}", delta_color="off",
          chart_data=(df["p90"] - df["p10"]).round(1).tolist(), chart_type="bar", border=True)

fig = go.Figure()
x = df["hora"]
for lo, hi, alpha in [("p10", "p90", 0.15), ("p20", "p80", 0.22), ("p30", "p70", 0.30)]:
    fig.add_trace(go.Scatter(x=x, y=df[hi], mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=x, y=df[lo], mode="lines", line=dict(width=0), fill="tonexty",
                             fillcolor=f"rgba(247,181,0,{alpha})", name=f"{lo}–{hi}"))
fig.add_trace(go.Scatter(x=x, y=df["p50"], mode="lines", name="p50", line=dict(color="#C98F00", width=3)))
fig.add_trace(go.Scatter(x=x, y=df["hace_una_semana"], mode="lines", name="Hace una semana",
                         line=dict(color="#7F8C8D", dash="dot")))
if not es_futuro:
    fig.add_trace(go.Scatter(x=x, y=df["real"], mode="markers", name="Real", marker=dict(color="#1B1F24", size=7)))
fig.update_layout(
    height=430, margin=dict(l=10, r=10, t=40, b=10), hovermode="x unified",
    title=f"{zona['nombre']} · {etiqueta_fecha(fecha, info['fecha_futuro'])}",
    xaxis=dict(title="Hora del día", dtick=2), yaxis=dict(title="Viajes por hora"),
    legend=dict(orientation="h", y=-0.2),
)
st.plotly_chart(fig, width="stretch")

st.subheader("Detalle horario")
tabla = df[["hora", "p10", "p50", "p90", "real", "hace_una_semana"]].copy()
tabla["hora"] = tabla["hora"].map(lambda h: f"{h:02d}:00")
if es_futuro:
    tabla = tabla.drop(columns="real")
max_p90 = float(df["p90"].max()) or 1.0
st.dataframe(
    tabla,
    hide_index=True,
    width="stretch",
    column_config={
        "hora": st.column_config.TextColumn("Hora"),
        "p10": st.column_config.NumberColumn("p10", format="%.1f"),
        "p50": st.column_config.ProgressColumn("p50 (mediana)", format="%.1f", min_value=0, max_value=max_p90),
        "p90": st.column_config.NumberColumn("p90", format="%.1f"),
        "real": st.column_config.NumberColumn("Real", format="%d"),
        "hace_una_semana": st.column_config.NumberColumn("Hace 1 semana", format="%d"),
    },
)
with st.expander("Ver todos los cuantiles"):
    st.dataframe(df[["hora"] + COLS_Q].round(2), hide_index=True, width="stretch")
