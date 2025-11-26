// AgentMove Demo - Main JavaScript

// API Configuration
const API_BASE = '';  // Same origin

// Global State
let map = null;
let markers = [];
let polyline = null;
let currentCity = 'Shanghai';
let currentTrajectory = null;

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
        document.getElementById('status-indicator').textContent = '🔴 连接失败';
    }
}

// Load available trajectories
async function loadTrajectories() {
    try {
        const response = await fetch(`${API_BASE}/api/trajectories/${currentCity}?limit=20`);
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
        }

        console.log('Trajectories loaded:', data.count);
    } catch (error) {
        console.error('Failed to load trajectories:', error);
        showNotification('加载轨迹失败', 'error');
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
    });

    // Model change
    document.getElementById('model-select').addEventListener('change', function (e) {
        console.log('Model changed to:', e.target.value);
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
}

// Load selected trajectory
async function loadSelectedTrajectory() {
    const select = document.getElementById('trajectory-select');
    const value = select.value;

    if (!value) {
        showNotification('请先选择一个轨迹', 'warning');
        return;
    }

    const [userId, trajId] = value.split('|');

    try {
        showLoading(true);
        const response = await fetch(`${API_BASE}/api/trajectory/${currentCity}/${userId}/${trajId}`);
        const data = await response.json();

        if (data.success) {
            currentTrajectory = data.trajectory;
            displayTrajectory(data.trajectory);
            showNotification('轨迹加载成功', 'success');
        }
    } catch (error) {
        console.error('Failed to load trajectory:', error);
        showNotification('加载轨迹详情失败', 'error');
    } finally {
        showLoading(false);
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

        const data = await response.json();

        console.log('Prediction response:', data);

        if (data.success) {
            displayPredictionResults(data.prediction);
            showNotification('预测完成', 'success');
        } else {
            // Display detailed error information
            let errorMessage = '预测失败\n\n';

            if (data.error) {
                errorMessage += `错误: ${data.error}\n`;
            }

            if (data.error_type) {
                errorMessage += `类型: ${data.error_type}\n`;
            }

            if (data.message) {
                errorMessage += `\n${data.message}\n`;
            }

            if (data.details && data.details.traceback) {
                errorMessage += `\n详细堆栈:\n${data.details.traceback.substring(0, 500)}...`;
            }

            console.error('Prediction failed with details:', data);
            alert(errorMessage);
            showNotification('预测失败 - 查看控制台获取详细信息', 'error');
        }
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
    try {
        showLoading(true);

        const response = await fetch(`${API_BASE}/api/example`);
        const data = await response.json();

        if (data.success) {
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
        }
    } catch (error) {
        console.error('Failed to load example:', error);
        showNotification('加载示例失败', 'error');
    } finally {
        showLoading(false);
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

// Show notification (simple alert for now, can be improved with toast notifications)
function showNotification(message, type) {
    const icons = {
        success: '✓',
        error: '✗',
        warning: '⚠'
    };

    const icon = icons[type] || 'ℹ';
    console.log(`${icon} ${message}`);

    // You can implement a better toast notification system here
    // For now, just use console.log
}

// Utility: Format JSON for display
function formatJSON(obj) {
    try {
        return JSON.stringify(obj, null, 2);
    } catch (e) {
        return String(obj);
    }
}
