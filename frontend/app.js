/**
 * Smart Surveillance System - Dashboard Application
 * Handles WebSocket connections, UI updates, and user interactions
 */

// ============================================================================
// Configuration
// ============================================================================

const CONFIG = {
    API_BASE: 'http://localhost:8000',
    WS_URL: 'ws://localhost:8000/ws/stream',
    REFRESH_INTERVAL: 30000, // 30 seconds
    MAX_LIVE_DETECTIONS: 10,
};

// ============================================================================
// Application State
// ============================================================================

const state = {
    websocket: null,
    isStreaming: false,
    currentView: 'dashboard',
    sessionDetections: 0,
    framesProcessed: 0,
    recentDetections: [],
    alertCount: 0,
};

// ============================================================================
// DOM Elements
// ============================================================================

const elements = {
    // Navigation
    navItems: document.querySelectorAll('.nav-item'),
    views: document.querySelectorAll('.view'),
    viewTitle: document.getElementById('viewTitle'),

    // Status
    connectionDot: document.getElementById('connectionDot'),
    connectionStatus: document.getElementById('connectionStatus'),
    uptime: document.getElementById('uptime'),
    fps: document.getElementById('fps'),
    alertBadge: document.getElementById('alertBadge'),

    // Dashboard Stats
    totalDetections: document.getElementById('totalDetections'),
    todayAlerts: document.getElementById('todayAlerts'),
    activeCameras: document.getElementById('activeCameras'),
    storageUsed: document.getElementById('storageUsed'),

    // Video
    dashboardPreview: document.getElementById('dashboardPreview'),
    dashboardOverlay: document.getElementById('dashboardOverlay'),
    liveStream: document.getElementById('liveStream'),
    liveOverlay: document.getElementById('liveOverlay'),

    // Lists
    recentAlertsList: document.getElementById('recentAlertsList'),
    liveDetections: document.getElementById('liveDetections'),
    alertsTableBody: document.getElementById('alertsTableBody'),
    evidenceGrid: document.getElementById('evidenceGrid'),

    // Session stats
    framesProcessed: document.getElementById('framesProcessed'),
    sessionDetections: document.getElementById('sessionDetections'),

    // Buttons
    refreshBtn: document.getElementById('refreshBtn'),
    startStreamBtn: document.getElementById('startStreamBtn'),
    saveSettingsBtn: document.getElementById('saveSettingsBtn'),
    testAlertBtn: document.getElementById('testAlertBtn'),

    // Settings
    confidenceSlider: document.getElementById('confidenceSlider'),
    confidenceValue: document.getElementById('confidenceValue'),
    alertsEnabled: document.getElementById('alertsEnabled'),
    cooldownInput: document.getElementById('cooldownInput'),

    // Modals
    alertModal: document.getElementById('alertModal'),
    evidenceModal: document.getElementById('evidenceModal'),
};

// ============================================================================
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initButtons();
    initSettings();
    updateCurrentDate();
    fetchStatus();
    fetchAlerts();
    fetchEvidence();

    // Set up refresh interval
    setInterval(fetchStatus, CONFIG.REFRESH_INTERVAL);
});

// ============================================================================
// Navigation
// ============================================================================

function initNavigation() {
    elements.navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const view = item.dataset.view;
            switchToView(view);
        });
    });
}

function switchToView(viewName) {
    // Update nav
    elements.navItems.forEach(item => {
        item.classList.toggle('active', item.dataset.view === viewName);
    });

    // Update views
    elements.views.forEach(view => {
        view.classList.toggle('active', view.id === `${viewName}View`);
    });

    // Update title
    const titles = {
        dashboard: 'Dashboard',
        live: 'Live Feed',
        alerts: 'Alerts',
        evidence: 'Evidence',
        settings: 'Settings',
    };
    elements.viewTitle.textContent = titles[viewName] || 'Dashboard';
    state.currentView = viewName;

    // Refresh data for specific views
    if (viewName === 'alerts') fetchAlerts();
    if (viewName === 'evidence') fetchEvidence();
}

// Make globally accessible
window.switchToView = switchToView;

// ============================================================================
// Buttons & Settings
// ============================================================================

function initButtons() {
    elements.refreshBtn.addEventListener('click', () => {
        fetchStatus();
        fetchAlerts();
        fetchEvidence();
    });

    elements.startStreamBtn.addEventListener('click', toggleStream);
    elements.saveSettingsBtn.addEventListener('click', saveSettings);
    elements.testAlertBtn.addEventListener('click', sendTestAlert);
}

