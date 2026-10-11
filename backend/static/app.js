/**
 * Air Quality Monitor — Vidarbha Region Live Air Guide
 * 2-Page Light UI Interactive Frontend Application
 */

let map = null;
let nodeMarkers = {};
let targetClickMarker = null;
let currentNodesData = null;
let activeTargetCoords = { lat: 21.1458, lon: 79.0882, name: "Nagpur Central" };

const VIDARBHA_PRESETS = {
    nagpur: { name: "Nagpur Central", lat: 21.1458, lon: 79.0882 },
    chandrapur: { name: "Chandrapur City", lat: 19.9615, lon: 79.2961 },
    amravati: { name: "Amravati Camp", lat: 20.9374, lon: 77.7796 },
    akola: { name: "Akola Industrial", lat: 20.7002, lon: 77.0082 }
};

// CPCB Category Helper
function getCPCBCategory(aqi) {
    if (aqi <= 50) return { name: "Good", class: "good", desc: "Minimal impact. Safe for everyone.", status: "Optimal health", color: "#10b981" };
    if (aqi <= 100) return { name: "Satisfactory", class: "satisfactory", desc: "Safe for everyday activities", status: "Ideal Air", color: "#22c55e" };
    if (aqi <= 200) return { name: "Moderate", class: "moderate", desc: "Sensitive groups should reduce prolonged exertion", status: "Normal OK", color: "#f59e0b" };
    if (aqi <= 300) return { name: "Poor", class: "poor", desc: "Noticeable haze. Face mask suggested for outdoor work.", status: "Use Mask", color: "#ea580c" };
    if (aqi <= 400) return { name: "Very Poor", class: "very-poor", desc: "Respiratory discomfort on prolonged exposure", status: "Stay Indoors", color: "#ef4444" };
    return { name: "Severe", class: "severe", desc: "Healthy people affected; serious health impact", status: "Severe Alert", color: "#dc2626" };
}

// 1. Navigation & 3-Page Tab Switcher
function initNavigation() {
    const tabCheckLoc = document.getElementById('tab-check-location');
    const tabPopular = document.getElementById('tab-popular-cities');
    const tabPanIndia = document.getElementById('tab-pan-india-hcho');
    const pageCheckLoc = document.getElementById('page-check-location');
    const pagePopular = document.getElementById('page-popular-cities');
    const pagePanIndia = document.getElementById('page-pan-india-hcho');
    const brandLogo = document.getElementById('brand-logo');

    function switchPage(pageName) {
        tabCheckLoc?.classList.remove('active');
        tabPopular?.classList.remove('active');
        tabPanIndia?.classList.remove('active');

        pageCheckLoc?.classList.add('hidden');
        pagePopular?.classList.add('hidden');
        pagePanIndia?.classList.add('hidden');

        if (pageName === 'page-check-location') {
            tabCheckLoc?.classList.add('active');
            pageCheckLoc?.classList.remove('hidden');

            setTimeout(() => {
                if (map) {
                    map.invalidateSize();
                    map.panTo([activeTargetCoords.lat, activeTargetCoords.lon], { animate: false });
                }
            }, 100);
        } else if (pageName === 'page-pan-india-hcho') {
            tabPanIndia?.classList.add('active');
            pagePanIndia?.classList.remove('hidden');

            setTimeout(() => {
                if (!indiaHchoMap) {
                    initIndiaHchoMap();
                } else {
                    indiaHchoMap.invalidateSize();
                }
            }, 100);
        } else {
            tabPopular?.classList.add('active');
            pagePopular?.classList.remove('hidden');
        }
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    if (tabCheckLoc) tabCheckLoc.addEventListener('click', () => switchPage('page-check-location'));
    if (tabPopular) tabPopular.addEventListener('click', () => switchPage('page-popular-cities'));
    if (tabPanIndia) tabPanIndia.addEventListener('click', () => switchPage('page-pan-india-hcho'));
    if (brandLogo) brandLogo.addEventListener('click', () => switchPage('page-popular-cities'));

    return { switchPage };
}

// 2. Initialize Leaflet Map (Light OpenStreetMap Basemap)
function initMap() {
    const mapElement = document.getElementById('vidarbha-map');
    if (!mapElement) return;

    map = L.map('vidarbha-map', {
        center: [20.65, 78.45],
        zoom: 7,
        zoomControl: true,
        attributionControl: false
    });

    // Clean OpenStreetMap Standard basemap (100% Free, zero watermarks, crystal clear roads & districts)
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 18
    }).addTo(map);

    // Map Click Listener -> Updates Target & Runs Prediction
    map.on('click', (e) => {
        const lat = parseFloat(e.latlng.lat.toFixed(4));
        const lon = parseFloat(e.latlng.lng.toFixed(4));
        selectCoordinate(lat, lon, `Custom Coordinate (${lat}, ${lon})`);
    });
}

// 3. Update or Place Interactive Target Pin
function updateTargetPin(lat, lon, label) {
    if (!map) return;

    if (targetClickMarker) {
        map.removeLayer(targetClickMarker);
    }

    const pinHtml = `
        <div style="background:#0f172a; color:#ffffff; padding:4px 10px; border-radius:999px; font-family:'Plus Jakarta Sans',sans-serif; font-size:11px; font-weight:700; border:2px solid #ffffff; box-shadow:0 4px 14px rgba(0,0,0,0.25); display:flex; align-items:center; gap:5px; transform:translate(-50%, -100%);">
            <span style="width:8px; height:8px; border-radius:50%; background:#10b981;"></span>
            <span>${label || 'Selected Location'}</span>
        </div>
    `;

    const icon = L.divIcon({
        className: 'custom-target-marker',
        html: pinHtml,
        iconSize: [120, 30],
        iconAnchor: [60, 30]
    });

    targetClickMarker = L.marker([lat, lon], { icon }).addTo(map);
}

