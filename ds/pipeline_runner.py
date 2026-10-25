"""
Master Daily Pipeline Orchestrator for Pan-India HCHO Hotspots, Wind & Fire Surveillance.
Automates daily ingestion, QA screening, Getis-Ord Gi* & DBSCAN hotspot clustering, 
and synoptic atmospheric transport analysis.

Usage:
  python ds/pipeline_runner.py             # Runs if data is stale (> 20 hours old or missing)
  python ds/pipeline_runner.py --force     # Forces execution of all 4 pipeline steps
  python ds/pipeline_runner.py --check     # Reports data freshness without running
  python ds/pipeline_runner.py --date 20261016  # Ingests a specific satellite overpass date
"""

import sys
import os
import json
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Ensure project directories are in sys.path
DS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = DS_DIR.parent
if str(DS_DIR) not in sys.path:
    sys.path.insert(0, str(DS_DIR))

# Import individual step modules
try:
    import importlib
    step01 = importlib.import_module("01_data_ingestion")
    step02 = importlib.import_module("02_preprocessing")
    step03 = importlib.import_module("03_hotspot_generation")
    step04 = importlib.import_module("04_correlation_analysis")
except Exception as e:
    # Fallback to direct file execution if filename numbering prevents regular import
    step01 = None
    step02 = None
    step03 = None
    step04 = None

DATA_DIR = DS_DIR / "data"
FINAL_MAP_DIR = DATA_DIR / "final_map_data"
EVAL_DIR = DATA_DIR / "evaluation_and_correlations"
PROCESSED_GRID_DIR = DATA_DIR / "processed_grid"
RAW_DIR = DATA_DIR / "raw"

# Legacy directory fallbacks
HOTSPOTS_DIR = EVAL_DIR if EVAL_DIR.exists() else DATA_DIR / "hotspots"
PROCESSED_DIR = FINAL_MAP_DIR if FINAL_MAP_DIR.exists() else DATA_DIR / "processed"

# Primary summary and metadata references
SUMMARY_FILE = EVAL_DIR / "hotspots_summary.json"
if not SUMMARY_FILE.exists():
    SUMMARY_FILE = DATA_DIR / "hotspots" / "hotspots_summary.json"

INGESTION_META_FILE = RAW_DIR / "metadata" / "ingestion_metadata.json"
if not INGESTION_META_FILE.exists():
    INGESTION_META_FILE = RAW_DIR / "ingestion_metadata.json"


def get_pipeline_status() -> dict:
    """
    Checks data freshness of the current DS hotspot layers.
    Determines if a daily refresh is due.
    """
    if not SUMMARY_FILE.exists():
        return {
            "status": "missing",
            "is_current": False,
            "message": "Hotspots summary does not exist. Initial run required.",
            "observation_date": None,
            "last_updated_ist": None,
            "age_hours": 999.0
        }

    try:
        with open(SUMMARY_FILE, "r") as f:
            summary = json.load(f)
        
        ts_utc_str = summary.get("timestamp_utc")
        obs_date = summary.get("observation_date", "Unknown")
        last_ist = summary.get("last_updated_ist", "Unknown")

        if ts_utc_str:
            ts_utc = datetime.fromisoformat(ts_utc_str.replace("Z", "+00:00"))
            age_seconds = (datetime.now(timezone.utc) - ts_utc).total_seconds()
            age_hours = round(age_seconds / 3600.0, 1)
        else:
            age_hours = 999.0

        # Max acceptable age before requiring daily update: 22 hours
        # (matching daily satellite orbit cadence)
        is_current = age_hours < 22.0

        return {
            "status": "ready" if is_current else "stale",
            "is_current": is_current,
            "observation_date": obs_date,
            "last_updated_ist": last_ist,
            "last_updated_utc": ts_utc_str,
            "age_hours": age_hours,
            "total_fires": summary.get("total_active_fires", 0),
            "total_clusters": summary.get("metrics", {}).get("distinct_clusters_count", 0),
            "message": f"Data is {'current' if is_current else 'stale'} ({age_hours}h old, satellite pass: {obs_date})"
        }
    except Exception as e:
        return {
            "status": "error",
            "is_current": False,
            "message": f"Error inspecting summary file: {e}",
            "observation_date": None,
            "last_updated_ist": None,
            "age_hours": 999.0
        }


