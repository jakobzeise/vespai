#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VespAI  –  hornet detection & SMS alert with Advanced Web Dashboard
Complete Version with Real-Time Data Integration and Fixed Log Updates

• YOLOv5 hornet detection
• Real-time web dashboard with live statistics
• SMS alerts through Lox24 API
• Automatic data logging and visualization
"""

# ───────────────────────── imports ─────────────────────────
import argparse
import datetime
import logging
import os
import sys
import threading
import time
from collections import deque
from dotenv import load_dotenv

import json

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vespai.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

import RPi.GPIO as GPIO
import cv2
import numpy as np
import psutil
import requests
import torch
from flask import Flask, Response, render_template_string, jsonify

# ───────────────────────── Configuration ─────────────────────────
# Load configuration from environment variables
LOX24_API_KEY = os.getenv("LOX24_API_KEY", "")  # Customer Number:API v2 Key
LOX24_SENDER = os.getenv("LOX24_SENDER", "VespAI")  # Sender name that appears on SMS
PHONE_NUMBER = os.getenv("PHONE_NUMBER", "")  # Target phone number for alerts
SMS_DELAY_MINUTES = int(os.getenv("SMS_DELAY_MINUTES", "5"))  # Minimum delay between SMS messages in minutes

# Web server configuration for SMS links
DOMAIN_NAME = os.getenv("DOMAIN_NAME", "localhost")  # Your domain name
USE_HTTPS = os.getenv("USE_HTTPS", "false").lower() == "true"  # HTTPS enabled
PUBLIC_URL = f"https://{DOMAIN_NAME}" if USE_HTTPS else f"http://{DOMAIN_NAME}"

# Validate critical configuration
if not LOX24_API_KEY and os.getenv("ENABLE_SMS", "true").lower() == "true":
    print("⚠️  Warning: LOX24_API_KEY not set - SMS alerts disabled")
if not PHONE_NUMBER and os.getenv("ENABLE_SMS", "true").lower() == "true":
    print("⚠️  Warning: PHONE_NUMBER not set - SMS alerts disabled")

# ───────────────────────── Flask Web Server ─────────────────────────
app = Flask(__name__)
web_frame = None
web_lock = threading.Lock()

# Real-time statistics
stats = {
    "frame_id": 0,
    "total_velutina": 0,
    "total_crabro": 0,
    "total_detections": 0,
    "fps": 0,
    "last_detection_time": None,
    "start_time": datetime.datetime.now(),
    "detection_log": deque(maxlen=20),  # Keep last 20 detections
    "hourly_stats": deque(maxlen=24),  # Keep last 24 hours
    "cpu_temp": 0,
    "cpu_usage": 0,
    "ram_usage": 0,
    "disk_usage": 0,
    "uptime": 0,
    "saved_images": 0,
    "sms_sent": 0,
    "sms_cost": 0.0,  # Track total SMS costs in EUR
    "confidence_avg": 0,
    "detection_history": [],  # For chart data
    "detection_frames": {},  # Store frames for each detection
    "last_sms_time": None  # Track last SMS sent time for delay
}

# Track detections per hour
hourly_detections = {hour: {"velutina": 0, "crabro": 0} for hour in range(24)}
current_hour = datetime.datetime.now().hour

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
                const entryId = `${entry.time}-${entry.message}`;
                currentIds.add(entryId);

                // Only add if it's a new entry
                if (!logMap.has(entryId)) {
                    const logEntry = document.createElement('div');
                    // Bestimme die Klasse basierend auf dem Typ
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

                    // Update hourly chart only every 10 seconds to prevent flickering
                    const now = Date.now();
                    if (data.hourly_stats && (now - lastChartUpdate > 10000)) {
                        lastChartUpdate = now;
                        const chart = document.getElementById('hourly-chart');
                        chart.innerHTML = '';
                        
                        // Check if we're on mobile (viewport width < 640px)
                        const isMobile = window.innerWidth < 640;
                        
                        if (isMobile) {
                            // Group hours into 6 bars (4 hours each) for mobile
                            const groupedStats = [];
                            const groups = [
                                { label: '1-4h', hours: [] },
                                { label: '5-8h', hours: [] },
                                { label: '9-12h', hours: [] },
                                { label: '13-16h', hours: [] },
                                { label: '17-20h', hours: [] },
                                { label: '21-24h', hours: [] }
                            ];
                            
                            // Group the hourly data
                            data.hourly_stats.forEach(hour => {
                                const groupIndex = Math.floor(hour.hour / 4);
                                if (groupIndex >= 0 && groupIndex < 6) {
                                    if (!groups[groupIndex].hours) groups[groupIndex].hours = [];
                                    groups[groupIndex].hours.push(hour);
                                }
                            });
                            
                            // Calculate totals for each group
                            groups.forEach(group => {
                                const totalVelutina = group.hours.reduce((sum, h) => sum + (h.velutina || 0), 0);
                                const totalCrabro = group.hours.reduce((sum, h) => sum + (h.crabro || 0), 0);
                                groupedStats.push({
                                    label: group.label,
                                    velutina: totalVelutina,
                                    crabro: totalCrabro,
                                    total: totalVelutina + totalCrabro
                                });
                            });
                            
                            const maxVal = Math.max(...groupedStats.map(g => g.total), 1);
                            
                            groupedStats.forEach(group => {
                                const bar = document.createElement('div');
                                bar.className = 'time-bar';
                                const height = Math.max(((group.total / maxVal) * 100), 2);
                                bar.style.height = height + '%';
                                
                                if (group.velutina > 0 && group.crabro > 0) {
                                    bar.style.background = 'linear-gradient(180deg, var(--danger) 0%, var(--honey) 100%)';
                                } else if (group.velutina > 0) {
                                    bar.style.background = 'linear-gradient(180deg, var(--danger) 0%, #ff0066 100%)';
                                } else if (group.crabro > 0) {
                                    bar.style.background = 'linear-gradient(180deg, var(--honey) 0%, var(--honey-dark) 100%)';
                                } else {
                                    bar.style.background = 'rgba(255,255,255,0.1)';
                                }
                                
                                bar.innerHTML = `<span class="time-bar-label">${group.label}</span>`;
                                bar.title = `${group.label} - Velutina: ${group.velutina}, Crabro: ${group.crabro}`;
                                chart.appendChild(bar);
                            });
                        } else {
                            // Desktop view - show all 24 hours
                            const maxVal = Math.max(...data.hourly_stats.map(h => h.total), 1);
                            
                            data.hourly_stats.forEach(hour => {
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
            
            // Try to open in new tab/window
            const newWindow = window.open(frameUrl, '_blank');
            
            // Fallback if popup blocked
            if (!newWindow || newWindow.closed || typeof newWindow.closed == 'undefined') {
                // If popup blocked, navigate to frame in current window
                if (confirm('Open detection frame? (Click OK to view in current window, Cancel to stay here)')) {
                    window.location.href = frameUrl;
                }
            }
        }

        // Update stats every 2 seconds
        setInterval(updateStats, 2000);
        updateStats();
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/video_feed')
def video_feed():
    def generate():
        global web_frame
        while True:
            with web_lock:
                if web_frame is None:
                    continue
                frame = web_frame.copy()

            # Höhere Qualität und keine zusätzliche Verzögerung
            (flag, encodedImage) = cv2.imencode(".jpg", frame,
                                                [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not flag:
                continue

            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' +
                   bytearray(encodedImage) + b'\r\n')

    return Response(generate(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/detection_frame/<frame_id>')
def get_detection_frame(frame_id):
    """Return a specific detection frame"""
    global stats

    if frame_id in stats["detection_frames"]:
        frame = stats["detection_frames"][frame_id]
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        response = Response(buffer.tobytes(), mimetype='image/jpeg')
        return response
    else:
        return "Frame not found", 404


@app.route('/frame/<frame_id>')
def serve_detection_frame(frame_id):
    """Serve detection frame with HTML page for SMS links"""
    global stats

    print(f"[DEBUG] Requested frame_id: {frame_id}")
    print(f"[DEBUG] Available frames: {list(stats['detection_frames'].keys())}")

    if frame_id in stats["detection_frames"]:
        frame = stats["detection_frames"][frame_id]
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        
        # Create HTML page with the image
        html_content = f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VespAI Detection - Frame {frame_id}</title>
    <style>
        body {{
            margin: 0;
            padding: 20px;
            background: #0a0a0a;
            color: white;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            text-align: center;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
        }}
        .header {{
            margin-bottom: 20px;
        }}
        .logo {{
            color: #ff6600;
            font-size: 2rem;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .frame-info {{
            background: rgba(255, 102, 0, 0.1);
            border: 1px solid #ff6600;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
        }}
        .detection-image {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(255, 102, 0, 0.3);
        }}
        .footer {{
            margin-top: 20px;
            font-size: 0.9rem;
            opacity: 0.7;
        }}
        .live-link {{
            display: inline-block;
            margin-top: 15px;
            padding: 10px 20px;
            background: #ff6600;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            transition: background 0.3s;
        }}
        .live-link:hover {{
            background: #ff4400;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">🛡️ VespAI Monitor</div>
            <h1>Hornet Detection</h1>
        </div>
        
        <div class="frame-info">
            <h2>Detection Frame: {frame_id}</h2>
            <p>Captured: {datetime.datetime.now().strftime("%d.%m.%Y at %H:%M:%S")}</p>
        </div>
        
        <img src="/api/detection_frame/{frame_id}" alt="Detection Frame" class="detection-image">
        
        <div class="footer">
            <p>VespAI Hornet Detection System</p>
            <a href="/" class="live-link">📱 View Live Dashboard</a>
        </div>
    </div>
</body>
</html>
        '''
        return html_content
    else:
        return f"Frame not found. Available frames: {list(stats['detection_frames'].keys())}", 404


@app.route('/api/frames')
def list_frames():
    """List all available detection frames for debugging"""
    global stats
    return jsonify({
        "available_frames": list(stats["detection_frames"].keys()),
        "frame_count": len(stats["detection_frames"])
    })


@app.route('/api/stats')
def api_stats():
    """Return current statistics as JSON"""
    global stats, hourly_detections

    # Calculate uptime
    uptime = datetime.datetime.now() - stats["start_time"]
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, _ = divmod(remainder, 60)

    # Get system stats
    try:
        cpu_temp = int(
            open('/sys/class/thermal/thermal_zone0/temp').read()) / 1000
    except:
        cpu_temp = 0

    # Calculate detection rate (per hour)
    if uptime.seconds > 0:
        detection_rate = round(
            (stats["total_detections"] / (uptime.seconds / 3600)), 1)
    else:
        detection_rate = 0

    # Prepare hourly stats for chart
    hourly_stats = []
    current_hour = datetime.datetime.now().hour
    for i in range(24):
        hour = (current_hour - 23 + i) % 24
        hourly_stats.append({
            "hour": hour,
            "velutina": hourly_detections[hour]["velutina"],
            "crabro": hourly_detections[hour]["crabro"],
            "total": hourly_detections[hour]["velutina"] +
                     hourly_detections[hour]["crabro"]
        })

    # Get last detection times
    last_velutina = None
    last_crabro = None
    last_sms = None

    for entry in reversed(list(stats["detection_log"])):
        if not last_velutina and "velutina" in entry.get("type", ""):
            last_velutina = entry["time"].split(" ")[1] if " " in entry[
                "time"] else entry["time"]
        if not last_crabro and "crabro" in entry.get("type", ""):
            last_crabro = entry["time"].split(" ")[1] if " " in entry[
                "time"] else entry["time"]
        if last_velutina and last_crabro:
            break

    return jsonify({
        "frame_id": stats["frame_id"],
        "total_velutina": stats["total_velutina"],
        "total_crabro": stats["total_crabro"],
        "total_detections": stats["total_detections"],
        "fps": stats["fps"],
        "uptime": f"{hours}h {minutes}m",
        "saved_images": stats["saved_images"],
        "sms_sent": stats["sms_sent"],
        "sms_cost": stats["sms_cost"],
        "cpu_temp": round(cpu_temp, 1),
        "cpu_usage": psutil.cpu_percent(),
        "ram_usage": psutil.virtual_memory().percent,
        "disk_usage": stats["disk_usage"],
        "detection_rate": detection_rate,
        "detection_log": list(stats["detection_log"]),
        "hourly_stats": hourly_stats,
        "last_velutina": last_velutina,
        "last_crabro": last_crabro,
        "last_sms": last_sms,
        "confidence_avg": round(stats["confidence_avg"], 1) if stats[
                                                                   "confidence_avg"] > 0 else 80
    })


def start_web_server():
    """Start Flask web server in background thread"""
    print("Starting web server on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)


# ────────────────  Lox24 SMS API  ──────────────────────────

class Lox24SMS:
    def __init__(self, api_key: str, sender_name: str = "VespAI"):
        # For Lox24, we need to split the credentials
        # Format should be "username:password" or just the API token
        self.api_key = api_key
        self.sender_name = sender_name
        self.sms_available = True

        # Try to parse if it's username:password format
        if ":" in api_key:
            self.username, self.password = api_key.split(":", 1)
        else:
            # Use API key as password with empty username
            self.username = ""
            self.password = api_key

    def send_sms(self, to: str, message: str):
        if not self.sms_available:
            print(f"[SMS disabled] Would send: {message}")
            return False

        url = "https://api.lox24.eu/sms"

        try:
            print(f"Sending SMS to {to}: {message[:50]}...")

            data = {
                'sender_id': self.sender_name,
                'text': message,
                'service_code': "direct",
                'phone': to,
                'delivery_at': 0,
                'is_unicode': True,
                'callback_data': '123456',
                'voice_lang': 'DE'
            }

            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'X-LOX24-AUTH-TOKEN': self.api_key,  # Use the token part
            }

            print("Post data : ", json.dumps(data, indent=4))

            # timeout is 100 seconds, the payload is automatically converted to json format
            res = requests.post(url, headers=headers, json=data, timeout=100)
            if res.status_code != 201:  # Created
                print("Error: Wrong response code on create sms")
                if res.status_code == 400:
                    print("Error:400 Invalid input")
                elif res.status_code == 401:
                    print("Error: code = 401 - Client ID or API key isn't active or invalid!")
                elif res.status_code == 402:
                    print("Error:402 There are not enough funds on your account!")
                elif res.status_code == 403:
                    print("Error: code = 403 - Account isn't activated. Please wait or contact to support!")
                elif res.status_code == 404:
                    print("Error:404 Resource not found")
                elif res.status_code in (500, 502, 503, 504):
                    print("System error! Please contact to LOX24 support!")
                else:
                    print(f"Error: code {res.status_code}")
                print("Response: ", res.text)
                return False, 0.0
            else:
                print(f'✓ Success: code = {res.status_code} - SMS sent successfully')
                response_data = res.json()
                print("Response: ", json.dumps(response_data, indent=4))
                
                # Extract cost from response if available
                cost = 0.0
                if 'price' in response_data:
                    cost = float(response_data['price'])
                elif 'cost' in response_data:
                    cost = float(response_data['cost'])
                elif 'total_price' in response_data:
                    cost = float(response_data['total_price'])
                
                return True, cost

        except requests.exceptions.RequestException as e:
            print(f"SMS Error: {e}")
            return False, 0.0

# Initialize Lox24 SMS client
lox24_client = None
print(f"Initializing Lox24 SMS with API key: {LOX24_API_KEY[:10]}...")
try:
    lox24_client = Lox24SMS(api_key=LOX24_API_KEY, sender_name=LOX24_SENDER)
    print(f"Lox24 client created. SMS available: {lox24_client.sms_available}")
    if lox24_client.sms_available:
        print("✓ Lox24 SMS module initialized successfully")
    else:
        print("⚠ Warning: Lox24 API key not configured - SMS disabled")
except Exception as e:
    print(f"✗ Error: Failed to initialize Lox24 SMS: {e}")
    lox24_client = None


def send_sms_with_delay(text: str, force: bool = False):
    """Send SMS with rate limiting - minimum delay between messages"""
    global stats

    # Check if SMS is disabled
    if os.getenv("ENABLE_SMS", "true").lower() != "true":
        logger.info(f"[SMS disabled] Would send: {text}")
        return False

    if not lox24_client:
        logger.warning(f"[SMS client unavailable] Would send: {text}")
        return False

    if not LOX24_API_KEY or not PHONE_NUMBER:
        logger.warning(f"[SMS not configured] Would send: {text}")
        return False

    # Check if enough time has passed since last SMS
    current_time = datetime.datetime.now()

    if not force and stats["last_sms_time"] is not None:
        time_since_last = (current_time - stats[
            "last_sms_time"]).total_seconds() / 60  # in minutes

        if time_since_last < SMS_DELAY_MINUTES:
            remaining = SMS_DELAY_MINUTES - time_since_last
            print(
                f"[SMS Rate Limited] Next SMS allowed in {remaining:.1f} minutes")
            print(f"[Queued Message] {text}")
            return False

    # Send the SMS
    result = lox24_client.send_sms(PHONE_NUMBER, text)
    
    # Handle both old format (bool) and new format (tuple)
    if isinstance(result, tuple):
        success, cost = result
    else:
        success = result
        cost = 0.0

    if success:
        stats["sms_sent"] += 1
        stats["sms_cost"] += cost
        stats["last_sms_time"] = current_time
        print(f"✓ SMS sent: {text}")
        if cost > 0:
            print(f"  Cost: {cost:.3f}€")

        # Update log
        log_entry = {
            "time": current_time.strftime("%H:%M:%S"),
            "message": f"📱 SMS Alert sent: {text}",
            "type": "sms"
        }
        stats["detection_log"].append(log_entry)
        return True
    else:
        print(f"✗ Failed to send SMS: {text}")
        return False


# ─────────────── Main Detection Function ─────────────────────────
def main():
    global web_frame, stats, hourly_detections, current_hour

    # Parse arguments
    argp = argparse.ArgumentParser()
    argp.add_argument("-a", "--min-motion-area", type=int, default=100)
    argp.add_argument("-b", "--brake", type=float, default=0.1)
    argp.add_argument("-c", "--conf", type=float, default=0.8)
    argp.add_argument("-d", "--dilation", type=int, default=1)
    argp.add_argument("-m", "--motion", action="store_true")
    argp.add_argument("-p", "--print", action="store_true")
    argp.add_argument("-rd", "--root", default=os.getcwd())
    argp.add_argument("-s", "--save", action="store_true")
    argp.add_argument("-sd", "--save-dir", default="monitor/detections")
    argp.add_argument("-v", "--video")
    argp.add_argument("-r", "--resolution", default="1920x1080")
    argp.add_argument("--web", action="store_true", help="Enable web server")
    args = argp.parse_args()

    # Parse resolution
    resolution_map = {"4k": (3840, 2160), "1080p": (1920, 1080),
                      "720p": (1280, 720)}
    if args.resolution in resolution_map:
        WIDTH, HEIGHT = resolution_map[args.resolution]
    else:
        try:
            WIDTH, HEIGHT = map(int, args.resolution.split('x'))
        except:
            WIDTH, HEIGHT = 1920, 1080

    print(f"Using resolution: {WIDTH}x{HEIGHT}")

    # Create directories
    if args.save:
        FRAME_DIR = os.path.join(args.save_dir, "frames")
        LABEL_DIR = os.path.join(args.save_dir, "labels")
        RESULT_DIR = os.path.join(args.save_dir, "results")
        for d in (FRAME_DIR, LABEL_DIR, RESULT_DIR):
            os.makedirs(d, exist_ok=True)

    # Initialize Camera
    if args.video:
        cap = cv2.VideoCapture(args.video)
    else:
        print("Initializing Logitech Brio USB webcam...")
        cap = cv2.VideoCapture(0, cv2.CAP_V4L2)

        if not cap.isOpened():
            cap = cv2.VideoCapture("/dev/video0", cv2.CAP_V4L2)
        if not cap.isOpened():
            cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            raise RuntimeError("Cannot open USB webcam!")

        fourcc = cv2.VideoWriter_fourcc('M', 'J', 'P', 'G')
        cap.set(cv2.CAP_PROP_FOURCC, fourcc)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
        cap.set(cv2.CAP_PROP_FPS, 30)

        print(f"Camera initialized")
        time.sleep(2)

    # Load YOLOv5 Model
    print("Loading YOLOv5 model...")
    weights_pt = os.path.join(args.root,
                              "/opt/vespai/models/yolov5-params/yolov5s-all-data.pt")

    # Alternative paths to try if main path doesn't exist
    if not os.path.exists(weights_pt):
        alternative_paths = [
            "yolov5s.pt",  # Default YOLOv5 small model
            "models/yolov5s.pt",
            os.path.join(os.getcwd(), "yolov5s.pt"),
            "yolov5s-all-data.pt"
        ]

        for alt_path in alternative_paths:
            if os.path.exists(alt_path):
                weights_pt = alt_path
                print(f"Using alternative model path: {weights_pt}")
                break

    if not os.path.exists(weights_pt):
        print(f"Error: Model weights not found at {weights_pt}")
        sys.exit(1)

    # Try different loading methods
    model = None

    # Method 1: Try yolov5 package
    try:
        import yolov5
        model = yolov5.load(weights_pt, device='cpu')
        model.conf = args.conf
        print("Model loaded via yolov5 package")
    except ImportError:
        print("yolov5 package not found, trying torch.hub...")

    # Method 2: Try local YOLOv5 directory
    if model is None:
        yolo_dir = os.path.join(args.root, "models/yolov5")
        if os.path.exists(yolo_dir):
            sys.path.insert(0, yolo_dir)
            try:
                model = torch.hub.load(yolo_dir, 'custom',
                                       path=weights_pt,
                                       source='local',
                                       force_reload=False,
                                       _verbose=False)
                model.conf = args.conf
                print("Model loaded from local YOLOv5 directory")
            except Exception as e:
                print(f"Local loading failed: {e}")

    # Method 3: Download from GitHub
    if model is None:
        try:
            model = torch.hub.load('ultralytics/yolov5', 'custom',
                                   path=weights_pt,
                                   force_reload=True,
                                   trust_repo=True,
                                   skip_validation=True,
                                   _verbose=False)
            model.conf = args.conf
            print("Model loaded from GitHub")
        except Exception as e:
            print(f"GitHub loading failed: {e}")
            sys.exit(1)

    if hasattr(model, 'names'):
        print(f"Classes: {model.names}")

    # Start Web Server
    if args.web:
        web_thread = threading.Thread(target=start_web_server)
        web_thread.daemon = True
        web_thread.start()
        time.sleep(2)
        print(f"Web interface: http://{os.uname()[1]}:5000")

    # Initialize variables
    frame_id = 1
    last_fps_time = time.time()
    fps_counter = 0
    total_confidence = 0
    confidence_count = 0

    # Motion detection
    vibe = None
    if args.motion:
        try:
            from vibe import BackgroundSubtractor
            ret0, frame0 = cap.read()
            if ret0 and frame0 is not None:
                vibe = BackgroundSubtractor()
                vibe.init_history(cv2.cvtColor(frame0, cv2.COLOR_BGR2GRAY))
                print("Motion detection enabled")
        except (ImportError, AttributeError) as e:
            print(f"Warning: Motion detection disabled - {e}")
            print("Continuing without motion detection...")
            vibe = None

    print("\nStarting detection loop...")
    print("Press Ctrl+C to stop\n")

    # Main Detection Loop
    try:
        while True:
            loop_start = time.time()
            ret, frame = cap.read()

            if not ret or frame is None:
                time.sleep(0.1)
                continue

            # Update FPS
            fps_counter += 1
            if time.time() - last_fps_time >= 1.0:
                stats["fps"] = fps_counter
                fps_counter = 0
                last_fps_time = time.time()

            # Check for hour change
            new_hour = datetime.datetime.now().hour
            if new_hour != current_hour:
                hourly_detections[current_hour] = {"velutina": 0, "crabro": 0}
                current_hour = new_hour

            # Motion detection
            if vibe:
                grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                seg = vibe.segmentation(grey)
                vibe.update(grey, seg)
                seg = cv2.medianBlur(seg, 3)
                seg = cv2.dilate(seg, None, iterations=args.dilation)
                contours, _ = cv2.findContours(seg, cv2.RETR_EXTERNAL,
                                               cv2.CHAIN_APPROX_SIMPLE)
                run_det = any(
                    cv2.contourArea(c) > args.min_motion_area for c in contours)
            else:
                run_det = True

            if run_det:
                # Run detection
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = model(rgb)

                # Count detections
                preds = results.pred[0]
                ah = 0  # Asian hornet
                eh = 0  # European hornet

                if len(preds) > 0:
                    for pred in preds:
                        x1, y1, x2, y2, conf, cls = pred
                        cls = int(cls)
                        confidence = float(conf)

                        total_confidence += confidence
                        confidence_count += 1

                        if cls == 1:
                            ah += 1
                            stats["total_velutina"] += 1
                            hourly_detections[current_hour]["velutina"] += 1
                            if args.print:
                                print(
                                    f"  Vespa velutina - conf: {confidence:.2f}")
                        elif cls == 0:
                            eh += 1
                            stats["total_crabro"] += 1
                            hourly_detections[current_hour]["crabro"] += 1
                            if args.print:
                                print(
                                    f"  Vespa crabro - conf: {confidence:.2f}")

                # Render results
                results.render()
                annotated = cv2.cvtColor(results.ims[0], cv2.COLOR_RGB2BGR)

                # Add overlay text
                cv2.putText(annotated,
                            f"Frame: {frame_id} | FPS: {stats['fps']}",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                            (0, 255, 0), 2)
                cv2.putText(annotated,
                            f"V: {stats['total_velutina']} | C: {stats['total_crabro']}",
                            (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                            (0, 255, 0), 2)

                # Update web frame - immer updaten, auch ohne Detection
                if args.web:
                    display_frame = cv2.resize(annotated, (960, 540))
                    with web_lock:
                        web_frame = display_frame.copy()

                # If hornets detected
                if ah + eh > 0:
                    stats["total_detections"] += 1
                    detection_time = datetime.datetime.now().strftime(
                        "%H:%M:%S")

                    # Store the annotated frame for this detection
                    detection_key = f"{frame_id}_{detection_time.replace(':', '')}"
                    stats["detection_frames"][detection_key] = annotated.copy()

                    # Keep only last 20 frames to manage memory
                    if len(stats["detection_frames"]) > 20:
                        oldest_key = list(stats["detection_frames"].keys())[0]
                        del stats["detection_frames"][oldest_key]

                    # Add to log with specific type
                    if ah > 0 and eh > 0:
                        # Beide Arten erkannt
                        log_entry = {
                            "time": detection_time,
                            "message": f"Detected: {ah} Velutina, {eh} Crabro",
                            "type": "both",
                            "frame_id": detection_key
                        }
                    elif ah > 0:
                        # Nur Velutina
                        log_entry = {
                            "time": detection_time,
                            "message": f"⚠️ Asian Hornet! {ah} Vespa Velutina detected",
                            "type": "velutina",
                            "frame_id": detection_key
                        }
                    else:
                        # Nur Crabro
                        log_entry = {
                            "time": detection_time,
                            "message": f"European Hornet: {eh} Vespa Crabro detected",
                            "type": "crabro",
                            "frame_id": detection_key
                        }

                    stats["detection_log"].append(log_entry)

                    print(
                        f">>> Detection #{stats['total_detections']} at frame {frame_id}")
                    print(f"    Velutina: {ah}, Crabro: {eh}")

                    # Save if enabled
                    if args.save:
                        ts = datetime.datetime.now().strftime(
                            "%d.%m.%Y-%H:%M:%S")
                        rname = os.path.join(RESULT_DIR, f"{ts}.jpeg")
                        fname = os.path.join(FRAME_DIR, f"{ts}.jpeg")

                        cv2.imwrite(rname, annotated)
                        cv2.imwrite(fname, frame)
                        stats["saved_images"] += 1

                        # Calculate disk usage
                        try:
                            stats["disk_usage"] = sum(
                                os.path.getsize(os.path.join(RESULT_DIR, f))
                                for f in os.listdir(RESULT_DIR) if
                                os.path.isfile(os.path.join(RESULT_DIR, f)))
                        except:
                            pass

                        # Send SMS alert with delay and frame URL
                        frame_url = f"{PUBLIC_URL}/frame/{detection_key}"
                        
                        if ah > 0:  # Asian hornet detected - high priority
                            sms_text = f"⚠️ ALERT: {ah} Asian Hornet(s) detected at {datetime.datetime.now().strftime('%H:%M')}! View image: {frame_url}"
                            send_sms_with_delay(sms_text)
                        elif eh > 0:  # Only European hornet
                            sms_text = f"ℹ️ Info: {eh} European Hornet(s) detected at {datetime.datetime.now().strftime('%H:%M')}. View: {frame_url}"
                            send_sms_with_delay(sms_text)

                # Update average confidence
                if confidence_count > 0:
                    stats["confidence_avg"] = (
                                                      total_confidence / confidence_count) * 100

            stats["frame_id"] = frame_id
            frame_id += 1

            # Frame rate limiting
            delay = args.brake - (time.time() - loop_start)
            if delay > 0:
                time.sleep(delay)

    except KeyboardInterrupt:
        print("\n\nStopping detection...")

    # Cleanup
    print("Cleaning up...")
    cap.release()

    try:
        GPIO.cleanup()
    except:
        pass

    print(f"\nFinal Statistics:")
    print(f"  Frames: {frame_id}")
    print(f"  Detections: {stats['total_detections']}")
    print(f"  Velutina: {stats['total_velutina']}")
    print(f"  Crabro: {stats['total_crabro']}")


if __name__ == '__main__':
    main()
