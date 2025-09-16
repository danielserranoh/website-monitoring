# system_monitor.py - Enhanced system monitoring for crash detection
import psutil
import time
import json
import logging
from datetime import datetime
import threading
import subprocess
import os

class SystemMonitor:
    def __init__(self, config_file='config.json'):
        self.config = self.load_config(config_file)
        self.log_file = 'system_metrics.log'
        self.interval = self.config['system_monitoring']['monitoring_interval_seconds']
        self.running = False

        # Setup logging
        log_level = getattr(logging, self.config['logging']['level'])
        logging.basicConfig(level=log_level)
        self.logger = logging.getLogger(__name__)

        # Baseline metrics for comparison
        self.baseline_memory = None
        self.baseline_cpu = None

        # Configuration thresholds
        self.memory_spike_threshold = self.config['system_monitoring']['memory_spike_threshold_multiplier']
        self.cpu_threshold = self.config['system_monitoring']['cpu_threshold_percent']
        self.system_memory_critical = self.config['system_monitoring']['system_memory_critical_percent']
        self.network_interval = self.config['system_monitoring']['network_monitoring_interval_seconds']

    def load_config(self, config_file):
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Config file {config_file} not found. Using default values.")
            return self._get_default_config()
        except json.JSONDecodeError:
            print(f"Invalid JSON in config file {config_file}. Using default values.")
            return self._get_default_config()

    def _get_default_config(self):
        """Return default configuration"""
        return {
            'system_monitoring': {
                'monitoring_interval_seconds': 5,
                'memory_spike_threshold_multiplier': 3,
                'cpu_threshold_percent': 80,
                'system_memory_critical_percent': 90,
                'network_monitoring_interval_seconds': 30
            },
            'suspect_services': {
                'curator': {'keywords': ['curator', 'social', 'feed'], 'enabled': True},
                'cookieyes': {'keywords': ['cookie', 'cmp', 'consent'], 'enabled': True},
                'serviceforce': {'keywords': ['serviceforce', 'whatsapp', 'chat'], 'enabled': True}
            },
            'logging': {'level': 'INFO'}
        }

    def start_monitoring(self):
        self.running = True
        monitor_thread = threading.Thread(target=self._monitor_loop)
        monitor_thread.daemon = True
        monitor_thread.start()
        return monitor_thread

    def stop_monitoring(self):
        self.running = False

    def _monitor_loop(self):
        with open(self.log_file, 'w') as f:
            f.write("timestamp,chrome_memory_mb,chrome_cpu_percent,chrome_processes,system_memory_percent,system_cpu_percent,network_connections,suspect_processes\n")

        while self.running:
            try:
                metrics = self._collect_metrics()
                self._log_metrics(metrics)
                self._detect_anomalies(metrics)
                time.sleep(self.interval)
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.interval)

    def _collect_metrics(self):
        try:
            # Chrome/Browser processes
            chrome_processes = []
            try:
                chrome_processes = [p for p in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent', 'cmdline'])
                                   if any(browser in p.info['name'].lower() for browser in ['chrome', 'chromium', 'browser'])]
            except (psutil.AccessDenied, psutil.NoSuchProcess) as e:
                self.logger.warning(f"Could not access some processes: {e}")

            chrome_memory = 0
            chrome_cpu = 0
            try:
                chrome_memory = sum(p.info['memory_info'].rss for p in chrome_processes) / 1024 / 1024
                chrome_cpu = sum(p.info['cpu_percent'] for p in chrome_processes)
            except (psutil.AccessDenied, psutil.NoSuchProcess) as e:
                self.logger.warning(f"Could not get Chrome process metrics: {e}")

            # System metrics
            system_memory = psutil.virtual_memory().percent
            system_cpu = psutil.cpu_percent()

            # Network connections (optional - may fail on macOS without permissions)
            network_connections = 0
            try:
                network_connections = len(psutil.net_connections())
            except (psutil.AccessDenied, PermissionError) as e:
                # This is expected on macOS without special permissions
                pass

            # Look for suspect processes/services
            suspect_processes = self._find_suspect_processes()

            return {
                'timestamp': datetime.now().isoformat(),
                'chrome_memory_mb': chrome_memory,
                'chrome_cpu_percent': chrome_cpu,
                'chrome_processes': len(chrome_processes),
                'system_memory_percent': system_memory,
                'system_cpu_percent': system_cpu,
                'network_connections': network_connections,
                'suspect_processes': suspect_processes
            }
        except Exception as e:
            self.logger.error(f"Error collecting metrics: {e}")
            # Return minimal metrics if collection fails
            return {
                'timestamp': datetime.now().isoformat(),
                'chrome_memory_mb': 0,
                'chrome_cpu_percent': 0,
                'chrome_processes': 0,
                'system_memory_percent': 0,
                'system_cpu_percent': 0,
                'network_connections': 0,
                'suspect_processes': {}
            }

    def _find_suspect_processes(self):
        suspects = {}
        try:
            for service_name, service_config in self.config['suspect_services'].items():
                if service_config['enabled']:
                    suspects[service_name] = []

            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline_list = proc.info.get('cmdline', [])
                    cmdline = ' '.join(cmdline_list) if cmdline_list else ''
                    name = proc.info.get('name', '').lower()

                    # Check each configured suspect service
                    for service_name, service_config in self.config['suspect_services'].items():
                        if service_config['enabled'] and service_name in suspects:
                            keywords = service_config['keywords']
                            if any(keyword in cmdline.lower() or keyword in name for keyword in keywords):
                                try:
                                    memory_mb = proc.memory_info().rss / 1024 / 1024 if proc.is_running() else 0
                                except (psutil.AccessDenied, psutil.NoSuchProcess):
                                    memory_mb = 0

                                suspects[service_name].append({
                                    'pid': proc.info['pid'],
                                    'name': proc.info['name'],
                                    'memory_mb': memory_mb
                                })

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        except Exception as e:
            self.logger.warning(f"Error finding suspect processes: {e}")

        return suspects

    def _log_metrics(self, metrics):
        with open(self.log_file, 'a') as f:
            suspect_count = sum(len(procs) for procs in metrics['suspect_processes'].values())
            f.write(f"{metrics['timestamp']},{metrics['chrome_memory_mb']:.2f},{metrics['chrome_cpu_percent']:.2f},"
                   f"{metrics['chrome_processes']},{metrics['system_memory_percent']:.2f},{metrics['system_cpu_percent']:.2f},"
                   f"{metrics['network_connections']},{suspect_count}\n")

    def _detect_anomalies(self, metrics):
        # Set baseline on first run
        if self.baseline_memory is None:
            self.baseline_memory = metrics['chrome_memory_mb']
            self.baseline_cpu = metrics['chrome_cpu_percent']
            return

        # Detect memory spikes
        if metrics['chrome_memory_mb'] > self.baseline_memory * self.memory_spike_threshold:
            self.logger.warning(f"Memory spike detected: {metrics['chrome_memory_mb']:.2f}MB (baseline: {self.baseline_memory:.2f}MB)")

        # Detect CPU spikes
        if metrics['chrome_cpu_percent'] > self.cpu_threshold:
            self.logger.warning(f"High CPU usage detected: {metrics['chrome_cpu_percent']:.2f}%")

        # Detect system resource exhaustion
        if metrics['system_memory_percent'] > self.system_memory_critical:
            self.logger.critical(f"System memory critically low: {metrics['system_memory_percent']:.2f}%")

        # Log suspect process activity
        for service, processes in metrics['suspect_processes'].items():
            if processes:
                total_memory = sum(p['memory_mb'] for p in processes)
                self.logger.info(f"{service.upper()} processes detected: {len(processes)} processes using {total_memory:.2f}MB")

