"""
Step 04: Data Split Package
Provides chronological window cuts and spatial Leave-One-Station-Out cross-validation partitioning.
"""

from .config import (
    MASTER_MATRIX_FILE,
    SPLIT_DIR,
    LOSO_DIR,
    TRAIN_START,
    TRAIN_END,
    VAL_START,
    VAL_END,
    TEST_START,
    TEST_END,
    TARGET_COLUMN,
    DROP_COLUMNS
)
from .splitter import DataSplitter

__all__ = [
    "MASTER_MATRIX_FILE",
    "SPLIT_DIR",
    "LOSO_DIR",
    "TRAIN_START",
    "TRAIN_END",
    "VAL_START",
    "VAL_END",
    "TEST_START",
    "TEST_END",
    "TARGET_COLUMN",
    "DROP_COLUMNS",
    "DataSplitter"
]
