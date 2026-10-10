"""
Step 08: Backend Service Launcher.
Starts the FastAPI application on http://localhost:8000.
"""

import sys
import io
import uvicorn
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.stdout and hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
ML_DIR = PROJECT_ROOT / "ml"

# Ensure all relevant paths are in sys.path
for p in [str(BACKEND_DIR), str(ML_DIR), str(ML_DIR / "step_07_serialization")]:
    if p not in sys.path:
        sys.path.insert(0, p)

if __name__ == "__main__":
    print("=" * 80)
    print(">> STARTING VIDARBHA AIR QUALITY VIRTUAL SENSOR BACKEND API")
    print(">> Dashboard UI: http://localhost:8000")
    print(">> API Documentation: http://localhost:8000/docs")
    print("=" * 80)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