def monitor_network_activity(config):
    """Monitor network activity for suspect services"""
    try:
        # Use netstat to monitor network connections
        result = subprocess.run(['netstat', '-an'], capture_output=True, text=True)

        # Get suspect keywords from config
        suspect_domains = []
        for service_name, service_config in config['suspect_services'].items():
            if service_config['enabled']:
                suspect_domains.extend(service_config['keywords'])

        active_connections = []

        for line in result.stdout.split('\n'):
            for domain in suspect_domains:
                if domain in line.lower():
                    active_connections.append(line.strip())

        if active_connections:
            with open('network_activity.log', 'a') as f:
                f.write(f"{datetime.now().isoformat()}: {len(active_connections)} suspect connections\n")
                for conn in active_connections:
                    f.write(f"  {conn}\n")

    except Exception as e:
        logging.error(f"Error monitoring network activity: {e}")

def main():
    print("Starting enhanced system monitoring...")
    print("Monitoring for:")
    print("- Chrome/Browser memory and CPU usage")
    print("- System resource utilization")
    print("- Suspect processes (configured services)")
    print("- Network activity")
    print("\nPress Ctrl+C to stop")

    monitor = SystemMonitor()

    # Show enabled suspect services
    enabled_services = [name for name, config in monitor.config['suspect_services'].items() if config['enabled']]
    print(f"Enabled suspect services: {', '.join(enabled_services)}")
    print()

    try:
        # Start system monitoring
        monitor.start_monitoring()

        # Monitor network activity
        while True:
            monitor_network_activity(monitor.config)
            time.sleep(monitor.network_interval)

    except KeyboardInterrupt:
        print("\nStopping monitoring...")
        monitor.stop_monitoring()
        print("Monitoring stopped")

if __name__ == "__main__":
    main()