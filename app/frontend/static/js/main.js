// AgentMove Demo - Main JavaScript

// API Configuration
const API_BASE = '';  // Same origin

// Global State
let map = null;
let markers = [];
let polyline = null;
let currentCity = 'Shanghai';
let currentTrajectory = null;
let customTrajectoryPoints = []; // For custom trajectory creation
let customPointMarkers = []; // Markers for custom trajectory points
let currentInputMode = 'map'; // 'map', 'form', or 'json'
let selectedUserId = null; // Currently selected user for browsing

// Map center coordinates
const MAP_CENTERS = {
    'Shanghai': [31.2304, 121.4737],
    'Beijing': [39.9042, 116.4074],
    'Tokyo': [35.6762, 139.6503],
    'NewYork': [40.7128, -74.0060],
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', function () {
    initializeMap();
    checkHealth();
    loadTrajectories();
    setupEventListeners();
});

// Initialize Leaflet Map
function initializeMap() {
    const center = MAP_CENTERS[currentCity];
    map = L.map('map').setView(center, 12);

    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19
    }).addTo(map);

    console.log('Map initialized');
}

// Check API health
async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE}/api/health`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();

        const statusIndicator = document.getElementById('status-indicator');
        if (data.status === 'healthy' && data.agent_loaded) {
            statusIndicator.textContent = '🟢 已连接';
            statusIndicator.classList.add('connected');
        } else {
            statusIndicator.textContent = '🟡 部分可用';
        }

        console.log('Health check:', data);
    } catch (error) {
        console.error('Health check failed:', error);
        const statusIndicator = document.getElementById('status-indicator');
        if (statusIndicator) {
            statusIndicator.textContent = '🔴 连接失败';
        }
        showNotification(`健康检查失败: ${error.message}`, 'error');
    }
}

// Load available trajectories
async function loadTrajectories() {
    try {
        const response = await fetch(`${API_BASE}/api/trajectories/${currentCity}?limit=20`);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        const select = document.getElementById('trajectory-select');
        select.innerHTML = '<option value="">-- 选择一个轨迹 --</option>';

        if (data.success && data.trajectories) {
            data.trajectories.forEach(traj => {
                const option = document.createElement('option');
                option.value = `${traj.user_id}|${traj.traj_id}`;
                option.textContent = `用户 ${traj.user_id} - 轨迹 ${traj.traj_id} (${traj.length} 点)`;
                select.appendChild(option);
            });
        } else if (!data.success) {
            throw new Error(data.message || data.error || '加载轨迹失败');
        }

        console.log('Trajectories loaded:', data.count || 0);
    } catch (error) {
        console.error('Failed to load trajectories:', error);
        showNotification(`加载轨迹失败: ${error.message}`, 'error');
    }
}

// Setup event listeners
function setupEventListeners() {
    // City change
    document.getElementById('city-select').addEventListener('change', function (e) {
        currentCity = e.target.value;
        const center = MAP_CENTERS[currentCity];
        map.setView(center, 12);
        loadTrajectories();
        clearMapData();
        // Reset user list when city changes
        selectedUserId = null;
        document.getElementById('user-list-container').style.display = 'none';
        document.getElementById('trajectory-list-container').style.display = 'none';
    });

    // Model change
    document.getElementById('model-select').addEventListener('change', function (e) {
        console.log('Model changed to:', e.target.value);
    });

    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const tabName = this.dataset.tab;
            switchTab(tabName);
        });
    });

    // Input mode switching
    document.querySelectorAll('.input-mode-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const mode = this.dataset.mode;
            switchInputMode(mode);
        });
    });

    // Load users button
    document.getElementById('load-users-btn').addEventListener('click', loadUsers);

    // User search
    const userSearch = document.getElementById('user-search');
    let searchTimeout;
    userSearch.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            loadUsers();
        }, 500);
    });

    // Load trajectory
    document.getElementById('load-trajectory-btn').addEventListener('click', loadSelectedTrajectory);

    // Random trajectory
    document.getElementById('random-trajectory-btn').addEventListener('click', function () {
        const select = document.getElementById('trajectory-select');
        const options = select.options;
        if (options.length > 1) {
            const randomIndex = Math.floor(Math.random() * (options.length - 1)) + 1;
            select.selectedIndex = randomIndex;
            loadSelectedTrajectory();
        }
    });

    // Predict button
    document.getElementById('predict-btn').addEventListener('click', runPrediction);

    // Example button
    document.getElementById('example-btn').addEventListener('click', loadExample);

    // Custom trajectory buttons
    document.getElementById('clear-custom-trajectory-btn').addEventListener('click', clearCustomTrajectory);
    document.getElementById('add-point-form-btn').addEventListener('click', addFormPoint);
    document.getElementById('validate-json-btn').addEventListener('click', validateJSON);
    document.getElementById('import-json-btn').addEventListener('click', importJSON);
    document.getElementById('preview-custom-trajectory-btn').addEventListener('click', previewCustomTrajectory);
    document.getElementById('save-custom-trajectory-btn').addEventListener('click', saveCustomTrajectory);

    // Map click for adding points (will be handled dynamically)
    setupMapClickHandler();
}

// Setup map click handler
let mapClickHandler = null;

function setupMapClickHandler() {
    // Remove existing handler if any
    if (mapClickHandler) {
        map.off('click', mapClickHandler);
    }
    
    // Add new handler
    mapClickHandler = function(e) {
        const createTab = document.getElementById('create-tab');
        if (createTab.classList.contains('active') && currentInputMode === 'map') {
            addPointFromMap(e.latlng);
        }
    };
    
    map.on('click', mapClickHandler);
}

// Tab switching
function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}-tab`).classList.add('active');

    // Clear custom trajectory when switching to browse tab
    if (tabName === 'browse') {
        clearCustomTrajectory();
    }
    
    // Re-setup map click handler
    setupMapClickHandler();
}