def run_daily_pipeline(force_refresh: bool = False, target_date: str = None) -> dict:
    """
    Executes the end-to-end daily data science pipeline:
      1. Ingest real-time S5P HCHO (DLR L3), NASA FIRMS active fires, Open-Meteo rolling wind vectors
      2. QA Filter and aggregate to 0.25-degree India grid
      3. Compute Getis-Ord Gi* spatial autocorrelation and DBSCAN density clustering
      4. Compute bivariate regression and ERA5 wind transport dispersion
    """
    print("\n" + "#" * 80)
    print("PAN-INDIA HCHO, WIND & FIRE DAILY HOTSPOT PIPELINE RUNNER")
    print("#" * 80)
    t0_master = time.time()

    status = get_pipeline_status()
    if not force_refresh and status.get("is_current") and not target_date:
        print(f"[*] Pipeline data is already fresh ({status['age_hours']}h old, satellite pass: {status['observation_date']}).")
        print("    Use --force to run anyway.")
        return {
            "success": True,
            "skipped": True,
            "reason": "Data already current within daily threshold.",
            "status": status
        }

    results = {"steps": {}}

    # Step 01: Ingestion
    print("\n>>> EXECUTING STEP 01: DATA INGESTION...")
    t_step = time.time()
    try:
        if step01 and hasattr(step01, "run_pipeline"):
            meta01 = step01.run_pipeline(target_date=target_date)
        else:
            # Fallback to subprocess
            import subprocess
            cmd = [sys.executable, str(DS_DIR / "01_data_ingestion.py")]
            if target_date:
                cmd.extend(["--date", target_date])
            res = subprocess.run(cmd, check=True)
            meta01 = {"exit_code": res.returncode}
        results["steps"]["01_ingestion"] = {"status": "success", "duration_sec": round(time.time() - t_step, 2), "metadata": meta01}
    except Exception as e:
        print(f"[FATAL ERROR] Step 01 Ingestion failed: {e}")
        return {"success": False, "failed_step": "01_ingestion", "error": str(e)}

    # Step 02: Preprocessing
    print("\n>>> EXECUTING STEP 02: QA SCREENING & SPATIAL HARMONIZATION...")
    t_step = time.time()
    try:
        if step02 and hasattr(step02, "run_pipeline"):
            meta02 = step02.run_pipeline()
        else:
            import subprocess
            subprocess.run([sys.executable, str(DS_DIR / "02_preprocessing.py")], check=True)
            meta02 = {}
        results["steps"]["02_preprocessing"] = {"status": "success", "duration_sec": round(time.time() - t_step, 2), "metadata": meta02}
    except Exception as e:
        print(f"[FATAL ERROR] Step 02 Preprocessing failed: {e}")
        return {"success": False, "failed_step": "02_preprocessing", "error": str(e)}

    # Step 03: Hotspots & Clustering
    print("\n>>> EXECUTING STEP 03: GETIS-ORD GI* & DBSCAN CLUSTERING...")
    t_step = time.time()
    try:
        if step03 and hasattr(step03, "run_pipeline"):
            meta03 = step03.run_pipeline()
        else:
            import subprocess
            subprocess.run([sys.executable, str(DS_DIR / "03_hotspot_generation.py")], check=True)
            meta03 = {}
        results["steps"]["03_hotspots"] = {"status": "success", "duration_sec": round(time.time() - t_step, 2), "metadata": meta03}
    except Exception as e:
        print(f"[FATAL ERROR] Step 03 Hotspot Generation failed: {e}")
        return {"success": False, "failed_step": "03_hotspots", "error": str(e)}

    # Step 04: Correlation & Wind Dispersion
    print("\n>>> EXECUTING STEP 04: CORRELATION & WIND ADVECTION TRANSPORT...")
    t_step = time.time()
    try:
        if step04 and hasattr(step04, "run_pipeline"):
            meta04 = step04.run_pipeline()
        else:
            import subprocess
            subprocess.run([sys.executable, str(DS_DIR / "04_correlation_analysis.py")], check=True)
            meta04 = {}
        results["steps"]["04_correlation"] = {"status": "success", "duration_sec": round(time.time() - t_step, 2), "metadata": meta04}
    except Exception as e:
        print(f"[FATAL ERROR] Step 04 Correlation failed: {e}")
        return {"success": False, "failed_step": "04_correlation", "error": str(e)}

    total_duration = round(time.time() - t0_master, 2)
    final_status = get_pipeline_status()
    results["success"] = True
    results["total_duration_sec"] = total_duration
    results["status"] = final_status

    print("\n" + "=" * 80)
    print(f"[PIPELINE SUCCESS] Daily HCHO, Fire & Wind Analysis updated in {total_duration}s.")
    print(f"Observation Date : {final_status.get('observation_date')}")
    print(f"Last Updated IST : {final_status.get('last_updated_ist')}")
    print(f"Active Fires     : {final_status.get('total_fires'):,}")
    print(f"Biomass Clusters : {final_status.get('total_clusters')}")
    print("=" * 80 + "\n")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Master Daily Pipeline for Pan-India HCHO Hotspots")
    parser.add_argument("--force", action="store_true", help="Force execution even if data is current")
    parser.add_argument("--check", action="store_true", help="Check data freshness and exit")
    parser.add_argument("--date", type=str, default=None, help="Target satellite overpass date (YYYYMMDD)")
    args = parser.parse_args()

    if args.check:
        st = get_pipeline_status()
        print(json.dumps(st, indent=2))
        sys.exit(0)

    res = run_daily_pipeline(force_refresh=args.force, target_date=args.date)
    if not res.get("success"):
        sys.exit(1)
