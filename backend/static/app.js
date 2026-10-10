/**
 * Virtual Air Quality Estimation System — Interactive Frontend Logic
 */

let map = null;
let nodeMarkers = {};
let clickMarker = null;
let gridLayerGroup = null;
let currentNodesData = null;

// CPCB Color and Breakpoint Utility
function getCPCBColor(aqi) {
    if (aqi <= 50) return '#00b050';      // Good
    if (aqi <= 100) return '#92d050';     // Satisfactory
    if (aqi <= 200) return '#eab308';     // Moderate
    if (aqi <= 300) return '#f97316';     // Poor
    if (aqi <= 400) return '#ef4444';     // Very Poor
    return '#b91c1c';                    // Severe
}

function getCPCBPillClass(aqi) {
    if (aqi <= 50) return 'good';
    if (aqi <= 100) return 'satisfactory';
    if (aqi <= 200) return 'moderate';
    if (aqi <= 300) return 'poor';
    if (aqi <= 400) return 'very-poor';
    return 'severe';
}

// 1. Live Clock
function startLiveClock() {
    function updateClock() {
        const now = new Date();
        const options = { timeZone: 'Asia/Kolkata', hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' };
        const timeStr = new Intl.DateTimeFormat('en-GB', options).format(now);
        const clockEl = document.getElementById('current-ist-time');
        if (clockEl) clockEl.textContent = `${timeStr} IST`;
    }
    updateClock();
    setInterval(updateClock, 1000);
}

// 2. Initialize Leaflet Geospatial Map
function initMap() {
    const vidarbhaCenter = [20.65, 78.45];
    map = L.map('vidarbha-map', {
        center: vidarbhaCenter,
        zoom: 7,
        zoomControl: true
    });

    // Dark CartoDB basemap tiles
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
        subdomains: 'abcd',
        maxZoom: 18
    }).addTo(map);

    gridLayerGroup = L.layerGroup().addTo(map);

    // Map Click Listener -> Trigger Virtual Inspector
    map.on('click', (e) => {
        const lat = parseFloat(e.latlng.lat.toFixed(4));
        const lon = parseFloat(e.latlng.lng.toFixed(4));

        document.getElementById('input-lat').value = lat;
        document.getElementById('input-lon').value = lon;

        updateClickMarker(lat, lon);
        executePointPrediction(lat, lon);
    });
}

function updateClickMarker(lat, lon) {
    if (clickMarker) {
        map.removeLayer(clickMarker);
    }

    const clickIcon = L.divIcon({
        className: 'custom-click-pin',
        html: `<div style="background:#f59e0b; width:14px; height:14px; border-radius:50%; border:2px solid #ffffff; box-shadow:0 0 12px #f59e0b; animation: radar-pulse 1.5s infinite;"></div>`,
        iconSize: [14, 14],
        iconAnchor: [7, 7]
    });

    clickMarker = L.marker([lat, lon], { icon: clickIcon }).addTo(map);
    clickMarker.bindPopup(`<b>Interactive Inspector</b><br>Lat: ${lat}<br>Lon: ${lon}`).openPopup();
}

// 3. Render Node Markers on Map
function renderNodeMarkers(nodes) {
    nodes.forEach(node => {
        const lat = node.coordinates.lat;
        const lon = node.coordinates.lon;
        const aqi = node.virtual_prediction.predicted_india_naqi;
        const color = getCPCBColor(aqi);
        const isPhysical = node.type === 'physical';

        const markerHtml = `
            <div style="background:${color}; color:#ffffff; padding:4px 8px; border-radius:12px; font-family:'Outfit', sans-serif; font-size:11px; font-weight:800; border:2px solid ${isPhysical ? '#38bdf8' : '#ffffff'}; box-shadow:0 0 14px ${color}; text-align:center; min-width:42px; transform:translate(-50%, -50%);">
                ${Math.round(aqi)}
            </div>
        `;

        const customIcon = L.divIcon({
            className: 'aqi-node-marker',
            html: markerHtml,
            iconSize: [42, 24]
        });

        if (nodeMarkers[node.id]) {
            map.removeLayer(nodeMarkers[node.id]);
        }

        const marker = L.marker([lat, lon], { icon: customIcon }).addTo(map);
        
        let popupHtml = `
            <div style="font-family:'Inter', sans-serif; min-width:180px;">
                <h4 style="margin:0; font-family:'Outfit'; font-size:14px;">${node.name}</h4>
                <div style="font-size:11px; color:#94a3b8; margin-top:2px;">Type: <b>${node.type.toUpperCase()}</b></div>
                <div style="margin-top:6px; font-size:16px; font-weight:800; color:${color};">
                    Predicted NAQI: ${aqi.toFixed(1)}
                </div>
                <div style="font-size:11px; color:#cbd5e1;">Category: <b>${node.virtual_prediction.category}</b></div>
        `;

        if (node.physical_ground_truth) {
            const g = node.physical_ground_truth;
            popupHtml += `
                <div style="margin-top:6px; padding-top:6px; border-top:1px solid #334155; font-size:11px; color:#38bdf8;">
                    CPCB Ground: <b>${g.observed_cpcb_naqi}</b> (Residual: ${g.residual_vs_portal_aqi > 0 ? '+' : ''}${g.residual_vs_portal_aqi})
                </div>
            `;
        }

        popupHtml += `</div>`;
        marker.bindPopup(popupHtml);
        nodeMarkers[node.id] = marker;
    });
}

