// VespAI Dashboard JavaScript
// Author: Jakob Zeise (Zeise Digital)

// Custom orange neon cursor
let cursor = null;

// Initialize custom cursor
document.addEventListener('DOMContentLoaded', function() {
    console.log('VespAI Dashboard: Initializing custom orange neon cursor...');
    // Create cursor element
    cursor = document.createElement('div');
    cursor.style.cssText = `
        position: fixed;
        width: 16px;
        height: 16px;
        background: #ff6600;
        border: 2px solid #ffffff;
        border-radius: 50%;
        pointer-events: none;
        z-index: 99999;
        box-shadow: 
            0 0 15px #ff6600,
            0 0 25px #ff6600,
            0 0 35px #ff6600,
            0 0 45px rgba(255, 102, 0, 0.8);
        transition: all 0.05s ease;
        transform: translate(-50%, -50%);
        opacity: 1;
        mix-blend-mode: screen;
    `;
    document.body.appendChild(cursor);
    console.log('VespAI Dashboard: Custom cursor created and added to page!');
    
    // Animate the glow
    setInterval(() => {
        if (cursor) {
            const intensity = Math.sin(Date.now() * 0.005) * 0.5 + 0.5;
            const glowSize = 15 + intensity * 15;
            cursor.style.boxShadow = `
                0 0 ${glowSize}px #ff6600,
                0 0 ${glowSize * 2}px #ff6600,
                0 0 ${glowSize * 3}px #ff6600,
                inset 0 0 10px #ffffff
            `;
        }
    }, 50);
});

// Track mouse movement
document.addEventListener('mousemove', function(e) {
    if (cursor) {
        cursor.style.left = e.clientX + 'px';
        cursor.style.top = e.clientY + 'px';
    }
});

// Hide cursor when leaving window
document.addEventListener('mouseleave', function() {
    if (cursor) cursor.style.opacity = '0';
});

// Show cursor when entering window
document.addEventListener('mouseenter', function() {
    if (cursor) cursor.style.opacity = '1';
});

// Track log entries to prevent duplicates
let logMap = new Map();
let lastChartUpdate = 0;

// Update time
function updateTime() {
    const now = new Date();
    document.getElementById('current-time').textContent = 
        now.toTimeString().split(' ')[0];
}
setInterval(updateTime, 1000);
updateTime();

// Update log without flickering
function updateLog(logData) {
    const logContent = document.getElementById('log-content');
    const currentIds = new Set();

    // Process each log entry
    logData.forEach((entry, index) => {
        const entryId = `${entry.timestamp}-${entry.species}-${entry.frame_id}`;
        currentIds.add(entryId);

        // Only add if it's a new entry
        if (!logMap.has(entryId)) {
            const logEntry = document.createElement('div');
            logEntry.className = `log-entry new ${entry.species}` + (entry.frame_id ? ' clickable' : '');
            logEntry.innerHTML = `
                <div class="log-time"><i class="fas fa-clock"></i> ${entry.timestamp}</div>
                <div>${entry.species === 'velutina' ? 'Asian Hornet' : 'European Hornet'} detected (${entry.confidence}%)</div>
            `;
            logEntry.dataset.id = entryId;
            if (entry.frame_id) {
                logEntry.dataset.frameId = entry.frame_id;
            }

            // Add click handler
            logEntry.addEventListener('click', function() {
                if (entry.frame_id) {
                    showDetectionFrame(entry.frame_id);
                }
            });

            // Add at the top
            logContent.insertBefore(logEntry, logContent.firstChild);
            logMap.set(entryId, logEntry);

            // Remove 'new' class after animation
            setTimeout(() => {
                logEntry.classList.remove('new');
            }, 500);
        }
    });

    // Remove old entries not in current data
    const allEntries = logContent.querySelectorAll('.log-entry');
    allEntries.forEach((element) => {
        const id = element.dataset.id;
        if (id && !currentIds.has(id)) {
            element.remove();
            logMap.delete(id);
        }
    });

    // Keep only last 20 visible
    while (logContent.children.length > 20) {
        const lastChild = logContent.lastChild;
        const id = lastChild.dataset.id;
        if (id) logMap.delete(id);
        lastChild.remove();
    }
}

