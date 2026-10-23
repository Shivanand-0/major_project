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
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

# Ensure backend and project root are on sys.path
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
for p in [str(BACKEND_DIR), str(PROJECT_ROOT), str(PROJECT_ROOT / "ds")]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend_config import (
    VIDARBHA_NODES,
    VIDARBHA_BOUNDS,
    CPCB_CATEGORIES,
    PIPELINE_MODEL_PATH
)
from services.estimator import get_estimator

try:
    from ds.pipeline_runner import get_pipeline_status, run_daily_pipeline
except Exception:
    get_pipeline_status = None
    run_daily_pipeline = None

import time
import threading

def _daily_scheduler_worker():
    """
    Background daemon thread that periodically checks if a new daily satellite pass is ready.
    Waits 90s after startup so server can boot and serve initial traffic smoothly, then checks every 4 hours.
    """
    time.sleep(90)  # Let server finish starting up and serve initial requests
    while True:
        try:
            if get_pipeline_status and run_daily_pipeline:
                st = get_pipeline_status()
                if not st.get("is_current"):
                    print("[SCHEDULER] Daily HCHO satellite data is stale. Initiating automatic daily update...")
                    run_daily_pipeline(force_refresh=False)
                else:
                    print(f"[SCHEDULER] Daily HCHO data is up to date (pass: {st.get('observation_date')}). Next check in 4h.")
        except Exception as err:
            print(f"[SCHEDULER ERROR] Daily check failed: {err}")
        # Sleep for 4 hours before checking next overpass
        time.sleep(4 * 3600)

app = FastAPI(
    title="Virtual Air Quality Estimation System (Vidarbha Grid)",
    description="Operational ML microservice mapping ECMWF meteorology and Copernicus CAMS chemical tracers to physical CPCB India NAQI standards.",
    version="1.0.0"
)

@app.on_event("startup")
async def start_daily_scheduler():
    t = threading.Thread(target=_daily_scheduler_worker, daemon=True, name="HCHO-Daily-Scheduler")
    t.start()

# Enable CORS for frontend integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_cache_control_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static/") or request.url.path == "/" or request.url.path.startswith("/api/hcho/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Static files directory
STATIC_DIR = BACKEND_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class CoordinatePredictionRequest(BaseModel):
    latitude: float = Field(..., ge=15.0, le=26.0, description="Latitude within Maharashtra/Central India")
    longitude: float = Field(..., ge=72.0, le=85.0, description="Longitude within Maharashtra/Central India")
    temperature_override: Optional[float] = Field(None, description="Optional temperature in Celsius")
    humidity_override: Optional[float] = Field(None, description="Optional relative humidity (%)")
    wind_speed_override: Optional[float] = Field(None, description="Optional wind speed in km/h")
    wind_dir_override: Optional[float] = Field(None, description="Optional wind direction (0-360 deg)")
    pm25_override: Optional[float] = Field(None, description="Optional CAMS PM2.5 in ug/m3")
    pm10_override: Optional[float] = Field(None, description="Optional CAMS PM10 in ug/m3")
    live_weather: Optional[Dict[str, Any]] = Field(None, description="Live meteorological telemetry fetched directly by client")
    live_aq: Optional[Dict[str, Any]] = Field(None, description="Live atmospheric chemical telemetry fetched directly by client")


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
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch live node states: {str(e)}")


@app.post("/api/predict")
async def predict_custom_coordinate(req: CoordinatePredictionRequest):
    """Predicts ground-level India NAQI for any coordinate across Vidarbha using live or custom parameters."""
    estimator = get_estimator()

    weather_override = dict(req.live_weather) if req.live_weather else {}
    if req.temperature_override is not None:
        weather_override["temperature_2m"] = req.temperature_override
    if req.humidity_override is not None:
        weather_override["relative_humidity_2m"] = req.humidity_override
    if req.wind_speed_override is not None:
        weather_override["wind_speed_10m"] = req.wind_speed_override
    if req.wind_dir_override is not None:
        weather_override["wind_direction_10m"] = req.wind_dir_override

    aq_override = dict(req.live_aq) if req.live_aq else {}
    if req.pm25_override is not None:
        aq_override["pm2_5"] = req.pm25_override
    if req.pm10_override is not None:
        aq_override["pm10"] = req.pm10_override

    try:
        result = estimator.predict_coordinate(
            lat=req.latitude,
            lon=req.longitude,
            weather_override=weather_override if weather_override else None,
            aq_override=aq_override if aq_override else None
        )
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
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