// Input mode switching
function switchInputMode(mode) {
    currentInputMode = mode;
    
    // Update buttons
    document.querySelectorAll('.input-mode-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-mode="${mode}"]`).classList.add('active');

    // Update content
    document.querySelectorAll('.input-mode-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`input-mode-${mode}`).classList.add('active');
    
    // Re-setup map click handler
    setupMapClickHandler();
}

// Load users list
async function loadUsers() {
    const btn = document.getElementById('load-users-btn');
    const originalText = btn ? btn.textContent : '';
    
    try {
        // Set loading state
        if (btn) {
            btn.disabled = true;
            btn.textContent = '加载中...';
        }
        
        const search = document.getElementById('user-search').value || null;
        const minLength = document.getElementById('trajectory-filter-min').value || null;
        const maxLength = document.getElementById('trajectory-filter-max').value || null;

        const params = new URLSearchParams();
        if (search) params.append('search', search);
        params.append('limit', '50');

        const response = await fetch(`${API_BASE}/api/users/${currentCity}?${params}`);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.message || data.error || '加载用户列表失败');
        }

        displayUserList(data.users);
        showNotification(`加载了 ${data.count} 个用户`, 'success');
    } catch (error) {
        console.error('Failed to load users:', error);
        showNotification(`加载用户列表失败: ${error.message}`, 'error');
    } finally {
        // Restore button state
        if (btn) {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    }
}

// Display user list
function displayUserList(users) {
    const container = document.getElementById('user-list');
    container.innerHTML = '';

    if (users.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: var(--text-secondary);">未找到用户</p>';
        document.getElementById('user-list-container').style.display = 'none';
        return;
    }

    document.getElementById('user-list-container').style.display = 'block';

    users.forEach(user => {
        const userCard = document.createElement('div');
        userCard.className = 'user-card';
        userCard.dataset.userId = user.user_id;
        userCard.innerHTML = `
            <div class="user-card-header">
                <span class="user-id">用户 ${user.user_id}</span>
                <span class="traj-count">${user.trajectory_count} 条轨迹</span>
            </div>
            <div class="user-stats">
                平均长度: ${user.avg_trajectory_length} 点 | 
                范围: ${user.min_length}-${user.max_length} 点
            </div>
        `;
        userCard.addEventListener('click', () => loadUserTrajectories(user.user_id));
        container.appendChild(userCard);
    });
}

// Load trajectories for a specific user
async function loadUserTrajectories(userId) {
    try {
        selectedUserId = userId;
        
        // Update selected user in UI
        document.querySelectorAll('.user-card').forEach(card => {
            card.classList.remove('selected');
        });
        document.querySelector(`[data-user-id="${userId}"]`).classList.add('selected');

        const response = await fetch(`${API_BASE}/api/user/${currentCity}/${userId}/trajectories`);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.message || data.error || '加载用户轨迹失败');
        }

        displayTrajectoryList(data.trajectories, userId);
        document.getElementById('selected-user-name').textContent = `(用户 ${userId})`;
        document.getElementById('trajectory-list-container').style.display = 'block';
        showNotification(`加载了 ${data.count} 条轨迹`, 'success');
    } catch (error) {
        console.error('Failed to load user trajectories:', error);
        showNotification(`加载用户轨迹失败: ${error.message}`, 'error');
    }
}

