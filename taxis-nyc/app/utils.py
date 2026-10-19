"""Funciones compartidas por las páginas de la app."""

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import streamlit as st

DIR_DATA = Path(__file__).resolve().parent / "data"
CUANTILES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
COLS_Q = [f"p{int(q * 100)}" for q in CUANTILES]
FECHAS_TEST = [f"2024-01-{d}" for d in range(25, 32)]
COLORES_SEGMENTO = {
    "Aeropuertos": "#1F77B4",
    "Manhattan Central": "#F7B500",
    "Vida Nocturna": "#9B59B6",
    "Barrios Periféricos": "#2CA02C",
}


def api_url() -> str:
    try:
        url = st.secrets["API_URL"]
    except Exception:
        url = os.environ.get("API_URL", "http://localhost:8000")
    return str(url).rstrip("/")


@st.cache_data(ttl=60, show_spinner=False)
def estado_api(url: str) -> bool:
    try:
        return requests.get(f"{url}/", timeout=20).json().get("status") == "ok"
    except Exception:
        return False


@st.cache_data(ttl=3600, show_spinner=False)
def obtener_info(url: str) -> dict | None:
    try:
        r = requests.get(f"{url}/info", timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def obtener_pronostico(url: str, zona_id: int, fecha: str) -> pd.DataFrame | None:
    """Devuelve un DataFrame horario con cuantiles, real y lag_168 (o None si falla)."""
    try:
        r = requests.get(f"{url}/pronostico", params={"zona_id": zona_id, "fecha": fecha}, timeout=30)
        if r.status_code == 404:
            return None
        r.raise_for_status()
    except Exception:
        return None
    filas = []
    for h in r.json()["horas"]:
        fila = {"hora": h["hora"], "fecha_hora": h["fecha_hora"], "real": h["real"],
                "hace_una_semana": h["hace_una_semana"]}
        fila.update(h["cuantiles"])
        filas.append(fila)
    df = pd.DataFrame(filas)
    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
    df["real"] = pd.to_numeric(df["real"], errors="coerce")
    return df


def pronostico_semana_test(url: str, zona_id: int) -> pd.DataFrame | None:
    partes = [obtener_pronostico(url, zona_id, f) for f in FECHAS_TEST]
    if any(p is None for p in partes):
        return None
    return pd.concat(partes, ignore_index=True)


def interpolar_cuantil(df: pd.DataFrame, q: float) -> np.ndarray:
    """Interpola linealmente entre los cuantiles disponibles (acotado a [0.1, 0.9])."""
    q = float(np.clip(q, CUANTILES[0], CUANTILES[-1]))
    valores = df[COLS_Q].to_numpy()
    return np.array([np.interp(q, CUANTILES, fila) for fila in valores])


@st.cache_data(show_spinner=False)
def cargar_segmentacion() -> pd.DataFrame:
    return pd.read_csv(DIR_DATA / "segmentacion_zonas.csv")


@st.cache_data(show_spinner=False)
def cargar_metricas() -> dict:
    return json.loads((DIR_DATA / "metricas_modelo.json").read_text(encoding="utf-8"))


def etiqueta_fecha(f: str, fecha_futuro: str = "2024-02-01") -> str:
    meses = {1: "ene", 2: "feb"}
    d = pd.Timestamp(f)
    dias = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    texto = f"{dias[d.dayofweek]} {d.day} {meses[d.month]}"
    return f"{texto} (mañana)" if f == fecha_futuro else texto


def requiere_info() -> tuple[str, dict]:
    url = api_url()
    info = obtener_info(url)
    if info is None:
        st.error(f"No se pudo conectar con la API en `{url}`. Revisa `API_URL` en los secrets o levanta la API local.")
        st.stop()
    return url, info


def selector_zona(info: dict, key: str) -> dict:
    zonas = info["zonas"]
    por_defecto = next((i for i, z in enumerate(zonas) if z["id"] == 161), 0)
    return st.selectbox(
        "Zona de recogida",
        zonas,
        index=por_defecto,
        format_func=lambda z: f"{z['nombre']} · {z['distrito']} (ID {z['id']})",
        key=key,
    )
