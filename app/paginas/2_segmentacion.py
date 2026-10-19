"""Página 2: segmentación de zonas con K-Means + PCA."""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils import COLORES_SEGMENTO, cargar_metricas, cargar_segmentacion

st.title("Segmentación de zonas")
st.caption("K-Means (k=4) sobre 8 variables estandarizadas de las zonas con ≥ 500 viajes en enero 2024.")

seg = cargar_segmentacion()
met = cargar_metricas()["segmentacion"]
HORAS = [f"h{h:02d}" for h in range(24)]

cols = st.columns(4)
for col, (nombre, color) in zip(cols, COLORES_SEGMENTO.items()):
    sub = seg[seg["segmento"] == nombre]
    col.metric(nombre, f"{len(sub)} zonas", delta=f"{sub['viajes_mes'].sum():,.0f} viajes/mes",
               delta_color="off", border=True)

segmentos = st.multiselect("Segmentos visibles", list(COLORES_SEGMENTO), default=list(COLORES_SEGMENTO))
vista = seg[seg["segmento"].isin(segmentos)].reset_index(drop=True)

fig = px.scatter(
    vista, x="pc1", y="pc2", color="segmento", color_discrete_map=COLORES_SEGMENTO,
    size="viajes_dia", size_max=28, custom_data=["PULocationID"],
    hover_name="zona_nombre",
    hover_data={"distrito": True, "viajes_dia": ":.0f", "distancia_mediana": ":.2f",
                "tarifa_mediana": ":.2f", "pct_noche": ":.0%", "pc1": False, "pc2": False},
    labels={"pc1": f"PC1 ({met['varianza_pca'][0]:.0%})", "pc2": f"PC2 ({met['varianza_pca'][1]:.0%})"},
)
fig.update_layout(height=480, margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", y=-0.15),
                  dragmode="lasso")
st.markdown("**Haz clic o selecciona con lazo/caja puntos del PCA** para filtrar la tabla y el perfil horario.")
evento = st.plotly_chart(fig, width="stretch", on_select="rerun",
                         selection_mode=("points", "box", "lasso"), key="pca")

ids = [p["customdata"][0] for p in evento.selection.points] if evento and evento.selection.points else []
seleccion = vista[vista["PULocationID"].isin(ids)] if ids else vista
if ids:
    st.success(f"{len(seleccion)} zonas seleccionadas en el gráfico.")
else:
    st.caption("Sin selección: se muestran todas las zonas visibles.")

col_a, col_b = st.columns([3, 2])
with col_a:
    st.subheader("Zonas")
    st.dataframe(
        seleccion[["zona_nombre", "distrito", "segmento", "viajes_dia", "distancia_mediana", "tarifa_mediana",
                   "propina_mediana", "pct_fin_semana", "pct_noche"]].sort_values("viajes_dia", ascending=False),
        hide_index=True, width="stretch", height=380,
        column_config={
            "zona_nombre": "Zona", "distrito": "Distrito", "segmento": "Segmento",
            "viajes_dia": st.column_config.ProgressColumn("Viajes/día", format="%.0f", min_value=0,
                                                          max_value=float(seg["viajes_dia"].max())),
            "distancia_mediana": st.column_config.NumberColumn("Dist. mediana (mi)", format="%.2f"),
            "tarifa_mediana": st.column_config.NumberColumn("Tarifa mediana", format="$%.2f"),
            "propina_mediana": st.column_config.NumberColumn("Propina mediana", format="$%.2f"),
            "pct_fin_semana": st.column_config.NumberColumn("% fin de semana", format="percent"),
            "pct_noche": st.column_config.NumberColumn("% noche", format="percent"),
        },
    )
with col_b:
    st.subheader("Perfil horario")
    perfil = seleccion.groupby("segmento")[HORAS].mean()
    fig_h = go.Figure()
    for nombre, fila in perfil.iterrows():
        fig_h.add_trace(go.Scatter(x=list(range(24)), y=fila.values * 100, mode="lines", name=nombre,
                                   line=dict(color=COLORES_SEGMENTO[nombre], width=3)))
    fig_h.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10), xaxis=dict(title="Hora", dtick=3),
                        yaxis=dict(title="% de viajes del día"), legend=dict(orientation="h", y=-0.25))
    st.plotly_chart(fig_h, width="stretch")

with st.expander("¿Por qué k = 4? Coeficiente de silueta"):
    sil = met["silueta_por_k"]
    fig_s = px.bar(x=[int(k) for k in sil], y=list(sil.values()), labels={"x": "k", "y": "Silueta"},
                   color=[("k elegido" if int(k) == met["k"] else "otro") for k in sil],
                   color_discrete_map={"k elegido": "#F7B500", "otro": "#B0B7C3"})
    fig_s.update_layout(height=300, showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig_s, width="stretch")
    st.markdown(
        "Variables (estandarizadas con `StandardScaler`): viajes/día (log), distancia mediana, tarifa mediana, "
        "propina mediana, % fin de semana, % mañana (6–11 h), % tarde (12–17 h), % noche (20–4 h). "
        "Los nombres de los segmentos se asignan automáticamente según el perfil promedio del cluster."
    )