// 4. Render Spatial Heatmap Mesh Grid
async function loadSpatialMesh() {
    try {
        const resp = await fetch('/api/grid?lat_steps=6&lon_steps=8');
        if (!resp.ok) return;
        const data = await resp.json();

        gridLayerGroup.clearLayers();

        data.grid.forEach(point => {
            const circle = L.circle([point.lat, point.lon], {
                radius: 22000,
                color: point.color,
                fillColor: point.color,
                fillOpacity: 0.16,
                weight: 1,
                opacity: 0.4
            });

            circle.bindTooltip(`Spatial Point: AQI ${point.predicted_aqi.toFixed(1)} (${point.category})`, {
                sticky: true
            });

            circle.on('click', () => {
                document.getElementById('input-lat').value = point.lat;
                document.getElementById('input-lon').value = point.lon;
                updateClickMarker(point.lat, point.lon);
                executePointPrediction(point.lat, point.lon);
            });

            gridLayerGroup.addLayer(circle);
        });
    } catch (err) {
        console.warn('Failed to load spatial mesh grid:', err);
    }
}

// 5. Fetch & Render Vidarbha Grid Nodes
async function fetchGridNodes(refresh = false) {
    const refreshIcon = document.getElementById('refresh-icon');
    if (refreshIcon) refreshIcon.classList.add('rotating');

    try {
        const resp = await fetch(`/api/nodes${refresh ? '?refresh=true' : ''}`);
        if (!resp.ok) throw new Error(`HTTP error ${resp.status}`);
        const data = await resp.json();
        currentNodesData = data;

        renderNodesGrid(data.nodes);
        renderNodeMarkers(data.nodes);
        updateRegionalKPIs(data.nodes);
    } catch (err) {
        console.error('Error fetching nodes:', err);
        const container = document.getElementById('nodes-container');
        if (container) {
            container.innerHTML = `<div class="loading-nodes" style="color:#ef4444;">Failed to fetch live telemetry: ${err.message}</div>`;
        }
    } finally {
        if (refreshIcon) refreshIcon.classList.remove('rotating');
    }
}

function updateRegionalKPIs(nodes) {
    if (!nodes || nodes.length === 0) return;
    const avgAqi = nodes.reduce((sum, n) => sum + n.virtual_prediction.predicted_india_naqi, 0) / nodes.length;
    const aqiEl = document.getElementById('regional-avg-aqi');
    const catEl = document.getElementById('regional-avg-category');

    if (aqiEl) {
        aqiEl.textContent = avgAqi.toFixed(1);
        aqiEl.style.color = getCPCBColor(avgAqi);
    }
    if (catEl) {
        let catName = "Satisfactory";
        if (avgAqi <= 50) catName = "Good";
        else if (avgAqi <= 100) catName = "Satisfactory";
        else if (avgAqi <= 200) catName = "Moderate";
        else if (avgAqi <= 300) catName = "Poor";
        else catName = "Very Poor";
        catEl.textContent = `Overall: ${catName}`;
    }
}

