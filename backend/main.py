"""
Step 08: Production Backend API Service.
FastAPI Application for the Virtual Spatiotemporal Air Quality Estimation System.
Serves real-time inference, CPCB ground-truth comparison, spatial grid heatmaps, and dashboard UI.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backend_config import (
    VIDARBHA_NODES,
    VIDARBHA_BOUNDS,
    CPCB_CATEGORIES,
    PIPELINE_MODEL_PATH
)
from services.estimator import get_estimator

app = FastAPI(
    title="Virtual Air Quality Estimation System (Vidarbha Grid)",
    description="Operational ML microservice mapping ECMWF meteorology and Copernicus CAMS chemical tracers to physical CPCB India NAQI standards.",
    version="1.0.0"
)

# Enable CORS for frontend integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files directory
STATIC_DIR = BACKEND_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class CoordinatePredictionRequest(BaseModel):
    latitude: float = Field(..., ge=18.0, le=23.0, description="Latitude within Maharashtra/Vidarbha region")
    longitude: float = Field(..., ge=75.0, le=82.0, description="Longitude within Maharashtra/Vidarbha region")
    temperature_override: Optional[float] = Field(None, description="Optional temperature in Celsius")
    humidity_override: Optional[float] = Field(None, description="Optional relative humidity (%)")
    wind_speed_override: Optional[float] = Field(None, description="Optional wind speed in km/h")
    wind_dir_override: Optional[float] = Field(None, description="Optional wind direction (0-360 deg)")
    pm25_override: Optional[float] = Field(None, description="Optional CAMS PM2.5 in ug/m3")
    pm10_override: Optional[float] = Field(None, description="Optional CAMS PM10 in ug/m3")


@app.get("/")
async def root():
    """Serves the interactive dashboard Single Page Application."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "message": "Virtual Air Quality Estimation API is online.",
        "documentation": "/docs",
        "nodes_endpoint": "/api/nodes",
        "predict_endpoint": "/api/predict"
    }


@app.get("/api/health")
async def health_check():
    """Returns system status, model metadata, and architecture stats."""
    estimator = get_estimator()
    meta = estimator.pipeline.metadata
    return {
        "status": "online",
        "model_type": meta.get("model_type"),
        "training_framework": "XGBoost Regressor Champion",
        "features_count": len(estimator.pipeline.feature_names),
        "test_mae": meta.get("error_margin_mae", 6.01),
        "test_r2": meta.get("r2_score", 0.9690),
        "target_standard": "CPCB India NAQI (24-hr Max Sub-Index)",
        "model_artifact": str(PIPELINE_MODEL_PATH.name)
    }


@app.get("/api/nodes")
async def get_vidarbha_nodes(refresh: bool = Query(False, description="Force refresh live API feeds")):
    """Returns real-time estimation, CPCB ground-truth comparison, and live meteorology for all 4 Vidarbha nodes."""
    estimator = get_estimator()
    try:
        data = estimator.get_all_nodes_status(force_refresh=refresh)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch live node states: {str(e)}")


@app.post("/api/predict")
async def predict_custom_coordinate(req: CoordinatePredictionRequest):
    """Predicts ground-level India NAQI for any coordinate across Vidarbha using live or custom parameters."""
    estimator = get_estimator()

    weather_override = None
    if any(x is not None for x in [req.temperature_override, req.humidity_override, req.wind_speed_override, req.wind_dir_override]):
        weather_override = {}
        if req.temperature_override is not None:
            weather_override["temperature_2m"] = req.temperature_override
        if req.humidity_override is not None:
            weather_override["relative_humidity_2m"] = req.humidity_override
        if req.wind_speed_override is not None:
            weather_override["wind_speed_10m"] = req.wind_speed_override
        if req.wind_dir_override is not None:
            weather_override["wind_direction_10m"] = req.wind_dir_override

    aq_override = None
    if any(x is not None for x in [req.pm25_override, req.pm10_override]):
        aq_override = {}
        if req.pm25_override is not None:
            aq_override["pm2_5"] = req.pm25_override
        if req.pm10_override is not None:
            aq_override["pm10"] = req.pm10_override

    try:
        result = estimator.predict_coordinate(
            lat=req.latitude,
            lon=req.longitude,
            weather_override=weather_override,
            aq_override=aq_override
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")


@app.get("/api/grid")
async def get_spatial_heatmap(lat_steps: int = Query(6, ge=4, le=10), lon_steps: int = Query(8, ge=5, le=12)):
    """Generates a spatial mesh grid across Vidarbha for map heatmap interpolation."""
    estimator = get_estimator()
    try:
        grid = estimator.get_spatial_heatmap_grid(lat_steps=lat_steps, lon_steps=lon_steps)
        return {
            "bounds": VIDARBHA_BOUNDS,
            "total_points": len(grid),
            "grid": grid
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Heatmap grid error: {str(e)}")


@app.get("/api/cpcb-standards")
async def get_cpcb_standards():
    """Returns official CPCB NAQI breakpoints and health advisory categories."""
    return {
        "categories": CPCB_CATEGORIES,
        "standard": "Central Pollution Control Board (CPCB) National Air Quality Index (NAQI)"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
