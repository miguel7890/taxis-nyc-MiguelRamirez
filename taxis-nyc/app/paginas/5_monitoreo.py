"""Página 5 (extra): monitoreo del error diario en la semana de test."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils import cargar_metricas, etiqueta_fecha, pronostico_semana_test, requiere_info, selector_zona

st.title("Monitoreo del error")
st.caption("Error diario del pronóstico p50 en la semana de test (25–31 ene) con alertas por límite crítico.")

url, info = requiere_info()

alcance = st.radio("Alcance", ["Zona seleccionada", "Todas las zonas (agregado del notebook)"], horizontal=True)

if alcance == "Zona seleccionada":
    zona = selector_zona(info, key="zona_monitoreo")
    df = pronostico_semana_test(url, zona["id"])
    if df is None:
        st.warning("No se pudo obtener la semana de test para esta zona.")
        st.stop()
    df["fecha"] = df["fecha_hora"].dt.strftime("%Y-%m-%d")
    df["abs_err"] = (df["real"] - df["p50"]).abs()
    df["dentro"] = (df["real"] >= df["p10"]) & (df["real"] <= df["p90"])
    diario = df.groupby("fecha").agg(real=("real", "sum"), p50=("p50", "sum"), abs_err=("abs_err", "sum"),
                                     mae=("abs_err", "mean"), cobertura=("dentro", "mean"))
    diario["wape"] = diario["abs_err"] / diario["real"].replace(0, np.nan)
    titulo = zona["nombre"]
else:
    diario = pd.DataFrame(cargar_metricas()["error_diario_test"]).T
    diario["cobertura"] = np.nan
    titulo = "Todas las zonas de pronóstico"

metrica = st.segmented_control("Métrica", ["WAPE (%)", "MAE (viajes/h)"], default="WAPE (%)")
if metrica is None:
    metrica = "WAPE (%)"
es_wape = metrica.startswith("WAPE")
valores = diario["wape"] * 100 if es_wape else diario["mae"]
maximo = float(np.nanmax(valores)) if len(valores) else 1.0
limite = st.slider(
    "Límite crítico", 0.0, round(max(maximo * 1.5, 1.0), 1),
    value=25.0 if es_wape else round(float(np.nanmean(valores)) * 1.2, 1),
    step=0.5, help="Días por encima de este valor generan alerta.",
)

colores = ["#E74C3C" if v > limite else "#2ECC71" for v in valores]
etiquetas = [etiqueta_fecha(f) for f in diario.index]
fig = go.Figure(go.Bar(x=etiquetas, y=valores, marker_color=colores,
                       text=[f"{v:.1f}" for v in valores], textposition="outside"))
fig.add_hline(y=limite, line_dash="dash", line_color="#E74C3C", annotation_text=f"Límite crítico: {limite:.1f}")
fig.update_layout(height=400, margin=dict(l=10, r=10, t=40, b=10), title=f"{metrica} diario · {titulo}",
                  yaxis=dict(title=metrica))
st.plotly_chart(fig, width="stretch")

excedidos = diario.index[valores > limite].tolist()
c1, c2, c3 = st.columns(3)
c1.metric(f"{metrica} promedio", f"{np.nanmean(valores):.1f}",
          chart_data=[round(float(v), 2) for v in valores], chart_type="line", border=True)
c2.metric("Días sobre el límite", f"{len(excedidos)} de {len(diario)}", border=True)
c3.metric("Peor día", etiquetas[int(np.nanargmax(valores))], delta=f"{np.nanmax(valores):.1f}",
          delta_color="inverse", border=True)

if excedidos:
    dias = ", ".join(etiqueta_fecha(f) for f in excedidos)
    if len(excedidos) >= 3:
        st.error(f"🚨 ALERTA CRÍTICA: {len(excedidos)} días superan el límite ({dias}). "
                 "Revisar posible deriva y considerar reentrenar el modelo.", icon=":material/warning:")
    else:
        st.warning(f"⚠️ Atención: {dias} supera(n) el límite crítico de {limite:.1f}.", icon=":material/info:")
    st.toast(f"{len(excedidos)} día(s) sobre el límite crítico", icon="🚨")
else:
    st.success("✅ Todos los días están dentro del límite crítico.", icon=":material/check_circle:")

tabla = diario.copy()
tabla.index = etiquetas
tabla["estado"] = np.where(valores.to_numpy() > limite, "🔴 Alerta", "🟢 OK")
st.dataframe(
    tabla[["real", "p50", "mae", "wape", "cobertura", "estado"]],
    width="stretch",
    column_config={
        "real": st.column_config.NumberColumn("Viajes reales", format="%.0f"),
        "p50": st.column_config.NumberColumn("Pronóstico p50", format="%.0f"),
        "mae": st.column_config.NumberColumn("MAE", format="%.2f"),
        "wape": st.column_config.ProgressColumn("WAPE", format="percent", min_value=0, max_value=1),
        "cobertura": st.column_config.NumberColumn("Cobertura p10–p90", format="percent"),
        "estado": "Estado",
    },
)
