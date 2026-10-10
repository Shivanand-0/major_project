"""
Step 01: Raw Ingestion Package
Provides tools for querying and archiving authentic ECMWF ERA5 meteorology and Copernicus CAMS / CPCB air quality measurements.
"""

from .config import VIDARBHA_STATIONS, HISTORICAL_START_DATE, HISTORICAL_END_DATE
from .weather_ingestion import AuthenticWeatherIngestion
from .air_quality_ingestion import AuthenticAirQualityIngestion
from .collector import DataIngestionEngine

__all__ = [
    "VIDARBHA_STATIONS",
    "HISTORICAL_START_DATE",
    "HISTORICAL_END_DATE",
    "AuthenticWeatherIngestion",
    "AuthenticAirQualityIngestion",
    "DataIngestionEngine"
]