// 4. Render City Nodes on Map
function renderCityMarkersOnMap(nodes) {
    if (!map || !nodes) return;

    nodes.forEach(node => {
        const lat = node.coordinates.lat;
        const lon = node.coordinates.lon;
        const aqi = Math.round(node.virtual_prediction.predicted_india_naqi);
        const cat = getCPCBCategory(aqi);

        const markerHtml = `
            <div class="custom-city-pin" id="marker-${node.id}">
                <span class="pin-bullet" style="background:${cat.color};"></span>
                <span>${node.city} • AQI ${aqi}</span>
            </div>
        `;

        const icon = L.divIcon({
            className: 'city-node-divicon',
            html: markerHtml,
            iconSize: [100, 26]
        });

        const marker = L.marker([lat, lon], { icon }).addTo(map);
        marker.on('click', () => {
            selectCoordinate(lat, lon, node.name, node);
        });

        nodeMarkers[node.id] = marker;
    });
}

// 5. Select Coordinate & Ingest Live Telemetry
async function selectCoordinate(lat, lon, name = null, cachedNode = null) {
    activeTargetCoords = { lat, lon, name: name || `${lat}°N, ${lon}°E` };

    // Update Target Coordinates Pill Overlay
    const coordsEl = document.getElementById('display-target-coords');
    if (coordsEl) coordsEl.textContent = `${lat.toFixed(4)}° N, ${lon.toFixed(4)}° E`;

    // Update Map Pin
    updateTargetPin(lat, lon, name);
    if (map) {
        map.panTo([lat, lon], { animate: true, duration: 0.6 });
    }

    // Set Reading Loading State
    const aqiNumEl = document.getElementById('reading-aqi-num');
    const titleEl = document.getElementById('reading-city-title');
    const pointCoordsEl = document.getElementById('reading-point-coords');
    if (titleEl) titleEl.textContent = `Current Air Quality in ${name || 'Selected Location'}`;
    if (pointCoordsEl) pointCoordsEl.textContent = `Selected Point: ${lat.toFixed(4)}° N, ${lon.toFixed(4)}° E`;

    try {
        let prediction = null;
        let features = null;
        let stationGround = null;

        if (cachedNode && cachedNode.virtual_prediction) {
            prediction = cachedNode.virtual_prediction;
            features = cachedNode.realtime_features;
            stationGround = cachedNode.physical_ground_truth;
        } else {
            const resp = await fetch('/api/predict', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ latitude: lat, longitude: lon })
            });
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const data = await resp.json();
            prediction = data.prediction;
            features = data.realtime_features;
            stationGround = data.physical_station_ground_truth;
        }

        updateReadingPanel(prediction, features, stationGround, name);
    } catch (err) {
        console.error('Failed to evaluate coordinate:', err);
        showToast(`Evaluation note: Using cached baseline for (${lat}, ${lon})`);
    }
}

// 6. Update Right Reading Panel with Telemetry
function updateReadingPanel(prediction, features, stationGround, locationName) {
    if (!prediction) return;

    const aqi = Math.round(prediction.predicted_india_naqi);
    const cat = getCPCBCategory(aqi);

    // Hero AQI Score
    const aqiNumEl = document.getElementById('reading-aqi-num');
    if (aqiNumEl) {
        aqiNumEl.textContent = aqi;
        aqiNumEl.style.color = cat.color;
    }

    // Category Pill
    const catPill = document.getElementById('reading-cat-pill');
    const catNameEl = document.getElementById('reading-cat-name');
    const catSubEl = document.getElementById('reading-cat-sub');
    if (catPill) {
        catPill.className = `cat-pill ${cat.class}`;
    }
    if (catNameEl) catNameEl.textContent = cat.name;
    if (catSubEl) catSubEl.textContent = cat.desc;

    // Guidance Banner
    const guidanceTextEl = document.getElementById('reading-guidance-text');
    if (guidanceTextEl) {
        if (aqi <= 50) {
            guidanceTextEl.textContent = "Air quality is pristine. Ideal for all outdoor exercises, jogging, sports, and fresh ventilation!";
        } else if (aqi <= 100) {
            guidanceTextEl.textContent = "Air quality is good. Great day for outdoor activities, walking, and opening windows!";
        } else if (aqi <= 200) {
            guidanceTextEl.textContent = "Moderate air quality. Unusually sensitive individuals should consider taking regular breaks during heavy exertion.";
        } else if (aqi <= 300) {
            guidanceTextEl.textContent = "Noticeable airborne dust and haze. Sensitive individuals should wear an N95 mask during prolonged outdoor exposure.";
        } else {
            guidanceTextEl.textContent = "High particulate concentration. Keep doors and windows closed, run HEPA filtration, and avoid outdoor sports.";
        }
    }

    // Weather & Pollutant Metrics
    const meteo = (features && features.meteorology) || {};
    const tracers = (features && features.atmospheric_tracers) || {};

    const tempEl = document.getElementById('metric-temp');
    const tempHintEl = document.getElementById('metric-temp-hint');
    if (tempEl) {
        const tVal = meteo.temperature_c !== undefined ? Math.round(meteo.temperature_c) : 32;
        tempEl.textContent = `${tVal}°C`;
        if (tempHintEl) tempHintEl.textContent = tVal > 33 ? "Warm & Sunny" : "Pleasant";
    }

    const rhEl = document.getElementById('metric-rh');
    const rhHintEl = document.getElementById('metric-rh-hint');
    if (rhEl) {
        const rhVal = meteo.relative_humidity_pct !== undefined ? Math.round(meteo.relative_humidity_pct) : 35;
        rhEl.textContent = `${rhVal}%`;
        if (rhHintEl) rhHintEl.textContent = rhVal > 60 ? "Humid" : "Comfortable";
    }

    const polEl = document.getElementById('metric-pollutant');
    const polHintEl = document.getElementById('metric-pollutant-hint');
    if (polEl) {
        const dom = prediction.dominant_pollutant || "PM2.5";
        polEl.textContent = `Dust & ${dom}`;
        if (polHintEl) {
            const pmVal = tracers.pm25 !== undefined ? Math.round(tracers.pm25) : 28;
            polHintEl.textContent = `${pmVal} µg/m³ ambient`;
        }
    }

    // Station Status Strip Below Map
    const stationNameEl = document.getElementById('station-name-text');
    const stationSubEl = document.getElementById('station-sub-text');
    const stationTimeEl = document.getElementById('station-time-str');

    if (stationGround && stationGround.observed_india_naqi !== null && stationGround.observed_india_naqi !== undefined) {
        if (stationNameEl) stationNameEl.textContent = stationGround.station_name || "Official CAAQMS Station";
        if (stationSubEl) {
            const resSign = stationGround.residual > 0 ? '+' : '';
            stationSubEl.textContent = `Physical CPCB India NAQI: ${stationGround.observed_india_naqi} (${stationGround.cpcb_category || 'CPCB'}) · Residual: ${resSign}${stationGround.residual} pts`;
        }
        if (stationTimeEl) stationTimeEl.textContent = stationGround.observed_time || "Updated Live IST";
    } else {
        if (stationNameEl) stationNameEl.textContent = "Autonomous AI Virtual Sensor Node";
        if (stationSubEl) stationSubEl.textContent = "Unmonitored Coordinate — Instantaneous ML Spatiotemporal Estimation (Zero Physical Monitor Here)";
        if (stationTimeEl) stationTimeEl.textContent = "Live Stream Model";
    }
}

