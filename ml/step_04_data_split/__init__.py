"""
Step 04: Data Split Package
Provides chronological window cuts and spatial Leave-One-Station-Out cross-validation partitioning.
"""

from .config import (
    MASTER_MATRIX_FILE,
    SPLIT_DIR,
    LOSO_DIR,
    SPLIT_STRATEGY,
    BLOCK_TRAIN_DAY_MAX,
    BLOCK_VAL_DAY_MIN,
    BLOCK_VAL_DAY_MAX,
    BLOCK_TEST_DAY_MIN,
    TARGET_COLUMN,
    DROP_COLUMNS
)
from .splitter import DataSplitter

__all__ = [
    "MASTER_MATRIX_FILE",
    "SPLIT_DIR",
    "LOSO_DIR",
    "SPLIT_STRATEGY",
    "BLOCK_TRAIN_DAY_MAX",
    "BLOCK_VAL_DAY_MIN",
    "BLOCK_VAL_DAY_MAX",
    "BLOCK_TEST_DAY_MIN",
    "TARGET_COLUMN",
    "DROP_COLUMNS",
    "DataSplitter"
]