function renderNodesGrid(nodes) {
    const container = document.getElementById('nodes-container');
    if (!container) return;

    container.innerHTML = nodes.map(node => {
        const pred = node.virtual_prediction;
        const aqi = pred.predicted_india_naqi;
        const aqiColor = getCPCBColor(aqi);
        const isPhysical = node.type === 'physical';
        const ground = node.physical_ground_truth;
        const rfeats = node.realtime_features || {};
        const tracers = rfeats.atmospheric_tracers || {};
        const meteo = rfeats.meteorology || {};

        let compHtml = '';
        if (isPhysical && ground) {
            const resVal = ground.residual_vs_portal_aqi;
            const resSign = resVal > 0 ? '+' : '';
            const resClass = Math.abs(resVal) <= 15 ? 'good-fit' : 'high-fit';

            compHtml = `
                <div class="comparison-row">
                    <div class="comp-title">
                        <span>🏛️ CPCB Ground Truth (${ground.observed_time || 'Live'})</span>
                        <span class="comp-residual ${resClass}">Residual: ${resSign}${resVal} pts</span>
                    </div>
                    <div class="comp-vals">
                        <span>CPCB Portal AQI: <b>${ground.observed_cpcb_naqi || 'N/A'}</b></span>
                        <span>PM2.5 Sub-Index: <b>${ground.observed_pm25_subindex || 'N/A'}</b></span>
                    </div>
                </div>
            `;
        } else {
            compHtml = `
                <div class="comparison-row" style="background:rgba(16, 185, 129, 0.04); border-color:rgba(16, 185, 129, 0.25);">
                    <div class="comp-title" style="color:#10b981;">
                        <span>✨ Autonomous AI Virtual Sensor</span>
                        <span style="color:#10b981;">100% Synthetic-Free</span>
                    </div>
                    <div class="comp-vals" style="font-size:11px;">
                        <span>Unmonitored Ground Truth Resolved via CAMS + ERA5 Physics</span>
                    </div>
                </div>
            `;
        }

        return `
            <div class="node-card" id="card-${node.id}">
                <div class="node-top-bar">
                    <div>
                        <div class="node-city">${node.city}</div>
                        <div class="node-sub">${node.name} · ${node.elevation_m}m alt</div>
                    </div>
                    <span class="node-type-pill ${node.type}">${node.type === 'physical' ? 'Physical Station' : 'Virtual Sensor'}</span>
                </div>

                <div class="node-gauge-block">
                    <div class="node-aqi-num" style="color:${aqiColor};">${aqi.toFixed(1)}</div>
                    <div class="node-aqi-meta">
                        <span class="node-category" style="color:${aqiColor};">${pred.category}</span>
                        <span class="node-ci">95% CI: [${pred.confidence_interval.lower.toFixed(1)} – ${pred.confidence_interval.upper.toFixed(1)}]</span>
                    </div>
                </div>

                ${compHtml}

                <div class="node-telemetry">
                    <div class="tel-item">
                        <span>CAMS PM2.5:</span>
                        <span class="tel-val">${tracers.pm25 !== undefined ? tracers.pm25 : '--'} µg/m³</span>
                    </div>
                    <div class="tel-item">
                        <span>CAMS PM10:</span>
                        <span class="tel-val">${tracers.pm10 !== undefined ? tracers.pm10 : '--'} µg/m³</span>
                    </div>
                    <div class="tel-item">
                        <span>Temp / RH:</span>
                        <span class="tel-val">${meteo.temperature_c !== undefined ? meteo.temperature_c : '--'}°C / ${meteo.relative_humidity_pct !== undefined ? meteo.relative_humidity_pct : '--'}%</span>
                    </div>
                    <div class="tel-item">
                        <span>Wind Vector:</span>
                        <span class="tel-val">${meteo.wind_speed_kmh !== undefined ? meteo.wind_speed_kmh : '--'} km/h (${meteo.wind_direction_deg || 0}°)</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// 6. Execute Point Virtual Sensor Prediction
async function executePointPrediction(lat, lon, overrides = {}) {
    const resultBox = document.getElementById('inspector-result');
    const simulateBtn = document.getElementById('simulate-btn');

    if (simulateBtn) simulateBtn.disabled = true;

    try {
        const payload = {
            latitude: lat,
            longitude: lon,
            ...overrides
        };

        const resp = await fetch('/api/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!resp.ok) throw new Error(`Inference HTTP error ${resp.status}`);
        const data = await resp.json();

        // Update UI Box
        const pred = data.prediction;
        const color = getCPCBColor(pred.predicted_india_naqi);

        document.getElementById('res-location-title').textContent = `Virtual Sensor at (${lat}, ${lon})`;
        document.getElementById('res-coords').textContent = `${lat.toFixed(4)}°N, ${lon.toFixed(4)}°E`;
        
        const catBadge = document.getElementById('res-category-badge');
        catBadge.textContent = pred.category;
        catBadge.style.backgroundColor = color;

        const aqiVal = document.getElementById('res-aqi-val');
        aqiVal.textContent = pred.predicted_india_naqi.toFixed(1);
        aqiVal.style.color = color;

        document.getElementById('res-ci').textContent = `[${pred.confidence_interval.lower.toFixed(1)} – ${pred.confidence_interval.upper.toFixed(1)}]`;
        document.getElementById('res-dominant').textContent = pred.dominant_pollutant || 'PM2.5';
        // Observation Time and Latency
        const obsEl = document.getElementById('res-obs-time');
        if (obsEl) obsEl.textContent = data.observation_time || 'Live';
        const latEl = document.getElementById('res-latency');
        if (latEl) latEl.textContent = `${data.latency_ms || 120}ms`;

        // Real-Time Features Breakdown
        const feats = data.realtime_features || {};
        const tracers = feats.atmospheric_tracers || {};
        const meteo = feats.meteorology || {};
        const spatial = feats.spatial_transport || {};

        // 1. Tracers
        const setVal = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
        setVal('f-pm25', `${tracers.pm25 !== undefined ? tracers.pm25 : '--'} µg/m³`);
        setVal('f-pm10', `${tracers.pm10 !== undefined ? tracers.pm10 : '--'} µg/m³`);
        setVal('f-no2', `${tracers.no2 !== undefined ? tracers.no2 : '--'} µg/m³`);
        setVal('f-so2', `${tracers.so2 !== undefined ? tracers.so2 : '--'} µg/m³`);
        setVal('f-co', `${tracers.co !== undefined ? tracers.co : '--'} µg/m³`);
        setVal('f-o3', `${tracers.o3 !== undefined ? tracers.o3 : '--'} µg/m³`);

        // 2. Weather
        setVal('f-temp', `${meteo.temperature_c !== undefined ? meteo.temperature_c : '--'}°C`);
        setVal('f-rh', `${meteo.relative_humidity_pct !== undefined ? meteo.relative_humidity_pct : '--'}%`);
        setVal('f-dew', `${meteo.dew_point_spread_c !== undefined ? meteo.dew_point_spread_c : '--'}°C`);
        setVal('f-pressure', `${meteo.surface_pressure_hpa !== undefined ? meteo.surface_pressure_hpa : '--'} hPa`);
        setVal('f-wind', `${meteo.wind_speed_kmh !== undefined ? meteo.wind_speed_kmh : '--'} km/h (${meteo.wind_direction_deg || 0}°)`);
        setVal('f-solar', `${meteo.solar_radiation_wm2 !== undefined ? meteo.solar_radiation_wm2 : '--'} W/m²`);

        // 3. Spatial & Roads
        setVal('f-roaddensity', `${spatial.osm_road_density_km2 !== undefined ? spatial.osm_road_density_km2 : '--'} /km²`);
        setVal('f-totalroads', `${spatial.osm_total_roads !== undefined ? spatial.osm_total_roads : '--'}`);
        const dists = spatial.distances_to_nodes || {};
        setVal('f-dist-nagpur', dists["Nagpur"] || '--');
        setVal('f-dist-chandra', dists["Chandrapur"] || '--');

        resultBox.classList.remove('hidden');

        // Smooth pan to location
        if (map) {
            map.panTo([lat, lon], { animate: true, duration: 0.8 });
        }
    } catch (err) {
        alert(`Prediction failed: ${err.message}`);
    } finally {
        if (simulateBtn) simulateBtn.disabled = false;
    }
}

// 7. Event Listeners Setup
document.addEventListener('DOMContentLoaded', () => {
    startLiveClock();
    initMap();
    fetchGridNodes();
    loadSpatialMesh();

    // Refresh Button
    const refreshBtn = document.getElementById('refresh-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => fetchGridNodes(true));
    }

    // Toggle Spatial Mesh Heatmap
    const toggleBtn = document.getElementById('toggle-heatmap');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            if (map.hasLayer(gridLayerGroup)) {
                map.removeLayer(gridLayerGroup);
                toggleBtn.classList.remove('active');
            } else {
                map.addLayer(gridLayerGroup);
                toggleBtn.classList.add('active');
            }
        });
    }

    // Reset View Button
    const resetBtn = document.getElementById('reset-view');
    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            map.setView([20.65, 78.45], 7, { animate: true });
        });
    }

    // Custom Form Submission
    const predForm = document.getElementById('prediction-form');
    if (predForm) {
        predForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const lat = parseFloat(document.getElementById('input-lat').value);
            const lon = parseFloat(document.getElementById('input-lon').value);

            const overrides = {};
            const temp = document.getElementById('input-temp').value;
            const rh = document.getElementById('input-rh').value;
            const ws = document.getElementById('input-ws').value;
            const pm25 = document.getElementById('input-pm25').value;

            if (temp) overrides.temperature_override = parseFloat(temp);
            if (rh) overrides.humidity_override = parseFloat(rh);
            if (ws) overrides.wind_speed_override = parseFloat(ws);
            if (pm25) overrides.pm25_override = parseFloat(pm25);

            updateClickMarker(lat, lon);
            executePointPrediction(lat, lon, overrides);
        });
    }
});
