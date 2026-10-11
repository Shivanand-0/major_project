"""
Configuration for Step 04: Data Splitting.
Defines strict chronological window boundaries, all 4 physical ground truth stations,
and spatial holdout (LOSO) parameters. Eliminates temporal and spatial data leakage.
"""

from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CLEAN_DIR = DATA_DIR / "clean"
SPLIT_DIR = DATA_DIR / "split"
LOSO_DIR = SPLIT_DIR / "loso_spatial_splits"
UNMONITORED_DIR = SPLIT_DIR / "unmonitored_deployment"

# Master matrix input (prefer 2025 CPCB physical matrix)
MASTER_MATRIX_2025 = CLEAN_DIR / "master_analytical_matrix_cpcb_2025.csv"
MASTER_MATRIX_LEGACY = CLEAN_DIR / "master_analytical_matrix.csv"
MASTER_MATRIX_FILE = MASTER_MATRIX_2025 if MASTER_MATRIX_2025.exists() else MASTER_MATRIX_LEGACY

# Ensure output directories exist
SPLIT_DIR.mkdir(parents=True, exist_ok=True)
LOSO_DIR.mkdir(parents=True, exist_ok=True)
UNMONITORED_DIR.mkdir(parents=True, exist_ok=True)

# Station Registry: All 4 Vidarbha stations have authentic CPCB CAAQMS physical ground truth
MONITORED_GROUND_STATIONS = [
    "NAGPUR_CENTRAL",     # Continuous CAAQMS (MPCB Civil Lines, OpenAQ ID: 5621)
    "CHANDRAPUR_MIDC",    # Continuous CAAQMS (MPCB MIDC Khutala, OpenAQ ID: 5565)
    "AMRAVATI_CENTRAL",   # Continuous CAAQMS (MPCB Shivneri Colony, OpenAQ ID: 3409458)
    "AKOLA_WEST"          # Continuous CAAQMS (MPCB Ramdaspeth, OpenAQ ID: 3409456)
]

# Splitting Strategy: 'seasonal_block' provides balanced seasonal coverage across
# summer, monsoon, and winter while maintaining strict non-overlapping temporal blocks.
SPLIT_STRATEGY = "seasonal_block"

# Seasonal Block Day Boundaries (Applied periodically across every month)
# Train: Days 1 to 20 (~64.1% of records)
# Validation: Days 21 to 25 (~17.6% of records)
# Test: Days 26 to end of month (~18.3% of records)
BLOCK_TRAIN_DAY_MAX = 20
BLOCK_VAL_DAY_MIN = 21
BLOCK_VAL_DAY_MAX = 25
BLOCK_TEST_DAY_MIN = 26

# Primary Target Variable: Official CPCB India NAQI Composite Index (Physical CAAQMS)
TARGET_COLUMN = "india_naqi"

# Metadata and static station lookup columns to drop from feature matrix X
# cams_satellite_naqi, dynamic wind alignment, and atmospheric physics REMAIN in X!
DROP_COLUMNS = [
    "timestamp",
    "station_id",
    "data_source",
    "india_naqi",   # Primary Target variable y
    # Static distance-to-station features act as memorized station categorical proxies:
    "dist_to_nagpur_central_km",
    "idw_weight_nagpur_central",
    "dist_to_chandrapur_midc_km",
    "idw_weight_chandrapur_midc",
    "dist_to_amravati_central_km",
    "idw_weight_amravati_central",
    "dist_to_akola_west_km",
    "idw_weight_akola_west"
]
