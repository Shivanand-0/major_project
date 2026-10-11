"""
Step 08: Production Backend API Service.
FastAPI Application for the Virtual Spatiotemporal Air Quality Estimation System.
Serves real-time inference, CPCB ground-truth comparison, spatial grid heatmaps, and dashboard UI.
"""

import os
import sys
import json
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
    meta = estimator.pipeline.metadata or {}
    model_name = meta.get("model_type", "LightGBM Regressor")
    return {
        "status": "online",
        "model_type": model_name,
        "training_framework": f"{model_name} Champion",
        "features_count": len(estimator.pipeline.feature_names),
        "test_mae": meta.get("error_margin_mae", meta.get("metrics", {}).get("test_mae", 22.61)),
        "test_r2": meta.get("r2_score", meta.get("metrics", {}).get("test_r2", 0.584)),
        "target_standard": "CPCB India NAQI (Max Criteria Pollutant Sub-Index)",
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


# ==============================================================================
# HCHO BIOMASS BURNING & SATELLITE SURVEILLANCE ENDPOINTS (PAN-INDIA)
# ==============================================================================
DS_DATA_DIR = BACKEND_DIR.parent / "ds" / "data"

@app.get("/api/hcho/summary")
async def get_hcho_summary():
    """Returns Pan-India S5P HCHO, VIIRS fire count, and Getis-Ord hotspot analytical summary."""
    summary_file = DS_DATA_DIR / "hotspots" / "hotspots_summary.json"
    corr_file = DS_DATA_DIR / "processed" / "correlation_report.json"
    
    if not summary_file.exists():
        raise HTTPException(status_code=404, detail="Hotspots summary not found. Run ds pipeline.")
    
    with open(summary_file, "r") as f:
        data = json.load(f)
    
    if corr_file.exists():
        with open(corr_file, "r") as f:
            corr_data = json.load(f)
            data["correlation"] = corr_data.get("statistical_correlation", {})
            data["wind_transport"] = corr_data.get("wind_transport_analysis", {})
    
    return data


@app.get("/api/hcho/hotspots")
async def get_hcho_hotspots():
    """Returns Getis-Ord Gi* significant HCHO hotspot points and DBSCAN cluster polygons."""
    gi_file = DS_DATA_DIR / "hotspots" / "hcho_hotspots_getis_ord.geojson"
    cluster_file = DS_DATA_DIR / "hotspots" / "biomass_clusters_dbscan.geojson"
    
    gi_geojson = json.load(open(gi_file)) if gi_file.exists() else {"type": "FeatureCollection", "features": []}
    cluster_geojson = json.load(open(cluster_file)) if cluster_file.exists() else {"type": "FeatureCollection", "features": []}
    
    return {
        "getis_ord_hotspots": gi_geojson,
        "dbscan_clusters": cluster_geojson
    }


@app.get("/api/hcho/fires")
async def get_active_fires():
    """Returns authentic NASA VIIRS & MODIS active fire detections across India."""
    fires_file = DS_DATA_DIR / "processed" / "active_fires_india_processed.geojson"
    if not fires_file.exists():
        raise HTTPException(status_code=404, detail="Active fires GeoJSON not found.")
    with open(fires_file, "r") as f:
        return json.load(f)


@app.get("/api/hcho/grid")
async def get_hcho_grid():
    """Returns Sentinel-5P TROPOMI tropospheric formaldehyde column concentration mesh."""
    grid_file = DS_DATA_DIR / "processed" / "india_hcho_aligned.geojson"
    if not grid_file.exists():
        raise HTTPException(status_code=404, detail="HCHO grid GeoJSON not found.")
    with open(grid_file, "r") as f:
        return json.load(f)


@app.get("/api/hcho/correlation")
async def get_hcho_correlation():
    """Returns statistical correlation and ERA5 wind transport analysis report."""
    corr_file = DS_DATA_DIR / "processed" / "correlation_report.json"
    if not corr_file.exists():
        raise HTTPException(status_code=404, detail="Correlation report not found.")
    with open(corr_file, "r") as f:
        return json.load(f)


@app.get("/api/hcho/wind")
async def get_hcho_wind_vectors():
    """Returns ECMWF ERA5 10m synoptic wind transport vectors over India."""
    wind_file = DS_DATA_DIR / "processed" / "wind_transport_vectors.geojson"
    if not wind_file.exists():
        raise HTTPException(status_code=404, detail="Wind transport GeoJSON not found.")
    with open(wind_file, "r") as f:
        return json.load(f)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
