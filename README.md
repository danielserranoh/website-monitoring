# Website Crash Monitoring System

A comprehensive Python-based monitoring tool using Playwright to detect and analyze random website crashes. Designed to identify the root cause of unpredictable crashes by continuously monitoring website performance, system resources, and suspect services.

## 🎯 Purpose

This monitoring system is specifically designed to catch random, unpredictable website crashes and identify their root cause. It continuously reloads the website every 1-2 minutes while collecting detailed performance and system metrics until a crash occurs.

## 🔍 Suspect Services Monitoring

The system specifically monitors these suspected crash culprits:
- **Curator**: Social network data loading service
- **CookieYes**: Cookie consent management platform (CMP)
- **ServiceForce**: WhatsApp chat service integration

## ✨ Features

- **Automated Website Monitoring**: Continuous page reloading with crash detection
- **Advanced Memory Leak Detection**: Real-time detection of memory growth patterns and leaks
- **System Resource Tracking**: Chrome memory/CPU usage and system performance
- **Suspect Service Detection**: Monitors processes and network activity for known suspects
- **Comprehensive Crash Data**: Screenshots, page content, and system state at crash time
- **Performance Metrics**: Core Web Vitals and loading performance with JavaScript heap analysis
- **Post-Crash Analysis**: Data correlation and pattern identification
- **Anomaly Detection**: Baseline comparison and threshold monitoring
- **Flexible Execution Modes**: Website-only, system-only, or combined monitoring
- **Professional CLI Interface**: Command-line options for different use cases
- **Automatic Log Backup**: Timestamped backup system preserves historical data
- **Modular Architecture**: Clean separation of concerns for easy extension
- **JSON Configuration**: Fully configurable monitoring parameters
- **Robust Error Handling**: Graceful handling of permissions and system limitations

## 📋 Prerequisites

- Python 3.8 or higher
- Node.js (for Playwright browser installation)

## 🚀 Quick Start

1. **Easy Installation & Run**:
```bash
chmod +x scripts/run_monitoring.sh
./scripts/run_monitoring.sh
```

2. **Manual Installation**:
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
playwright install chromium
```

## 🎮 Usage

### Option 1: Automated Script (Recommended)
```bash
./scripts/run_monitoring.sh
```

### Option 2: Professional CLI Interface
```bash
# Combined monitoring (default)
python main.py

# Website monitoring only
python main.py --website-only

# System monitoring only
python main.py --system-only

# Run analysis on existing data
python main.py --analyze

# Use custom configuration
python main.py --config config/production.json

# Enable verbose logging
python main.py --verbose

