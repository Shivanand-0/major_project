"""
Step 01: Raw Ingestion Package.
Provides modules for fetching authentic data from external sources:
  - WeatherIngestion         — ECMWF ERA5 & Open-Meteo
  - AirQualityIngestion      — Copernicus CAMS satellite
  - CPCBStationFeed          — Live CPCB portal scraping
  - CpcbBulkIngestion        — OpenAQ S3 historical archive
  - OpenStreetMapRoadIngestion — OSM Overpass road network
  - DataIngestionEngine      — Unified orchestrator
"""

from .config import VIDARBHA_STATIONS, TRAINING_START_DATE, TRAINING_END_DATE
from .naqi import compute_composite_naqi, compute_subindex, get_naqi_category
from .weather_ingestion import WeatherIngestion
from .air_quality_ingestion import AirQualityIngestion
from .cpcb_ground_truth import CPCBStationFeed
from .cpcb_bulk_ingestion import CpcbBulkIngestion
from .osm_road_fetcher import OpenStreetMapRoadIngestion
from .collector import DataIngestionEngine

__all__ = [
    "VIDARBHA_STATIONS",
    "TRAINING_START_DATE",
    "TRAINING_END_DATE",
    "compute_composite_naqi",
    "compute_subindex",
    "get_naqi_category",
    "WeatherIngestion",
    "AirQualityIngestion",
    "CPCBStationFeed",
    "CpcbBulkIngestion",
    "OpenStreetMapRoadIngestion",
    "DataIngestionEngine",
]
