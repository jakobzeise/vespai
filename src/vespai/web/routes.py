#!/usr/bin/env python3
"""
VespAI Web Routes Module

This module contains all essential Flask web routes for the VespAI hornet detection system.
Routes extracted from the working web_preview.py implementation to provide a clean,
modular web interface.

Key Features:
- Live MJPEG video streaming from camera
- Real-time detection statistics API
- Detection frame viewing with SMS-friendly links
- System monitoring (CPU, RAM, temperature)
- Interactive dashboard with live updates

Routes:
- GET /: Main dashboard page
- GET /video_feed: Live MJPEG video stream
- GET /api/stats: Real-time system statistics JSON
- GET /api/detection_frame/<id>: Individual detection frame images
- GET /frame/<id>: HTML page for viewing detection frames
- GET /api/frames: List all available detection frames

Author: VespAI Team
Version: 1.0
"""

import cv2
import psutil
import datetime
from flask import Response, render_template_string, jsonify

# Original HTML template from working web_preview.py
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VespAI Monitor - Live Dashboard</title>

    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">

    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        :root {
            --primary: #ff6600;
            --danger: #ff0040;
            --warning: #ffa500;
            --success: #00ff88;
            --info: #00d4ff;
            --dark: #0a0a0a;
            --card-bg: #141414;
            --border: #2a2a2a;
            --text: #ffffff;
            --text-dim: #888;
            --honey: #ffa500;
            --honey-dark: #cc8400;
        }

        html {
            overflow-x: hidden;
            width: 100%;
        }

        body {
            font-family: 'Inter', sans-serif;
            background: #0a0a0a;
            color: var(--text);
            min-height: 100vh;
            overflow-x: hidden;
            position: relative;
            width: 100%;
        }

        /* Honeycomb pattern background */
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            opacity: 0.03;
            background-image: 
                linear-gradient(30deg, transparent 0%, transparent 70%, var(--honey) 70%, var(--honey) 100%),
                linear-gradient(90deg, transparent 0%, transparent 70%, var(--honey) 70%, var(--honey) 100%),
                linear-gradient(150deg, transparent 0%, transparent 70%, var(--honey) 70%, var(--honey) 100%);
            background-size: 50px 86.6px;
            background-position: 0 0, 25px 43.3px, 25px 43.3px;
            pointer-events: none;
            z-index: 0;
        }

        body::after {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: radial-gradient(ellipse at center, transparent 0%, rgba(10,10,10,0.4) 100%);
            pointer-events: none;
            z-index: 1;
        }

        /* Ensure all content is above the background */
        .header, .container {
            position: relative;
            z-index: 10;
        }

        /* Header */
        .header {
            background: rgba(20,20,20,0.95);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid var(--border);
            padding: 1.5rem 2rem;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .header-content {
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }

        .logo {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .logo-icon {
            width: 50px;
            height: 50px;
            background: linear-gradient(135deg, var(--primary) 0%, var(--honey) 100%);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            animation: pulse-glow 3s infinite;
            position: relative;
        }

        /* Bee/wasp icon animation */
        .logo-icon::after {
            content: '🐝';
            position: absolute;
            font-size: 20px;
            animation: bee-fly 10s infinite ease-in-out;
        }

        @keyframes bee-fly {
            0%, 100% { transform: translate(0, 0) rotate(0deg); }
            25% { transform: translate(10px, -5px) rotate(10deg); }
            50% { transform: translate(-10px, -10px) rotate(-10deg); }
            75% { transform: translate(-5px, 5px) rotate(5deg); }
        }

        @keyframes pulse-glow {
            0%, 100% { box-shadow: 0 0 20px rgba(255,102,0,0.5); }
            50% { box-shadow: 0 0 40px rgba(255,102,0,0.8); }
        }

        .logo h1 {
            font-size: 1.8rem;
            font-weight: 800;
            background: linear-gradient(135deg, var(--primary) 0%, var(--warning) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        /* Status Bar */
        .status-bar {
            display: flex;
            gap: 2rem;
            align-items: center;
            flex-wrap: wrap;
        }

        .status-item {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .live-indicator {
            width: 10px;
            height: 10px;
            background: var(--success);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }

        /* Container */
        .container {
            max-width: 1400px;
            margin: 2rem auto;
            padding: 0 2rem;
        }

        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        .stat-card {
            background: rgba(20, 20, 20, 0.8);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.5rem;
            position: relative;
            overflow: hidden;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }

        /* Hexagon pattern for stat cards */
        .stat-card::after {
            content: '';
            position: absolute;
            top: -20px;
            right: -20px;
            width: 80px;
            height: 80px;
            background: linear-gradient(45deg, transparent 30%, var(--honey) 30%, var(--honey) 70%, transparent 70%);
            opacity: 0.05;
            transform: rotate(30deg);
        }

        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(255,102,0,0.2);
        }

        .stat-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--primary) 0%, var(--warning) 100%);
        }

        .stat-card.danger::before {
            background: linear-gradient(90deg, var(--danger) 0%, var(--warning) 100%);
        }

        .stat-value {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            transition: all 0.3s ease;
        }

        .stat-label {
            color: var(--text-dim);
            font-size: 0.9rem;
            text-transform: uppercase;
        }

        .stat-detail {
            font-size: 0.85rem;
            color: var(--text-dim);
            margin-top: 0.5rem;
        }

        /* Main Grid */
        .main-grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 2rem;
            margin-bottom: 2rem;
        }

        @media (max-width: 1024px) {
            .main-grid {
                grid-template-columns: 1fr;
            }
            .stats-grid {
                grid-template-columns: repeat(2, 1fr);
                gap: 1rem;
            }
            .stat-card {
                padding: 1rem;
            }
            .stat-value {
                font-size: 2rem;
            }
        }

        @media (max-width: 640px) {
            .header-content {
                flex-direction: column;
                text-align: center;
                gap: 0.75rem;
            }
            .status-bar {
                justify-content: center;
                width: 100%;
                gap: 1rem;
            }
            .status-item {
                font-size: 0.85rem;
            }
            .container {
                padding: 0 0.5rem;
                margin: 1rem auto;
            }
            /* Show 6 stat cards on mobile in 2x3 grid */
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 0.5rem;
                margin-bottom: 1rem;
            }
            .stat-card {
                padding: 1rem;
                aspect-ratio: 1;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                text-align: center;
                border-radius: 20px;
                box-shadow: 0 4px 15px rgba(255, 102, 0, 0.15);
                transition: all 0.3s ease;
            }
            .stat-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(255, 102, 0, 0.25);
            }
            .stat-value {
                font-size: 1.8rem;
                font-weight: 800;
                margin-bottom: 0.25rem;
                line-height: 1;
                color: #ffffff;
                text-shadow: 0 2px 8px rgba(255, 102, 0, 0.3);
            }
            .stat-label {
                font-size: 0.8rem;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 0.25rem;
                color: #ff6600;
                opacity: 1;
            }
            .stat-detail {
                font-size: 0.7rem;
                margin-top: 0.25rem;
                color: #cccccc;
                font-weight: 500;
                opacity: 1;
            }
            .chart-card {
                overflow: visible;
                padding: 1rem;
                padding-bottom: 3rem;
                margin-left: -0.5rem;
                margin-right: -0.5rem;
            }
            .chart-card h3 {
                font-size: 0.9rem;
                margin-bottom: 0.5rem;
            }
            .time-chart {
                height: 220px;
                overflow-x: visible;
                overflow-y: visible;
                display: flex;
                justify-content: space-evenly;
                align-items: flex-end;
                padding: 0.5rem 1rem;
                padding-bottom: 45px;
                position: relative;
                margin-bottom: 5px;
            }
            .time-bar {
                flex: 1;
                min-width: 35px;
                max-width: 50px;
                margin: 0 3px;
            }
            .time-bar-label {
                font-size: 0.65rem;
                bottom: -30px;
                left: 50%;
                transform: translateX(-50%);
                white-space: nowrap;
            }
            /* Video container improvements */
            .video-container {
                margin-bottom: 1rem;
                width: calc(100vw - 1rem);
                margin-left: -0.25rem;
                margin-right: -0.25rem;
            }
            .video-feed {
                width: 100%;
                height: auto;
                min-height: 250px;
                object-fit: cover;
            }
            .video-header {
                padding: 1rem;
                flex-direction: column;
                gap: 0.75rem;
                text-align: center;
            }
            .video-header h2 {
                font-size: 1.1rem;
                margin: 0;
                font-weight: 600;
            }
            .video-controls {
                width: 100%;
                justify-content: center;
                align-items: center;
                gap: 1rem;
                flex-wrap: wrap;
            }
            .fullscreen-btn {
                font-size: 0.8rem;
                padding: 0.5rem 1rem;
                min-width: 120px;
                text-align: center;
            }
            .live-badge {
                font-size: 0.75rem;
                padding: 0.3rem 0.75rem;
                min-width: 60px;
                text-align: center;
                justify-content: center;
            }
            .detection-log {
                height: 350px;
            }
            .log-header {
                padding: 0.75rem;
            }
            .log-header h3 {
                font-size: 0.9rem;
            }
            .log-content {
                padding: 0.5rem;
            }
            .log-entry {
                padding: 0.75rem;
                margin-bottom: 0.5rem;
            }
            .log-time {
                font-size: 0.75rem;
            }
            .logo h1 {
                font-size: 1.2rem;
            }
            .logo-icon {
                width: 40px;
                height: 40px;
            }
            .system-info {
                grid-template-columns: repeat(2, 1fr);
                padding: 1rem;
                gap: 0.75rem;
            }
            .system-value {
                font-size: 1.2rem;
            }
            .system-label {
                font-size: 0.7rem;
            }
        }

        /* Video Container */
        .video-container {
            background: rgba(20, 20, 20, 0.9);
            border: 1px solid var(--border);
            border-radius: 16px;
            overflow: hidden;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px rgba(255, 102, 0, 0.1);
        }

        .video-header {
            padding: 1rem 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border);
        }

        .video-controls {
            display: flex;
            gap: 0.5rem;
        }

        .fullscreen-btn {
            background: rgba(255,255,255,0.1);
            border: 1px solid var(--border);
            color: var(--text);
            padding: 0.5rem 1rem;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .fullscreen-btn:hover {
            background: var(--primary);
            transform: translateY(-2px);
        }

        .live-badge {
            background: var(--danger);
            color: white;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
            animation: pulse 2s infinite;
            display: flex;
            align-items: center;
            gap: 0.25rem;
        }

        .video-feed {
            width: 100%;
            height: auto;
            display: block;
            background: #000;
        }

        /* Detection Log */
        .detection-log {
            background: rgba(20, 20, 20, 0.9);
            border: 1px solid var(--border);
            border-radius: 16px;
            height: 600px;
            display: flex;
            flex-direction: column;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px rgba(255, 102, 0, 0.1);
        }

        .log-header {
            padding: 1rem 1.5rem;
            border-bottom: 1px solid var(--border);
        }

        .log-content {
            flex: 1;
            overflow-y: auto;
            padding: 1rem;
        }

        .log-entry {
            background: rgba(255,255,255,0.03);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1rem;
            margin-bottom: 1rem;
            transition: all 0.3s ease;
            cursor: pointer;
        }

        .log-entry:hover {
            background: rgba(255,255,255,0.08);
            transform: translateX(-5px);
            box-shadow: 0 5px 15px rgba(255,102,0,0.3);
        }

        .log-entry.new {
            animation: slideIn 0.5s ease;
        }

        @keyframes slideIn {
            from { 
                opacity: 0; 
                transform: translateX(20px); 
            }
            to { 
                opacity: 1; 
                transform: translateX(0); 
            }
        }

        .log-entry.velutina {
            border-color: var(--danger);
            background: rgba(255,0,64,0.05);
        }

        .log-entry.crabro {
            border-color: var(--warning);
            background: rgba(255,165,0,0.05);
        }

        .log-time {
            color: var(--primary);
            font-weight: 600;
            margin-bottom: 0.5rem;
        }

        .log-entry.clickable {
            position: relative;
        }

        .log-entry.clickable::after {
            content: '\f03e';
            font-family: 'Font Awesome 5 Free';
            font-weight: 900;
            position: absolute;
            right: 1rem;
            top: 50%;
            transform: translateY(-50%);
            opacity: 0.5;
            transition: opacity 0.3s ease;
        }

        .log-entry.clickable:hover::after {
            opacity: 1;
        }

        /* Chart */
        .chart-card {
            background: rgba(20, 20, 20, 0.9);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px rgba(255, 102, 0, 0.1);
            position: relative;
        }

        /* Hexagon decoration for chart */
        .chart-card::before {
            content: '';
            position: absolute;
            top: 10px;
            right: 10px;
            width: 40px;
            height: 40px;
            background: var(--honey);
            opacity: 0.05;
            clip-path: polygon(30% 0%, 70% 0%, 100% 30%, 100% 70%, 70% 100%, 30% 100%, 0% 70%, 0% 30%);
        }

        .time-chart {
            display: flex;
            align-items: flex-end;
            justify-content: space-around;
            height: 200px;
            padding: 1rem 0;
            gap: 0.5rem;
        }

        .time-bar {
            flex: 1;
            max-width: 30px;
            background: linear-gradient(180deg, var(--primary) 0%, var(--warning) 100%);
            border-radius: 4px 4px 0 0;
            position: relative;
            transition: all 0.3s ease;
            min-height: 5px;
        }

        .time-bar:hover {
            transform: scaleY(1.1);
            filter: brightness(1.2);
        }

        .time-bar-label {
            position: absolute;
            bottom: -25px;
            left: 50%;
            transform: translateX(-50%);
            font-size: 0.65rem;
            color: var(--text-dim);
            white-space: nowrap;
        }

        /* System Info */
        .system-info {
            background: rgba(20, 20, 20, 0.9);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.5rem;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px rgba(255, 102, 0, 0.1);
        }

        .system-stat {
            text-align: center;
        }

        .system-value {
            font-size: 1.5rem;
            font-weight: 600;
            color: var(--primary);
            transition: all 0.3s ease;
        }

        .system-label {
            font-size: 0.85rem;
            color: var(--text-dim);
            margin-top: 0.25rem;
        }

        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 10px;
        }

        ::-webkit-scrollbar-track {
            background: var(--dark);
        }

        ::-webkit-scrollbar-thumb {
            background: var(--border);
            border-radius: 5px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: var(--primary);
        }

        /* Frame Overlay */
        .frame-overlay {
            animation: fadeIn 0.3s ease-in-out;
        }

        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translate(-50%, -50%) scale(0.9);
            }
            to {
                opacity: 1;
                transform: translate(-50%, -50%) scale(1);
            }
        }
    </style>