@app.get("/api/hcho/status")
async def get_hcho_pipeline_status():
    """Returns real-time data freshness, observation date, and sync status of the daily HCHO pipeline."""
    if get_pipeline_status:
        return get_pipeline_status()
    summary_file = DS_DATA_DIR / "hotspots" / "hotspots_summary.json"
    if summary_file.exists():
        with open(summary_file, "r") as f:
            data = json.load(f)
        return {
            "status": "ready",
            "observation_date": data.get("observation_date", "Operational Satellite Pass"),
            "last_updated_ist": data.get("last_updated_ist", "Recent"),
            "is_current": True
        }
    return {"status": "missing", "is_current": False}


@app.post("/api/hcho/refresh")
async def refresh_hcho_daily_pipeline(background_tasks: BackgroundTasks, force: bool = Query(True, description="Force re-ingestion and clustering")):
    """Triggers the automated daily ingestion, preprocessing, Getis-Ord Gi*, and DBSCAN clustering pipeline."""
    if not run_daily_pipeline:
        raise HTTPException(status_code=500, detail="Pipeline runner module not available.")
    
    # Run in background to avoid blocking client
    def run_worker():
        try:
            print("[BACKEND] Executing automated daily HCHO hotspot pipeline...")
            run_daily_pipeline(force_refresh=force)
        except Exception as e:
            print(f"[BACKEND ERROR] Background pipeline execution failed: {e}")

    background_tasks.add_task(run_worker)
    return {
        "message": "Automated daily HCHO, wind & fire pipeline execution started in background.",
        "status": "processing",
        "forced": force
    }


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
            data["spatial_clustering_evaluation"] = corr_data.get("spatial_clustering_evaluation", {})
            if "clustering_evaluation" not in data and "spatial_clustering_evaluation" in corr_data:
                data["clustering_evaluation"] = corr_data["spatial_clustering_evaluation"]

    # Ensure top-level KPIs for frontend cards
    metrics = data.get("metrics", {})
    if "total_active_fires" not in data or data["total_active_fires"] is None:
        data["total_active_fires"] = metrics.get("total_active_fires", 0)
    if "total_fire_radiative_power_mw" not in data or data["total_fire_radiative_power_mw"] is None:
        data["total_fire_radiative_power_mw"] = metrics.get("total_frp_mw", 0)
    if "peak_hcho_column_10_15" not in data or data["peak_hcho_column_10_15"] is None:
        data["peak_hcho_column_10_15"] = metrics.get("max_india_hcho_e15", 0)

    # Ensure correlation keys
    if "correlation" in data and isinstance(data["correlation"], dict):
        reg = data["correlation"].get("regression", {})
        if "r_squared" not in data["correlation"] and "r_squared" in reg:
            data["correlation"]["r_squared"] = reg["r_squared"]

    # Ensure wind transport keys
    if "wind_transport" in data and isinstance(data["wind_transport"], dict):
        if "calm_mean_hcho" not in data["wind_transport"] and "calm_layer_mean_hcho" in data["wind_transport"]:
            data["wind_transport"]["calm_mean_hcho"] = data["wind_transport"]["calm_layer_mean_hcho"]
        if "windy_mean_hcho" not in data["wind_transport"] and "dispersion_layer_mean_hcho" in data["wind_transport"]:
            data["wind_transport"]["windy_mean_hcho"] = data["wind_transport"]["dispersion_layer_mean_hcho"]
    
    if "top_clusters" in data and "dbscan_clusters" not in data:
        data["dbscan_clusters"] = {"top_clusters": data["top_clusters"]}
    
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
