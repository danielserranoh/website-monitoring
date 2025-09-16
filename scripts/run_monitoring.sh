#!/bin/bash

# Website Monitoring Script
# This script runs both the website monitor and system monitor in parallel

echo "Starting Website Performance Monitoring System"
echo "=============================================="

# Check if config.json exists, if not create it interactively
if [ ! -f "config/config.json" ]; then
    echo "Config file not found. Setting up configuration..."

    # Prompt for URL
    read -p "Enter the website URL to monitor: " TARGET_URL
    if [[ ! $TARGET_URL =~ ^https?:// ]]; then
        TARGET_URL="https://$TARGET_URL"
    fi

    # Prompt for reload interval
    read -p "Enter reload interval in seconds (default 90): " RELOAD_INTERVAL
    RELOAD_INTERVAL=${RELOAD_INTERVAL:-90}

    # Create config directory and config.json
    mkdir -p config
    cat > config/config.json << EOF
{
  "monitoring": {
    "target_url": "$TARGET_URL",
    "reload_interval_seconds": $RELOAD_INTERVAL,
    "page_timeout_ms": 30000,
    "headless_browser": false,
    "wait_for_networkidle": true
  },
  "system_monitoring": {
    "monitoring_interval_seconds": 5,
    "memory_spike_threshold_multiplier": 3,
    "cpu_threshold_percent": 80,
    "system_memory_critical_percent": 90,
    "network_monitoring_interval_seconds": 30
  },
  "suspect_services": {
    "curator": {
      "keywords": ["curator", "social-network", "feed"],
      "enabled": true
    },
    "cookieyes": {
      "keywords": ["cookieyes", "cookie-consent", "cmp"],
      "enabled": true
    },
    "serviceforce": {
      "keywords": ["serviceforce", "whatsapp", "chat"],
      "enabled": true
    }
  },
  "output": {
    "screenshots_enabled": true,
    "performance_logging": true,
    "console_logging": true,
    "reports_directory": "reports",
    "screenshots_directory": "screenshots",
    "logs_directory": "logs"
  },
  "logging": {
    "level": "INFO",
    "console_output": true,
    "file_output": true,
    "log_file": "monitoring.log"
  }
}
EOF

    echo "Configuration saved to config/config.json"
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install requirements
echo "Installing dependencies..."
pip install -r requirements.txt

# Install Playwright browsers
echo "Installing Playwright browsers..."
playwright install chromium

# Create necessary directories
mkdir -p reports screenshots logs

# Backup existing logs with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
if [ -f "logs/monitoring.log" ] || [ -f "logs/website_monitor.log" ] || [ -f "logs/system_monitor.log" ] || [ -f "logs/system_metrics.log" ] || [ -d "reports" ]; then
    echo "Backing up existing logs..."
    BACKUP_DIR="logs/backup_$TIMESTAMP"
    mkdir -p "$BACKUP_DIR"

    # Backup log files from logs directory
    [ -f "logs/monitoring.log" ] && mv "logs/monitoring.log" "$BACKUP_DIR/"
    [ -f "logs/website_monitor.log" ] && mv "logs/website_monitor.log" "$BACKUP_DIR/"
    [ -f "logs/system_monitor.log" ] && mv "logs/system_monitor.log" "$BACKUP_DIR/"
    [ -f "logs/system_metrics.log" ] && mv "logs/system_metrics.log" "$BACKUP_DIR/"
    [ -f "logs/network_activity.log" ] && mv "logs/network_activity.log" "$BACKUP_DIR/"

    # Also check for legacy log files in root (for backward compatibility)
    [ -f "monitoring.log" ] && mv "monitoring.log" "$BACKUP_DIR/"
    [ -f "website_monitor.log" ] && mv "website_monitor.log" "$BACKUP_DIR/"
    [ -f "system_monitor.log" ] && mv "system_monitor.log" "$BACKUP_DIR/"
    [ -f "system_metrics.log" ] && mv "system_metrics.log" "$BACKUP_DIR/"
    [ -f "network_activity.log" ] && mv "network_activity.log" "$BACKUP_DIR/"

    # Backup reports and screenshots (if they exist)
    if [ -d "reports" ] && [ "$(ls -A reports 2>/dev/null)" ]; then
        cp -r reports "$BACKUP_DIR/"
    fi
    if [ -d "screenshots" ] && [ "$(ls -A screenshots 2>/dev/null)" ]; then
        cp -r screenshots "$BACKUP_DIR/"
    fi

    echo "Logs backed up to: $BACKUP_DIR"
fi

# Clean up for fresh start
echo "Starting fresh monitoring session..."
rm -f *.log  # Clean any legacy logs in root
rm -f logs/*.log  # Clean active logs
rm -rf reports/* screenshots/*
mkdir -p reports screenshots logs

# Display current configuration
echo ""
echo "Current Configuration:"
echo "====================="
TARGET_URL=$(python3 -c "import json; print(json.load(open('config/config.json'))['monitoring']['target_url'])")
RELOAD_INTERVAL=$(python3 -c "import json; print(json.load(open('config/config.json'))['monitoring']['reload_interval_seconds'])")
echo "Target URL: $TARGET_URL"
echo "Reload Interval: $RELOAD_INTERVAL seconds"
echo ""

# Function to cleanup background processes
cleanup() {
    echo "Stopping monitoring processes..."
    kill $SYSTEM_PID 2>/dev/null
    kill $WEBSITE_PID 2>/dev/null
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

# Start system monitoring in background
echo "Starting system monitoring..."
python3 -m src.monitors.system_monitor > logs/system_monitor.log 2>&1 &
SYSTEM_PID=$!

# Wait a moment for system monitor to start
sleep 2

# Start website monitoring in background
echo "Starting website monitoring..."
python3 main.py > logs/website_monitor.log 2>&1 &
WEBSITE_PID=$!

# Wait a moment for website monitor to start
sleep 3

echo "Monitoring active. Logs are being written to:"
echo "- Website Monitor: logs/website_monitor.log"
echo "- System Monitor: logs/system_monitor.log"
echo "- Combined Log: logs/monitoring.log"
echo ""
echo "Press Ctrl+C to stop monitoring..."

# Monitor the processes and show status
RELOAD_COUNT=0
START_TIME=$(date +%s)
while kill -0 $WEBSITE_PID 2>/dev/null && kill -0 $SYSTEM_PID 2>/dev/null; do
    sleep 30

    # Calculate runtime
    CURRENT_TIME=$(date +%s)
    RUNTIME=$((CURRENT_TIME - START_TIME))
    RUNTIME_MIN=$((RUNTIME / 60))
    RUNTIME_SEC=$((RUNTIME % 60))

    # Check reload count from logs
    if [ -f "logs/website_monitor.log" ]; then
        NEW_RELOAD_COUNT=$(grep -c "Reload #" logs/website_monitor.log 2>/dev/null || echo "0")
        if [ "$NEW_RELOAD_COUNT" != "$RELOAD_COUNT" ]; then
            RELOAD_COUNT=$NEW_RELOAD_COUNT
            echo "$(date): ✅ Page reload #$RELOAD_COUNT completed"
        fi
    fi

    # Show comprehensive status
    echo "$(date): 🔍 Monitoring active - Runtime: ${RUNTIME_MIN}m ${RUNTIME_SEC}s"
    echo "  📊 Website Monitor (PID: $WEBSITE_PID) - Reloads: $RELOAD_COUNT"
    echo "  💻 System Monitor (PID: $SYSTEM_PID) - Tracking Chrome & suspects"

    # Show recent alerts if any
    if [ -f "logs/system_monitor.log" ]; then
        RECENT_ALERTS=$(tail -5 logs/system_monitor.log | grep -E "(WARNING|ERROR)" | wc -l)
        if [ "$RECENT_ALERTS" -gt 0 ]; then
            echo "  ⚠️  Recent alerts: $RECENT_ALERTS (check logs/system_monitor.log)"
        fi
    fi

    echo "  💾 Logs: logs/website_monitor.log | logs/system_monitor.log | logs/monitoring.log"
    echo ""
done

# Check which process died
if ! kill -0 $WEBSITE_PID 2>/dev/null; then
    echo "Website monitoring process stopped unexpectedly"
    echo "Check logs/website_monitor.log for details"
fi

if ! kill -0 $SYSTEM_PID 2>/dev/null; then
    echo "System monitoring process stopped unexpectedly"
    echo "Check logs/system_monitor.log for details"
fi

# Cleanup
cleanup