</head>
<body>
    <!-- Header -->
    <header class="header">
        <div class="header-content">
            <div class="logo">
                <div class="logo-icon">
                    <i class="fas fa-shield-alt"></i>
                </div>
                <h1>VespAI Monitor</h1>
            </div>

            <div class="status-bar">
                <div class="status-item">
                    <div class="live-indicator"></div>
                    <span>Live</span>
                </div>
                <div class="status-item">
                    <i class="fas fa-clock"></i>
                    <span id="current-time"></span>
                </div>
                <div class="status-item">
                    <i class="fas fa-chart-line"></i>
                    <span id="fps">0 FPS</span>
                </div>
            </div>
        </div>
    </header>

    <!-- Container -->
    <div class="container">
        <!-- Stats Grid -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value" id="frame-count">0</div>
                <div class="stat-label">Frames Processed</div>
                <div class="stat-detail" id="uptime">Uptime: 0h 0m</div>
            </div>

            <div class="stat-card danger">
                <div class="stat-value" style="color: var(--danger);" id="velutina-count">0</div>
                <div class="stat-label">Vespa Velutina</div>
                <div class="stat-detail" id="velutina-last">-</div>
            </div>

            <div class="stat-card">
                <div class="stat-value" style="color: var(--warning);" id="crabro-count">0</div>
                <div class="stat-label">Vespa Crabro</div>
                <div class="stat-detail" id="crabro-last">-</div>
            </div>

            <div class="stat-card">
                <div class="stat-value" style="color: var(--success);" id="total-detections">0</div>
                <div class="stat-label">Total Detections</div>
                <div class="stat-detail" id="detection-rate">0/h</div>
            </div>

            <div class="stat-card">
                <div class="stat-value" id="sms-count">0</div>
                <div class="stat-label">SMS Alerts</div>
                <div class="stat-detail" id="last-sms">-</div>
            </div>

            <div class="stat-card">
                <div class="stat-value" id="sms-cost">0.00€</div>
                <div class="stat-label">SMS Costs</div>
                <div class="stat-detail" id="cost-per-sms">-</div>
            </div>
        </div>

        <!-- Main Grid -->
        <div class="main-grid">
            <!-- Video Container -->
            <div class="video-container">
                <div class="video-header">
                    <h2>Live Detection Feed</h2>
                    <div class="video-controls">
                        <div class="live-badge">● LIVE</div>
                        <button class="fullscreen-btn" onclick="toggleFullscreen()">
                            <i class="fas fa-expand"></i> Fullscreen
                        </button>
                    </div>
                </div>
                <img src="/video_feed" alt="Live Feed" class="video-feed" id="video-feed">
            </div>

            <!-- Detection Log -->
            <div class="detection-log">
                <div class="log-header">
                    <h3><i class="fas fa-list"></i> Detection Log</h3>
                </div>
                <div class="log-content" id="log-content">
                    <!-- Logs will be inserted here -->
                </div>
            </div>
        </div>

        <!-- Hourly Chart -->
        <div class="chart-card">
            <h3 style="margin-bottom: 1rem;"><i class="fas fa-chart-bar" style="color: var(--honey);"></i> Detections per Hour (Last 24h)</h3>
            <div class="time-chart" id="hourly-chart">
                <!-- Chart bars will be inserted here -->
            </div>
        </div>

        <!-- System Info -->
        <div class="system-info">
            <div class="system-stat">
                <div class="system-value" id="cpu-temp">0°C</div>
                <div class="system-label">CPU Temp</div>
            </div>
            <div class="system-stat">
                <div class="system-value" id="cpu-usage">0%</div>
                <div class="system-label">CPU Usage</div>
            </div>
            <div class="system-stat">
                <div class="system-value" id="ram-usage">0%</div>
                <div class="system-label">RAM Usage</div>
            </div>
            <div class="system-stat">
                <div class="system-value" id="confidence">80%</div>
                <div class="system-label">Confidence</div>
            </div>
        </div>
    </div>

    <script>
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
                    if (data.cpu_temp !== undefined) document.getElementById('cpu-temp').textContent = data.cpu_temp + '°C';
                    if (data.cpu_usage !== undefined) document.getElementById('cpu-usage').textContent = data.cpu_usage + '%';
                    if (data.ram_usage !== undefined) document.getElementById('ram-usage').textContent = data.ram_usage + '%';
                    if (data.confidence_avg !== undefined) document.getElementById('confidence').textContent = data.confidence_avg.toFixed(0) + '%';

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
    </script>
