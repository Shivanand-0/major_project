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

    function switchPage(pageName = 'page-check-location') {
        tabCheckLoc?.classList.remove('active');
        tabPopular?.classList.remove('active');
        tabPanIndia?.classList.remove('active');

        pageCheckLoc?.classList.add('hidden');
        pagePopular?.classList.add('hidden');
        pagePanIndia?.classList.add('hidden');

        if (pageName === 'page-popular-cities') {
            tabPopular?.classList.add('active');
            pagePopular?.classList.remove('hidden');
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
            // Default: Check Location (Primary Interactive Map View)
            tabCheckLoc?.classList.add('active');
            pageCheckLoc?.classList.remove('hidden');

            setTimeout(() => {
                if (map) {
                    map.invalidateSize();
                    map.panTo([activeTargetCoords.lat, activeTargetCoords.lon], { animate: false });
                }
            }, 100);
        }
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    if (tabCheckLoc) tabCheckLoc.addEventListener('click', () => switchPage('page-check-location'));
    if (tabPopular) tabPopular.addEventListener('click', () => switchPage('page-popular-cities'));
    if (tabPanIndia) tabPanIndia.addEventListener('click', () => switchPage('page-pan-india-hcho'));
    if (brandLogo) brandLogo.addEventListener('click', () => switchPage('page-check-location'));

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
function updateTargetPin(lat, lon, label = null, prediction = null, features = null) {
    if (!map) return;

    if (targetClickMarker) {
        map.removeLayer(targetClickMarker);
    }

    const pinHtml = `
        <div class="custom-map-pin-wrap">
            <div class="pin-pulse-ring ring-emerald"></div>
            <div class="pin-marker-head pin-emerald">
                <svg width="28" height="36" viewBox="0 0 24 32" fill="none">
                    <path d="M12 0C5.372 0 0 5.373 0 12c0 8.5 12 20 12 20s12-11.5 12-20c0-6.627-5.372-12-12-12z" fill="#059669"/>
                    <circle cx="12" cy="11" r="4.5" fill="#ffffff"/>
                </svg>
            </div>
        </div>
    `;

    const icon = L.divIcon({
        className: 'custom-pin-divicon',
        html: pinHtml,
        iconSize: [28, 36],
        iconAnchor: [14, 36],
        popupAnchor: [0, -36]
    });

    let popupContent = '';
    const locTitle = label || `Coordinate (${lat.toFixed(3)}, ${lon.toFixed(3)})`;
    const coordsStr = `${lat.toFixed(4)}° N, ${lon.toFixed(4)}° E`;

    if (prediction) {
        const aqi = Math.round(prediction.predicted_india_naqi);
        const cat = getCPCBCategory(aqi);

        popupContent = `
            <div class="map-interactive-popup">
                <div class="popup-top-row">
                    <span class="popup-sub-tag">LIVE SENSOR PIN</span>
                    <span class="popup-aqi-pill ${cat.class}">AQI ${aqi} · ${cat.name}</span>
                </div>
                <h4 class="popup-loc-title">${locTitle}</h4>
                <div class="popup-coords-text">${coordsStr}</div>
                <div class="popup-footer-status">
                    <span class="popup-status-dot" style="background:${cat.color};"></span>
                    <span>${cat.desc}</span>
                </div>
            </div>
        `;
    } else {
        popupContent = `
            <div class="map-interactive-popup">
                <div class="popup-top-row">
                    <span class="popup-sub-tag">SELECTED LOCATION</span>
                    <span class="popup-aqi-pill moderate">Evaluating...</span>
                </div>
                <h4 class="popup-loc-title">${locTitle}</h4>
                <div class="popup-coords-text">${coordsStr}</div>
                <div class="popup-loading-line">
                    <span class="live-dot pulse"></span>
                    <span>Evaluating real-time atmospheric telemetry...</span>
                </div>
            </div>
        `;
    }

    targetClickMarker = L.marker([lat, lon], { icon }).addTo(map);
    targetClickMarker.bindPopup(popupContent, {
        offset: [0, -4],
        closeButton: true,
        autoClose: false,
        className: 'custom-leaflet-popup-card'
    }).openPopup();
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

// Helper: Toggle Real-Time Reading Panel Loader State
function setReadingCardLoading(isLoading, locationName = null) {
    const loaderEl = document.getElementById('reading-loader');
    const bodyEl = document.getElementById('reading-content-body');
    const subtitleEl = document.getElementById('reading-loader-subtitle');

    if (loaderEl && bodyEl) {
        if (isLoading) {
            loaderEl.style.display = 'flex';
            bodyEl.style.display = 'none';
            bodyEl.classList.remove('fade-in');
            if (subtitleEl) {
                subtitleEl.textContent = locationName
                    ? `Querying atmospheric telemetry & running AI models for ${locationName}...`
                    : 'Querying atmospheric telemetry feeds & spatiotemporal ML models...';
            }
        } else {
            loaderEl.style.display = 'none';
            bodyEl.style.display = 'flex';
            bodyEl.classList.remove('fade-in');
            void bodyEl.offsetWidth; // Trigger reflow for smooth fade-in
            bodyEl.classList.add('fade-in');
        }
    }
}

let currentEvaluationId = 0;

// 5. Select Coordinate & Ingest Live Telemetry
async function selectCoordinate(lat, lon, name = null, cachedNode = null) {
    const evalId = ++currentEvaluationId;
    activeTargetCoords = { lat, lon, name: name || `${lat}°N, ${lon}°E` };

    // Update Target Coordinates Pill Overlay
    const coordsEl = document.getElementById('display-target-coords');
    if (coordsEl) coordsEl.textContent = `${lat.toFixed(4)}° N, ${lon.toFixed(4)}° E`;

    // Update Map Pin (opens immediately with loading state)
    updateTargetPin(lat, lon, name);
    if (map) {
        map.panTo([lat, lon], { animate: true, duration: 0.6 });
    }

    // Set Reading Loading State
    const titleEl = document.getElementById('reading-city-title');
    const pointCoordsEl = document.getElementById('reading-point-coords');
    if (titleEl) titleEl.textContent = `Current Air Quality in ${name || 'Selected Location'}`;
    if (pointCoordsEl) pointCoordsEl.textContent = `Selected Point: ${lat.toFixed(4)}° N, ${lon.toFixed(4)}° E`;

    // Show Loader & hide stale previous readings
    setReadingCardLoading(true, name);

    try {
        let prediction = null;
        let features = null;
        let stationGround = null;

        if (cachedNode && cachedNode.virtual_prediction) {
            prediction = cachedNode.virtual_prediction;
            features = cachedNode.realtime_features;
            stationGround = cachedNode.physical_ground_truth;
        } else {
            // Fetch live authentic real-time telemetry directly from client browser
            // (Using client's unthrottled residential/mobile IP to avoid cloud shared-IP 429 rate limits)
            let liveWeather = null;
            let liveAq = null;
            try {
                const weatherUrl = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,relative_humidity_2m,dew_point_2m,surface_pressure,wind_speed_10m,wind_direction_10m,wind_gusts_10m,precipitation,cloud_cover,direct_radiation&timezone=Asia%2FKolkata`;
                const aqUrl = `https://air-quality-api.open-meteo.com/v1/air-quality?latitude=${lat}&longitude=${lon}&current=pm2_5,pm10,nitrogen_dioxide,sulphur_dioxide,ozone,carbon_monoxide&timezone=Asia%2FKolkata`;

                const [wRes, aqRes] = await Promise.all([
                    fetch(weatherUrl, { cache: 'no-cache' }).then(r => r.ok ? r.json() : null).catch(() => null),
                    fetch(aqUrl, { cache: 'no-cache' }).then(r => r.ok ? r.json() : null).catch(() => null)
                ]);

                if (wRes && wRes.current) liveWeather = wRes.current;
                if (aqRes && aqRes.current) liveAq = aqRes.current;
            } catch (fetchErr) {
                console.warn('Client-side direct telemetry fetch notice:', fetchErr);
            }

            const reqPayload = { latitude: lat, longitude: lon };
            if (liveWeather) reqPayload.live_weather = liveWeather;
            if (liveAq) reqPayload.live_aq = liveAq;

            const resp = await fetch('/api/predict', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(reqPayload)
            });
            if (!resp.ok) {
                let errDetail = `HTTP ${resp.status}`;
                try {
                    const errJson = await resp.json();
                    if (errJson && errJson.detail) errDetail = errJson.detail;
                } catch(e) {}
                throw new Error(errDetail);
            }
            const data = await resp.json();
            prediction = data.prediction;
            features = data.realtime_features;
            stationGround = data.physical_station_ground_truth;
        }

        if (evalId !== currentEvaluationId) return;

        updateReadingPanel(prediction, features, stationGround, name);
        // Refresh popup with resolved telemetry & AQI
        updateTargetPin(lat, lon, name, prediction, features);
    } catch (err) {
        if (evalId !== currentEvaluationId) return;
        console.error('Failed to evaluate coordinate in real-time:', err);
        showToast(`Real-time evaluation notice: ${err.message || 'Unable to fetch live telemetry'}`);
        setReadingCardLoading(false);
    }
}

// 6. Update Right Reading Panel with Telemetry
function updateReadingPanel(prediction, features, stationGround, locationName) {
    if (!prediction) {
        setReadingCardLoading(false);
        return;
    }

    setReadingCardLoading(false);

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
        const nagpurNode = data.nodes ? (data.nodes.find(n => n.city && n.city.toLowerCase() === 'nagpur') || data.nodes[0]) : null;
        if (nagpurNode) {
            selectCoordinate(nagpurNode.coordinates.lat, nagpurNode.coordinates.lon, nagpurNode.name, nagpurNode);
        } else {
            selectCoordinate(21.1458, 79.0882, "Nagpur Central");
        }
    } catch (err) {
        console.warn('Live node stream notice, evaluating primary hub:', err);
        selectCoordinate(21.1458, 79.0882, "Nagpur Central");
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
    switchPage('page-check-location');
    fetchAllNodes();
    setupHchoDetailsToggle();

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

    // Initialize Pan-India HCHO details toggle button
    setupHchoDetailsToggle();
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

    // Initialize Layer Toggles, Zoom controls & More Info collapse
    setupHchoLayerToggles();
    setupHchoZoomControls();
    setupHchoDetailsToggle();

    // Fetch and render data
    await loadHchoAnalyticsData();
}

function setupHchoLayerToggles() {
    const toggleFires = document.getElementById('toggle-layer-fires');
    const toggleHotspots = document.getElementById('toggle-layer-hotspots');
    const toggleWind = document.getElementById('toggle-layer-wind');
    const toggleClusters = document.getElementById('toggle-layer-clusters');

    function toggleLayer(btn, layerGroup, layerName) {
        if (!btn || !layerGroup || !indiaHchoMap) return;
        if (indiaHchoMap.hasLayer(layerGroup)) {
            indiaHchoMap.removeLayer(layerGroup);
            btn.classList.remove('active');
            showToast(`${layerName} layer hidden`);
        } else {
            indiaHchoMap.addLayer(layerGroup);
            btn.classList.add('active');
            showToast(`${layerName} layer visible`);
        }
    }

    if (toggleFires) {
        toggleFires.addEventListener('click', () => toggleLayer(toggleFires, fireLayerGroup, 'Active Fires'));
    }
    if (toggleHotspots) {
        toggleHotspots.addEventListener('click', () => toggleLayer(toggleHotspots, hotspotLayerGroup, 'Getis-Ord Gi* Hotspots'));
    }
    if (toggleWind) {
        toggleWind.addEventListener('click', () => toggleLayer(toggleWind, windLayerGroup, 'ERA5 Wind Vectors'));
    }
    if (toggleClusters) {
        toggleClusters.addEventListener('click', () => toggleLayer(toggleClusters, clusterLayerGroup, 'DBSCAN Plume Clusters'));
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

function setupHchoDetailsToggle() {
    const toggleBtn = document.getElementById('btn-toggle-hcho-details');
    const detailsContainer = document.getElementById('hcho-scientific-details');
    const btnText = document.getElementById('btn-more-info-text');

    if (!toggleBtn || !detailsContainer) return;
    if (toggleBtn.dataset.bound === 'true') return;
    toggleBtn.dataset.bound = 'true';

    // Ensure initial collapsed state is synchronized
    if (detailsContainer.style.display !== 'block') {
        detailsContainer.style.display = 'none';
        detailsContainer.classList.add('hidden');
        toggleBtn.classList.remove('active');
        toggleBtn.setAttribute('aria-expanded', 'false');
    }

    toggleBtn.addEventListener('click', (e) => {
        e.preventDefault();
        const isHidden = detailsContainer.style.display === 'none' || detailsContainer.classList.contains('hidden');
        if (isHidden) {
            detailsContainer.style.display = 'block';
            detailsContainer.classList.remove('hidden');
            toggleBtn.classList.add('active');
            toggleBtn.setAttribute('aria-expanded', 'true');
            if (btnText) btnText.textContent = "Hide Atmospheric Analytics & Regional Breakdown";
            setTimeout(() => {
                detailsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 60);
        } else {
            detailsContainer.style.display = 'none';
            detailsContainer.classList.add('hidden');
            toggleBtn.classList.remove('active');
            toggleBtn.setAttribute('aria-expanded', 'false');
            if (btnText) btnText.textContent = "More Info: View Atmospheric Analytics & Regional Breakdown";
        }
    });
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
            const data = await hotspotsRes.json();
            // /api/hcho/hotspots returns { getis_ord_hotspots: FeatureCollection, dbscan_clusters: FeatureCollection }
            const giGeojson = data.getis_ord_hotspots || (data.type === 'FeatureCollection' ? data : null);
            const clusterGeojson = data.dbscan_clusters || null;

            hchoCache.hotspots = giGeojson;
            hchoCache.clusters = clusterGeojson;

            if (giGeojson) {
                renderHotspotsLayer(giGeojson);
            }
            if (clusterGeojson) {
                renderClustersLayer(clusterGeojson);
            }
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

    // Update Sync Status Pill with Authentic Observation Date
    const elSyncStatus = document.getElementById('hcho-sync-status');
    if (elSyncStatus) {
        let obsDateText = '';
        if (data.observation_date) {
            const raw = String(data.observation_date).replace(/-/g, '');
            if (raw.length === 8) {
                const y = raw.slice(0, 4);
                const m = raw.slice(4, 6);
                const d = raw.slice(6, 8);
                const dt = new Date(`${y}-${m}-${d}T00:00:00Z`);
                obsDateText = dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
            } else {
                obsDateText = data.observation_date;
            }
        }
        elSyncStatus.textContent = obsDateText
            ? `Daily Pass: ${obsDateText} · Satellite & Wind Synced`
            : 'Satellite & ERA5 Synced · India Domain';
    }

    // Bind Refresh Button
    const refreshBtn = document.getElementById('hcho-refresh-btn');
    if (refreshBtn && !refreshBtn.dataset.bound) {
        refreshBtn.dataset.bound = 'true';
        refreshBtn.addEventListener('click', async (e) => {
            e.stopPropagation();
            refreshBtn.classList.add('spinning');
            if (elSyncStatus) elSyncStatus.textContent = 'Syncing Daily Satellite Feed...';
            try {
                const res = await fetch('/api/hcho/refresh?force=true', { method: 'POST' });
                if (res.ok) {
                    let attempts = 0;
                    const pollInterval = setInterval(async () => {
                        attempts++;
                        try {
                            const stRes = await fetch('/api/hcho/status');
                            if (stRes.ok) {
                                const st = await stRes.json();
                                if (st.is_current && attempts > 3) {
                                    clearInterval(pollInterval);
                                    await loadHchoAnalyticsData();
                                    refreshBtn.classList.remove('spinning');
                                    return;
                                }
                            }
                        } catch (err) { }
                        if (attempts >= 15) {
                            clearInterval(pollInterval);
                            await loadHchoAnalyticsData();
                            refreshBtn.classList.remove('spinning');
                        }
                    }, 3000);
                }
            } catch (err) {
                console.error('Error refreshing HCHO daily feed:', err);
                refreshBtn.classList.remove('spinning');
            }
        });
    }

    // Top 4 KPIs
    const elFires = document.getElementById('hcho-kpi-fires');
    const totalFires = data.total_active_fires != null ? data.total_active_fires : data.metrics?.total_active_fires;
    if (elFires && totalFires != null) {
        elFires.textContent = totalFires.toLocaleString();
    }

    const elFrp = document.getElementById('hcho-kpi-frp');
    const totalFrp = data.total_fire_radiative_power_mw != null ? data.total_fire_radiative_power_mw : data.metrics?.total_frp_mw;
    if (elFrp && totalFrp != null) {
        elFrp.textContent = `${totalFrp.toLocaleString(undefined, { maximumFractionDigits: 1 })} MW`;
    }

    const elPeak = document.getElementById('hcho-kpi-peak');
    const peakHcho = data.peak_hcho_column_10_15 != null ? data.peak_hcho_column_10_15 : data.metrics?.max_india_hcho_e15;
    if (elPeak && peakHcho != null) {
        elPeak.textContent = `${peakHcho.toFixed(1)} × 10¹⁵`;
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

    const cSil = document.getElementById('corr-val-sil');
    const silVal = data.metrics?.silhouette_score ?? data.clustering_evaluation?.silhouette_score ?? data.spatial_clustering_evaluation?.silhouette_score;
    if (cSil && silVal != null) {
        cSil.textContent = `S = ${silVal.toFixed(3)}`;
    }
    const subSil = document.getElementById('corr-sub-sil');
    const nClust = data.metrics?.distinct_clusters_count ?? data.clustering_evaluation?.total_clusters ?? (data.top_clusters ? data.top_clusters.length : null);
    if (subSil && nClust != null) {
        subSil.textContent = `${nClust} Discrete Regional Clusters`;
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
    const topClusters = data.top_clusters || data.dbscan_clusters?.top_clusters || [];

    if (clustersCountTag) {
        if (silVal != null) {
            clustersCountTag.textContent = `${topClusters.length} Clusters · Sil: ${silVal.toFixed(2)}`;
            clustersCountTag.title = `DBSCAN Silhouette Score: ${silVal.toFixed(4)} (Benchmark >0.50 confirms strong cluster separation)`;
        } else {
            clustersCountTag.textContent = `${topClusters.length} Clusters`;
        }
    }

    if (clustersContainer && topClusters.length > 0) {
        clustersContainer.innerHTML = '';
        topClusters.forEach(cl => {
            const item = document.createElement('div');
            item.className = 'cluster-item';
            const firesCount = (cl.total_active_fires != null ? cl.total_active_fires : (cl.total_fires || 0)).toLocaleString();
            const frpVal = (cl.total_frp_mw != null ? cl.total_frp_mw : (cl.total_frp || 0)).toFixed(1);
            const hchoVal = (cl.mean_hcho_molec_cm2_e15 != null ? cl.mean_hcho_molec_cm2_e15 : (cl.mean_hcho || 0)).toFixed(2);

            item.innerHTML = `
                <div class="cluster-tag-badge">Cluster #${cl.cluster_id}</div>
                <div class="cluster-item-title">${cl.cluster_name || cl.region_label || `Cluster #${cl.cluster_id}`}</div>
                <div class="cluster-item-metrics">
                    <span>🔥 ${firesCount} fires</span>
                    <span>⚡ ${frpVal} MW FRP</span>
                    <span>🌌 ${hchoVal} × 10¹⁵</span>
                </div>
            `;
            item.addEventListener('click', () => {
                const cLat = cl.centroid?.lat != null ? cl.centroid.lat : cl.center_lat;
                const cLon = cl.centroid?.lon != null ? cl.centroid.lon : cl.center_lon;
                if (indiaHchoMap && cLat && cLon) {
                    indiaHchoMap.flyTo([cLat, cLon], 7, { duration: 1.2 });
                    sampleIndiaLocation(cLat, cLon, cl);
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

        let color = p.color || '#f59e0b';
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

        const sign = z >= 0 ? '+' : '';
        marker.bindTooltip(`
            <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:11px; font-weight:600; padding:2px 4px;">
                <b>Hotspot Gi* Z: ${sign}${z.toFixed(2)}</b><br/>
                HCHO Column: ${hcho.toFixed(2)} × 10¹⁵ molec/cm²<br/>
                FRP: ${(p.total_frp || p.frp_mw || 0).toFixed(1)} MW (${p.fire_count || 0} fires)<br/>
                <span style="font-size:10px; color:#64748b;">${p.eco_zone || 'Hotspot Point'}</span>
            </div>
        `, { sticky: true });

        marker.on('click', () => {
            sampleIndiaLocation(lat, lon, p);
        });

        hotspotLayerGroup.addLayer(marker);
    });
}

function renderClustersLayer(geojson) {
    if (!clusterLayerGroup || !geojson || !geojson.features) return;
    clusterLayerGroup.clearLayers();

    geojson.features.forEach(f => {
        const p = f.properties || {};

        // 1. Draw cluster boundary polygon
        const poly = L.geoJSON(f, {
            style: {
                color: '#6d28d9',
                weight: 2.5,
                opacity: 0.95,
                dashArray: '6, 6',
                fillColor: '#8b5cf6',
                fillOpacity: 0.22
            }
        });

        const tooltipHtml = `
            <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:12px; font-weight:700; padding:4px 6px;">
                <span style="color:#7c3aed; text-transform:uppercase; font-size:10px; font-weight:800; letter-spacing:0.05em;">DBSCAN Plume Cluster #${p.cluster_id}</span><br/>
                <span style="font-size:13px; color:#0f172a;">${p.cluster_name || p.region_tag || `Cluster #${p.cluster_id}`}</span><br/>
                <div style="font-size:11px; color:#475569; font-weight:500; margin-top:3px; line-height:1.4;">
                    🔥 ${(p.total_active_fires || 0).toLocaleString()} fires · ${(p.total_frp_mw || 0).toFixed(1)} MW FRP<br/>
                    Mean HCHO: ${(p.mean_hcho_molec_cm2_e15 || 0).toFixed(2)} × 10¹⁵ molec/cm²<br/>
                    Gi* Mean Z: +${(p.mean_gi_z_score || 0).toFixed(2)} · Wind: ${(p.mean_wind_speed_ms || 3.0).toFixed(1)} m/s
                </div>
            </div>
        `;

        poly.bindTooltip(tooltipHtml, { sticky: true });
        poly.on('click', (e) => {
            const cLat = p.centroid?.lat != null ? p.centroid.lat : e.latlng.lat;
            const cLon = p.centroid?.lon != null ? p.centroid.lon : e.latlng.lng;
            sampleIndiaLocation(cLat, cLon, p);
        });
        clusterLayerGroup.addLayer(poly);

        // 2. Draw centroid badge marker
        const cLat = p.centroid?.lat;
        const cLon = p.centroid?.lon;
        if (cLat != null && cLon != null && !isNaN(cLat) && !isNaN(cLon)) {
            const badgeHtml = `
                <div class="dbscan-map-badge" style="background:#7c3aed; color:#ffffff; padding:3px 9px; border-radius:999px; font-size:10px; font-weight:800; font-family:'Plus Jakarta Sans',sans-serif; box-shadow:0 3px 10px rgba(124,58,237,0.45); display:flex; align-items:center; gap:5px; white-space:nowrap; border:1.5px solid #ffffff; cursor:pointer;">
                    <span>🏷️ #${p.cluster_id}</span>
                    <span style="background:rgba(255,255,255,0.25); padding:1px 5px; border-radius:6px; font-size:9.5px;">${(p.total_active_fires || 0).toLocaleString()} 🔥</span>
                </div>
            `;

            const icon = L.divIcon({
                className: 'custom-pin-divicon',
                html: badgeHtml,
                iconSize: [90, 24],
                iconAnchor: [45, 12]
            });

            const marker = L.marker([cLat, cLon], { icon });
            marker.bindTooltip(tooltipHtml, { sticky: true });
            marker.on('click', () => {
                sampleIndiaLocation(cLat, cLon, p);
            });
            clusterLayerGroup.addLayer(marker);
        }
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

function getWindFlowDescription(deg, u = null, v = null) {
    if (deg == null || isNaN(deg)) return { label: 'Variable', origin: 'Variable', dest: 'Variable', flowAngle: 0 };

    // Normalize meteorological degree (direction wind comes FROM, 0° = N, 90° = E, 180° = S, 270° = W)
    const norm = ((deg % 360) + 360) % 360;

    // Downstream flow heading angle (where wind blows TO, 0° = N, 90° = E, 180° = S, 270° = W)
    let flowAngle = 0;
    if (u != null && v != null && (u !== 0 || v !== 0)) {
        flowAngle = ((Math.atan2(u, v) * 180 / Math.PI) + 360) % 360;
    } else {
        flowAngle = (norm + 180) % 360;
    }

    // Standard atmospheric transport direction:
    // Wind coming from NE (e.g. 22.5° - 78.75°) flows toward SW (NE ➔ SW)
    let label = "NW ➔ SE";
    let origin = "NW";
    let dest = "SE";

    if (norm >= 337.5 || norm < 22.5) {
        label = "N ➔ S"; origin = "N"; dest = "S";
    } else if (norm < 78.75) {
        label = "NE ➔ SW"; origin = "NE"; dest = "SW";
    } else if (norm < 101.25) {
        label = "E ➔ W"; origin = "E"; dest = "W";
    } else if (norm < 157.5) {
        label = "SE ➔ NW"; origin = "SE"; dest = "NW";
    } else if (norm < 202.5) {
        label = "S ➔ N"; origin = "S"; dest = "N";
    } else if (norm < 258.75) {
        label = "SW ➔ NE"; origin = "SW"; dest = "NE";
    } else if (norm < 281.25) {
        label = "W ➔ E"; origin = "W"; dest = "E";
    } else {
        label = "NW ➔ SE"; origin = "NW"; dest = "SE";
    }

    return { label, origin, dest, angle: norm, flowAngle };
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
        const u = p.u_component;
        const v = p.v_component;

        // Downstream advection vector (pointing in the direction the air and emissions are transported)
        const flowInfo = getWindFlowDescription(dir, u, v);
        const flowAngle = flowInfo.flowAngle;

        // SVG Arrow rotated by downstream flow direction
        const arrowHtml = `
            <div style="transform: rotate(${flowAngle}deg); display:flex; align-items:center; justify-content:center; opacity:0.80; pointer-events:none;">
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

    // Compute or extract metrics
    let hchoVal = 2.25;
    let zScore = 0.5;
    let firesNearby = 0;
    let frpNearby = 0;

    if (knownProps) {
        hchoVal = knownProps.hcho_column_10_15 || (knownProps.hcho_molec_cm2_e15 != null ? knownProps.hcho_molec_cm2_e15 : (knownProps.mean_hcho_molec_cm2_e15 != null ? knownProps.mean_hcho_molec_cm2_e15 : (knownProps.hcho_tropospheric_column ? knownProps.hcho_tropospheric_column * 60221.4 : 2.5)));
        zScore = knownProps.gi_star_z_score != null ? knownProps.gi_star_z_score : (knownProps.gi_z_score != null ? knownProps.gi_z_score : (knownProps.mean_gi_z_score != null ? knownProps.mean_gi_z_score : 0));
        firesNearby = knownProps.fire_count != null ? knownProps.fire_count : (knownProps.total_active_fires != null ? knownProps.total_active_fires : (knownProps.total_fires || 0));
        frpNearby = knownProps.total_frp != null ? knownProps.total_frp : (knownProps.frp_mw != null ? knownProps.frp_mw : (knownProps.total_frp_mw || 0));
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
                        zScore = f.properties?.gi_star_z_score != null ? f.properties.gi_star_z_score : (f.properties?.gi_z_score != null ? f.properties.gi_z_score : 0);
                        hchoVal = f.properties?.hcho_column_10_15 != null ? f.properties.hcho_column_10_15 : (f.properties?.hcho_molec_cm2_e15 != null ? f.properties.hcho_molec_cm2_e15 : 2.4);
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
    let uComp = null;
    let vComp = null;
    let transportDesc = null;

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
                uComp = p.u_component != null ? p.u_component : null;
                vComp = p.v_component != null ? p.v_component : null;
                transportDesc = p.transport_direction || null;
            }
        });
    }

    const windInfo = getWindFlowDescription(windDir, uComp, vComp);
    const flowAngle = windInfo.flowAngle;
    let dirCard = windInfo.label;
    if (transportDesc) {
        const match = transportDesc.match(/\(([^)]+)\)/);
        if (match) dirCard = match[1];
    }

    // Update Right Inspector Panel
    const elCoords = document.getElementById('hcho-insp-coords');
    if (elCoords) elCoords.textContent = `${lat.toFixed(4)}° N, ${lon.toFixed(4)}° E`;

    const elTitle = document.getElementById('hcho-insp-title');
    if (elTitle) elTitle.textContent = regionName;

    const elZone = document.getElementById('hcho-insp-zone');
    if (elZone) {
        elZone.innerHTML = `<b>Region:</b> ${regionName} — <span>${ecoDesc}</span>`;
    }

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
    if (elWindDir) {
        elWindDir.innerHTML = `
            <span style="display:inline-flex; align-items:center; gap:4px;">
                ${Math.round(windDir)}° (${dirCard})
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="transform: rotate(${flowAngle}deg); vertical-align: middle; display: inline-block;">
                    <line x1="12" y1="19" x2="12" y2="5"></line>
                    <polyline points="5 12 12 5 19 12"></polyline>
                </svg>
            </span>
        `;
    }

    // Place or move animated SVG pin marker
    if (indiaClickMarker) {
        indiaHchoMap.removeLayer(indiaClickMarker);
    }

    const pinHtml = `
        <div class="custom-map-pin-wrap">
            <div class="pin-pulse-ring ring-violet"></div>
            <div class="pin-marker-head pin-violet">
                <svg width="28" height="36" viewBox="0 0 24 32" fill="none">
                    <path d="M12 0C5.372 0 0 5.373 0 12c0 8.5 12 20 12 20s12-11.5 12-20c0-6.627-5.372-12-12-12z" fill="#7c3aed"/>
                    <circle cx="12" cy="11" r="4.5" fill="#ffffff"/>
                </svg>
            </div>
        </div>
    `;

    const icon = L.divIcon({
        className: 'custom-pin-divicon',
        html: pinHtml,
        iconSize: [28, 36],
        iconAnchor: [14, 36],
        popupAnchor: [0, -36]
    });

    const sign = zScore >= 0 ? '+' : '';
    const zScoreDisplay = `Z = ${sign}${zScore.toFixed(2)}`;
    const zClass = zScore >= 2.58 ? 'text-red' : zScore >= 1.96 ? 'text-amber' : 'text-blue';
    const hotspotBadgeClass = zScore >= 2.58 ? 'bg-hotspot-99' : zScore >= 1.96 ? 'bg-hotspot-95' : 'bg-hotspot-norm';
    const confLabel = zScore >= 2.58 ? '99% Hotspot' : zScore >= 1.96 ? '95% Hotspot' : zScore >= 1.65 ? '90% Hotspot' : 'Baseline / Low';

    const popupContent = `
        <div class="map-interactive-popup">
            <div class="popup-top-row">
                <span class="popup-sub-tag">HCHO SAMPLER PIN</span>
                <span class="popup-hcho-badge ${hotspotBadgeClass}">${confLabel}</span>
            </div>
            <h4 class="popup-loc-title">${regionName}</h4>
            <div class="popup-coords-text">${lat.toFixed(4)}° N, ${lon.toFixed(4)}° E</div>
            <div class="popup-mini-grid">
                <div class="popup-mini-item">
                    <span class="p-lbl">S5P HCHO Column</span>
                    <span class="p-val text-violet">${hchoVal.toFixed(2)} × 10¹⁵</span>
                </div>
                <div class="popup-mini-item">
                    <span class="p-lbl">Spatial Z-Score</span>
                    <span class="p-val ${zClass}">${zScoreDisplay}</span>
                </div>
                <div class="popup-mini-item">
                    <span class="p-lbl">Nearby Fires</span>
                    <span class="p-val">${firesNearby} fires</span>
                </div>
                <div class="popup-mini-item">
                    <span class="p-lbl">ERA5 Advection</span>
                    <span class="p-val" style="display:inline-flex; align-items:center; gap:5px;">
                        <span>${windSpeed.toFixed(1)} m/s · ${dirCard}</span>
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="transform: rotate(${flowAngle}deg); flex-shrink: 0;">
                            <line x1="12" y1="19" x2="12" y2="5"></line>
                            <polyline points="5 12 12 5 19 12"></polyline>
                        </svg>
                    </span>
                </div>
            </div>
            <div class="popup-footer-status">
                <span class="popup-status-dot" style="background:${zScore >= 2.58 ? '#ef4444' : zScore >= 1.96 ? '#f59e0b' : '#3b82f6'};"></span>
                <span>${ecoDesc}</span>
            </div>
        </div>
    `;

    indiaClickMarker = L.marker([lat, lon], { icon }).addTo(indiaHchoMap);
    indiaClickMarker.bindPopup(popupContent, {
        offset: [0, -4],
        closeButton: true,
        autoClose: false,
        className: 'custom-leaflet-popup-card'
    }).openPopup();
}
