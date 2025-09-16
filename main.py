import asyncio
import time
import json
import logging
from datetime import datetime
from playwright.async_api import async_playwright
import threading
import psutil
import os

class WebsiteMonitor:
    def __init__(self, config_file='config.json'):
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
            print(f"Config file {config_file} not found. Please create it or use default values.")
            raise
        except json.JSONDecodeError:
            print(f"Invalid JSON in config file {config_file}")
            raise

    async def monitor_website(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context()
            page = await context.new_page()

            # Enable network monitoring
            page.on("response", self.log_network_response)
            page.on("console", self.log_console_message)
            page.on("pageerror", self.log_page_error)

            while not self.crash_detected:
                try:
                    self.reload_count += 1
                    start_time = time.time()

                    self.logger.info(f"Reload #{self.reload_count} - Loading {self.target_url}")

                    # Navigate to page
                    wait_until = "networkidle" if self.wait_networkidle else "load"
                    response = await page.goto(self.target_url, wait_until=wait_until, timeout=self.page_timeout)
                    load_time = time.time() - start_time

                    # Check if page loaded successfully
                    if response.status >= 400:
                        self.logger.error(f"HTTP Error: {response.status}")
                        await self.capture_crash_data(page, "HTTP_ERROR")
                        break

                    # Wait for suspect services to load
                    await self.monitor_suspect_services(page)

                    # Capture performance metrics
                    await self.capture_performance_metrics(page, load_time)

                    # Take screenshot
                    if self.config['output']['screenshots_enabled']:
                        screenshot_dir = self.config['output']['screenshots_directory']
                        await page.screenshot(path=f"{screenshot_dir}/reload_{self.reload_count}_{int(time.time())}.png")

                    self.logger.info(f"Reload #{self.reload_count} completed in {load_time:.2f}s")

                    # Wait before next reload
                    await asyncio.sleep(self.reload_interval)

                except Exception as e:
                    self.logger.error(f"Crash detected on reload #{self.reload_count}: {str(e)}")
                    await self.capture_crash_data(page, "EXCEPTION", str(e))
                    self.crash_detected = True
                    break

            await browser.close()

    async def monitor_suspect_services(self, page):
        suspects = {}
        for service_name, service_config in self.config['suspect_services'].items():
            if service_config['enabled']:
                suspects[service_name] = service_config['keywords']

        for service, keywords in suspects.items():
            try:
                # Check network requests for these services
                await page.wait_for_timeout(1000)  # Give time for requests

                # Monitor console for service-related errors
                await page.evaluate(f"""
                    console.log('Checking {service} service status');
                    // Check if service is loaded
                    if (window.{service} || document.querySelector('[data-service="{service}"]')) {{
                        console.log('{service} detected and loaded');
                    }}
                """)
            except Exception as e:
                self.logger.warning(f"Error monitoring {service}: {str(e)}")

    async def capture_performance_metrics(self, page, load_time):
        try:
            # Get Core Web Vitals and performance metrics
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
                        resource_count: performance.getEntriesByType('resource').length
                    };
                }
            """)

            # Add system metrics
            system_metrics = self.get_system_metrics()

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

    def get_system_metrics(self):
        chrome_processes = [p for p in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent'])
                          if 'chrome' in p.info['name'].lower()]

        total_memory = sum(p.info['memory_info'].rss for p in chrome_processes) / 1024 / 1024
        total_cpu = sum(p.info['cpu_percent'] for p in chrome_processes)

        return {
            'chrome_memory_mb': total_memory,
            'chrome_cpu_percent': total_cpu,
            'chrome_process_count': len(chrome_processes),
            'system_memory_percent': psutil.virtual_memory().percent,
            'system_cpu_percent': psutil.cpu_percent()
        }

    async def capture_crash_data(self, page, crash_type, error_details=None):
        crash_data = {
            'timestamp': datetime.now().isoformat(),
            'session_duration': (datetime.now() - self.session_start).total_seconds(),
            'reload_count': self.reload_count,
            'crash_type': crash_type,
            'error_details': error_details,
            'system_metrics': self.get_system_metrics()
        }

        try:
            reports_dir = self.config['output']['reports_directory']
            screenshots_dir = self.config['output']['screenshots_directory']

            # Capture final screenshot
            if self.config['output']['screenshots_enabled']:
                await page.screenshot(path=f"{screenshots_dir}/crash_{int(time.time())}.png")

            # Get page content
            content = await page.content()
            with open(f'{reports_dir}/crash_page_{int(time.time())}.html', 'w') as f:
                f.write(content)

        except Exception as e:
            self.logger.error(f"Error capturing crash data: {str(e)}")

        # Save crash data
        reports_dir = self.config['output']['reports_directory']
        with open(f'{reports_dir}/crash_data.json', 'a') as f:
            f.write(json.dumps(crash_data) + '\n')

        self.logger.critical(f"CRASH DETECTED: {crash_type}")
        self.logger.critical(f"Crash data saved. Session ran for {crash_data['session_duration']:.2f} seconds")

    def log_network_response(self, response):
        # Get all suspect keywords from config
        suspect_keywords = []
        for service_name, service_config in self.config['suspect_services'].items():
            if service_config['enabled']:
                suspect_keywords.extend(service_config['keywords'])

        if any(suspect in response.url.lower() for suspect in suspect_keywords):
            self.logger.info(f"Suspect service request: {response.url} - Status: {response.status}")

    def log_console_message(self, msg):
        if self.config['output']['console_logging'] and msg.type in ['error', 'warning']:
            self.logger.warning(f"Console {msg.type}: {msg.text}")

    def log_page_error(self, error):
        self.logger.error(f"Page error: {error}")

async def main():
    # Try to load config first
    try:
        monitor = WebsiteMonitor()

        # If URL is not set in config, exit with error (no interactive mode in background)
        if not monitor.target_url:
            print("ERROR: target_url not set in config.json")
            print("Please set the 'target_url' field in config.json or run the script interactively")
            return

    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"ERROR: Config file issue - {e}")
        print("Please create a valid config.json file or run './run_monitoring.sh' to set up configuration")
        return

    print(f"Starting website monitoring for: {monitor.target_url}")
    print(f"Reload interval: {monitor.reload_interval} seconds")
    print("Monitoring will run until crash detected or manually stopped...")

    try:
        await monitor.monitor_website()
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
    except Exception as e:
        print(f"Monitoring failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())