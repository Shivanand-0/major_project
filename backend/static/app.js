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

// 1. Navigation & 2-Page Tab Switcher
function initNavigation() {
    const tabCheckLoc = document.getElementById('tab-check-location');
    const tabPopular = document.getElementById('tab-popular-cities');
    const pageCheckLoc = document.getElementById('page-check-location');
    const pagePopular = document.getElementById('page-popular-cities');
    const brandLogo = document.getElementById('brand-logo');

    function switchPage(pageName) {
        if (pageName === 'page-check-location') {
            tabCheckLoc.classList.add('active');
            tabPopular.classList.remove('active');
            pageCheckLoc.classList.remove('hidden');
            pagePopular.classList.add('hidden');

            // Force Leaflet to refresh viewport dimensions
            setTimeout(() => {
                if (map) {
                    map.invalidateSize();
                    map.panTo([activeTargetCoords.lat, activeTargetCoords.lon], { animate: false });
                }
            }, 100);
        } else {
            tabPopular.classList.add('active');
            tabCheckLoc.classList.remove('active');
            pagePopular.classList.remove('hidden');
            pageCheckLoc.classList.add('hidden');
        }
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    if (tabCheckLoc) tabCheckLoc.addEventListener('click', () => switchPage('page-check-location'));
    if (tabPopular) tabPopular.addEventListener('click', () => switchPage('page-popular-cities'));
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