// Display trajectory list
function displayTrajectoryList(trajectories, userId) {
    const container = document.getElementById('trajectory-list');
    container.innerHTML = '';

    if (trajectories.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: var(--text-secondary);">该用户没有轨迹</p>';
        return;
    }

    trajectories.forEach(traj => {
        const trajCard = document.createElement('div');
        trajCard.className = 'trajectory-card';
        trajCard.dataset.userId = userId;
        trajCard.dataset.trajId = traj.traj_id;
        
        const timeRangeText = traj.time_range 
            ? `${traj.time_range.start} - ${traj.time_range.end}`
            : '时间未知';

        trajCard.innerHTML = `
            <div class="trajectory-card-header">
                <span class="traj-id">轨迹 ${traj.traj_id}</span>
                <span class="traj-length">${traj.length} 点</span>
            </div>
            <div class="traj-time-range">${timeRangeText}</div>
        `;
        trajCard.addEventListener('click', () => {
            loadTrajectoryDetail(userId, traj.traj_id);
        });
        container.appendChild(trajCard);
    });
}

// Load trajectory detail (from browse tab)
async function loadTrajectoryDetail(userId, trajId) {
    try {
        showLoading(true);
        const response = await fetch(`${API_BASE}/api/trajectory/${currentCity}/${userId}/${trajId}`);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.message || data.error || '加载轨迹详情失败');
        }

        currentTrajectory = data.trajectory;
        displayTrajectory(data.trajectory);
        showNotification('轨迹加载成功', 'success');
        // Switch to browse tab if not already there
        switchTab('browse');
    } catch (error) {
        console.error('Failed to load trajectory:', error);
        showNotification(`加载轨迹详情失败: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

// Load selected trajectory
async function loadSelectedTrajectory() {
    const btn = document.getElementById('load-trajectory-btn');
    const originalText = btn ? btn.textContent : '';
    const select = document.getElementById('trajectory-select');
    const value = select.value;

    if (!value) {
        showNotification('请先选择一个轨迹', 'warning');
        return;
    }

    const [userId, trajId] = value.split('|');

    try {
        // Set loading state
        if (btn) {
            btn.disabled = true;
            btn.textContent = '加载中...';
        }
        showLoading(true);
        const response = await fetch(`${API_BASE}/api/trajectory/${currentCity}/${userId}/${trajId}`);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.message || data.error || '加载轨迹详情失败');
        }

        currentTrajectory = data.trajectory;
        displayTrajectory(data.trajectory);
        showNotification('轨迹加载成功', 'success');
    } catch (error) {
        console.error('Failed to load trajectory:', error);
        showNotification(`加载轨迹详情失败: ${error.message}`, 'error');
    } finally {
        showLoading(false);
        // Restore button state
        if (btn) {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    }
}

// Display trajectory on map
function displayTrajectory(trajectory) {
    clearMapData();

    const points = trajectory.trajectory_points;
    if (!points || points.length === 0) return;

    // Draw trajectory line
    const latlngs = points.map(p => [p.latitude, p.longitude]);
    polyline = L.polyline(latlngs, {
        color: '#3388ff',
        weight: 3,
        opacity: 0.7
    }).addTo(map);

    // Add markers for each point
    points.forEach((point, index) => {
        const marker = L.circleMarker([point.latitude, point.longitude], {
            radius: 8,
            fillColor: '#3388ff',
            color: '#fff',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.8
        }).addTo(map);

        // Add popup
        const popupContent = `
            <div class="popup-content">
                <h4>轨迹点 ${index + 1}</h4>
                <p><strong>时间:</strong> ${point.timestamp}</p>
                <p><strong>类别:</strong> ${point.category || 'Unknown'}</p>
                <p><strong>停留时长:</strong> ${point.duration} 分钟</p>
                ${point.venue_id ? `<p><strong>地点 ID:</strong> ${point.venue_id}</p>` : ''}
            </div>
        `;
        marker.bindPopup(popupContent);

        markers.push(marker);
    });

    // Fit map to trajectory bounds
    map.fitBounds(polyline.getBounds(), { padding: [50, 50] });

    console.log('Trajectory displayed:', points.length, 'points');
}

// Run prediction
async function runPrediction() {
    if (!currentTrajectory) {
        showNotification('请先加载一个轨迹', 'warning');
        return;
    }

    const modelSelect = document.getElementById('model-select');
    const modelName = modelSelect.value;
    const platform = modelSelect.options[modelSelect.selectedIndex].parentElement.label || 'SiliconFlow';
    const promptType = document.getElementById('prompt-select').value;

    const requestData = {
        city_name: currentCity,
        model_name: modelName,
        platform: platform.split(' ')[0],  // Remove (免费) etc.
        prompt_type: promptType,
        user_id: currentTrajectory.user_id,
        traj_id: currentTrajectory.traj_id
    };

    try {
        showLoading(true);
        document.getElementById('results-section').style.display = 'none';

        console.log('Sending prediction request:', requestData);

        const response = await fetch(`${API_BASE}/api/predict`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || errorData.error || `HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        console.log('Prediction response:', data);

        if (!data.success) {
            // Display detailed error information
            let errorMessage = data.message || data.error || '预测失败';
            
            if (data.error_type) {
                errorMessage += ` (${data.error_type})`;
            }

            if (data.details && data.details.traceback) {
                console.error('Prediction failed with details:', data);
            }

            throw new Error(errorMessage);
        }

        displayPredictionResults(data.prediction);
        showNotification('预测完成', 'success');
    } catch (error) {
        console.error('Prediction request failed:', error);

        let errorMessage = '预测请求失败\n\n';
        errorMessage += `错误: ${error.message}\n`;
        errorMessage += `\n请检查:\n`;
        errorMessage += `1. 服务器是否正常运行\n`;
        errorMessage += `2. API keys 是否配置正确\n`;
        errorMessage += `3. 数据是否已处理完成\n`;
        errorMessage += `\n查看浏览器控制台和服务器日志获取更多信息`;

        alert(errorMessage);
        showNotification('预测失败: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// Display prediction results
function displayPredictionResults(prediction) {
    // Show results section
    document.getElementById('results-section').style.display = 'block';

    // Update values
    document.getElementById('prediction-venue').textContent = prediction.prediction.venue_id || 'N/A';
    document.getElementById('ground-truth-venue').textContent = prediction.ground_truth.venue_id || 'N/A';

    // Check if prediction is correct
    const isCorrect = prediction.prediction.venue_id == prediction.ground_truth.venue_id;
    const matchElement = document.getElementById('prediction-match');
    matchElement.textContent = isCorrect ? '✓ 预测正确!' : '✗ 预测错误';
    matchElement.className = 'result-match ' + (isCorrect ? 'correct' : 'incorrect');

    // Display reasoning
    document.getElementById('prediction-reason').textContent =
        prediction.prediction.explanation || '无推理说明';

    // Display module outputs if available
    if (prediction.module_outputs) {
        document.getElementById('memory-output').textContent =
            JSON.stringify(prediction.module_outputs.memory, null, 2) || 'N/A';
        document.getElementById('spatial-output').textContent =
            JSON.stringify(prediction.module_outputs.spatial_world, null, 2) || 'N/A';
        document.getElementById('social-output').textContent =
            JSON.stringify(prediction.module_outputs.social_world, null, 2) || 'N/A';
    }

    // Add prediction and ground truth markers to map
    addPredictionMarkers(prediction);

    // Scroll to results
    document.getElementById('results-section').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Add prediction and ground truth markers
function addPredictionMarkers(prediction) {
    const gt = prediction.ground_truth;

    if (gt.latitude && gt.longitude) {
        // Ground truth marker (green)
        const gtMarker = L.marker([gt.latitude, gt.longitude], {
            icon: L.divIcon({
                className: 'custom-marker',
                html: '🟢',
                iconSize: [30, 30]
            })
        }).addTo(map);

        gtMarker.bindPopup(`
            <div class="popup-content">
                <h4>真实位置</h4>
                <p><strong>地点 ID:</strong> ${gt.venue_id}</p>
                <p><strong>地址:</strong> ${gt.address || 'N/A'}</p>
            </div>
        `);

        markers.push(gtMarker);

        // If prediction has coordinates (might need to look up), add prediction marker
        // For now, just use ground truth location with different color if correct/incorrect
        const isCorrect = prediction.prediction.venue_id == gt.venue_id;
        if (!isCorrect) {
            // Add a red marker near the last trajectory point to indicate wrong prediction
            const lastPoint = currentTrajectory.trajectory_points[currentTrajectory.trajectory_points.length - 1];
            const predMarker = L.marker([lastPoint.latitude + 0.01, lastPoint.longitude + 0.01], {
                icon: L.divIcon({
                    className: 'custom-marker',
                    html: '🔴',
                    iconSize: [30, 30]
                })
            }).addTo(map);

            predMarker.bindPopup(`
                <div class="popup-content">
                    <h4>预测位置</h4>
                    <p><strong>地点 ID:</strong> ${prediction.prediction.venue_id}</p>
                    <p>(实际位置可能不同)</p>
                </div>
            `);

            markers.push(predMarker);
        }
    }
}

// Load example prediction
async function loadExample() {
    const btn = document.getElementById('example-btn');
    const originalText = btn ? btn.textContent : '';
    
    try {
        // Set loading state
        if (btn) {
            btn.disabled = true;
            btn.textContent = '加载中...';
        }
        showLoading(true);

        const response = await fetch(`${API_BASE}/api/example`);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.message || data.error || '加载示例失败');
        }

        // Display example trajectory
        const exampleTraj = data.prediction.context_trajectory;
        const exampleData = {
            trajectory_points: exampleTraj.map((point, index) => ({
                timestamp: point.time,
                latitude: point.lat,
                longitude: point.lng,
                category: point.venue || 'Example',
                duration: 30,
                venue_id: index + 1,
                index: index
            })),
            user_id: 'example_user',
            traj_id: '1'
        };

        currentTrajectory = exampleData;
        displayTrajectory(exampleData);

        // Display prediction results
        displayPredictionResults(data.prediction);

            showNotification('示例加载成功 (演示数据)', 'success');
    } catch (error) {
        console.error('Failed to load example:', error);
        showNotification(`加载示例失败: ${error.message}`, 'error');
    } finally {
        showLoading(false);
        // Restore button state
        if (btn) {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    }
}

// Clear map data
function clearMapData() {
    markers.forEach(marker => map.removeLayer(marker));
    markers = [];

    if (polyline) {
        map.removeLayer(polyline);
        polyline = null;
    }

    document.getElementById('results-section').style.display = 'none';
}

// Show/hide loading indicator
function showLoading(show) {
    document.getElementById('loading-indicator').style.display = show ? 'block' : 'none';
    document.getElementById('predict-btn').disabled = show;
}

// Toast Notification System
function createToastContainer() {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    return container;
}

function showNotification(message, type = 'info') {
    const icons = {
        success: '✓',
        error: '✗',
        warning: '⚠',
        info: 'ℹ'
    };

    const icon = icons[type] || 'ℹ';
    
    // Also log to console for debugging
    console.log(`${icon} ${message}`);

    // Create toast container if it doesn't exist
    const container = createToastContainer();

    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${icon}</span>
        <span class="toast-content">${message}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;

    // Add to container
    container.appendChild(toast);

    // Auto remove after 5 seconds
    setTimeout(() => {
        if (toast.parentElement) {
            toast.classList.add('slide-out');
            setTimeout(() => {
                if (toast.parentElement) {
                    toast.remove();
                }
            }, 300);
        }
    }, 5000);
}

// Utility: Format JSON for display
function formatJSON(obj) {
    try {
        return JSON.stringify(obj, null, 2);
    } catch (e) {
        return String(obj);
    }
}

// ========== Custom Trajectory Creation Functions ==========

// Add point from map click
function addPointFromMap(latlng) {
    const point = {
        timestamp: new Date().toISOString(),
        latitude: latlng.lat,
        longitude: latlng.lng,
        category: 'Unknown',
        venue_id: null,
        address: ''
    };
    
    customTrajectoryPoints.push(point);
    updateCustomPointsList();
    addCustomPointMarker(latlng, customTrajectoryPoints.length - 1);
}

// Add custom point marker to map
function addCustomPointMarker(latlng, index) {
    const marker = L.marker(latlng, {
        icon: L.divIcon({
            className: 'custom-marker',
            html: `<div style="background: #ff6b6b; color: white; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; font-weight: bold; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);">${index + 1}</div>`,
            iconSize: [24, 24]
        })
    }).addTo(map);

    marker.bindPopup(`
        <div class="popup-content">
            <h4>轨迹点 ${index + 1}</h4>
            <p><strong>纬度:</strong> ${latlng.lat.toFixed(6)}</p>
            <p><strong>经度:</strong> ${latlng.lng.toFixed(6)}</p>
            <button onclick="editCustomPoint(${index})" style="margin-top: 5px; padding: 5px 10px;">编辑</button>
            <button onclick="deleteCustomPoint(${index})" style="margin-top: 5px; padding: 5px 10px; background: #ef4444;">删除</button>
        </div>
    `);

    customPointMarkers.push(marker);
    updateCustomTrajectoryPolyline();
}

// Update custom points list display
function updateCustomPointsList() {
    const container = document.getElementById('custom-points-list');
    container.innerHTML = '';

    customTrajectoryPoints.forEach((point, index) => {
        const item = document.createElement('div');
        item.className = 'custom-point-item';
        item.innerHTML = `
            <div class="point-info">
                <strong>点 ${index + 1}</strong>: 
                ${point.latitude.toFixed(4)}, ${point.longitude.toFixed(4)}<br>
                <small>${point.category} | ${new Date(point.timestamp).toLocaleString()}</small>
            </div>
            <div class="point-actions">
                <button class="btn btn-secondary" onclick="editCustomPoint(${index})">编辑</button>
                <button class="btn btn-secondary" onclick="deleteCustomPoint(${index})" style="background: #ef4444;">删除</button>
            </div>
        `;
        container.appendChild(item);
    });
}

// Edit custom point
window.editCustomPoint = function(index) {
    const point = customTrajectoryPoints[index];
    const category = prompt('输入地点类别:', point.category || 'Unknown');
    if (category !== null) {
        point.category = category;
        const venueId = prompt('输入地点ID (可选，留空跳过):', point.venue_id || '');
        if (venueId !== null) {
            point.venue_id = venueId ? parseInt(venueId) : null;
        }
        const address = prompt('输入地址 (可选，留空跳过):', point.address || '');
        if (address !== null) {
            point.address = address;
        }
        updateCustomPointsList();
    }
};

// Delete custom point
window.deleteCustomPoint = function(index) {
    if (confirm(`确定要删除点 ${index + 1} 吗？`)) {
        // Remove marker
        if (customPointMarkers[index]) {
            map.removeLayer(customPointMarkers[index]);
        }
        customPointMarkers.splice(index, 1);
        customTrajectoryPoints.splice(index, 1);
        
        // Re-index remaining markers
        customPointMarkers.forEach((marker, i) => {
            marker.setIcon(L.divIcon({
                className: 'custom-marker',
                html: `<div style="background: #ff6b6b; color: white; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; font-weight: bold; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);">${i + 1}</div>`,
                iconSize: [24, 24]
            }));
        });
        
        updateCustomPointsList();
        updateCustomTrajectoryPolyline();
    }
};

// Update custom trajectory polyline
function updateCustomTrajectoryPolyline() {
    if (polyline) {
        map.removeLayer(polyline);
    }
    
    if (customTrajectoryPoints.length > 1) {
        const latlngs = customTrajectoryPoints.map(p => [p.latitude, p.longitude]);
        polyline = L.polyline(latlngs, {
            color: '#ff6b6b',
            weight: 3,
            opacity: 0.7
        }).addTo(map);
        map.fitBounds(polyline.getBounds(), { padding: [50, 50] });
    }
}

// Clear custom trajectory
function clearCustomTrajectory() {
    customTrajectoryPoints = [];
    customPointMarkers.forEach(marker => map.removeLayer(marker));
    customPointMarkers = [];
    if (polyline) {
        map.removeLayer(polyline);
        polyline = null;
    }
    updateCustomPointsList();
    document.getElementById('form-points-container').innerHTML = '';
    document.getElementById('json-input').value = '';
    document.getElementById('json-validation-result').innerHTML = '';
}

// Add form point
function addFormPoint() {
    const container = document.getElementById('form-points-container');
    const index = customTrajectoryPoints.length;
    
    const pointItem = document.createElement('div');
    pointItem.className = 'form-point-item';
    pointItem.innerHTML = `
        <h5>
            轨迹点 ${index + 1}
            <button class="btn btn-secondary" onclick="removeFormPoint(${index})" style="padding: 0.25rem 0.75rem; font-size: 0.8rem; background: #ef4444;">删除</button>
        </h5>
        <div class="form-group">
            <label>时间戳</label>
            <input type="datetime-local" id="point-${index}-timestamp" class="form-control" value="${new Date().toISOString().slice(0, 16)}">
        </div>
        <div class="form-group">
            <label>纬度</label>
            <input type="number" id="point-${index}-latitude" class="form-control" step="any" placeholder="31.2304">
        </div>
        <div class="form-group">
            <label>经度</label>
            <input type="number" id="point-${index}-longitude" class="form-control" step="any" placeholder="121.4737">
        </div>
        <div class="form-group">
            <label>地点类别</label>
            <input type="text" id="point-${index}-category" class="form-control" placeholder="Residence, Office, Restaurant...">
        </div>
        <div class="form-group">
            <label>地点ID (可选)</label>
            <input type="number" id="point-${index}-venue_id" class="form-control" placeholder="1">
        </div>
        <div class="form-group">
            <label>地址 (可选)</label>
            <input type="text" id="point-${index}-address" class="form-control" placeholder="Pudong, Lujiazui, Home, Century Avenue">
        </div>
    `;
    container.appendChild(pointItem);
}

// Remove form point
window.removeFormPoint = function(index) {
    const container = document.getElementById('form-points-container');
    const items = container.querySelectorAll('.form-point-item');
    if (items[index]) {
        items[index].remove();
        // Re-index remaining items
        updateFormPointsIndexing();
    }
};

// Update form points indexing
function updateFormPointsIndexing() {
    const container = document.getElementById('form-points-container');
    const items = container.querySelectorAll('.form-point-item');
    items.forEach((item, index) => {
        const h5 = item.querySelector('h5');
        h5.innerHTML = `
            轨迹点 ${index + 1}
            <button class="btn btn-secondary" onclick="removeFormPoint(${index})" style="padding: 0.25rem 0.75rem; font-size: 0.8rem; background: #ef4444;">删除</button>
        `;
        // Update input IDs
        item.querySelectorAll('input').forEach(input => {
            const oldId = input.id;
            const newId = oldId.replace(/point-\d+-/, `point-${index}-`);
            input.id = newId;
        });
    });
}

// Validate JSON
async function validateJSON() {
    const btn = document.getElementById('validate-json-btn');
    const originalText = btn ? btn.textContent : '';
    const jsonInput = document.getElementById('json-input').value;
    const resultDiv = document.getElementById('json-validation-result');
    
    if (!jsonInput.trim()) {
        resultDiv.innerHTML = '<p style="color: var(--error-color);">请输入JSON数据</p>';
        resultDiv.className = 'validation-result error';
        return;
    }
    
    try {
        // Set loading state
        if (btn) {
            btn.disabled = true;
            btn.textContent = '验证中...';
        }
        const data = JSON.parse(jsonInput);
        
        if (!data.trajectory_points || !Array.isArray(data.trajectory_points)) {
            throw new Error('JSON必须包含trajectory_points数组');
        }
        
        // Send to validation API
        const response = await fetch(`${API_BASE}/api/trajectory/validate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                trajectory_points: data.trajectory_points
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.valid) {
            resultDiv.innerHTML = `
                <p style="color: var(--success-color);">✓ JSON格式有效</p>
                <p>包含 ${result.point_count} 个轨迹点</p>
                ${result.warnings && result.warnings.length > 0 
                    ? `<p style="color: var(--warning-color);">警告: ${result.warnings.join('; ')}</p>` 
                    : ''}
            `;
            resultDiv.className = 'validation-result success';
        } else {
            resultDiv.innerHTML = `
                <p style="color: var(--error-color);">✗ JSON格式无效</p>
                <ul>
                    ${result.errors.map(e => `<li>${e}</li>`).join('')}
                </ul>
                ${result.warnings && result.warnings.length > 0 
                    ? `<p style="color: var(--warning-color);">警告: ${result.warnings.join('; ')}</p>` 
                    : ''}
            `;
            resultDiv.className = 'validation-result error';
        }
    } catch (error) {
        resultDiv.innerHTML = `<p style="color: var(--error-color);">JSON解析错误: ${error.message}</p>`;
        resultDiv.className = 'validation-result error';
        showNotification(`JSON验证失败: ${error.message}`, 'error');
    } finally {
        // Restore button state
        if (btn) {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    }
}

// Import JSON
async function importJSON() {
    const btn = document.getElementById('import-json-btn');
    const originalText = btn ? btn.textContent : '';
    const jsonInput = document.getElementById('json-input').value;
    
    if (!jsonInput.trim()) {
        showNotification('请输入JSON数据', 'warning');
        return;
    }
    
    try {
        // Set loading state
        if (btn) {
            btn.disabled = true;
            btn.textContent = '导入中...';
        }
        const data = JSON.parse(jsonInput);
        
        if (!data.trajectory_points || !Array.isArray(data.trajectory_points)) {
            throw new Error('JSON必须包含trajectory_points数组');
        }
        
        // Clear existing custom trajectory
        clearCustomTrajectory();
        
        // Add points from JSON
        data.trajectory_points.forEach(point => {
            customTrajectoryPoints.push({
                timestamp: point.timestamp || new Date().toISOString(),
                latitude: point.latitude,
                longitude: point.longitude,
                category: point.category || 'Unknown',
                venue_id: point.venue_id || null,
                address: point.address || ''
            });
        });
        
        // Display points on map
        customTrajectoryPoints.forEach((point, index) => {
            addCustomPointMarker(L.latLng(point.latitude, point.longitude), index);
        });
        
        updateCustomPointsList();
        updateCustomTrajectoryPolyline();
        
        showNotification(`成功导入 ${customTrajectoryPoints.length} 个轨迹点`, 'success');
    } catch (error) {
        showNotification(`导入失败: ${error.message}`, 'error');
    } finally {
        // Restore button state
        if (btn) {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    }
}

// Preview custom trajectory
function previewCustomTrajectory() {
    if (currentInputMode === 'form') {
        // Collect points from form
        customTrajectoryPoints = [];
        const container = document.getElementById('form-points-container');
        const items = container.querySelectorAll('.form-point-item');
        
        items.forEach((item, index) => {
            const timestamp = document.getElementById(`point-${index}-timestamp`).value;
            const lat = parseFloat(document.getElementById(`point-${index}-latitude`).value);
            const lng = parseFloat(document.getElementById(`point-${index}-longitude`).value);
            const category = document.getElementById(`point-${index}-category`).value || 'Unknown';
            const venueId = document.getElementById(`point-${index}-venue_id`).value;
            const address = document.getElementById(`point-${index}-address`).value;
            
            if (!isNaN(lat) && !isNaN(lng)) {
                customTrajectoryPoints.push({
                    timestamp: timestamp ? new Date(timestamp).toISOString() : new Date().toISOString(),
                    latitude: lat,
                    longitude: lng,
                    category: category,
                    venue_id: venueId ? parseInt(venueId) : null,
                    address: address
                });
            }
        });
        
        // Clear existing markers
        customPointMarkers.forEach(marker => map.removeLayer(marker));
        customPointMarkers = [];
        
        // Add markers
        customTrajectoryPoints.forEach((point, index) => {
            addCustomPointMarker(L.latLng(point.latitude, point.longitude), index);
        });
    }
    
    if (customTrajectoryPoints.length === 0) {
        showNotification('请先添加轨迹点', 'warning');
        return;
    }
    
    // Display trajectory on map
    updateCustomTrajectoryPolyline();
    showNotification(`预览 ${customTrajectoryPoints.length} 个轨迹点`, 'success');
}

// Save custom trajectory
async function saveCustomTrajectory() {
    const btn = document.getElementById('save-custom-trajectory-btn');
    const originalText = btn ? btn.textContent : '';
    
    // Collect points if in form mode
    if (currentInputMode === 'form') {
        previewCustomTrajectory();
    }
    
    if (customTrajectoryPoints.length === 0) {
        showNotification('请先添加轨迹点', 'warning');
        return;
    }
    
    try {
        // Set loading state
        if (btn) {
            btn.disabled = true;
            btn.textContent = '保存中...';
        }
        showLoading(true);
        
        const response = await fetch(`${API_BASE}/api/trajectory/custom`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: 'custom_user_' + Date.now(),
                trajectory_points: customTrajectoryPoints
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.message || data.error || '保存自定义轨迹失败');
        }

        currentTrajectory = data.trajectory;
        showNotification('自定义轨迹已保存', 'success');
        // Switch to browse tab
        switchTab('browse');
    } catch (error) {
        console.error('Failed to save custom trajectory:', error);
        showNotification('保存失败: ' + error.message, 'error');
    } finally {
        showLoading(false);
        // Restore button state
        if (btn) {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    }
}
