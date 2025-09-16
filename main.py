#!/usr/bin/env python3
"""
Website Monitoring System - Main Entry Point

A comprehensive monitoring system for detecting website crashes and performance issues.
"""

import asyncio
import argparse
import sys
import os

# Add src to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.config_manager import ConfigManager
from src.utils.logger import setup_logging, log_system_info
from src.monitors.website_monitor import WebsiteMonitor
from src.monitors.system_monitor import SystemMonitor
from src.analysis.crash_analyzer import CrashAnalyzer


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Website Monitoring System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python main.py                                    # Start monitoring with default config
  python main.py --config config/production.json   # Use specific config file
  python main.py --analyze                          # Run crash analysis only
  python main.py --website-only                     # Run website monitoring only
  python main.py --system-only                      # Run system monitoring only
        '''
    )

    parser.add_argument(
        '--config', '-c',
        default='config/config.json',
        help='Configuration file path (default: config/config.json)'
    )

    parser.add_argument(
        '--analyze', '-a',
        action='store_true',
        help='Run crash analysis on existing data and exit'
    )

    parser.add_argument(
        '--website-only',
        action='store_true',
        help='Run only website monitoring (no system monitoring)'
    )

    parser.add_argument(
        '--system-only',
        action='store_true',
        help='Run only system monitoring (no website monitoring)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    return parser.parse_args()


async def run_website_monitoring(config):
    """Run website monitoring"""
    monitor = WebsiteMonitor(config_file=args.config)
    await monitor.start_monitoring()


def run_system_monitoring(config):
    """Run system monitoring"""
    monitor = SystemMonitor(config_file=args.config)
    monitor_thread = monitor.start_monitoring()

    try:
        # Keep the main thread alive
        monitor_thread.join()
    except KeyboardInterrupt:
        print("Stopping system monitoring...")
        monitor.stop_monitoring()
        monitor_thread.join()


async def run_combined_monitoring(config):
    """Run both website and system monitoring"""
    import threading

    # Start system monitoring in a separate thread
    system_monitor = SystemMonitor(config_file=args.config)
    system_thread = system_monitor.start_monitoring()

    try:
        # Start website monitoring in the main async loop
        website_monitor = WebsiteMonitor(config_file=args.config)
        await website_monitor.start_monitoring()

    except KeyboardInterrupt:
        print("\\nStopping monitoring...")
    finally:
        # Clean shutdown
        system_monitor.stop_monitoring()
        system_thread.join()


def run_analysis(config):
    """Run crash analysis"""
    analyzer = CrashAnalyzer()

    print("Loading monitoring data...")
    analyzer.load_data()

    print("Analyzing crash patterns...")
    analyzer.analyze_crash_patterns()

    print("Finding pre-crash patterns...")
    analyzer.find_pre_crash_patterns()

    print("Generating report...")
    analyzer.generate_report()

    print("Creating visualizations...")
    analyzer.plot_metrics()

    print("Analysis complete. Check reports/ directory for results.")


def main():
    """Main entry point"""
    global args
    args = parse_arguments()

    try:
        # Load configuration
        config = ConfigManager.load_config(args.config)

        # Adjust log level if verbose
        if args.verbose:
            config['logging']['level'] = 'DEBUG'

        # Setup logging
        logger = setup_logging(config)
        log_system_info(logger, config)

        # Run based on mode
        if args.analyze:
            logger.info("Running crash analysis mode")
            run_analysis(config)

        elif args.website_only:
            logger.info("Running website monitoring only")
            asyncio.run(run_website_monitoring(config))

        elif args.system_only:
            logger.info("Running system monitoring only")
            run_system_monitoring(config)

        else:
            logger.info("Running combined monitoring (website + system)")
            asyncio.run(run_combined_monitoring(config))

    except KeyboardInterrupt:
        print("\\nMonitoring stopped by user")
        sys.exit(0)
    except FileNotFoundError as e:
        print(f"Error: Configuration file not found: {e}")
        print(f"Please ensure {args.config} exists or run with --config path/to/config.json")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()