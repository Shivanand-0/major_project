"""
Step 08: Backend Service Launcher.
Starts the FastAPI application on http://localhost:8000.
"""

import sys
import io
import uvicorn
from pathlib import Path
import os

# Ensure UTF-8 output on Windows console
if sys.stdout and hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 1. Define folder layout explicitly relative to PROJECT_ROOT (D:\college_dev)
PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"
ML_DIR = PROJECT_ROOT / "ml"

# Ensure all relevant paths are in sys.path
for p in [str(BACKEND_DIR), str(ML_DIR), str(ML_DIR / "step_07_serialization")]:
    if p not in sys.path:
        sys.path.insert(0, p)

if __name__ == "__main__":
    print("=" * 80)
    print(">> STARTING VIDARBHA AIR QUALITY VIRTUAL SENSOR BACKEND API")
    print("=" * 80)
    
    # Render provides the port dynamically. Fallback to 8000 for local use.
    port = int(os.environ.get("PORT", 8000))
    
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=port, 
        reload=True, 
        app_dir=str(BACKEND_DIR)
    )
