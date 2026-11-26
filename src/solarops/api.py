import os

import mlflow.sklearn
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="SolarOps Maroc API", description="API de prévision solaire")

# MLflow où chercher les modèles dans le conteneur Docker
os.environ["MLFLOW_TRACKING_URI"] = "file:///app/mlruns"

# On charge TON modèle grâce à TON Run ID
MODEL_URI = "runs:/c7d0f35886214c60b020a23ea37112b0/random_forest_model" 
model = mlflow.sklearn.load_model(MODEL_URI)

# On définit le format des données d'entrée (Pydantic)
class SolarFeatures(BaseModel):
    hour_sin: float
    hour_cos: float
    month_sin: float
    month_cos: float
    radiation_lag_24h: float
    solar_zenith: float
    clear_sky_proxy: float
    temperature_2m: float
    relative_humidity_2m: float
    surface_pressure: float
    cloud_cover: float
    cloud_cover_low: float
    cloud_cover_mid: float
    cloud_cover_high: float
    wind_speed_10m: float
    wind_direction_10m: float

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/predict")
def predict(features: SolarFeatures):
    # On convertit les données reçues en DataFrame
    input_df = pd.DataFrame([features.dict()])
    
    # On fait la prédiction avec le modèle
    prediction = model.predict(input_df)[0]
    
    return {"prediction_kw": round(float(prediction), 2)}