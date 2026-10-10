### 🔑 API Key Requirement

**No API key or signup is required!**  
Both the **ECMWF ERA5 Weather Archive** and **Copernicus CAMS Air Quality** APIs via Open-Meteo and the **WAQI** real-time feed are open-access and completely free for research/development.

### 💻 Commands to Run and Re-Fetch the Data

Ensure you are in the project root directory (`d:\college_dev\ml`).

#### 1\. Full Historical Data Ingestion (All 4 Vidarbha Stations for Full Year):

```powershell
.\venv\Scripts\python step_01_raw_ingestion\collector.py --mode historical
```

*(If your virtual environment is already activated in your terminal, you can simply run `python step_01_raw_ingestion\collector.py --mode historical`)*

#### 2\. Test Live Real-Time Ingestion (Current Weather & Live CPCB Physical Station):

```powershell
.\venv\Scripts\python step_01_raw_ingestion\collector.py --mode live --city nagpur
```

#### 3\. Run Individual Modules Directly (Optional):

*   To fetch only **ECMWF ERA5 Weather**:
    
    ```powershell
    .\venv\Scripts\python step_01_raw_ingestion\weather_ingestion.py
    ```
    
*   To fetch only **Copernicus CAMS Air Quality**:
    
    ```powershell
    .\venv\Scripts\python step_01_raw_ingestion\air_quality_ingestion.py
    ```
    

#### 4\. Custom Date Range (Optional):

If you want to fetch a specific date range:

```powershell
.\venv\Scripts\python step_01_raw_ingestion\collector.py --mode historical --start-date 2023-06-01 --end-date 2023-12-31
```

Once you’ve run the command and inspected the output, let me know when you’re ready to proceed to **Step 02: Preprocessing & Traffic Congestion Index (TCI)**!