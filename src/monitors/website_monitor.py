"""
Website Monitor

Handles automated website monitoring, page reloading, and crash detection.
"""

import asyncio
import time
import json
import logging
from datetime import datetime
from playwright.async_api import async_playwright
import psutil
import os


class WebsiteMonitor:
    def __init__(self, config_file='config/config.json'):
        self.config = self.load_config(config_file)
        self.target_url = self.config['monitoring']['target_url']
        self.reload_interval = self.config['monitoring']['reload_interval_seconds']
        self.page_timeout = self.config['monitoring']['page_timeout_ms']
        self.headless = self.config['monitoring']['headless_browser']
        self.wait_networkidle = self.config['monitoring']['wait_for_networkidle']

        self.session_start = datetime.now()
        self.reload_count = 0
        self.crash_detected = False

        # Setup logging
        log_level = getattr(logging, self.config['logging']['level'])
        handlers = []

        if self.config['logging']['file_output']:
            handlers.append(logging.FileHandler(self.config['logging']['log_file']))
        if self.config['logging']['console_output']:
            handlers.append(logging.StreamHandler())

        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=handlers
        )
        self.logger = logging.getLogger(__name__)

        # Ensure directories exist
        os.makedirs(self.config['output']['reports_directory'], exist_ok=True)
        os.makedirs(self.config['output']['screenshots_directory'], exist_ok=True)
        if 'logs_directory' in self.config['output']:
            os.makedirs(self.config['output']['logs_directory'], exist_ok=True)

    def load_config(self, config_file):
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Config file {config_file} not found. Please check the path.")
            raise
        except json.JSONDecodeError:
            print(f"Invalid JSON in config file {config_file}.")
            raise

    async def start_monitoring(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context()
            page = await context.new_page()

            # Enable console and error logging
            if self.config['output']['console_logging']:
                page.on("console", lambda msg: self.logger.info(f"Console: {msg.text}"))
                page.on("pageerror", lambda error: self.logger.error(f"Page error: {error}"))

            # Monitor network requests for suspect services
            self._setup_network_monitoring(page)

            self.logger.info(f"Starting monitoring session for {self.target_url}")

            try:
                while not self.crash_detected:
                    start_time = time.time()
                    self.reload_count += 1

                    try:
                        self.logger.info(f"Reload #{self.reload_count} - Loading {self.target_url}")

                        # Wait for network idle if configured
                        wait_until = 'networkidle' if self.wait_networkidle else 'load'
                        await page.goto(self.target_url, timeout=self.page_timeout, wait_until=wait_until)

                        load_time = time.time() - start_time

                        # Take screenshot
                        if self.config['output']['screenshots_enabled']:
                            screenshot_dir = self.config['output']['screenshots_directory']
                            await page.screenshot(path=f"{screenshot_dir}/reload_{self.reload_count}_{int(time.time())}.png")

                        self.logger.info(f"Reload #{self.reload_count} completed in {load_time:.2f}s")

                        # Capture performance metrics
                        await self.capture_performance_metrics(page, load_time)

                    except Exception as e:
                        self.logger.error(f"Crash detected on reload #{self.reload_count}: {str(e)}")
                        await self.capture_crash_data(page, "page_load_timeout", str(e))
                        self.crash_detected = True
                        break

                    # Wait before next reload
                    await asyncio.sleep(self.reload_interval)

            finally:
                await browser.close()

    def _setup_network_monitoring(self, page):
        """Setup network request monitoring for suspect services"""
        suspect_keywords = []
        for service_name, service_config in self.config['suspect_services'].items():
            if service_config.get('enabled', True):
                suspect_keywords.extend(service_config.get('keywords', []))

        def handle_request(request):
            url = request.url.lower()
            for keyword in suspect_keywords:
                if keyword.lower() in url:
                    self.logger.info(f"Suspect service request: {request.url}")
                    break

        def handle_response(response):
            url = response.url.lower()
            for keyword in suspect_keywords:
                if keyword.lower() in url:
                    self.logger.info(f"Suspect service request: {response.url} - Status: {response.status}")
                    break

        page.on("request", handle_request)
        page.on("response", handle_response)

    async def capture_performance_metrics(self, page, load_time):
        """Capture detailed performance metrics"""
        try:
            # Get performance data from the page
            metrics = await page.evaluate("""
                () => {
                    const navigation = performance.getEntriesByType('navigation')[0];
                    const paint = performance.getEntriesByType('paint');

                    return {
                        dom_content_loaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
                        load_event: navigation.loadEventEnd - navigation.loadEventStart,
                        first_paint: paint.find(p => p.name === 'first-paint')?.startTime || 0,
                        first_contentful_paint: paint.find(p => p.name === 'first-contentful-paint')?.startTime || 0,
                        memory_usage: performance.memory ? performance.memory.usedJSHeapSize : 0,
                        js_heap_size_limit: performance.memory ? performance.memory.jsHeapSizeLimit : 0,
                        total_js_heap_size: performance.memory ? performance.memory.totalJSHeapSize : 0,
                        resource_count: performance.getEntriesByType('resource').length
                    };
                }
            """)

            # Add system metrics (include JS heap data from page metrics)
            js_heap_mb = (metrics.get('memory_usage', 0) / 1024 / 1024) if metrics.get('memory_usage') else 0
            system_metrics = self.get_system_metrics(js_heap_mb)

            performance_data = {
                'timestamp': datetime.now().isoformat(),
                'reload_count': self.reload_count,
                'load_time': load_time,
                'page_metrics': metrics,
                'system_metrics': system_metrics
            }

            # Save to file
            if self.config['output']['performance_logging']:
                reports_dir = self.config['output']['reports_directory']
                with open(f'{reports_dir}/performance_data.jsonl', 'a') as f:
                    f.write(json.dumps(performance_data) + '\n')

        except Exception as e:
            self.logger.error(f"Error capturing performance metrics: {str(e)}")

    def get_system_metrics(self, js_heap_mb=0):
        chrome_processes = [p for p in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent'])
                          if 'chrome' in p.info['name'].lower()]

        total_memory = sum(p.info['memory_info'].rss for p in chrome_processes) / 1024 / 1024
        total_cpu = sum(p.info['cpu_percent'] for p in chrome_processes)

        return {
            'chrome_memory_mb': total_memory,
            'chrome_cpu_percent': total_cpu,
            'chrome_process_count': len(chrome_processes),
            'system_memory_percent': psutil.virtual_memory().percent,
            'system_cpu_percent': psutil.cpu_percent(),
            'js_heap_mb': js_heap_mb
        }

    async def capture_crash_data(self, page, crash_type, error_details=None):
        crash_data = {
            'timestamp': datetime.now().isoformat(),
            'crash_type': crash_type,
            'reload_count': self.reload_count,
            'session_duration': (datetime.now() - self.session_start).total_seconds(),
            'error_details': error_details,
            'target_url': self.target_url,
            'system_metrics': self.get_system_metrics()
        }

        # Save crash data
        reports_dir = self.config['output']['reports_directory']
        with open(f'{reports_dir}/crash_data.json', 'w') as f:
            json.dump(crash_data, f, indent=2)

        # Capture crash screenshot
        if self.config['output']['screenshots_enabled']:
            try:
                screenshot_dir = self.config['output']['screenshots_directory']
                await page.screenshot(path=f"{screenshot_dir}/crash_{int(time.time())}.png")
            except Exception as e:
                self.logger.error(f"Failed to capture crash screenshot: {str(e)}")

        # Capture page content
        try:
            page_content = await page.content()
            with open(f'{reports_dir}/crash_page_{int(time.time())}.html', 'w') as f:
                f.write(page_content)
        except Exception as e:
            self.logger.error(f"Failed to capture page content: {str(e)}")

        self.logger.critical(f"Crash data saved: {crash_type}")