// VespAI Dashboard JavaScript

// Track log entries to prevent duplicates
let logMap = new Map();
let lastChartUpdate = 0;

// Update time display
function updateTime() {
    const now = new Date();
    document.getElementById('current-time').textContent = 
        now.toTimeString().split(' ')[0];
}

// Update log without flickering
function updateLog(logData) {
    const logContent = document.getElementById('log-content');
    const currentIds = new Set();

    // Process each log entry
    logData.forEach((entry, index) => {
        const entryId = `${entry.time}-${entry.message}`;
        currentIds.add(entryId);

        // Only add if it's a new entry
        if (!logMap.has(entryId)) {
            const logEntry = document.createElement('div');
            
            // Determine CSS class based on detection type
            let typeClass = '';
            if (entry.type === 'velutina') {
                typeClass = ' velutina';
            } else if (entry.type === 'crabro') {
                typeClass = ' crabro';
            } else if (entry.message && entry.message.includes('Velutina')) {
                typeClass = ' velutina';
            } else if (entry.message && entry.message.includes('Crabro')) {
                typeClass = ' crabro';
            }

            logEntry.className = 'log-entry new' + typeClass + (entry.frame_id ? ' clickable' : '');
            logEntry.innerHTML = `
                <div class="log-time"><i class="fas fa-clock"></i> ${entry.time}</div>
                <div>${entry.message}</div>
            `;
            logEntry.dataset.id = entryId;
            if (entry.frame_id) {
                logEntry.dataset.frameId = entry.frame_id;
            }

            // Add click handler for detection frames
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

// Smooth value updates with animation
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

// Fetch and update live statistics
function updateStats() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            // Update counters with animation
            updateValue('frame-count', data.frame_id);
            updateValue('velutina-count', data.total_velutina);
            updateValue('crabro-count', data.total_crabro);
            updateValue('total-detections', data.total_detections);
            updateValue('sms-count', data.sms_sent);
            
            // Update SMS cost
            if (data.sms_cost !== undefined) {
                document.getElementById('sms-cost').textContent = data.sms_cost.toFixed(2) + '€';
                if (data.sms_sent > 0) {
                    const costPerSms = (data.sms_cost / data.sms_sent).toFixed(3);
                    document.getElementById('cost-per-sms').textContent = costPerSms + '€/SMS';
                }
            }

            // Update other stats
            document.getElementById('fps').textContent = data.fps.toFixed(1) + ' FPS';
            document.getElementById('uptime').textContent = 'Uptime: ' + data.uptime;
            document.getElementById('cpu-temp').textContent = data.cpu_temp + '°C';
            document.getElementById('cpu-usage').textContent = data.cpu_usage + '%';
            document.getElementById('ram-usage').textContent = data.ram_usage + '%';

            if (data.confidence_avg) {
                document.getElementById('confidence').textContent = data.confidence_avg.toFixed(0) + '%';
            }

            // Update detection rate
            if (data.detection_rate !== undefined) {
                document.getElementById('detection-rate').textContent = data.detection_rate + '/h';
            }

            // Update last detection times
            if (data.last_velutina) {
                document.getElementById('velutina-last').textContent = 'Last: ' + data.last_velutina;
            }
            if (data.last_crabro) {
                document.getElementById('crabro-last').textContent = 'Last: ' + data.last_crabro;
            }
            if (data.last_sms) {
                document.getElementById('last-sms').textContent = 'Last: ' + data.last_sms;
            }

            // Update log without flickering
            if (data.detection_log) {
                updateLog(data.detection_log);
            }

            // Update hourly chart (throttled to prevent flickering)
            const now = Date.now();
            if (data.hourly_stats && (now - lastChartUpdate > 10000)) {
                lastChartUpdate = now;
                updateHourlyChart(data.hourly_stats);
            }
        })
        .catch(error => {
            console.error('Error fetching stats:', error);
        });
}

// Update hourly detection chart
function updateHourlyChart(hourlyStats) {
    const chart = document.getElementById('hourly-chart');
    chart.innerHTML = '';
    
    const isMobile = window.innerWidth < 640;
    
    if (isMobile) {
        // Mobile: Group hours into 6 bars
        const groupedStats = groupHourlyData(hourlyStats);
        const maxVal = Math.max(...groupedStats.map(g => g.total), 1);
        
        groupedStats.forEach(group => {
            const bar = createChartBar(group, maxVal);
            chart.appendChild(bar);
        });
    } else {
        // Desktop: Show all 24 hours
        const maxVal = Math.max(...hourlyStats.map(h => h.total), 1);
        
        hourlyStats.forEach(hour => {
            const bar = createChartBar(hour, maxVal, true);
            chart.appendChild(bar);
        });
    }
}

// Group hourly data for mobile display
function groupHourlyData(hourlyStats) {
    const groups = [
        { label: '1-4h', hours: [] },
        { label: '5-8h', hours: [] },
        { label: '9-12h', hours: [] },
        { label: '13-16h', hours: [] },
        { label: '17-20h', hours: [] },
        { label: '21-24h', hours: [] }
    ];
    
    hourlyStats.forEach(hour => {
        const groupIndex = Math.floor(hour.hour / 4);
        if (groupIndex >= 0 && groupIndex < 6) {
            groups[groupIndex].hours.push(hour);
        }
    });
    
    return groups.map(group => {
        const totalVelutina = group.hours.reduce((sum, h) => sum + (h.velutina || 0), 0);
        const totalCrabro = group.hours.reduce((sum, h) => sum + (h.crabro || 0), 0);
        return {
            label: group.label,
            velutina: totalVelutina,
            crabro: totalCrabro,
            total: totalVelutina + totalCrabro
        };
    });
}

// Create a chart bar element
function createChartBar(data, maxVal, isHourly = false) {
    const bar = document.createElement('div');
    bar.className = 'time-bar';
    const height = Math.max(((data.total / maxVal) * 100), 2);
    bar.style.height = height + '%';
    
    // Set color based on detection types
    if (data.velutina > 0 && data.crabro > 0) {
        bar.style.background = 'linear-gradient(180deg, var(--danger) 0%, var(--honey) 100%)';
    } else if (data.velutina > 0) {
        bar.style.background = 'linear-gradient(180deg, var(--danger) 0%, #ff0066 100%)';
    } else if (data.crabro > 0) {
        bar.style.background = 'linear-gradient(180deg, var(--honey) 0%, var(--honey-dark) 100%)';
    } else {
        bar.style.background = 'rgba(255,255,255,0.1)';
    }
    
    const label = isHourly ? `${data.hour}h` : data.label;
    bar.innerHTML = `<span class="time-bar-label">${label}</span>`;
    bar.title = `${label} - Velutina: ${data.velutina}, Crabro: ${data.crabro}`;
    
    return bar;
}

// Toggle fullscreen mode for video canvas
function toggleFullscreen() {
    const canvas = document.getElementById('video-feed');
    if (!document.fullscreenElement) {
        canvas.requestFullscreen().catch(err => {
            console.error(`Error attempting to enable fullscreen: ${err.message}`);
        });
    } else {
        document.exitFullscreen();
    }
}

// Show detection frame in new window/tab
function showDetectionFrame(frameId) {
    const frameUrl = `/frame/${frameId}`;
    
    // Try to open in new tab
    const newWindow = window.open(frameUrl, '_blank');
    
    // Fallback if popup blocked
    if (!newWindow || newWindow.closed || typeof newWindow.closed == 'undefined') {
        if (confirm('Open detection frame? (Click OK to view in current window, Cancel to stay here)')) {
            window.location.href = frameUrl;
        }
    }
}

// Simple and reliable video streaming - no complex classes needed

// Ultra-smooth canvas-based video feed with zero flickering
function startVideoPolling() {
    const canvas = document.getElementById('video-feed');
    
    if (!canvas) {
        console.error('Video canvas element not found');
        return;
    }
    
    const ctx = canvas.getContext('2d');
    if (!ctx) {
        console.error('Canvas 2D context not supported');
        return;
    }
    
    // Set canvas to smooth scaling
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    
    console.log('Using ultra-smooth canvas approach - zero flickering possible');
    
    let frameCounter = 0;
    let lastFrameTime = Date.now();
    let fps = 0;
    
    // Smooth canvas update every 1000ms
    setInterval(() => {
        frameCounter++;
        const timestamp = Date.now();
        const random = Math.random();
        const counter = frameCounter;
        
        // Calculate FPS
        const timeDiff = timestamp - lastFrameTime;
        if (timeDiff > 0) {
            fps = Math.round(1000 / timeDiff);
        }
        lastFrameTime = timestamp;
        
        // Multiple cache-busting parameters
        const newSrc = `/current_frame.jpg?t=${timestamp}&r=${random}&c=${counter}&bust=${Date.now()}`;
        
        // Load image and draw on canvas (prevents all flickering)
        const img = new Image();
        img.onload = function() {
            // Clear canvas with dark background
            ctx.fillStyle = '#1a1a1a';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            // Draw video frame
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
            
            // Add canvas overlay info
            ctx.fillStyle = '#00ff00';
            ctx.font = '14px Arial';
            ctx.fillText(`Live Frame ${counter}`, 10, canvas.height - 40);
            ctx.fillText(`${new Date().toLocaleTimeString()}`, 10, canvas.height - 20);
            
            console.log(`✓ Canvas frame ${counter} rendered at ${new Date().toLocaleTimeString()}`);
        };
        img.onerror = function() {
            console.warn(`✗ Frame ${counter} failed to load`);
            // Draw error frame on canvas
            ctx.fillStyle = '#333';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#ff6600';
            ctx.font = '24px Arial';
            ctx.fillText('Loading...', canvas.width/2 - 60, canvas.height/2);
        };
        img.src = newSrc;
    }, 1000);
    
    updateVideoStatus('Live (Canvas)', '#0f0');
}

function updateVideoStatus(message, color) {
    const statusElement = document.getElementById('video-status');
    if (statusElement) {
        statusElement.textContent = message;
        statusElement.style.color = color;
    }
}

// Clean, simple video management - no unused functions

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    // Start time updates
    setInterval(updateTime, 1000);
    updateTime();
    
    // Start stats updates every 2 seconds
    setInterval(updateStats, 2000);
    updateStats();
    
    // Start ultra-simple video polling after page loads
    setTimeout(() => {
        startVideoPolling();
    }, 1000);
    
    console.log('VespAI Dashboard initialized with proven video approach');
});