"""
OpenStreetMap Real Road Network Ingestion Module.
Queries the official OpenStreetMap Overpass API to fetch real, physical road infrastructure:
  - Total road segments within radius
  - Major arterial highways (motorway, trunk, primary)
  - Secondary commercial roads & tertiary collectors
  - Calculated physical road density per km²
"""

import time
import requests
import json
from pathlib import Path
from typing import Dict, Any

try:
    from step_01_raw_ingestion.config import VIDARBHA_STATIONS
except ImportError:
    import sys
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from step_01_raw_ingestion.config import VIDARBHA_STATIONS


class OpenStreetMapRoadIngestion:
    """Queries real road network segments from OpenStreetMap Overpass API."""

    OVERPASS_URL = "https://overpass-api.de/api/interpreter"
    HEADERS = {
        "User-Agent": "VidarbhaAirQualityResearch/1.0"
    }

    def fetch_road_infrastructure(self, lat: float, lon: float, radius_m: int = 1200) -> Dict[str, Any]:
        """
        Queries real-world OSM road network within radius_m of (lat, lon).
        """
        query = f'[out:json][timeout:25];(way["highway"](around:{radius_m},{lat},{lon}););out tags;'
        print(f"[OSM Ingestion] Fetching real road network for ({lat:.4f}, {lon:.4f}) radius {radius_m}m...")

        for attempt in range(1, 4):
            try:
                response = requests.post(self.OVERPASS_URL, data={"data": query}, headers=self.HEADERS, timeout=30)
                if response.status_code == 200:
                    elements = response.json().get("elements", [])

                    major_highways = 0
                    secondary_roads = 0
                    residential_roads = 0

                    for el in elements:
                        hw = el.get("tags", {}).get("highway", "")
                        if hw in ["motorway", "trunk", "primary"]:
                            major_highways += 1
                        elif hw in ["secondary", "tertiary"]:
                            secondary_roads += 1
                        elif hw in ["residential", "living_street", "unclassified", "service"]:
                            residential_roads += 1

                    total_roads = len(elements)
                    radius_km = radius_m / 1000.0
                    area_sqkm = 3.14159 * (radius_km ** 2)
                    road_density_per_sqkm = round(total_roads / max(0.1, area_sqkm), 2)

                    result = {
                        "latitude": lat,
                        "longitude": lon,
                        "total_road_segments": total_roads,
                        "major_highways_count": major_highways,
                        "secondary_roads_count": secondary_roads,
                        "residential_roads_count": residential_roads,
                        "road_density_per_sqkm": road_density_per_sqkm
                    }
                    print(f"[OSM Ingestion] Success: {total_roads} roads (Major: {major_highways}, Secondary: {secondary_roads}, Density: {road_density_per_sqkm}/km2)")
                    return result
            except Exception as e:
                print(f"[OSM Ingestion] Attempt {attempt} failed: {e}")
                time.sleep(2 * attempt)

        return {
            "latitude": lat,
            "longitude": lon,
            "total_road_segments": 0,
            "major_highways_count": 0,
            "secondary_roads_count": 0,
            "residential_roads_count": 0,
            "road_density_per_sqkm": 0.0
        }

    def fetch_all_stations_road_data(self) -> Dict[str, Dict[str, Any]]:
        """Queries and archives real OpenStreetMap road infrastructure for all Vidarbha stations."""
        results = {}
        for station_id, meta in VIDARBHA_STATIONS.items():
            road_info = self.fetch_road_infrastructure(lat=meta["latitude"], lon=meta["longitude"], radius_m=1200)
            results[station_id] = road_info
            time.sleep(2)

        output_file = Path(__file__).resolve().parent.parent / "data" / "raw" / "real_osm_road_network.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)

        print(f"\n[SUCCESS] Real OSM Road Network archived to: {output_file}")
        return results


if __name__ == "__main__":
    osm = OpenStreetMapRoadIngestion()
    osm.fetch_all_stations_road_data()