</body>
</html>
'''


def register_routes(app, stats, hourly_detections, web_frame, web_lock):
    """
    Register all essential web routes with the Flask app.
    
    Args:
        app (Flask): The Flask application instance
        stats (dict): Global statistics dictionary containing detection counts, system stats, etc.
        hourly_detections (dict): Dictionary tracking detections per hour (24-hour format)
        web_frame (numpy.ndarray): Current video frame for streaming
        web_lock (threading.Lock): Thread lock for safe web frame access
    """
    
    @app.route('/')
    def index():
        """
        Serve the main dashboard page with live video feed and statistics.
        
        Returns:
            str: HTML content for the main VespAI dashboard
        """
        return render_template_string(HTML_TEMPLATE)

    @app.route('/video_feed')
    def video_feed():
        """
        Provide live MJPEG video stream from the camera.
        
        This endpoint streams live video frames in Motion JPEG format using 
        multipart HTTP response. Frames are continuously encoded and sent
        to connected clients.
        
        Returns:
            Response: Flask Response object with MJPEG stream mimetype
        """
        def generate():
            """
            Generator function that yields MJPEG frames for streaming.
            
            Yields:
                bytes: MJPEG frame data with HTTP multipart boundaries
            """
            while True:
                with web_lock:
                    if web_frame is not None:
                        # Encode frame to JPEG
                        ret, buffer = cv2.imencode('.jpg', web_frame)
                        if ret:
                            yield (b'--frame\r\n'
                                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

        return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

    @app.route('/api/detection_frame/<frame_id>')
    def get_detection_frame(frame_id):
        """
        Return a specific detection frame as JPEG image.
        
        Args:
            frame_id (str): Unique identifier for the detection frame
            
        Returns:
            Response: JPEG image data or 404 error if frame not found
        """
        if frame_id in stats["detection_frames"]:
            frame = stats["detection_frames"][frame_id]
            ret, buffer = cv2.imencode('.jpg', frame)
            if ret:
                return Response(buffer.tobytes(), mimetype='image/jpeg')
        return "Frame not found", 404

    @app.route('/frame/<frame_id>')
    def serve_detection_frame(frame_id):
        """
        Serve detection frame with HTML page for SMS links and viewing.
        
        This creates a user-friendly HTML page that displays the detection frame
        with navigation options. Primarily used for SMS alert links.
        
        Args:
            frame_id (str): Unique identifier for the detection frame
            
        Returns:
            str: HTML page with detection frame or 404 error message
        """
        print(f"[DEBUG] Requested frame_id: {frame_id}")
        print(f"[DEBUG] Available frames: {list(stats['detection_frames'].keys())}")
        
        if frame_id not in stats["detection_frames"]:
            return f"Frame {frame_id} not found", 404
            
        return render_template_string(FRAME_TEMPLATE, frame_id=frame_id)

    @app.route('/api/frames')
    def list_frames():
        """
        List all available detection frames for debugging purposes.
        
        Returns:
            dict: JSON response containing list of available frame IDs and count
        """
        return jsonify({
            "available_frames": list(stats["detection_frames"].keys()),
            "total_frames": len(stats["detection_frames"])
        })

    @app.route('/api/stats')
    def api_stats():
        """
        Return current system and detection statistics as JSON.
        
        This endpoint provides real-time statistics including:
        - Detection counts (Asian/European hornets, total)
        - System performance (CPU, RAM, temperature, uptime)
        - SMS alert statistics
        - Hourly detection data for charts
        - Recent detection log entries
        
        Returns:
            dict: JSON response with complete system statistics
        """
        # Calculate uptime
        uptime_seconds = (datetime.datetime.now() - stats["start_time"]).total_seconds()
        stats["uptime"] = uptime_seconds

        # Get system stats
        try:
            stats["cpu_usage"] = psutil.cpu_percent(interval=0.1)
            stats["ram_usage"] = psutil.virtual_memory().percent
            stats["disk_usage"] = psutil.disk_usage('/').percent
        except:
            pass

        # CPU temperature (Raspberry Pi)
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = int(f.read()) / 1000
                stats["cpu_temp"] = temp
        except:
            stats["cpu_temp"] = 0

        # Prepare hourly data for chart
        hourly_data = []
        for hour in range(24):
            hourly_data.append({
                "hour": f"{hour:02d}:00",
                "velutina": hourly_detections[hour]["velutina"],
                "crabro": hourly_detections[hour]["crabro"],
                "total": hourly_detections[hour]["velutina"] + hourly_detections[hour]["crabro"]
            })

        response_data = dict(stats)
        response_data["hourly_data"] = hourly_data
        
        # Add missing fields with defaults if not present
        response_data.setdefault("sms_sent", 0)
        response_data.setdefault("sms_cost", 0.0)
        response_data.setdefault("saved_images", 0)
        response_data.setdefault("last_sms_time", None)
        
        # Convert deque to list for JSON serialization
        if "detection_log" in response_data:
            response_data["detection_log"] = list(response_data["detection_log"])
        if "hourly_stats" in response_data:
            response_data["hourly_stats"] = list(response_data["hourly_stats"])
        
        # Format timestamps
        if response_data.get("last_detection_time"):
            response_data["last_detection_time"] = response_data["last_detection_time"].strftime("%H:%M:%S")
        if response_data.get("last_sms_time"):
            response_data["last_sms_time"] = response_data["last_sms_time"].strftime("%H:%M:%S")
            
        if response_data.get("start_time"):
            response_data["start_time"] = response_data["start_time"].strftime("%H:%M:%S")

        return jsonify(response_data)


# HTML Templates extracted from working web_preview.py
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VespAI - Hornet Detection System</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e3c72, #2a5298);
            color: white;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .header p {
            font-size: 1.1rem;
            opacity: 0.9;
        }
        
        .main-grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }
        
        .video-section {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
        }
        
        .video-container {
            position: relative;
            width: 100%;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        
        .video-stream {
            width: 100%;
            height: auto;
            display: block;
        }
        
        .stats-section {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        
        .stat-card {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
            transition: transform 0.3s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
        }
        
        .stat-value {
            font-size: 2rem;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .stat-label {
            font-size: 0.9rem;
            opacity: 0.8;
        }
        
        .velutina { color: #ff4444; }
        .crabro { color: #44ff44; }
        .total { color: #ffaa44; }
        
        .system-stats {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
        }
        
        .system-stats h3 {
            margin-bottom: 15px;
            text-align: center;
        }
        
        .system-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        
        .detections-section {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
        }
        
        .detection-log {
            max-height: 300px;
            overflow-y: auto;
            margin-top: 15px;
        }
        
        .detection-item {
            background: rgba(255,255,255,0.1);
            margin: 5px 0;
            padding: 10px;
            border-radius: 8px;
            border-left: 4px solid #44ff44;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .detection-item:hover {
            background: rgba(255,255,255,0.2);
        }
        
        .detection-item.velutina {
            border-left-color: #ff4444;
        }
        
        .detection-time {
            font-size: 0.8rem;
            opacity: 0.7;
        }
        
        .status-bar {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 15px;
            margin-top: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
            text-align: center;
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            background: #44ff44;
            border-radius: 50%;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        @media (max-width: 768px) {
            .main-grid {
                grid-template-columns: 1fr;
            }
            
            .stats-grid {
                grid-template-columns: 1fr;
            }
            
            .header h1 {
                font-size: 2rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🐝 VespAI Detection System</h1>
            <p>Real-time Asian & European Hornet Detection</p>
        </div>
        
        <div class="main-grid">
            <div class="video-section">
                <h2 style="margin-bottom: 15px;">📹 Live Camera Feed</h2>
                <div class="video-container">
                    <img src="/video_feed" alt="Live Video Feed" class="video-stream">
                </div>
            </div>
            
            <div class="stats-section">
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value velutina" id="velutina-count">0</div>
                        <div class="stat-label">Asian Hornets</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value crabro" id="crabro-count">0</div>
                        <div class="stat-label">European Hornets</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value total" id="total-count">0</div>
                        <div class="stat-label">Total Detections</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="fps">0</div>
                        <div class="stat-label">FPS</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="sms-count">0</div>
                        <div class="stat-label">SMS Alerts</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="sms-cost">0.00€</div>
                        <div class="stat-label">SMS Costs</div>
                    </div>
                </div>
                
                <div class="system-stats">
                    <h3>📊 System Status</h3>
                    <div class="system-grid">
                        <div>CPU: <span id="cpu-usage">0%</span></div>
                        <div>RAM: <span id="ram-usage">0%</span></div>
                        <div>Temp: <span id="cpu-temp">0°C</span></div>
                        <div>Uptime: <span id="uptime">0s</span></div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="detections-section">
            <h2>📋 Recent Detections</h2>
            <div class="detection-log" id="detection-log">
                <p style="opacity: 0.7; text-align: center;">No detections yet...</p>
            </div>
        </div>
        
        <div class="status-bar">
            <span class="status-indicator"></span>
            System Active - Monitoring for hornets...
        </div>
    </div>

    <script>
        function updateStats() {
            fetch('/api/stats')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('velutina-count').textContent = data.total_velutina;
                    document.getElementById('crabro-count').textContent = data.total_crabro;
                    document.getElementById('total-count').textContent = data.total_detections;
                    document.getElementById('fps').textContent = data.fps.toFixed(1);
                    document.getElementById('sms-count').textContent = data.sms_sent;
                    document.getElementById('sms-cost').textContent = data.sms_cost.toFixed(2) + '€';
                    
                    // Update system stats
                    document.getElementById('cpu-usage').textContent = data.cpu_usage.toFixed(1) + '%';
                    document.getElementById('ram-usage').textContent = data.ram_usage.toFixed(1) + '%';
                    document.getElementById('cpu-temp').textContent = data.cpu_temp.toFixed(1) + '°C';
                    
                    // Format uptime
                    const uptime = data.uptime;
                    const hours = Math.floor(uptime / 3600);
                    const minutes = Math.floor((uptime % 3600) / 60);
                    document.getElementById('uptime').textContent = `${hours}h ${minutes}m`;
                    
                    // Update detection log
                    const logDiv = document.getElementById('detection-log');
                    if (data.detection_log && data.detection_log.length > 0) {
                        logDiv.innerHTML = '';
                        data.detection_log.slice(-10).reverse().forEach(detection => {
                            const item = document.createElement('div');
                            item.className = `detection-item ${detection.species === 'velutina' ? 'velutina' : 'crabro'}`;
                            item.onclick = () => window.open(`/frame/${detection.frame_id}`, '_blank');
                            item.innerHTML = `
                                <strong>${detection.species === 'velutina' ? '🐝 Asian Hornet' : '🐛 European Hornet'}</strong>
                                <div class="detection-time">${detection.timestamp} - Confidence: ${detection.confidence}%</div>
                            `;
                            logDiv.appendChild(item);
                        });
                    }
                })
                .catch(error => console.error('Error fetching stats:', error));
        }
        
        // Update every 2 seconds
        setInterval(updateStats, 2000);
        updateStats(); // Initial load
    </script>
</body>
</html>'''

