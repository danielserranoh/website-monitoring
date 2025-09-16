"""
Logging Utilities

Centralized logging configuration and utilities.
"""

import logging
import os
from typing import Dict, Any, List, Optional


def setup_logging(config: Dict[str, Any]) -> logging.Logger:
    """
    Setup centralized logging configuration.

    Args:
        config: Configuration dictionary

    Returns:
        Configured logger instance
    """
    log_config = config.get('logging', {})

    # Get log level
    log_level = getattr(logging, log_config.get('level', 'INFO').upper())

    # Setup handlers
    handlers = []

    # File handler
    if log_config.get('file_output', True):
        log_file = log_config.get('log_file', 'monitoring.log')
        # Ensure log directory exists
        os.makedirs(os.path.dirname(log_file) if os.path.dirname(log_file) else '.', exist_ok=True)
        handlers.append(logging.FileHandler(log_file))

    # Console handler
    if log_config.get('console_output', True):
        handlers.append(logging.StreamHandler())

    # Format
    log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Configure basic logging
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=handlers,
        force=True  # Override any existing configuration
    )

    # Create and return logger
    logger = logging.getLogger('website_monitoring')
    logger.info("Logging configured successfully")

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def setup_component_logger(component_name: str, config: Dict[str, Any]) -> logging.Logger:
    """
    Setup logging for a specific component.

    Args:
        component_name: Name of the component
        config: Configuration dictionary

    Returns:
        Component-specific logger
    """
    logger = logging.getLogger(f'website_monitoring.{component_name}')

    # Add component-specific configuration if needed
    log_config = config.get('logging', {})

    # Create component-specific log file if configured
    if log_config.get('component_files', False):
        log_file = f"{component_name}.log"
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


class LogContext:
    """Context manager for adding context to log messages"""

    def __init__(self, logger: logging.Logger, context: str):
        self.logger = logger
        self.context = context
        self.old_format = None

    def __enter__(self):
        # Store original format and add context
        for handler in self.logger.handlers:
            if hasattr(handler, 'formatter') and handler.formatter:
                self.old_format = handler.formatter._fmt
                new_format = f"%(asctime)s - [{self.context}] - %(name)s - %(levelname)s - %(message)s"
                handler.setFormatter(logging.Formatter(new_format))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original format
        if self.old_format:
            for handler in self.logger.handlers:
                if hasattr(handler, 'formatter'):
                    handler.setFormatter(logging.Formatter(self.old_format))


def log_performance(logger: logging.Logger, operation: str, duration: float,
                   threshold: Optional[float] = None) -> None:
    """
    Log performance metrics for operations.

    Args:
        logger: Logger instance
        operation: Name of the operation
        duration: Duration in seconds
        threshold: Warning threshold in seconds
    """
    message = f"Operation '{operation}' completed in {duration:.3f}s"

    if threshold and duration > threshold:
        logger.warning(f"SLOW: {message} (threshold: {threshold:.3f}s)")
    else:
        logger.info(message)


def log_memory_usage(logger: logging.Logger, component: str, memory_mb: float,
                    threshold_mb: Optional[float] = None) -> None:
    """
    Log memory usage for components.

    Args:
        logger: Logger instance
        component: Component name
        memory_mb: Memory usage in MB
        threshold_mb: Warning threshold in MB
    """
    message = f"{component} memory usage: {memory_mb:.2f}MB"

    if threshold_mb and memory_mb > threshold_mb:
        logger.warning(f"HIGH MEMORY: {message} (threshold: {threshold_mb:.2f}MB)")
    else:
        logger.debug(message)


def log_system_info(logger: logging.Logger, config: Dict[str, Any]) -> None:
    """
    Log system and configuration information at startup.

    Args:
        logger: Logger instance
        config: Configuration dictionary
    """
    logger.info("=== Website Monitoring System Started ===")
    logger.info(f"Target URL: {config.get('monitoring', {}).get('target_url', 'Not configured')}")
    logger.info(f"Reload interval: {config.get('monitoring', {}).get('reload_interval_seconds', 'Not configured')}s")
    logger.info(f"Memory leak detection: {'Enabled' if config.get('memory_leak_detection', {}).get('enabled', False) else 'Disabled'}")

    # Log enabled suspect services
    suspect_services = config.get('suspect_services', {})
    enabled_services = [name for name, conf in suspect_services.items() if conf.get('enabled', True)]
    logger.info(f"Monitoring suspect services: {', '.join(enabled_services) if enabled_services else 'None'}")

    logger.info("=========================================")