// Smooth value updates
function updateValue(elementId, newValue, suffix = '') {
    const element = document.getElementById(elementId);
    if (element) {
        const currentValue = element.textContent.replace(suffix, '');
        if (currentValue !== newValue.toString()) {
            element.style.transform = 'scale(1.1)';
            element.textContent = newValue + suffix;
            setTimeout(() => {
                element.style.transform = 'scale(1)';
            }, 300);
        }
    }
}

// Fetch live stats
function updateStats() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            // Update counters with animation
            updateValue('frame-count', data.frame_id || 0);
            updateValue('velutina-count', data.total_velutina || 0);
            updateValue('crabro-count', data.total_crabro || 0);
            updateValue('total-detections', data.total_detections || 0);
            updateValue('sms-count', data.sms_sent || 0);
            
            // Update SMS cost
            if (data.sms_cost !== undefined) {
                document.getElementById('sms-cost').textContent = data.sms_cost.toFixed(2) + '€';
                if (data.sms_sent > 0) {
                    const costPerSms = (data.sms_cost / data.sms_sent).toFixed(3);
                    document.getElementById('cost-per-sms').textContent = costPerSms + '€/SMS';
                }
            }

            // Update other stats
            document.getElementById('fps').textContent = (data.fps || 0).toFixed(1) + ' FPS';
            
            // Update system info with safety checks
            if (data.cpu_temp !== undefined) document.getElementById('cpu-temp').textContent = Math.round(data.cpu_temp) + '°C';
            if (data.cpu_usage !== undefined) document.getElementById('cpu-usage').textContent = data.cpu_usage + '%';
            if (data.ram_usage !== undefined) document.getElementById('ram-usage').textContent = data.ram_usage + '%';
            if (data.uptime !== undefined) document.getElementById('uptime-sys').textContent = data.uptime;

            // Update log without flickering
            if (data.detection_log) {
                updateLog(data.detection_log);
            }

            // Update hourly chart
            if (data.hourly_data && (Date.now() - lastChartUpdate > 10000)) {
                lastChartUpdate = Date.now();
                const chart = document.getElementById('hourly-chart');
                chart.innerHTML = '';
                
                const maxVal = Math.max(...data.hourly_data.map(h => h.total), 1);
                
                data.hourly_data.forEach(hour => {
                    const bar = document.createElement('div');
                    bar.className = 'time-bar';
                    const height = Math.max(((hour.total / maxVal) * 100), 2);
                    bar.style.height = height + '%';

                    if (hour.velutina > 0 && hour.crabro > 0) {
                        bar.style.background = 'linear-gradient(180deg, var(--danger) 0%, var(--honey) 100%)';
                    } else if (hour.velutina > 0) {
                        bar.style.background = 'linear-gradient(180deg, var(--danger) 0%, #ff0066 100%)';
                    } else if (hour.crabro > 0) {
                        bar.style.background = 'linear-gradient(180deg, var(--honey) 0%, var(--honey-dark) 100%)';
                    } else {
                        bar.style.background = 'rgba(255,255,255,0.1)';
                    }

                    bar.innerHTML = `<span class="time-bar-label">${hour.hour}h</span>`;
                    bar.title = `${hour.hour}:00 - Velutina: ${hour.velutina}, Crabro: ${hour.crabro}`;
                    chart.appendChild(bar);
                });
            }
        })
        .catch(error => {
            console.error('Error fetching stats:', error);
        });
}

// Fullscreen function
function toggleFullscreen() {
    const video = document.getElementById('video-feed');
    if (!document.fullscreenElement) {
        video.requestFullscreen().catch(err => {
            console.error(`Error attempting to enable fullscreen: ${err.message}`);
        });
    } else {
        document.exitFullscreen();
    }
}

// Show detection frame in new tab/window
function showDetectionFrame(frameId) {
    const frameUrl = `/frame/${frameId}`;
    window.open(frameUrl, '_blank');
}

// Update stats every 2 seconds
setInterval(updateStats, 2000);
updateStats();