function initSettings() {
    elements.confidenceSlider.addEventListener('input', (e) => {
        elements.confidenceValue.textContent = `${Math.round(e.target.value * 100)}%`;
    });
}

// ============================================================================
// WebSocket Connection
// ============================================================================

function connectWebSocket() {
    if (state.websocket && state.websocket.readyState === WebSocket.OPEN) {
        return;
    }

    updateConnectionStatus('connecting');
    state.websocket = new WebSocket(CONFIG.WS_URL);

    state.websocket.onopen = () => {
        console.log('✅ WebSocket connected');
        updateConnectionStatus('connected');
        state.isStreaming = true;
        updateStreamButton();
    };

    state.websocket.onmessage = (event) => {
        if (event.data instanceof Blob) {
            // Binary data = video frame
            handleVideoFrame(event.data);
        } else {
            // JSON data = detection or control message
            try {
                const data = JSON.parse(event.data);
                handleWebSocketMessage(data);
            } catch (e) {
                console.error('Failed to parse message:', e);
            }
        }
    };

    state.websocket.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
        updateConnectionStatus('error');
    };

    state.websocket.onclose = () => {
        console.log('🔌 WebSocket closed');
        updateConnectionStatus('disconnected');
        state.isStreaming = false;
        updateStreamButton();

        // Show overlay
        elements.dashboardOverlay.classList.remove('hidden');
        elements.liveOverlay.classList.remove('hidden');
    };
}

function disconnectWebSocket() {
    if (state.websocket) {
        state.websocket.send(JSON.stringify({ action: 'stop' }));
        state.websocket.close();
        state.websocket = null;
    }
    state.isStreaming = false;
    updateStreamButton();
}

function toggleStream() {
    if (state.isStreaming) {
        disconnectWebSocket();
    } else {
        connectWebSocket();
    }
}

function updateStreamButton() {
    if (state.isStreaming) {
        elements.startStreamBtn.innerHTML = '<span>⏹️</span> Stop Stream';
        elements.startStreamBtn.classList.add('btn-danger');
    } else {
        elements.startStreamBtn.innerHTML = '<span>▶️</span> Start Stream';
        elements.startStreamBtn.classList.remove('btn-danger');
    }
}

// ============================================================================
// Message Handlers
// ============================================================================

function handleVideoFrame(blob) {
    const url = URL.createObjectURL(blob);

    // Update both preview and live stream
    elements.dashboardPreview.src = url;
    elements.liveStream.src = url;

    // Hide overlays
    elements.dashboardOverlay.classList.add('hidden');
    elements.liveOverlay.classList.add('hidden');

    // Update frame count
    state.framesProcessed++;
    elements.framesProcessed.textContent = state.framesProcessed.toLocaleString();

    // Revoke old URLs to prevent memory leaks
    setTimeout(() => URL.revokeObjectURL(url), 100);
}

function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'detection':
            handleDetection(data.data);
            break;
        case 'error':
            console.error('Server error:', data.message);
            showNotification('Error', data.message, 'error');
            break;
        case 'status':
            updateStats(data.data);
            break;
    }
}

function handleDetection(detection) {
    // Update counts
    state.sessionDetections++;
    state.alertCount++;
    elements.sessionDetections.textContent = state.sessionDetections;
    elements.alertBadge.textContent = state.alertCount;

    // Add to recent detections
    state.recentDetections.unshift(detection);
    if (state.recentDetections.length > CONFIG.MAX_LIVE_DETECTIONS) {
        state.recentDetections.pop();
    }

    // Update live detection list
    updateLiveDetections();

    // Show alert modal for high-confidence detections
    if (detection.confidence >= 0.8) {
        showAlertModal(detection);
    }

    // Play alert sound
    playAlertSound();

    // Show notification
    showNotification(
        'Weapon Detected!',
        `${detection.class_name.toUpperCase()} detected with ${(detection.confidence * 100).toFixed(0)}% confidence`,
        'danger'
    );
}

function updateLiveDetections() {
    if (state.recentDetections.length === 0) {
        elements.liveDetections.innerHTML = `
            <div class="empty-state small">
                <span>Monitoring...</span>
            </div>
        `;
        return;
    }

    elements.liveDetections.innerHTML = state.recentDetections
        .map(det => `
            <div class="detection-item">
                <div class="detection-item-header">
                    <span class="detection-type">⚠️ ${det.class_name}</span>
                    <span class="detection-confidence">${(det.confidence * 100).toFixed(0)}%</span>
                </div>
                <div class="detection-time">${formatTime(det.timestamp)}</div>
            </div>
        `)
        .join('');
}

