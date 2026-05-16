/**
 * live_tracking.js — Phase 1: Multi-Bus Live Tracking Module
 *
 * Architecture:
 *   - Polling-based (replaces WebSocket stub later by swapping fetchAllBuses)
 *   - Single entry point: processBusData(buses)
 *   - Marker registry: markers[bus_id] — never recreates, only updates
 *   - Follow mode: one bus at a time
 *   - Offline detection: > 30s since last_updated → gray marker
 *   - Auto-remove: > 5min offline → marker removed
 *
 * Future WebSocket upgrade:
 *   Replace the setInterval(fetchAllBuses, POLL_INTERVAL) call with a WebSocket
 *   that calls processBusData(data.buses) on message — nothing else changes.
 */

// ─── CONFIG ─────────────────────────────────────────────────────────────────
const POLL_INTERVAL    = 5000;   // ms between API polls
const OFFLINE_THRESHOLD = 30;   // seconds — bus marked offline
const REMOVE_THRESHOLD  = 300;  // seconds (5 min) — stale marker removed
const API_URL          = '/api/buses/locations/';
const DEFAULT_CENTER   = [23.7508, 90.3865]; // UAP Campus, Green Road, Farmgate
const DEFAULT_ZOOM     = 14;

// ─── PREDEFINED ROUTES (UAP UNIVERSITY) ──────────────────────────────────────
const PREDEFINED_ROUTES = {
    mirpur: {
        name: 'Mirpur Route',
        color: '#ff4757',
        path: [
            [23.8061, 90.3784], [23.7964, 90.3768], [23.7768, 90.3874], 
            [23.7588, 90.3939], [23.7508, 90.3865]
        ]
    },
    narayanganj: {
        name: 'Narayanganj Route',
        color: '#2ed573',
        path: [
            [23.6238, 90.4998], [23.6811, 90.4566], [23.7088, 90.4357], 
            [23.7399, 90.3945], [23.7508, 90.3865]
        ]
    },
    gabtoli: {
        name: 'Gabtoli Route',
        color: '#1e90ff',
        path: [
            [23.7852, 90.3424], [23.7719, 90.3622], [23.7588, 90.3939], [23.7508, 90.3865]
        ]
    },
    uttara: {
        name: 'Uttara Route',
        color: '#ffa502',
        path: [
            [23.8762, 90.3822], [23.8103, 90.4125], [23.7933, 90.4069], 
            [23.7588, 90.3939], [23.7508, 90.3865]
        ]
    }
};

// ─── STATE ──────────────────────────────────────────────────────────────────
let map           = null;        // Leaflet map instance
let pollTimer     = null;        // setInterval handle
let followedBusId = null;        // bus_id currently in follow mode (or null)
let currentRouteId = 'all';      // Currently selected route filter
let routePolylines = {};         // Map of L.Polyline objects

/**
 * markers registry: { [bus_id]: { marker: L.Marker, lastSeen: Date, busData: {} } }
 * Never recreated — positions updated in-place.
 */
const markers = {};

// ─── MAP INIT ────────────────────────────────────────────────────────────────

/**
 * initMap — Initialise Leaflet map, start polling.
 * Called once on DOMContentLoaded.
 */
function initMap() {
    map = L.map('map', {
        center: DEFAULT_CENTER,
        zoom: DEFAULT_ZOOM,
        zoomControl: true,
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
    }).addTo(map);

    // Fetch immediately, then start polling
    fetchAllBuses();
    pollTimer = setInterval(fetchAllBuses, POLL_INTERVAL);
}

// ─── DATA FETCHING ───────────────────────────────────────────────────────────

/**
 * fetchAllBuses — Poll /api/buses/locations/ and pipe data into processBusData.
 * This is the ONLY function that needs to change for WebSocket migration.
 */
