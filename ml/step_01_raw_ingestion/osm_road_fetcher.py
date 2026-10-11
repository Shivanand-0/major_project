"""
OpenStreetMap Road Network Ingestion Module.
Queries the OSM Overpass API to fetch real road infrastructure metrics:
  - Total road segments within radius
  - Major arterial highways (motorway, trunk, primary)
  - Secondary and tertiary roads
  - Physical road density per km²
"""

import sys
import time
import json
import requests
from pathlib import Path
from typing import Dict, Any

# Ensure ML root is in path for direct execution
_ML_ROOT = Path(__file__).resolve().parent.parent
if str(_ML_ROOT) not in sys.path:
    sys.path.insert(0, str(_ML_ROOT))

try:
    from .config import VIDARBHA_STATIONS, OSM_RAW_DIR
except (ImportError, ValueError):
    from step_01_raw_ingestion.config import VIDARBHA_STATIONS, OSM_RAW_DIR


class OpenStreetMapRoadIngestion:
    """Queries real road network segments from OpenStreetMap Overpass API."""

    OVERPASS_URL = "https://overpass-api.de/api/interpreter"
    HEADERS = {"User-Agent": "VidarbhaAirQualityResearch/1.0"}

    def fetch_road_infrastructure(self, lat: float, lon: float, radius_m: int = 1200) -> Dict[str, Any]:
        """
        Queries OSM road network within radius_m of (lat, lon).

        Returns:
            Dict with road counts and density metrics.
        """
        query = f'[out:json][timeout:25];(way["highway"](around:{radius_m},{lat},{lon}););out tags;'
        print(f"[OSM] Fetching roads for ({lat:.4f}, {lon:.4f}) r={radius_m}m...")

        for attempt in range(1, 4):
            try:
                resp = requests.post(self.OVERPASS_URL, data={"data": query},
                                     headers=self.HEADERS, timeout=30)
                if resp.status_code == 200:
                    elements = resp.json().get("elements", [])

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

                    total = len(elements)
                    radius_km = radius_m / 1000.0
                    area_sqkm = 3.14159 * (radius_km ** 2)
                    density = round(total / max(0.1, area_sqkm), 2)

                    result = {
                        "latitude": lat,
                        "longitude": lon,
                        "total_road_segments": total,
                        "major_highways_count": major_highways,
                        "secondary_roads_count": secondary_roads,
                        "residential_roads_count": residential_roads,
                        "road_density_per_sqkm": density
                    }
                    print(f"[OSM] [OK] {total} roads (Major={major_highways}, "
                          f"Secondary={secondary_roads}, Density={density}/km2)")
                    return result
            except Exception as e:
                print(f"[OSM] Attempt {attempt} failed: {e}")
                time.sleep(2 * attempt)

        return {
            "latitude": lat, "longitude": lon,
            "total_road_segments": 0, "major_highways_count": 0,
            "secondary_roads_count": 0, "residential_roads_count": 0,
            "road_density_per_sqkm": 0.0
        }

    def fetch_all_stations(self) -> Dict[str, Dict[str, Any]]:
        """Queries OSM road infrastructure for all Vidarbha stations and saves to JSON."""
        results = {}
        for station_id, meta in VIDARBHA_STATIONS.items():
            results[station_id] = self.fetch_road_infrastructure(
                lat=meta["latitude"], lon=meta["longitude"], radius_m=1200
            )
            time.sleep(2)

        output_file = OSM_RAW_DIR / "osm_road_network.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n[OSM] [OK] Saved -> {output_file}")
        return results


if __name__ == "__main__":
    OpenStreetMapRoadIngestion().fetch_all_stations()