// ============================================================================
// API Calls
// ============================================================================

async function fetchStatus() {
    try {
        const response = await fetch(`${CONFIG.API_BASE}/api/status`);
        const data = await response.json();
        updateStats(data);
    } catch (error) {
        console.error('Failed to fetch status:', error);
    }
}

async function fetchAlerts() {
    try {
        const response = await fetch(`${CONFIG.API_BASE}/api/alerts?limit=50`);
        const data = await response.json();
        updateAlertsTable(data.alerts || []);
        updateRecentAlertsList(data.alerts || []);
    } catch (error) {
        console.error('Failed to fetch alerts:', error);
    }
}

async function fetchEvidence() {
    try {
        const response = await fetch(`${CONFIG.API_BASE}/api/detections?limit=50`);
        const data = await response.json();
        updateEvidenceGrid(data.detections || []);
    } catch (error) {
        console.error('Failed to fetch evidence:', error);
    }
}

async function saveSettings() {
    const settings = {
        confidence_threshold: parseFloat(elements.confidenceSlider.value),
        alerts_enabled: elements.alertsEnabled.checked,
        cooldown_seconds: parseInt(elements.cooldownInput.value),
    };

    try {
        const response = await fetch(`${CONFIG.API_BASE}/api/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings),
        });

        if (response.ok) {
            showNotification('Settings Saved', 'Configuration updated successfully', 'success');
        } else {
            throw new Error('Failed to save settings');
        }
    } catch (error) {
        console.error('Failed to save settings:', error);
        showNotification('Error', 'Failed to save settings', 'error');
    }
}

async function sendTestAlert() {
    try {
        const response = await fetch(`${CONFIG.API_BASE}/api/alerts/test`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ weapon_type: 'gun' }),
        });

        const result = await response.json();

        if (result.triggered) {
            showNotification('Test Alert Sent', 'Alert sent successfully', 'success');
        } else {
            showNotification('Alert Not Sent', result.reason || 'Unknown error', 'warning');
        }
    } catch (error) {
        console.error('Failed to send test alert:', error);
        showNotification('Error', 'Failed to send test alert', 'error');
    }
}

// ============================================================================
// UI Updates
// ============================================================================

function updateConnectionStatus(status) {
    const dot = elements.connectionDot;
    const text = elements.connectionStatus;

    dot.classList.remove('connected', 'error');

    switch (status) {
        case 'connected':
            dot.classList.add('connected');
            text.textContent = 'Connected';
            break;
        case 'connecting':
            text.textContent = 'Connecting...';
            break;
        case 'disconnected':
            text.textContent = 'Disconnected';
            break;
        case 'error':
            dot.classList.add('error');
            text.textContent = 'Connection Error';
            break;
    }
}

function updateStats(data) {
    if (data.detection_count !== undefined) {
        elements.totalDetections.textContent = data.detection_count.toLocaleString();
    }

    if (data.alerts?.alert_count !== undefined) {
        elements.todayAlerts.textContent = data.alerts.alert_count;
    }

    if (data.uptime) {
        elements.uptime.textContent = data.uptime;
    }

    if (data.video?.current_fps !== undefined) {
        elements.fps.textContent = data.video.current_fps;
    }

    if (data.storage?.storage_size_mb !== undefined) {
        elements.storageUsed.textContent = `${data.storage.storage_size_mb} MB`;
    }

    // Update settings values
    if (data.config?.confidence_threshold !== undefined) {
        elements.confidenceSlider.value = data.config.confidence_threshold;
        elements.confidenceValue.textContent = `${Math.round(data.config.confidence_threshold * 100)}%`;
    }

    if (data.alerts?.enabled !== undefined) {
        elements.alertsEnabled.checked = data.alerts.enabled;
    }

    if (data.alerts?.cooldown_seconds !== undefined) {
        elements.cooldownInput.value = data.alerts.cooldown_seconds;
    }
}

function updateAlertsTable(alerts) {
    if (alerts.length === 0) {
        elements.alertsTableBody.innerHTML = `
            <tr>
                <td colspan="6" class="empty-cell">No alerts recorded</td>
            </tr>
        `;
        return;
    }

    elements.alertsTableBody.innerHTML = alerts
        .map(alert => `
            <tr>
                <td>${formatDateTime(alert.timestamp)}</td>
                <td><span class="weapon-badge ${alert.weapon_type}">${alert.weapon_type}</span></td>
                <td>${(alert.confidence * 100).toFixed(0)}%</td>
                <td>${alert.location}</td>
                <td>${alert.channels.map(c => `<span class="channel-badge">${c}</span>`).join('')}</td>
                <td>
                    ${alert.evidence_path ?
                `<button class="btn btn-ghost btn-sm" onclick="viewEvidenceById('${alert.evidence_path}')">View</button>` :
                '-'}
                </td>
            </tr>
        `)
        .join('');
}

function updateRecentAlertsList(alerts) {
    const recent = alerts.slice(0, 5);

    if (recent.length === 0) {
        elements.recentAlertsList.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">✅</span>
                <span>No recent alerts</span>
            </div>
        `;
        return;
    }

    elements.recentAlertsList.innerHTML = recent
        .map(alert => `
            <div class="alert-item danger">
                <span class="alert-item-icon">🚨</span>
                <div class="alert-item-content">
                    <div class="alert-item-title">${alert.weapon_type.toUpperCase()} Detected</div>
                    <div class="alert-item-meta">${formatTime(alert.timestamp)} · ${(alert.confidence * 100).toFixed(0)}% · ${alert.location}</div>
                </div>
            </div>
        `)
        .join('');
}

function updateEvidenceGrid(evidence) {
    if (evidence.length === 0) {
        elements.evidenceGrid.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">📁</span>
                <span>No evidence collected yet</span>
            </div>
        `;
        return;
    }

    elements.evidenceGrid.innerHTML = evidence
        .map(item => `
            <div class="evidence-card" onclick="showEvidenceModal('${item.id}')">
                <img class="evidence-thumb" src="${CONFIG.API_BASE}/api/evidence/${item.id}?annotated=true" 
                     alt="${item.weapon_type}" loading="lazy">
                <div class="evidence-info">
                    <div class="evidence-type">${item.weapon_type}</div>
                    <div class="evidence-meta">${formatDateTime(item.timestamp)}</div>
                    <div class="evidence-meta">${(item.confidence * 100).toFixed(0)}% confidence</div>
                </div>
            </div>
        `)
        .join('');
}

function updateCurrentDate() {
    const now = new Date();
    document.getElementById('currentDate').textContent = now.toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

// ============================================================================
// Modals
// ============================================================================

function showAlertModal(detection) {
    document.getElementById('alertWeaponType').textContent = detection.class_name.toUpperCase();
    document.getElementById('alertConfidence').textContent = `${(detection.confidence * 100).toFixed(0)}%`;
    document.getElementById('alertLocation').textContent = 'Camera 1';
    document.getElementById('alertTime').textContent = formatTime(detection.timestamp);

    // Set the detection image - use the current live stream frame
    const alertImage = document.getElementById('alertImage');
    if (alertImage && elements.liveStream.src) {
        alertImage.src = elements.liveStream.src;
    }

    elements.alertModal.classList.add('active');
}

function closeModal() {
    elements.alertModal.classList.remove('active');
}

function showEvidenceModal(evidenceId) {
    const img = document.getElementById('evidenceModalImage');
    img.src = `${CONFIG.API_BASE}/api/evidence/${evidenceId}?annotated=true`;
    elements.evidenceModal.classList.add('active');
}

function closeEvidenceModal() {
    elements.evidenceModal.classList.remove('active');
}

function viewEvidence() {
    closeModal();
    switchToView('evidence');
}

// Make modal functions globally accessible
window.closeModal = closeModal;
window.closeEvidenceModal = closeEvidenceModal;
window.showEvidenceModal = showEvidenceModal;
window.viewEvidence = viewEvidence;

// ============================================================================
// Utilities
// ============================================================================

function formatTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

function formatDateTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function showNotification(title, message, type = 'info') {
    // Browser notification if supported
    if ('Notification' in window && Notification.permission === 'granted') {
        new Notification(title, {
            body: message,
            icon: type === 'danger' ? '🚨' : '🛡️'
        });
    }

    // Console log
    const icons = { danger: '🚨', warning: '⚠️', success: '✅', info: 'ℹ️' };
    console.log(`${icons[type] || 'ℹ️'} ${title}: ${message}`);
}

function playAlertSound() {
    // Create oscillator for alert beep
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);

        oscillator.frequency.value = 800;
        oscillator.type = 'sine';
        gainNode.gain.value = 0.1;

        oscillator.start();

        setTimeout(() => {
            oscillator.stop();
            audioContext.close();
        }, 200);
    } catch (e) {
        // Audio not supported
    }
}

// Request notification permission
if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
}