async function fetchAllBuses() {
    try {
        const response = await fetch(API_URL, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();

        if (data.success && Array.isArray(data.buses)) {
            processBusData(data.buses);
            updateStatusBar(data.buses);
        }
    } catch (err) {
        console.warn('[LiveTracking] Fetch error:', err.message);
        setStatusError();
    }
}

// ─── CORE PROCESSING ─────────────────────────────────────────────────────────

/**
 * processBusData — Single entry point for bus data (polling OR future WebSocket).
 * Creates new markers, updates existing ones, removes stale ones.
 * @param {Array} buses — array of bus objects from API
 */
function processBusData(buses) {
    const activeBusIds = new Set();

    buses.forEach(busData => {
        if (busData.latitude == null || busData.longitude == null) return;

        // Filter by selected route if not 'all'
        if (currentRouteId !== 'all') {
            const busRouteCode = (busData.route_code || '').toLowerCase();
            if (!busRouteCode.includes(currentRouteId)) {
                // If marker exists but now filtered out, remove it
                if (markers[busData.id]) removeMarker(busData.id);
                return;
            }
        }

        activeBusIds.add(busData.id);

        if (markers[busData.id]) {
            updateMarker(busData);
        } else {
            createMarker(busData);
        }
    });

    // Check for stale / remove very old markers
    Object.keys(markers).forEach(id => {
        const numId = parseInt(id);
        if (!activeBusIds.has(numId)) {
            // Bus no longer in API — treat as offline
            const entry = markers[id];
            const age = (Date.now() - entry.lastSeen) / 1000;
            if (age > REMOVE_THRESHOLD) {
                removeMarker(id);
            } else {
                applyOfflineStyle(entry.marker, true);
            }
        }
    });

    renderActiveBusCards(buses);
}

/**
 * selectRoute — Change the active route filter and draw its path.
 */
window.selectRoute = function(routeId) {
    currentRouteId = routeId;
    
    // Clear existing polylines
    Object.values(routePolylines).forEach(p => p.remove());
    routePolylines = {};

    if (routeId !== 'all' && PREDEFINED_ROUTES[routeId]) {
        const route = PREDEFINED_ROUTES[routeId];
        const poly = L.polyline(route.path, {
            color: route.color,
            weight: 6,
            opacity: 0.6,
            dashArray: '10, 15',
            lineJoin: 'round'
        }).addTo(map);
        
        routePolylines[routeId] = poly;
        map.fitBounds(poly.getBounds(), { padding: [50, 50] });
    } else {
        map.setView(DEFAULT_CENTER, DEFAULT_ZOOM);
    }

    // Trigger immediate refresh of markers
    fetchAllBuses();
};

// ─── MARKER MANAGEMENT ───────────────────────────────────────────────────────

/**
 * createMarker — Create a new Leaflet marker and register it.
 * @param {Object} busData
 */
function createMarker(busData) {
    const offline = isOffline(busData.last_updated);
    const icon = buildBusIcon(busData.bus_number, offline);

    const marker = L.marker([busData.latitude, busData.longitude], { icon })
        .addTo(map)
        .bindPopup(renderPopup(busData), { maxWidth: 280, minWidth: 220 });

    marker.on('click', () => onMarkerClick(busData.id));

    markers[busData.id] = {
        marker,
        lastSeen: Date.now(),
        busData: { ...busData },
    };
}

/**
 * updateMarker — Move existing marker to new position, refresh popup content.
 * Never recreates the marker object — preserves open popup state.
 * @param {Object} busData
 */
function updateMarker(busData) {
    const entry = markers[busData.id];
    const offline = isOffline(busData.last_updated);

    // Smooth position update
    entry.marker.setLatLng([busData.latitude, busData.longitude]);

    // Update popup content (even if closed — user reopens to fresh data)
    entry.marker.setPopupContent(renderPopup(busData));

    // Update icon if online/offline state changed
    const wasOffline = entry.marker._wasOffline || false;
    if (offline !== wasOffline) {
        entry.marker.setIcon(buildBusIcon(busData.bus_number, offline));
        entry.marker._wasOffline = offline;
    }

    // If this bus is followed, keep map centered on it
    if (followedBusId === busData.id) {
        map.panTo([busData.latitude, busData.longitude], { animate: true, duration: 0.5 });
    }

    entry.lastSeen = Date.now();
    entry.busData = { ...busData };

    // Update info panel if this bus is selected
    const selectedId = getSelectedBusId();
    if (selectedId === busData.id) {
        updateInfoPanel(busData);
    }
}

/**
 * removeMarker — Remove marker from map and registry.
 * @param {string|number} busId
 */
function removeMarker(busId) {
    if (markers[busId]) {
        markers[busId].marker.remove();
        delete markers[busId];
        if (followedBusId === parseInt(busId)) clearFollowBus();
    }
}

// ─── ICON BUILDER ────────────────────────────────────────────────────────────

/**
 * buildBusIcon — Build a Leaflet DivIcon for a bus marker.
 * Online: blue gradient bus emoji. Offline: gray desaturated.
 */
function buildBusIcon(busNumber, offline) {
    const bg        = offline ? '#6b7280' : '#1e40af';
    const pulse     = offline ? '' : '<span class="lt-pulse"></span>';
    const shortNum  = busNumber.replace(/[^0-9A-Za-z-]/g, '').slice(0, 6);

    return L.divIcon({
        className: '',
        html: `
            <div class="lt-marker ${offline ? 'lt-marker--offline' : 'lt-marker--online'}" style="background:${bg};">
                ${pulse}
                <span class="lt-marker__icon">🚌</span>
                <span class="lt-marker__label">${shortNum}</span>
            </div>`,
        iconSize:   [60, 44],
        iconAnchor: [30, 22],
        popupAnchor:[0, -24],
    });
}

// ─── POPUP ────────────────────────────────────────────────────────────────────

/**
 * renderPopup — Build popup HTML for a bus marker.
 * Modular: can be called standalone for WebSocket updates.
 * @param {Object} busData
 * @returns {string} HTML string
 */
function renderPopup(busData) {
    const offline = isOffline(busData.last_updated);
    const statusBadge = offline
        ? '<span class="lt-badge lt-badge--offline">⚠ OFFLINE</span>'
        : '<span class="lt-badge lt-badge--online">● LIVE</span>';

    const lastUpdatedStr = busData.last_updated
        ? formatTimestamp(busData.last_updated)
        : 'Never';

    const isFollowed = followedBusId === busData.id;
    const followBtnText  = isFollowed ? '📍 Unfollow Bus' : '🎯 Follow Bus';
    const followBtnClass = isFollowed ? 'lt-popup-btn lt-popup-btn--unfollow' : 'lt-popup-btn lt-popup-btn--follow';

    return `
        <div class="lt-popup">
            <div class="lt-popup__header">
                <strong>🚌 ${escapeHtml(busData.bus_number)}</strong>
                ${statusBadge}
            </div>
            <div class="lt-popup__row">
                <span class="lt-popup__label">Driver</span>
                <span class="lt-popup__value">${escapeHtml(busData.driver_name || 'N/A')}</span>
            </div>
            <div class="lt-popup__row">
                <span class="lt-popup__label">Route</span>
                <span class="lt-popup__value">${escapeHtml(busData.route_code || 'N/A')}</span>
            </div>
            <div class="lt-popup__row">
                <span class="lt-popup__label">Coordinates</span>
                <span class="lt-popup__value">${busData.latitude.toFixed(5)}, ${busData.longitude.toFixed(5)}</span>
            </div>
            <div class="lt-popup__row">
                <span class="lt-popup__label">Last Updated</span>
                <span class="lt-popup__value">${lastUpdatedStr}</span>
            </div>
            <button class="${followBtnClass}" onclick="toggleFollow(${busData.id})">${followBtnText}</button>
        </div>`;
}

// ─── FOLLOW MODE ─────────────────────────────────────────────────────────────

/**
 * toggleFollow — Toggle follow mode for a specific bus.
 * Called from popup button (global scope needed).
 */
window.toggleFollow = function(busId) {
    if (followedBusId === busId) {
        clearFollowBus();
    } else {
        setFollowBus(busId);
    }
    // Refresh all open popups to reflect new follow state
    if (markers[busId]) {
        const entry = markers[busId];
        entry.marker.setPopupContent(renderPopup(entry.busData));
    }
    updateFollowIndicator();
};

/**
 * setFollowBus — Enable follow mode: map will center on this bus on every update.
 * @param {number} busId
 */
function setFollowBus(busId) {
    followedBusId = busId;
    // Immediately pan to the bus
    if (markers[busId]) {
        const { busData } = markers[busId];
        map.setView([busData.latitude, busData.longitude], Math.max(map.getZoom(), 15), { animate: true });
    }
}

/**
 * clearFollowBus — Disable follow mode; user can pan freely.
 */
function clearFollowBus() {
    followedBusId = null;
    updateFollowIndicator();
}

// ─── OFFLINE DETECTION ───────────────────────────────────────────────────────

/**
 * isOffline — Returns true if the bus hasn't sent an update in > OFFLINE_THRESHOLD seconds.
 * @param {string|null} lastUpdatedISO — ISO 8601 string from API
 * @returns {boolean}
 */
function isOffline(lastUpdatedISO) {
    if (!lastUpdatedISO) return true;
    const age = (Date.now() - new Date(lastUpdatedISO).getTime()) / 1000;
    return age > OFFLINE_THRESHOLD;
}

function applyOfflineStyle(marker, offline) {
    // Used when a bus vanishes from the API response but is < 5min old
    const busId = Object.keys(markers).find(id => markers[id].marker === marker);
    if (!busId) return;
    const entry = markers[busId];
    marker.setIcon(buildBusIcon(entry.busData.bus_number, offline));
}

// ─── INFO PANEL ──────────────────────────────────────────────────────────────

let _selectedBusId = null;

function getSelectedBusId() { return _selectedBusId; }

/**
 * onMarkerClick — Called when user clicks a bus marker.
 * Updates the side info panel.
 */
function onMarkerClick(busId) {
    _selectedBusId = busId;
    if (markers[busId]) updateInfoPanel(markers[busId].busData);
}

/**
 * updateInfoPanel — Refresh the right-side bus info panel DOM.
 * @param {Object} busData
 */
function updateInfoPanel(busData) {
    const panel = document.getElementById('lt-info-panel');
    if (!panel) return;

    const offline = isOffline(busData.last_updated);
    const statusHtml = offline
        ? '<span class="lt-info-badge lt-info-badge--offline">⚠ OFFLINE</span>'
        : '<span class="lt-info-badge lt-info-badge--online">● LIVE</span>';

    panel.innerHTML = `
        <div class="lt-info__header">
            <span class="lt-info__bus-icon">🚌</span>
            <div>
                <div class="lt-info__bus-num">${escapeHtml(busData.bus_number)}</div>
                ${statusHtml}
            </div>
        </div>
        <div class="lt-info__rows">
            <div class="lt-info__row"><span class="lt-info__label">Driver</span><span class="lt-info__val">${escapeHtml(busData.driver_name || 'N/A')}</span></div>
            <div class="lt-info__row"><span class="lt-info__label">Route</span><span class="lt-info__val">${escapeHtml(busData.route_code || 'N/A')}</span></div>
            <div class="lt-info__row"><span class="lt-info__label">Latitude</span><span class="lt-info__val">${busData.latitude.toFixed(6)}</span></div>
            <div class="lt-info__row"><span class="lt-info__label">Longitude</span><span class="lt-info__val">${busData.longitude.toFixed(6)}</span></div>
            <div class="lt-info__row"><span class="lt-info__label">Last Update</span><span class="lt-info__val">${formatTimestamp(busData.last_updated)}</span></div>
        </div>
        <div class="lt-info__actions">
            <button class="lt-info-btn lt-info-btn--center" onclick="centerOnBus(${busData.id})">🎯 Center Map</button>
            <button id="lt-follow-btn" class="lt-info-btn ${followedBusId === busData.id ? 'lt-info-btn--active' : 'lt-info-btn--follow'}"
                onclick="toggleFollow(${busData.id})">
                ${followedBusId === busData.id ? '📍 Unfollow' : '🎯 Follow Bus'}
            </button>
        </div>`;
}

/**
 * centerOnBus — Pan and zoom to a bus's current position.
 */
window.centerOnBus = function(busId) {
    if (markers[busId]) {
        const { busData } = markers[busId];
        map.setView([busData.latitude, busData.longitude], 16, { animate: true });
    }
};

// ─── BUS CARD GRID ───────────────────────────────────────────────────────────

/**
 * renderActiveBusCards — Render the bottom bus card grid.
 * Each card is clickable; shows online/offline status.
 */
function renderActiveBusCards(buses) {
    const container = document.getElementById('lt-bus-cards');
    if (!container) return;

    if (!buses.length) {
        container.innerHTML = '<p class="lt-no-buses">No active buses found. Add bus location data via the admin or driver app.</p>';
        return;
    }

    container.innerHTML = buses
        .filter(b => b.latitude != null)
        .map(b => {
            const offline = isOffline(b.last_updated);
            return `
                <div class="lt-card ${offline ? 'lt-card--offline' : 'lt-card--online'}"
                     onclick="selectBusCard(${b.id})" id="lt-card-${b.id}">
                    <div class="lt-card__icon">${offline ? '⚫' : '🟢'}</div>
                    <div class="lt-card__num">${escapeHtml(b.bus_number)}</div>
                    <div class="lt-card__route">${escapeHtml(b.route_code || 'N/A')}</div>
                    <div class="lt-card__driver">${escapeHtml(b.driver_name || 'N/A')}</div>
                    <div class="lt-card__status">${offline ? 'Offline' : 'Live'}</div>
                </div>`;
        })
        .join('');
}

/**
 * selectBusCard — Click handler for bus cards.
 * Centers map on bus, opens its popup, updates info panel.
 */
window.selectBusCard = function(busId) {
    _selectedBusId = busId;
    if (markers[busId]) {
        const entry = markers[busId];
        map.setView([entry.busData.latitude, entry.busData.longitude], 15, { animate: true });
        entry.marker.openPopup();
        updateInfoPanel(entry.busData);
    }
    // Highlight selected card
    document.querySelectorAll('.lt-card').forEach(c => c.classList.remove('lt-card--selected'));
    const card = document.getElementById(`lt-card-${busId}`);
    if (card) card.classList.add('lt-card--selected');
};

// ─── STATUS BAR ──────────────────────────────────────────────────────────────

function updateStatusBar(buses) {
    const onlineCount = buses.filter(b => b.latitude != null && !isOffline(b.last_updated)).length;
    const totalCount  = buses.filter(b => b.latitude != null).length;

    const el = document.getElementById('lt-status-count');
    if (el) el.textContent = `${onlineCount} / ${totalCount} buses live`;

    const timeEl = document.getElementById('lt-status-time');
    if (timeEl) timeEl.textContent = `Updated: ${new Date().toLocaleTimeString()}`;
}

function setStatusError() {
    const el = document.getElementById('lt-status-count');
    if (el) el.textContent = 'Connection error — retrying…';
}

function updateFollowIndicator() {
    const el = document.getElementById('lt-follow-indicator');
    if (!el) return;
    if (followedBusId && markers[followedBusId]) {
        const busNum = markers[followedBusId].busData.bus_number;
        el.textContent = `📍 Following: ${busNum}`;
        el.style.display = 'inline-block';
    } else {
        el.style.display = 'none';
    }
}

// ─── UTILITIES ────────────────────────────────────────────────────────────────

/**
 * formatTimestamp — Human-friendly relative or absolute time.
 * e.g. "Just now", "2 min ago", or "10:35:42 AM"
 */
function formatTimestamp(isoString) {
    if (!isoString) return 'Unknown';
    const d = new Date(isoString);
    const age = (Date.now() - d.getTime()) / 1000;
    if (age < 10)  return 'Just now';
    if (age < 60)  return `${Math.round(age)}s ago`;
    if (age < 3600) return `${Math.floor(age / 60)}m ${Math.round(age % 60)}s ago`;
    return d.toLocaleTimeString();
}

function escapeHtml(str) {
    if (typeof str !== 'string') return String(str ?? '');
    return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ─── BOOTSTRAP ───────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', initMap);
