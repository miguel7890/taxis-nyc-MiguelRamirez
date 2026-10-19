"""Página 3: decisión de flota con el cuantil óptimo de costos."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils import (etiqueta_fecha, interpolar_cuantil, obtener_pronostico, pronostico_semana_test,
                   requiere_info, selector_zona)

st.title("Decisión de flota")
st.caption("¿Cuántos taxis posicionar cada hora? Se elige el cuantil que minimiza el costo esperado.")

url, info = requiere_info()

c1, c2 = st.columns([3, 2])
with c1:
    zona = selector_zona(info, key="zona_decision")
with c2:
    fecha = st.selectbox("Día a planificar", info["fechas"], index=len(info["fechas"]) - 1,
                         format_func=lambda f: etiqueta_fecha(f, info["fecha_futuro"]))

with st.spinner("Consultando pronósticos de la semana de test..."):
    df_dia = obtener_pronostico(url, zona["id"], fecha)
    df_test = pronostico_semana_test(url, zona["id"])
if df_dia is None or df_test is None:
    st.warning("No se pudieron obtener los pronósticos para esta zona.")
    st.stop()


def costo(plan: np.ndarray, real: np.ndarray, c_perdido: float, c_ocioso: float) -> float:
    faltante = np.maximum(real - plan, 0)
    sobrante = np.maximum(plan - real, 0)
    return float(c_perdido * faltante.sum() + c_ocioso * sobrante.sum())


@st.fragment
def panel_decision():
    s1, s2 = st.columns(2)
    c_perdido = s1.slider("Costo de un viaje perdido (C_perdido, USD)", 1.0, 50.0, 20.0, 0.5,
                          help="Ingreso/margen que se pierde cuando hay demanda y no hay taxi.")
    c_ocioso = s2.slider("Costo de un taxi ocioso (C_ocioso, USD/hora)", 1.0, 50.0, 8.0, 0.5,
                         help="Combustible, tiempo del conductor y desgaste sin pasajero.")
    q_opt = c_perdido / (c_perdido + c_ocioso)

    col_f, col_q = st.columns([2, 1], vertical_alignment="center")
    with col_f:
        st.latex(r"q^{*} = \frac{C_{perdido}}{C_{perdido} + C_{ocioso}} = "
                 rf"\frac{{{c_perdido:.1f}}}{{{c_perdido:.1f} + {c_ocioso:.1f}}} = {q_opt:.3f}")
    with col_q:
        st.metric("Cuantil óptimo q*", f"p{q_opt * 100:.0f}", border=True)
    if not 0.1 <= q_opt <= 0.9:
        st.caption("q* está fuera de [0.1, 0.9]: se usa el cuantil extremo disponible.")

    plan = np.ceil(interpolar_cuantil(df_dia, q_opt))
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_dia["hora"], y=plan, name=f"Recomendación (q*={q_opt:.2f})", marker_color="#F7B500"))
    fig.add_trace(go.Scatter(x=df_dia["hora"], y=df_dia["p50"], name="p50", mode="lines",
                             line=dict(color="#1F77B4", width=3)))
    if df_dia["real"].notna().any():
        fig.add_trace(go.Scatter(x=df_dia["hora"], y=df_dia["real"], name="Real", mode="markers",
                                 marker=dict(color="#1B1F24", size=8)))
    fig.update_layout(height=400, margin=dict(l=10, r=10, t=40, b=10), hovermode="x unified",
                      title=f"Plan horario · {zona['nombre']} · {etiqueta_fecha(fecha, info['fecha_futuro'])}",
                      xaxis=dict(title="Hora", dtick=2), yaxis=dict(title="Taxis / viajes"),
                      legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, width="stretch")

    real_t = df_test["real"].to_numpy()
    estrategias = {
        f"Recomendación q*={q_opt:.2f}": np.ceil(interpolar_cuantil(df_test, q_opt)),
        "Mediana p50": np.ceil(df_test["p50"].to_numpy()),
        "Hace una semana (lag 168)": df_test["hace_una_semana"].to_numpy(),
    }
    filas = []
    for nombre, p in estrategias.items():
        filas.append({
            "Estrategia": nombre,
            "Costo total (USD)": costo(p, real_t, c_perdido, c_ocioso),
            "Viajes perdidos": float(np.maximum(real_t - p, 0).sum()),
            "Horas-taxi ociosas": float(np.maximum(p - real_t, 0).sum()),
        })
    tabla = pd.DataFrame(filas)
    base = tabla.loc[1, "Costo total (USD)"]
    ahorro = base - tabla.loc[0, "Costo total (USD)"]

    st.subheader("Costo financiero en la semana de test (25–31 ene)")
    m1, m2, m3 = st.columns(3)
    m1.metric("Costo con q*", f"${tabla.loc[0, 'Costo total (USD)']:,.0f}", border=True)
    m2.metric("Costo con p50", f"${base:,.0f}", border=True)
    m3.metric("Ahorro vs p50", f"${ahorro:,.0f}", delta=f"{ahorro / base * 100:+.1f}%" if base else None,
              border=True)
    st.dataframe(tabla, hide_index=True, width="stretch", column_config={
        "Costo total (USD)": st.column_config.NumberColumn(format="$%.0f"),
        "Viajes perdidos": st.column_config.NumberColumn(format="%.0f"),
        "Horas-taxi ociosas": st.column_config.NumberColumn(format="%.0f"),
    })

    descarga = pd.DataFrame({
        "zona_id": zona["id"], "zona": zona["nombre"], "fecha": fecha,
        "hora": df_dia["hora"].map(lambda h: f"{h:02d}:00"),
        "taxis_recomendados": plan.astype(int), "p50": df_dia["p50"].round(2),
        "cuantil_optimo": round(q_opt, 4), "real": df_dia["real"],
    })
    st.download_button("Descargar plan horario (CSV)", descarga.to_csv(index=False).encode("utf-8"),
                       file_name=f"plan_flota_zona{zona['id']}_{fecha}.csv", mime="text/csv",
                       icon=":material/download:", type="primary")


panel_decision()