// 7. Fetch Live Data for All Vidarbha Nodes & Populate Popular Cities
async function fetchAllNodes() {
    try {
        const resp = await fetch('/api/nodes');
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        currentNodesData = data;

        // Render markers on map
        renderCityMarkersOnMap(data.nodes);

        // Populate Popular Cities Grid Cards
        populatePopularCitiesGrid(data.nodes);

        // Preload Nagpur on Check Location Page
        const nagpurNode = data.nodes.find(n => n.city.toLowerCase() === 'nagpur') || data.nodes[0];
        if (nagpurNode) {
            selectCoordinate(nagpurNode.coordinates.lat, nagpurNode.coordinates.lon, nagpurNode.name, nagpurNode);
        }
    } catch (err) {
        console.warn('Live node stream note:', err);
    }
}

// 8. Populate Page 2: Popular Cities Grid
function populatePopularCitiesGrid(nodes) {
    if (!nodes) return;

    nodes.forEach(node => {
        const cityKey = node.city.toLowerCase();
        const pred = node.virtual_prediction;
        const aqi = Math.round(pred.predicted_india_naqi);
        const cat = getCPCBCategory(aqi);
        const rfeats = node.realtime_features || {};
        const meteo = rfeats.meteorology || {};

        // Update AQI Pill
        const pillEl = document.getElementById(`pill-${cityKey}`);
        if (pillEl) {
            pillEl.className = `city-aqi-pill ${cat.class}`;
            pillEl.innerHTML = `<span class="pill-icon">${aqi <= 100 ? '✓' : '⚠️'}</span><span class="pill-text">${aqi} · ${cat.name}</span>`;
        }

        // Update Advice Quote
        const quoteEl = document.getElementById(`quote-${cityKey}`);
        if (quoteEl) {
            quoteEl.className = `city-advice-quote ${cat.class}`;
            if (aqi <= 50) {
                quoteEl.innerHTML = `<b>Air Quality: Good (${aqi})</b> — Clean atmosphere with minimal airborne particulate matter.`;
            } else if (aqi <= 100) {
                quoteEl.innerHTML = `<b>Air Quality: Satisfactory (${aqi})</b> — Clean and fresh air. Perfect for morning jogs, sports, and outdoor activities.`;
            } else if (aqi <= 200) {
                quoteEl.innerHTML = `<b>Air Quality: Moderate (${aqi})</b> — Sensitive individuals should consider reducing prolonged outdoor exertion.`;
            } else {
                quoteEl.innerHTML = `<b>Air Quality: Poor (${aqi})</b> — Noticeable haze near urban corridors. Mask recommended for outdoor work.`;
            }
        }

        // Update Temperature
        const tempEl = document.getElementById(`stat-temp-${cityKey}`);
        if (tempEl && meteo.temperature_c !== undefined) {
            tempEl.textContent = `${Math.round(meteo.temperature_c)}°C`;
        }

        // Update Air Speed
        const windEl = document.getElementById(`stat-wind-${cityKey}`);
        if (windEl && meteo.wind_speed_kmh !== undefined) {
            windEl.textContent = `${Math.round(meteo.wind_speed_kmh)} km/h`;
        }

        // Update Status Column
        const statusEl = document.getElementById(`stat-status-${cityKey}`);
        if (statusEl) {
            statusEl.textContent = cat.status;
            statusEl.className = `stat-main ${aqi <= 100 ? 'text-emerald' : 'text-amber'}`;
        }
    });
}

