"""Taxis NYC: Pronóstico, Segmentación y Decisión Operativa."""

import streamlit as st

from utils import api_url, estado_api

st.set_page_config(page_title="Taxis NYC", page_icon="🚕", layout="wide")

paginas = [
    st.Page("paginas/1_pronostico.py", title="Pronóstico", icon=":material/insights:", default=True),
    st.Page("paginas/2_segmentacion.py", title="Segmentación", icon=":material/scatter_plot:"),
    st.Page("paginas/3_decision.py", title="Decisión de flota", icon=":material/local_taxi:"),
    st.Page("paginas/4_ficha.py", title="Ficha del modelo", icon=":material/description:"),
    st.Page("paginas/5_monitoreo.py", title="Monitoreo", icon=":material/monitor_heart:"),
]
nav = st.navigation(paginas)

with st.sidebar:
    st.markdown("## 🚕 Taxis NYC")
    st.caption("Pronóstico, segmentación y decisión operativa · Yellow Taxi enero 2024")
    url = api_url()
    if estado_api(url):
        st.badge("API conectada", icon=":material/check_circle:", color="green")
    else:
        st.badge("API sin conexión", icon=":material/error:", color="red")
    st.caption(f"API: `{url}`")
    if st.button("Reintentar conexión", icon=":material/refresh:", width="stretch"):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.caption("Entrenamiento: 8–24 ene · Test: 25–31 ene · Pronóstico: 1 feb 2024")

nav.run()