# Get help
python main.py --help
```

### Option 3: Legacy Manual Execution
```bash
# For backward compatibility, you can still run components separately
python -m src.monitors.website_monitor
python -m src.monitors.system_monitor
```

## 📊 System Architecture

### **src/monitors/** - Monitoring Components
- **WebsiteMonitor**: Automated page reloading, network monitoring, crash detection
- **SystemMonitor**: Chrome/browser memory tracking, system resource monitoring
- **Real-time integration**: Memory leak detection and anomaly detection

### **src/detectors/** - Detection Systems
- **MemoryLeakDetector**: Advanced memory leak detection with trend analysis
- **Multi-layer detection**: Trend analysis, garbage collection monitoring, baseline comparison
- **Configurable thresholds**: Chrome memory, JS heap, per-reload analysis

### **src/analysis/** - Post-Event Analysis
- **CrashAnalyzer**: Crash pattern analysis and correlation
- **Pre-crash behavior identification**: System behavior leading to crashes
- **Data visualization**: Comprehensive reporting and trend charts

### **src/utils/** - Support Systems
- **ConfigManager**: Centralized configuration with validation
- **Logger**: Professional logging system with component-specific loggers
- **Modular design**: Easy to extend and maintain

## 📈 Performance Metrics

The system tracks:
- **Core Web Vitals**: FCP, LCP, CLS
- **Page Performance**: Load times, DOM content loaded
- **Memory Usage**: JavaScript heap, Chrome processes, system memory
- **System Resources**: CPU, memory, network connections
- **Suspect Activity**: Process detection, network requests

## 🔍 Memory Leak Detection

Advanced memory leak detection with multiple detection strategies:

### **Detection Patterns**
- **Short-term rapid growth**: >10MB/min over 5 minutes
- **Medium-term sustained growth**: >500MB over 30 minutes
- **Long-term percentage growth**: >200% from baseline
- **Garbage collection failures**: No GC for >5 minutes
- **Per-reload memory leaks**: >10MB cumulative per reload
- **Memory spikes**: Sudden 50%+ increases

### **Analysis Features**
- **Baseline establishment**: Automatic baseline from first 10 samples
- **Trend analysis**: Linear regression with R-squared correlation
- **Cross-reload tracking**: Memory growth patterns across page reloads
- **Configurable sensitivity**: Adjustable thresholds for different environments
- **Real-time alerts**: Immediate warnings when leak patterns detected

## 📁 Data Output

### Reports Directory (`reports/`)
- `performance_data.jsonl` - Performance metrics per reload
- `crash_data.json` - Detailed crash information
- `crash_analysis_report.txt` - Comprehensive analysis report
- `crash_page_*.html` - HTML content at crash time
- `plots/` - Data visualization charts

### Other Outputs
- `system_metrics.log` - Continuous system monitoring data
- `monitoring.log` - Complete activity and error log
- `screenshots/` - Visual evidence at reload and crash times
- `network_activity.log` - Suspect service network activity

## 🕵️ Crash Detection Strategy

1. **Continuous Monitoring**: Reload website every 1-2 minutes
2. **Resource Tracking**: Monitor memory, CPU, and network usage
3. **Service Monitoring**: Track suspect services (curator, cookieyes, serviceforce)
4. **Crash Capture**: Detect exceptions, HTTP errors, and timeouts
5. **Data Correlation**: Link crash events with system metrics
6. **Pattern Analysis**: Identify trends leading to crashes

## 🔧 Configuration

The system uses `config/config.json` for all configuration. The new ConfigManager provides validation and defaults. If no config exists, the system will create one interactively.

### Configuration File Structure

```json
{
  "monitoring": {
    "target_url": "https://example.com",
    "reload_interval_seconds": 90,
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
```

### Key Configuration Options

#### Monitoring Settings
- `target_url`: Website to monitor (leave empty for interactive prompt)
- `reload_interval_seconds`: Time between page reloads (default: 90)
- `page_timeout_ms`: Maximum time to wait for page load (default: 30000)
- `headless_browser`: Run browser in headless mode (default: false)
- `wait_for_networkidle`: Wait for network idle before considering page loaded

#### System Monitoring
- `monitoring_interval_seconds`: How often to collect system metrics (default: 5)
- `memory_spike_threshold_multiplier`: Memory spike detection threshold (default: 3x baseline)
- `cpu_threshold_percent`: High CPU usage threshold (default: 80%)
- `system_memory_critical_percent`: Critical system memory threshold (default: 90%)

#### Suspect Services
Each suspect service can be:
- **Enabled/Disabled**: Set `"enabled": true/false`
- **Customized**: Add keywords to monitor in the `"keywords"` array
- **Extended**: Add new suspect services by adding new entries

#### Output Control
- `screenshots_enabled`: Capture screenshots during monitoring
- `performance_logging`: Save performance metrics to files
- `console_logging`: Log console errors and warnings
- Custom directory paths for reports, screenshots, and logs

## 📊 Analysis and Reports

After crashes occur, run the analysis tool:
```bash
python analyze_crash_data.py
```

This generates:
- Crash frequency analysis
- Suspect service correlation scores
- Pre-crash behavior patterns
- Memory and CPU trend analysis
- Actionable recommendations

## 🎯 Expected Workflow

1. **Start Monitoring**: Run `./run_monitoring.sh` (automatically backs up existing logs)
2. **Monitor Status**: Real-time updates every 30 seconds show progress and alerts
3. **Wait for Crash**: System runs until crash detected (or manually stopped)
4. **Analyze Data**: Run `python analyze_crash_data.py` to correlate crash patterns
5. **Review Reports**: Check `reports/crash_analysis_report.txt` for insights
6. **Identify Culprit**: Use suspect rankings and timeline data to focus investigation

## 🔧 Monitoring Status Explained

The enhanced status reporting shows:
```bash
🔍 Monitoring active - Runtime: 5m 30s
  📊 Website Monitor (PID: 13073) - Reloads: 8
  💻 System Monitor (PID: 13065) - Tracking Chrome & suspects
  ⚠️  Recent alerts: 1 (check system_monitor.log)
  💾 Logs: website_monitor.log | system_monitor.log | monitoring.log
```

- **Runtime**: Total monitoring session duration
- **PID numbers**: Process IDs for the two monitoring components
- **Reloads**: Number of successful page reloads completed
- **Recent alerts**: System warnings (high CPU, memory spikes, etc.)
- **Log files**: Where to find detailed monitoring data

## 🗂️ Automatic Log Management

The system automatically handles log organization:
- **Backup on start**: Existing logs moved to `logs/backup_YYYYMMDD_HHMMSS/`
- **Fresh session**: Each run starts with clean logs for clear analysis
- **Historical preservation**: Previous monitoring sessions saved for comparison

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

MIT License