// 9. Toast Notification Helper
function showToast(message) {
    const toast = document.getElementById('toast-message');
    const toastText = document.getElementById('toast-text');
    if (!toast || !toastText) return;

    toastText.textContent = message;
    toast.classList.remove('hidden');

    setTimeout(() => {
        toast.classList.add('hidden');
    }, 3200);
}

// 10. Setup DOM Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    const { switchPage } = initNavigation();
    initMap();
    fetchAllNodes();

    // "View Detailed Forecast" buttons on Popular Cities Page
    document.querySelectorAll('.btn-card-forecast').forEach(btn => {
        btn.addEventListener('click', () => {
            const lat = parseFloat(btn.dataset.lat);
            const lon = parseFloat(btn.dataset.lon);
            const cityKey = btn.dataset.city;
            const targetCity = VIDARBHA_PRESETS[cityKey] || { name: cityKey, lat, lon };

            // Switch to Page 1
            switchPage('page-check-location');

            // Select this city
            const node = currentNodesData?.nodes?.find(n => n.city.toLowerCase() === cityKey);
            selectCoordinate(lat, lon, targetCity.name, node);

            // Update search input to match
            const searchInput = document.getElementById('location-search-input');
            if (searchInput) searchInput.value = targetCity.name;
        });
    });

    // Quick Lookup Chips on Page 1
    document.querySelectorAll('.lookup-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const cityKey = chip.dataset.city;
            const target = VIDARBHA_PRESETS[cityKey];
            if (target) {
                const searchInput = document.getElementById('location-search-input');
                if (searchInput) searchInput.value = target.name;

                const node = currentNodesData?.nodes?.find(n => n.city.toLowerCase() === cityKey);
                selectCoordinate(target.lat, target.lon, target.name, node);
            }
        });
    });

    // Search Form Submit
    const searchForm = document.getElementById('search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const query = document.getElementById('location-search-input').value.trim().toLowerCase();

            // Check if coordinates
            const coordMatch = query.match(/(-?\d+\.?\d*)[,\s]+(-?\d+\.?\d*)/);
            if (coordMatch) {
                const lat = parseFloat(coordMatch[1]);
                const lon = parseFloat(coordMatch[2]);
                selectCoordinate(lat, lon, `Coordinate (${lat}, ${lon})`);
                return;
            }

            // Check city names
            if (query.includes('chandrapur')) {
                selectCoordinate(19.9615, 79.2961, "Chandrapur City");
            } else if (query.includes('amravati')) {
                selectCoordinate(20.9374, 77.7796, "Amravati Camp");
            } else if (query.includes('akola')) {
                selectCoordinate(20.7002, 77.0082, "Akola Industrial");
            } else if (query.includes('wardha')) {
                selectCoordinate(20.7453, 78.6022, "Wardha Sevagram");
            } else if (query.includes('yavatmal')) {
                selectCoordinate(20.3888, 78.1204, "Yavatmal MIDC");
            } else {
                selectCoordinate(21.1458, 79.0882, "Nagpur Central");
            }
        });
    }

    // Locate Me Button
    const locateBtn = document.getElementById('btn-locate-me');
    if (locateBtn) {
        locateBtn.addEventListener('click', () => {
            if ("geolocation" in navigator) {
                navigator.geolocation.getCurrentPosition(
                    (pos) => {
                        const lat = parseFloat(pos.coords.latitude.toFixed(4));
                        const lon = parseFloat(pos.coords.longitude.toFixed(4));
                        selectCoordinate(lat, lon, "Your Current Location");
                        showToast(`📍 Located at ${lat}° N, ${lon}° E`);
                    },
                    (err) => {
                        // Fallback to Nagpur
                        selectCoordinate(21.1458, 79.0882, "Nagpur Central");
                        showToast("Location access declined. Displaying Vidarbha Hub (Nagpur).");
                    },
                    { timeout: 6000 }
                );
            } else {
                showToast("Geolocation not supported by your browser.");
            }
        });
    }

    // Save Location Button
    const saveLocBtn = document.getElementById('btn-save-location');
    if (saveLocBtn) {
        saveLocBtn.addEventListener('click', () => {
            const fav = {
                name: activeTargetCoords.name,
                lat: activeTargetCoords.lat,
                lon: activeTargetCoords.lon,
                savedAt: new Date().toISOString()
            };
            try {
                localStorage.setItem('saved_air_location', JSON.stringify(fav));
                showToast(`🔖 Saved "${activeTargetCoords.name}" to favorites!`);
            } catch (e) {
                showToast(`Saved "${activeTargetCoords.name}"!`);
            }
        });
    }

    // Share Report Button
    const shareBtn = document.getElementById('btn-share-report');
    if (shareBtn) {
        shareBtn.addEventListener('click', () => {
            const aqiVal = document.getElementById('reading-aqi-num')?.textContent || '--';
            const catVal = document.getElementById('reading-cat-name')?.textContent || 'AQI';
            const textToCopy = `Air Quality Alert for ${activeTargetCoords.name}: India NAQI is ${aqiVal} (${catVal}) via Vidarbha Live Air Guide.`;

            if (navigator.clipboard) {
                navigator.clipboard.writeText(textToCopy).then(() => {
                    showToast("↗ Report summary copied to clipboard!");
                }).catch(() => {
                    showToast("↗ Report prepared for sharing!");
                });
            } else {
                showToast("↗ Report prepared for sharing!");
            }
        });
    }
});

