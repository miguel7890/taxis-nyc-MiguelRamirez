"""API de pronóstico de demanda de taxis NYC (FastAPI)."""

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

BASE = Path(__file__).resolve().parent
CUANTILES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
FEATURES = ["zona", "hora", "dia_semana", "es_fin_semana",
            "lag_24", "lag_48", "lag_167", "lag_168", "lag_169", "media_dia_anterior"]
DIA_FUTURO = date(2024, 2, 1)

modelo = xgb.XGBRegressor()
modelo.load_model(BASE / "modelo_pronostico.ubj")

demanda = pd.read_parquet(BASE / "demanda.parquet")
demanda["hora_viaje"] = pd.to_datetime(demanda["hora_viaje"])
demanda["fecha"] = demanda["hora_viaje"].dt.date
ZONAS_IDS = sorted(demanda["PULocationID"].unique().tolist())
demanda["zona"] = pd.Categorical(demanda["PULocationID"], categories=ZONAS_IDS)
FECHAS = sorted(demanda["fecha"].unique())

app = FastAPI(
    title="Taxis NYC — API de Pronóstico",
    description="Pronóstico horario por cuantiles (XGBoost) de viajes de Yellow Taxi por zona.",
    version="1.0.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])


def _a_float(v):
    return None if pd.isna(v) else float(v)


@app.get("/")
def health():
    return {"status": "ok"}


@app.get("/info")
def info():
    zonas = (
        demanda[["PULocationID", "zona_nombre", "distrito"]]
        .drop_duplicates()
        .sort_values("PULocationID")
    )
    return {
        "zonas": [
            {"id": int(r.PULocationID), "nombre": r.zona_nombre, "distrito": r.distrito}
            for r in zonas.itertuples()
        ],
        "fechas": [f.isoformat() for f in FECHAS],
        "fecha_futuro": DIA_FUTURO.isoformat(),
        "cuantiles": CUANTILES,
    }


@app.get("/pronostico")
def pronostico(
    zona_id: int = Query(..., description="PULocationID de la zona"),
    fecha: date = Query(..., description="Fecha entre 2024-01-25 y 2024-02-01"),
):
    df = demanda[(demanda["PULocationID"] == zona_id) & (demanda["fecha"] == fecha)].sort_values("hora_viaje")
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No hay datos para zona {zona_id} en {fecha}")

    pred = np.clip(np.sort(modelo.predict(df[FEATURES]), axis=1), 0, None)
    es_futuro = fecha == DIA_FUTURO
    fila0 = df.iloc[0]
    horas = []
    for i, r in enumerate(df.itertuples()):
        horas.append({
            "hora": int(r.hora),
            "fecha_hora": r.hora_viaje.isoformat(),
            "cuantiles": {f"p{int(q * 100)}": round(float(pred[i, j]), 3) for j, q in enumerate(CUANTILES)},
            "real": None if es_futuro else _a_float(r.viajes),
            "hace_una_semana": _a_float(r.lag_168),
        })
    return {
        "zona_id": zona_id,
        "zona_nombre": fila0["zona_nombre"],
        "distrito": fila0["distrito"],
        "fecha": fecha.isoformat(),
        "es_futuro": es_futuro,
        "cuantiles": CUANTILES,
        "horas": horas,
    }