FRAME_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VespAI - Detection Frame</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #1a1a1a;
            color: white;
            margin: 0;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        
        .header {
            text-align: center;
            margin-bottom: 20px;
        }
        
        .frame-container {
            max-width: 90vw;
            max-height: 70vh;
            border: 2px solid #444;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }
        
        .frame-image {
            width: 100%;
            height: auto;
            display: block;
        }
        
        .actions {
            margin-top: 20px;
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            justify-content: center;
        }
        
        .btn {
            padding: 10px 20px;
            background: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
            transition: background 0.3s;
        }
        
        .btn:hover {
            background: #0056b3;
        }
        
        .btn-secondary {
            background: #6c757d;
        }
        
        .btn-secondary:hover {
            background: #545b62;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🐝 VespAI Detection</h1>
        <p>Detection Frame: {{ frame_id }}</p>
    </div>
    
    <div class="frame-container">
        <img src="/api/detection_frame/{{ frame_id }}" alt="Detection Frame" class="frame-image">
    </div>
    
    <div class="actions">
        <a href="/" class="btn">📊 Back to Dashboard</a>
        <a href="/api/detection_frame/{{ frame_id }}" class="btn btn-secondary" download="detection_{{ frame_id }}.jpg">💾 Download Image</a>
    </div>
</body>
</html>'''