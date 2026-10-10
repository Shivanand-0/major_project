"""
Configuration for Step 04: Data Splitting.
Defines strict chronological window boundaries, monitored vs. unmonitored station partitions,
and spatial holdout parameters. Eliminates temporal and spatial data leakage.
"""

from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CLEAN_DIR = DATA_DIR / "clean"
SPLIT_DIR = DATA_DIR / "split"
LOSO_DIR = SPLIT_DIR / "loso_spatial_splits"
UNMONITORED_DIR = SPLIT_DIR / "unmonitored_deployment"

# Master matrix input
MASTER_MATRIX_FILE = CLEAN_DIR / "master_analytical_matrix.csv"

# Ensure output directories exist
SPLIT_DIR.mkdir(parents=True, exist_ok=True)
LOSO_DIR.mkdir(parents=True, exist_ok=True)
UNMONITORED_DIR.mkdir(parents=True, exist_ok=True)

# Station Categorization (Ground Truth Monitored vs. Virtual Target Deployment)
MONITORED_GROUND_STATIONS = [
    "NAGPUR_CENTRAL",     # Continuous CAAQMS (MPCB UID: 12444 / 8824)
    "CHANDRAPUR_MIDC"     # Continuous CAAQMS (MPCB UID: 9147)
]

UNMONITORED_TARGET_STATIONS = [
    "AMRAVATI_CENTRAL",   # No continuous CAAQMS (Virtual Sensor Target)
    "AKOLA_WEST"          # No continuous CAAQMS (Virtual Sensor Target)
]

# Chronological Window Cut Boundaries (Strict temporal separation)
TRAIN_START = "2023-01-01 00:00:00"
TRAIN_END   = "2023-08-31 23:00:00"  # 8 months (~67%)

VAL_START   = "2023-09-01 00:00:00"
VAL_END     = "2023-10-31 23:00:00"  # 2 months (~17%)

TEST_START  = "2023-11-01 00:00:00"
TEST_END    = "2023-12-31 23:00:00"  # 2 months (~17% - Winter peak & inversion period)

# Primary Target Variable: Official CPCB India NAQI Composite Index
TARGET_COLUMN = "india_naqi"

# Metadata / Non-feature columns to drop from input feature matrix X
DROP_COLUMNS = [
    "timestamp",
    "station_id",
    "data_source",
    "india_naqi"   # Primary Target variable y
]