// ==============================================================================
// 11. PAN-INDIA HCHO & BIOMASS BURNING SURVEILLANCE MODULE (PAGE 3)
// ==============================================================================
let indiaHchoMap = null;
let fireLayerGroup = null;
let hotspotLayerGroup = null;
let windLayerGroup = null;
let clusterLayerGroup = null;
let indiaClickMarker = null;

let hchoCache = {
    summary: null,
    hotspots: null,
    fires: null,
    wind: null
};

async function initIndiaHchoMap() {
    const mapElement = document.getElementById('india-hcho-map');
    if (!mapElement || indiaHchoMap) return;

    // Create Map centered on the Indian subcontinent
    indiaHchoMap = L.map('india-hcho-map', {
        center: [22.8, 79.5],
        zoom: 5,
        minZoom: 4,
        maxZoom: 14,
        zoomControl: true,
        attributionControl: false
    });

    // Basemap: Clean Light OpenStreetMap
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 18
    }).addTo(indiaHchoMap);

    // Dedicated Layer Groups
    clusterLayerGroup = L.layerGroup().addTo(indiaHchoMap);
    hotspotLayerGroup = L.layerGroup().addTo(indiaHchoMap);
    windLayerGroup = L.layerGroup().addTo(indiaHchoMap);
    fireLayerGroup = L.layerGroup().addTo(indiaHchoMap);

    // Map Click Inspector
    indiaHchoMap.on('click', (e) => {
        const lat = parseFloat(e.latlng.lat.toFixed(4));
        const lon = parseFloat(e.latlng.lng.toFixed(4));
        sampleIndiaLocation(lat, lon);
    });

    // Initialize Layer Toggles & Zoom controls
    setupHchoLayerToggles();
    setupHchoZoomControls();

    // Fetch and render data
    await loadHchoAnalyticsData();
}

function setupHchoLayerToggles() {
    const toggleFires = document.getElementById('toggle-layer-fires');
    const toggleHotspots = document.getElementById('toggle-layer-hotspots');
    const toggleWind = document.getElementById('toggle-layer-wind');
    const toggleClusters = document.getElementById('toggle-layer-clusters');

    function toggleLayer(btn, layerGroup) {
        if (!btn || !layerGroup || !indiaHchoMap) return;
        if (indiaHchoMap.hasLayer(layerGroup)) {
            indiaHchoMap.removeLayer(layerGroup);
            btn.classList.remove('active');
        } else {
            indiaHchoMap.addLayer(layerGroup);
            btn.classList.add('active');
        }
    }

    if (toggleFires) {
        toggleFires.addEventListener('click', () => toggleLayer(toggleFires, fireLayerGroup));
    }
    if (toggleHotspots) {
        toggleHotspots.addEventListener('click', () => toggleLayer(toggleHotspots, hotspotLayerGroup));
    }
    if (toggleWind) {
        toggleWind.addEventListener('click', () => toggleLayer(toggleWind, windLayerGroup));
    }
    if (toggleClusters) {
        toggleClusters.addEventListener('click', () => toggleLayer(toggleClusters, clusterLayerGroup));
    }
}

function setupHchoZoomControls() {
    const btnIndia = document.getElementById('btn-zoom-india');
    const btnIgp = document.getElementById('btn-zoom-igp');
    const btnCentral = document.getElementById('btn-zoom-central');
    const btnNe = document.getElementById('btn-zoom-ne');
    const allZoomBtns = [btnIndia, btnIgp, btnCentral, btnNe];

    function setActiveBtn(activeBtn) {
        allZoomBtns.forEach(b => b?.classList.remove('active'));
        activeBtn?.classList.add('active');
    }

    if (btnIndia) {
        btnIndia.addEventListener('click', () => {
            setActiveBtn(btnIndia);
            indiaHchoMap?.flyTo([22.8, 79.5], 5, { duration: 1.2 });
        });
    }
    if (btnIgp) {
        btnIgp.addEventListener('click', () => {
            setActiveBtn(btnIgp);
            indiaHchoMap?.flyTo([30.1, 75.8], 7, { duration: 1.2 });
        });
    }
    if (btnCentral) {
        btnCentral.addEventListener('click', () => {
            setActiveBtn(btnCentral);
            indiaHchoMap?.flyTo([21.2, 79.5], 7, { duration: 1.2 });
        });
    }
    if (btnNe) {
        btnNe.addEventListener('click', () => {
            setActiveBtn(btnNe);
            indiaHchoMap?.flyTo([25.5, 92.5], 7, { duration: 1.2 });
        });
    }
}

async function loadHchoAnalyticsData() {
    try {
        // 1. Fetch Summary & Statistics
        const summaryRes = await fetch('/api/hcho/summary');
        if (summaryRes.ok) {
            hchoCache.summary = await summaryRes.json();
            renderHchoSummary(hchoCache.summary);
        }

        // 2. Fetch Getis-Ord Hotspots & DBSCAN Clusters
        const hotspotsRes = await fetch('/api/hcho/hotspots');
        if (hotspotsRes.ok) {
            hchoCache.hotspots = await hotspotsRes.json();
            renderHotspotsLayer(hchoCache.hotspots);
        }

        // 3. Fetch Active Fire Points
        const firesRes = await fetch('/api/hcho/fires');
        if (firesRes.ok) {
            hchoCache.fires = await firesRes.json();
            renderFiresLayer(hchoCache.fires);
        }

        // 4. Fetch ERA5 Wind Vectors
        const windRes = await fetch('/api/hcho/wind');
        if (windRes.ok) {
            hchoCache.wind = await windRes.json();
            renderWindLayer(hchoCache.wind);
        }

        // Initial default sampling (Central India / Vidarbha Corridor)
        sampleIndiaLocation(21.1458, 79.0882);

    } catch (err) {
        console.error('Error loading HCHO analytics data:', err);
    }
}

