# 🚕 Taxis NYC: Pronóstico, Segmentación y Decisión Operativa

Proyecto de Machine Learning sobre los viajes de **Yellow Taxi de Nueva York (enero 2024)**:

1. **Pronóstico** horario de demanda por zona con **XGBoost multi-cuantil** (p10…p90).
2. **Segmentación** de zonas con **K-Means (k=4) + PCA**.
3. **Decisión operativa**: cuántos taxis posicionar cada hora usando el **cuantil óptimo de costos**
   $q^* = C_{perdido} / (C_{perdido} + C_{ocioso})$.

Arquitectura: notebook de preparación → **API FastAPI** (Render) → **App Streamlit** (Streamlit Community Cloud).

## 👥 Integrantes

| Nombre |
|---|
|Miguel Antonio Ramirez Rivera|
|Jose Villalta|


## 🌐 Despliegue

| Componente | Enlace |
|---|---|
| App Streamlit | https://kodigo-taxis-nyc-miguelramirez.streamlit.app/ |
| API (Render) – documentación | https://taxis-nyc-miguelramirez.onrender.com/docs |

## 📊 Datos

- Viajes: https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet
- Zonas: https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv

El notebook lee los datos directamente desde la URL (no se versiona el parquet crudo de ~50 MB).

## 📏 Reglas de negocio

| Regla | Implementación |
|---|---|
| Zonas Unknown | Se descartan `PULocationID` 264 y 265 |
| Segmentación | Zonas con ≥ 500 viajes en enero 2024 (100 zonas) |
| Pronóstico | Zonas con ≥ 3,000 viajes en enero 2024 (58 zonas) |
| Entrenamiento | 8 – 24 de enero (inclusive) |
| Test | 25 – 31 de enero |
| Pronóstico futuro | 1 de febrero de 2024 ("mañana", sin dato real) |
| Sin fuga de datos | Lags 24, 48, 167, 168, 169 h y media de las 24 h del día anterior. Sin `train_test_split` |

## 📁 Estructura

```
taxis-nyc/
├── preparacion.ipynb          # ETL, modelo de pronóstico y segmentación
├── README.md
├── api/
│   ├── main.py                # FastAPI: /, /info, /pronostico
│   ├── modelo_pronostico.ubj  # XGBoost multi-cuantil
│   ├── demanda.parquet        # Features + demanda real 25 ene – 1 feb
│   └── requirements.txt
└── app/
    ├── streamlit_app.py       # Navegación (st.navigation) + sidebar
    ├── utils.py               # Cliente de la API y utilidades compartidas
    ├── requirements.txt
    ├── .streamlit/config.toml # Tema
    ├── data/
    │   ├── segmentacion_zonas.csv
    │   └── metricas_modelo.json
    └── paginas/
        ├── 1_pronostico.py    # Bandas de cuantiles, KPIs, tabla horaria
        ├── 2_segmentacion.py  # PCA interactivo (clic/lazo filtra)
        ├── 3_decision.py      # q*, costos y descarga del plan
        ├── 4_ficha.py         # Ficha técnica, limitaciones y ética
        └── 5_monitoreo.py     # (Extra) Error diario con límite crítico
```

## 📈 Resultados (test 25–31 ene)

| Métrica | Valor |
|---|---|
| MAE p50 | 11.68 viajes/h (referencia *hace una semana*: 11.88) |
| WAPE p50 | 16.5 % |
| Cobertura del intervalo p10–p90 | 81.9 % (objetivo 80 %) |
| Silueta K-Means | máxima en k = 4 (0.392) |

## ▶️ Ejecución local

Requisitos: Python 3.10+.

```bash
# 1. Entorno
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r api/requirements.txt -r app/requirements.txt
pip install scikit-learn jupyter                       # solo para el notebook

# 2. (Opcional) Regenerar artefactos: modelo, demanda.parquet y segmentación
jupyter nbconvert --to notebook --execute --inplace preparacion.ipynb

# 3. API  ->  http://localhost:8000/docs
cd api && uvicorn main:app --reload --port 8000

# 4. App (en otra terminal)  ->  http://localhost:8501
cd app && streamlit run streamlit_app.py
```

La app lee la URL de la API desde `st.secrets["API_URL"]` (por defecto `http://localhost:8000`).
Para apuntar a otra API, crear `app/.streamlit/secrets.toml` a partir de `secrets.toml.example`:

```toml
API_URL = "https://TU-API.onrender.com"
```

### Ejemplos de la API

```bash
curl http://localhost:8000/
curl http://localhost:8000/info
curl "http://localhost:8000/pronostico?zona_id=161&fecha=2024-02-01"
```

## ☁️ Despliegue

**API en Render** (Web Service)
- Root Directory: `api`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

**App en Streamlit Community Cloud**
- Main file path: `app/streamlit_app.py`
- Secrets: `API_URL = "https://taxis-nyc-miguelramirez.onrender.com"`

> El plan gratuito de Render "duerme" el servicio tras inactividad; la primera petición puede tardar ~1 minuto.
> Usa el botón **Reintentar conexión** de la barra lateral.