function renderHchoSummary(data) {
    if (!data) return;

    // Top 4 KPIs
    const elFires = document.getElementById('hcho-kpi-fires');
    if (elFires && data.total_active_fires != null) {
        elFires.textContent = data.total_active_fires.toLocaleString();
    }

    const elFrp = document.getElementById('hcho-kpi-frp');
    if (elFrp && data.total_fire_radiative_power_mw != null) {
        elFrp.textContent = `${data.total_fire_radiative_power_mw.toLocaleString(undefined, { maximumFractionDigits: 1 })} MW`;
    }

    const elPeak = document.getElementById('hcho-kpi-peak');
    if (elPeak && data.peak_hcho_column_10_15 != null) {
        elPeak.textContent = `${data.peak_hcho_column_10_15.toFixed(1)} × 10¹⁵`;
    }

    const elR = document.getElementById('hcho-kpi-r');
    if (elR && data.correlation?.pearson_r != null) {
        elR.textContent = `r = ${data.correlation.pearson_r.toFixed(3)}`;
    }

    // Correlation card values
    const cR = document.getElementById('corr-val-r');
    if (cR && data.correlation?.pearson_r != null) {
        cR.textContent = `r = ${data.correlation.pearson_r.toFixed(3)}`;
    }
    const cRho = document.getElementById('corr-val-rho');
    if (cRho && data.correlation?.spearman_rho != null) {
        cRho.textContent = `ρ = ${data.correlation.spearman_rho.toFixed(3)}`;
    }
    const cR2 = document.getElementById('corr-val-r2');
    if (cR2 && data.correlation?.r_squared != null) {
        cR2.textContent = `R² = ${data.correlation.r_squared.toFixed(3)}`;
    }

    // Transport card values
    const tCalm = document.getElementById('transport-calm-val');
    if (tCalm && data.wind_transport?.calm_mean_hcho != null) {
        tCalm.textContent = `${data.wind_transport.calm_mean_hcho.toFixed(2)} × 10¹⁵`;
    }
    const tWind = document.getElementById('transport-wind-val');
    if (tWind && data.wind_transport?.windy_mean_hcho != null) {
        tWind.textContent = `${data.wind_transport.windy_mean_hcho.toFixed(2)} × 10¹⁵`;
    }

    // Populate DBSCAN Clusters in Sidebar
    const clustersContainer = document.getElementById('clusters-container');
    const clustersCountTag = document.getElementById('clusters-count-tag');
    const topClusters = data.dbscan_clusters?.top_clusters || [];

    if (clustersCountTag) {
        clustersCountTag.textContent = `${topClusters.length} Clusters`;
    }

    if (clustersContainer && topClusters.length > 0) {
        clustersContainer.innerHTML = '';
        topClusters.forEach(cl => {
            const item = document.createElement('div');
            item.className = 'cluster-item';
            item.innerHTML = `
                <div class="cluster-tag-badge">Cluster #${cl.cluster_id}</div>
                <div class="cluster-item-title">${cl.region_label || `Cluster #${cl.cluster_id}`}</div>
                <div class="cluster-item-metrics">
                    <span>🔥 ${(cl.total_fires || 0).toLocaleString()} fires</span>
                    <span>⚡ ${(cl.total_frp || 0).toFixed(1)} MW FRP</span>
                    <span>🌌 ${(cl.mean_hcho || 0).toFixed(2)} × 10¹⁵</span>
                </div>
            `;
            item.addEventListener('click', () => {
                if (indiaHchoMap && cl.center_lat && cl.center_lon) {
                    indiaHchoMap.flyTo([cl.center_lat, cl.center_lon], 7, { duration: 1.2 });
                    sampleIndiaLocation(cl.center_lat, cl.center_lon);
                }
            });
            clustersContainer.appendChild(item);
        });
    }
}

function renderHotspotsLayer(geojson) {
    if (!hotspotLayerGroup || !geojson || !geojson.features) return;
    hotspotLayerGroup.clearLayers();

    geojson.features.forEach(f => {
        const coords = f.geometry?.coordinates;
        const p = f.properties || {};
        const lat = p.lat != null ? p.lat : (Array.isArray(coords) ? coords[1] : null);
        const lon = p.lon != null ? p.lon : (Array.isArray(coords) ? coords[0] : null);
        if (lat == null || lon == null || isNaN(lat) || isNaN(lon)) return;

        const z = p.gi_star_z_score != null ? p.gi_star_z_score : (p.gi_z_score != null ? p.gi_z_score : 0);
        const hcho = p.hcho_column_10_15 != null ? p.hcho_column_10_15 : (p.hcho_molec_cm2_e15 != null ? p.hcho_molec_cm2_e15 : 2.5);

        let color = '#f59e0b';
        let radius = 4.5;
        if (z >= 2.58) {
            color = '#dc2626'; // 99% confidence
            radius = 6.0;
        } else if (z >= 1.96) {
            color = '#ea580c'; // 95% confidence
            radius = 5.0;
        }

        const marker = L.circleMarker([lat, lon], {
            radius: radius,
            fillColor: color,
            color: '#ffffff',
            weight: 0.8,
            fillOpacity: 0.85
        });

        marker.bindTooltip(`
            <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:11px; font-weight:600; padding:2px 4px;">
                <b>Hotspot Gi* Z: +${z.toFixed(2)}</b><br/>
                HCHO Column: ${hcho.toFixed(2)} × 10¹⁵ molec/cm²<br/>
                FRP: ${(p.total_frp || p.frp_mw || 0).toFixed(1)} MW (${p.fire_count || 0} fires)
            </div>
        `, { sticky: true });

        marker.on('click', () => {
            sampleIndiaLocation(lat, lon, p);
        });

        hotspotLayerGroup.addLayer(marker);
    });
}

function renderFiresLayer(geojson) {
    if (!fireLayerGroup || !geojson || !geojson.features) return;
    fireLayerGroup.clearLayers();

    geojson.features.forEach(f => {
        const coords = f.geometry?.coordinates;
        const p = f.properties || {};
        const lat = p.latitude != null ? p.latitude : (p.lat != null ? p.lat : (Array.isArray(coords) ? coords[1] : null));
        const lon = p.longitude != null ? p.longitude : (p.lon != null ? p.lon : (Array.isArray(coords) ? coords[0] : null));
        if (lat == null || lon == null || isNaN(lat) || isNaN(lon)) return;

        const frp = p.frp != null ? p.frp : (p.frp_mw != null ? p.frp_mw : 15);
        const radius = Math.min(6.5, Math.max(3.0, Math.sqrt(frp) * 0.8));

        const marker = L.circleMarker([lat, lon], {
            radius: radius,
            fillColor: '#ef4444',
            color: '#b91c1c',
            weight: 1,
            fillOpacity: 0.75
        });

        marker.bindTooltip(`
            <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:11px; padding:2px 4px;">
                <b>🔥 Active Biomass Fire</b><br/>
                FRP: ${frp.toFixed(1)} MW<br/>
                Satellite: ${p.satellite || 'VIIRS 375m'}
            </div>
        `, { sticky: true });

        marker.on('click', () => {
            sampleIndiaLocation(lat, lon);
        });

        fireLayerGroup.addLayer(marker);
    });
}

function renderWindLayer(geojson) {
    if (!windLayerGroup || !geojson || !geojson.features) return;
    windLayerGroup.clearLayers();

    // Subsample slightly if very dense to keep rendering silky smooth
    geojson.features.forEach((f, idx) => {
        if (idx % 2 !== 0) return; // Keep 50% for optimal visual density
        const coords = f.geometry?.coordinates;
        const p = f.properties || {};

        let lat = p.origin_lat != null ? p.origin_lat : (Array.isArray(coords) && Array.isArray(coords[0]) ? coords[0][1] : (coords ? coords[1] : null));
        let lon = p.origin_lon != null ? p.origin_lon : (Array.isArray(coords) && Array.isArray(coords[0]) ? coords[0][0] : (coords ? coords[0] : null));
        if (lat == null || lon == null || isNaN(lat) || isNaN(lon)) return;

        const speed = p.wind_speed_ms != null ? p.wind_speed_ms : (p.wind_speed_m_s != null ? p.wind_speed_m_s : 3.0);
        const dir = p.wind_dir_deg != null ? p.wind_dir_deg : 315;

        // SVG Arrow rotated by direction
        const arrowHtml = `
            <div style="transform: rotate(${dir}deg); display:flex; align-items:center; justify-content:center; opacity:0.65; pointer-events:none;">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="12" y1="19" x2="12" y2="5"></line>
                    <polyline points="5 12 12 5 19 12"></polyline>
                </svg>
            </div>
        `;

        const icon = L.divIcon({
            className: 'wind-arrow-icon',
            html: arrowHtml,
            iconSize: [16, 16],
            iconAnchor: [8, 8]
        });

        const marker = L.marker([lat, lon], { icon, interactive: false });
        windLayerGroup.addLayer(marker);
    });
}

function sampleIndiaLocation(lat, lon, knownProps = null) {
    if (!indiaHchoMap || lat == null || lon == null || isNaN(lat) || isNaN(lon)) return;

    // Place or move click pin
    if (indiaClickMarker) {
        indiaHchoMap.removeLayer(indiaClickMarker);
    }

    const pinHtml = `
        <div style="background:#0f172a; color:#ffffff; padding:4px 10px; border-radius:999px; font-family:'Plus Jakarta Sans',sans-serif; font-size:11px; font-weight:700; border:2px solid #ffffff; box-shadow:0 4px 14px rgba(0,0,0,0.25); display:flex; align-items:center; gap:5px; transform:translate(-50%, -100%);">
            <span style="width:8px; height:8px; border-radius:50%; background:#8b5cf6;"></span>
            <span>${lat.toFixed(2)}° N, ${lon.toFixed(2)}° E</span>
        </div>
    `;

    const icon = L.divIcon({
        className: 'custom-hcho-marker',
        html: pinHtml,
        iconSize: [140, 30],
        iconAnchor: [70, 30]
    });

    indiaClickMarker = L.marker([lat, lon], { icon }).addTo(indiaHchoMap);

    // Update Coordinates Line
    const elCoords = document.getElementById('hcho-insp-coords');
    if (elCoords) elCoords.textContent = `${lat.toFixed(4)}° N, ${lon.toFixed(4)}° E`;

    // Determine Ecoregion & Location Name
    let regionName = "Indian Subcontinent";
    let ecoDesc = "General Atmospheric Domain";

    if (lat >= 28.0 && lon <= 78.0) {
        regionName = "Punjab-Haryana Agricultural Basin";
        ecoDesc = "Post-harvest paddy stubble burning zone; dense seasonal smoke plumes.";
    } else if (lat >= 24.0 && lat <= 28.0 && lon >= 77.0 && lon <= 88.0) {
        regionName = "Central & Eastern Indo-Gangetic Corridor";
        ecoDesc = "Downwind advection corridor; high optical depth and aerosol accumulation.";
    } else if (lat >= 18.0 && lat <= 24.0 && lon >= 76.0 && lon <= 83.5) {
        regionName = "Central India Deciduous Forest (Vidarbha / MP)";
        ecoDesc = "Seasonal dry deciduous biomass clearing and forest fire enhancement.";
    } else if (lon >= 89.0 && lat >= 23.0) {
        regionName = "Northeast Highlands";
        ecoDesc = "Jhum shifting cultivation burning across hill terrains.";
    } else if (lat < 18.0) {
        regionName = "Deccan Peninsula & Coastal India";
        ecoDesc = "Maritime boundary layer with dispersed regional agricultural fires.";
    }

    const elTitle = document.getElementById('hcho-insp-title');
    if (elTitle) elTitle.textContent = regionName;

    const elZone = document.getElementById('hcho-insp-zone');
    if (elZone) {
        elZone.innerHTML = `<b>Region:</b> ${regionName} — <span>${ecoDesc}</span>`;
    }

    // Compute or extract metrics
    let hchoVal = 2.25;
    let zScore = 0.5;
    let firesNearby = 0;
    let frpNearby = 0;

    if (knownProps) {
        hchoVal = knownProps.hcho_column_10_15 || (knownProps.hcho_tropospheric_column ? knownProps.hcho_tropospheric_column * 60221.4 : 2.5);
        zScore = knownProps.gi_star_z_score || 0;
        firesNearby = knownProps.fire_count || 0;
        frpNearby = knownProps.total_frp || 0;
    } else {
        if (hchoCache.fires?.features) {
            hchoCache.fires.features.forEach(f => {
                const c = f.geometry?.coordinates;
                if (!c) return;
                const dLat = Math.abs(c[1] - lat);
                const dLon = Math.abs(c[0] - lon);
                if (dLat < 0.6 && dLon < 0.6) {
                    firesNearby++;
                    frpNearby += (f.properties?.frp || 10);
                }
            });
        }

        let minD = 999;
        if (hchoCache.hotspots?.features) {
            hchoCache.hotspots.features.forEach(f => {
                const c = f.geometry?.coordinates;
                if (!c) return;
                const d = Math.hypot(c[1] - lat, c[0] - lon);
                if (d < minD) {
                    minD = d;
                    if (d < 1.2) {
                        zScore = f.properties?.gi_star_z_score || 0;
                        hchoVal = f.properties?.hcho_column_10_15 || 2.4;
                    }
                }
            });
        }

        if (firesNearby > 0) {
            hchoVal = Math.max(hchoVal, 2.5 + Math.min(13.3, frpNearby * 0.05));
            zScore = Math.max(zScore, Math.min(4.8, 1.2 + firesNearby * 0.15));
        }
    }

    let windSpeed = 3.2;
    let windDir = 315;
    if (hchoCache.wind?.features) {
        let minWindD = 999;
        hchoCache.wind.features.forEach(f => {
            const p = f.properties || {};
            const wLat = p.origin_lat != null ? p.origin_lat : (f.geometry?.coordinates?.[0]?.[1]);
            const wLon = p.origin_lon != null ? p.origin_lon : (f.geometry?.coordinates?.[0]?.[0]);
            if (wLat == null || wLon == null) return;
            const d = Math.hypot(wLat - lat, wLon - lon);
            if (d < minWindD) {
                minWindD = d;
                windSpeed = p.wind_speed_ms != null ? p.wind_speed_ms : (p.wind_speed_m_s != null ? p.wind_speed_m_s : 3.2);
                windDir = p.wind_dir_deg != null ? p.wind_dir_deg : 315;
            }
        });
    }

    const dirCard = windDir >= 300 || windDir <= 45 ? "NW ➔ SE" : windDir < 135 ? "NE ➔ SW" : "W ➔ E";

    const elHcho = document.getElementById('hcho-insp-val');
    if (elHcho) elHcho.textContent = `${hchoVal.toFixed(2)} × 10¹⁵`;

    const elZ = document.getElementById('hcho-insp-z');
    if (elZ) {
        const sign = zScore >= 0 ? '+' : '';
        elZ.textContent = `Z = ${sign}${zScore.toFixed(2)}`;
        elZ.className = `insp-m-val ${zScore >= 2.58 ? 'text-red' : zScore >= 1.96 ? 'text-amber' : 'text-blue'}`;
    }

    const elFiresCount = document.getElementById('hcho-insp-fires');
    if (elFiresCount) elFiresCount.textContent = `${firesNearby} fires`;

    const elFrpCount = document.getElementById('hcho-insp-frp');
    if (elFrpCount) elFrpCount.textContent = `Total FRP: ${frpNearby.toFixed(1)} MW`;

    const elWind = document.getElementById('hcho-insp-wind');
    if (elWind) elWind.textContent = `${windSpeed.toFixed(1)} m/s`;

    const elWindDir = document.getElementById('hcho-insp-wind-dir');
    if (elWindDir) elWindDir.textContent = `${Math.round(windDir)}° (${dirCard})`;
}
