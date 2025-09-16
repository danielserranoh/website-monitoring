"""
Memory Leak Detection Module for Website Monitoring System

This module provides comprehensive memory leak detection capabilities by analyzing
memory usage patterns, trends, and garbage collection behavior.
"""

import logging
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import statistics


class MemoryTrend:
    """Represents memory trend analysis results"""
    def __init__(self, growth_rate: float, total_growth: float, percentage_growth: float,
                 slope: float, r_squared: float):
        self.growth_rate = growth_rate  # MB per minute
        self.total_growth = total_growth  # MB absolute
        self.percentage_growth = percentage_growth  # Percentage
        self.slope = slope  # Linear regression slope
        self.r_squared = r_squared  # Correlation coefficient


class MemoryLeakDetector:
    """
    Advanced memory leak detection system that analyzes multiple memory metrics
    and patterns to identify potential memory leaks before they cause crashes.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config['memory_leak_detection']
        self.logger = logging.getLogger(__name__)

        # Memory history storage
        max_samples = self.config['sampling_window_minutes'] * 60  # Convert to seconds
        self.memory_history = deque(maxlen=max_samples)
        self.reload_boundaries = []  # Track reload timestamps and memory snapshots

        # Baseline tracking
        self.baseline_chrome_memory = None
        self.baseline_js_heap = None
        self.baseline_established = False

        # Alert tracking
        self.leak_alerts = []
        self.last_gc_time = None

        # Configuration shortcuts
        self.thresholds = self.config['detection_thresholds']
        self.trend_windows = self.config['trend_analysis']

        self.logger.info("Memory leak detector initialized with sensitivity: %s",
                        self.config.get('alert_sensitivity', 'medium'))

    def add_memory_sample(self, metrics: Dict[str, Any], reload_count: int = 0) -> List[str]:
        """
        Add a new memory sample and analyze for leak patterns.

        Args:
            metrics: Dictionary containing memory metrics
            reload_count: Current reload count for per-reload analysis

        Returns:
            List of detected leak signals
        """
        timestamp = datetime.now()

        # Extract memory values
        chrome_memory = metrics.get('chrome_memory_mb', 0)
        js_heap = metrics.get('js_heap_mb', 0)  # Will be added from main.py
        system_memory = metrics.get('system_memory_percent', 0)

        # Create memory sample
        sample = {
            'timestamp': timestamp,
            'chrome_memory': chrome_memory,
            'js_heap': js_heap,
            'system_memory': system_memory,
            'reload_count': reload_count
        }

        self.memory_history.append(sample)

        # Track reload boundaries for per-reload analysis
        if len(self.memory_history) > 1:
            prev_reload = self.memory_history[-2]['reload_count']
            if reload_count > prev_reload:
                self.reload_boundaries.append({
                    'timestamp': timestamp,
                    'reload_count': reload_count,
                    'chrome_memory': chrome_memory,
                    'js_heap': js_heap
                })

        # Establish baseline if not set
        if not self.baseline_established and len(self.memory_history) >= 10:
            self._establish_baseline()

        # Detect garbage collection events
        self._detect_gc_events(js_heap)

        # Analyze for leak patterns
        leak_signals = []
        if self.baseline_established and len(self.memory_history) >= 60:  # Need at least 1 minute of data
            leak_signals = self._analyze_leak_patterns()

        return leak_signals

    def _establish_baseline(self):
        """Establish baseline memory usage from initial samples"""
        if len(self.memory_history) < 10:
            return

        recent_samples = list(self.memory_history)[-10:]

        self.baseline_chrome_memory = statistics.mean(s['chrome_memory'] for s in recent_samples)
        self.baseline_js_heap = statistics.mean(s['js_heap'] for s in recent_samples)
        self.baseline_established = True

        self.logger.info("Memory baseline established - Chrome: %.2fMB, JS Heap: %.2fMB",
                        self.baseline_chrome_memory, self.baseline_js_heap)

    def _detect_gc_events(self, current_js_heap: float):
        """Detect garbage collection events by monitoring JS heap decreases"""
        if len(self.memory_history) < 2:
            return

        prev_heap = self.memory_history[-2]['js_heap']

        # Detect significant heap decrease (likely GC)
        if current_js_heap < prev_heap * 0.9:  # 10% decrease
            self.last_gc_time = datetime.now()
            if self.config.get('log_detailed_analysis', False):
                self.logger.info("Garbage collection detected - Heap: %.2fMB -> %.2fMB",
                               prev_heap, current_js_heap)

    def _analyze_leak_patterns(self) -> List[str]:
        """Analyze memory history for various leak patterns"""
        leak_signals = []

        # 1. Trend analysis for different time windows
        trends = self._calculate_trends()
        leak_signals.extend(self._evaluate_trend_patterns(trends))

        # 2. Garbage collection analysis
        gc_signals = self._analyze_gc_patterns()
        leak_signals.extend(gc_signals)

        # 3. Per-reload memory analysis
        reload_signals = self._analyze_per_reload_patterns()
        leak_signals.extend(reload_signals)

        # 4. Memory spike detection
        spike_signals = self._detect_memory_spikes()
        leak_signals.extend(spike_signals)

        # Log detected signals
        if leak_signals and self.config.get('log_detailed_analysis', False):
            self.logger.warning("Memory leak signals detected: %s", ', '.join(leak_signals))

        return leak_signals

    def _calculate_trends(self) -> Dict[str, MemoryTrend]:
        """Calculate memory trends for different time windows"""
        trends = {}
        current_time = datetime.now()

        for window_name, window_seconds in self.trend_windows.items():
            # Filter samples within time window
            cutoff_time = current_time - timedelta(seconds=window_seconds)
            window_samples = [s for s in self.memory_history if s['timestamp'] >= cutoff_time]

            if len(window_samples) < 5:  # Need minimum samples
                continue

            trends[window_name] = self._calculate_memory_trend(window_samples)

        return trends

    def _calculate_memory_trend(self, samples: List[Dict]) -> MemoryTrend:
        """Calculate trend metrics for a set of memory samples"""
        if len(samples) < 2:
            return MemoryTrend(0, 0, 0, 0, 0)

        # Extract time series data
        times = [(s['timestamp'] - samples[0]['timestamp']).total_seconds() for s in samples]
        chrome_values = [s['chrome_memory'] for s in samples]

        # Calculate basic metrics
        total_growth = chrome_values[-1] - chrome_values[0]
        time_span_minutes = times[-1] / 60
        growth_rate = total_growth / time_span_minutes if time_span_minutes > 0 else 0

        baseline = chrome_values[0] if chrome_values[0] > 0 else 1
        percentage_growth = (total_growth / baseline) * 100

        # Calculate linear regression
        slope, r_squared = self._linear_regression(times, chrome_values)

        return MemoryTrend(growth_rate, total_growth, percentage_growth, slope, r_squared)

    def _linear_regression(self, x_values: List[float], y_values: List[float]) -> Tuple[float, float]:
        """Simple linear regression to calculate slope and R-squared"""
        if len(x_values) != len(y_values) or len(x_values) < 2:
            return 0.0, 0.0

        n = len(x_values)
        x_mean = statistics.mean(x_values)
        y_mean = statistics.mean(y_values)

        # Calculate slope
        numerator = sum((x_values[i] - x_mean) * (y_values[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 0.0, 0.0

        slope = numerator / denominator

        # Calculate R-squared
        y_pred = [slope * (x - x_mean) + y_mean for x in x_values]
        ss_res = sum((y_values[i] - y_pred[i]) ** 2 for i in range(n))
        ss_tot = sum((y_values[i] - y_mean) ** 2 for i in range(n))

        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

        return slope, r_squared

    def _evaluate_trend_patterns(self, trends: Dict[str, MemoryTrend]) -> List[str]:
        """Evaluate trend patterns for leak signals"""
        signals = []
        chrome_thresholds = self.thresholds['chrome_process_memory']

        for window_name, trend in trends.items():
            # Check growth rate threshold
            if trend.growth_rate > chrome_thresholds['growth_rate_threshold_mb_per_min']:
                signals.append(f'{window_name}_rapid_growth')

            # Check total growth threshold
            if trend.total_growth > chrome_thresholds['total_growth_threshold_mb']:
                signals.append(f'{window_name}_excessive_growth')

            # Check percentage growth threshold
            if trend.percentage_growth > chrome_thresholds['percentage_growth_threshold']:
                signals.append(f'{window_name}_percentage_growth')

            # Check for sustained growth (high correlation)
            if trend.r_squared > 0.8 and trend.slope > 0:
                signals.append(f'{window_name}_sustained_growth')

        return signals

    def _analyze_gc_patterns(self) -> List[str]:
        """Analyze garbage collection patterns"""
        signals = []
        js_thresholds = self.thresholds['js_heap_memory']

        # Check for prolonged periods without GC
        if self.last_gc_time:
            time_since_gc = (datetime.now() - self.last_gc_time).total_seconds()
            if time_since_gc > js_thresholds['no_gc_duration_threshold_seconds']:
                signals.append('no_garbage_collection')
        elif len(self.memory_history) > 300:  # 5 minutes without any GC detected
            signals.append('no_garbage_collection_detected')

        return signals

    def _analyze_per_reload_patterns(self) -> List[str]:
        """Analyze memory patterns across page reloads"""
        signals = []

        if len(self.reload_boundaries) < 2:
            return signals

        reload_thresholds = self.thresholds['per_reload_analysis']

        # Check if memory is properly freed between reloads
        recent_reloads = self.reload_boundaries[-5:]  # Last 5 reloads
        if len(recent_reloads) >= 2:
            memory_growth_per_reload = []
            for i in range(1, len(recent_reloads)):
                growth = (recent_reloads[i]['chrome_memory'] -
                         recent_reloads[i-1]['chrome_memory'])
                memory_growth_per_reload.append(growth)

            avg_growth = statistics.mean(memory_growth_per_reload)
            if avg_growth > reload_thresholds['cumulative_leak_per_reload_mb']:
                signals.append('cumulative_reload_leak')

        return signals

    def _detect_memory_spikes(self) -> List[str]:
        """Detect sudden memory spikes that might indicate leaks"""
        signals = []

        if len(self.memory_history) < 10:
            return signals

        recent_samples = list(self.memory_history)[-10:]
        current_memory = recent_samples[-1]['chrome_memory']

        # Compare with recent average
        recent_avg = statistics.mean(s['chrome_memory'] for s in recent_samples[:-1])

        # Detect significant spike
        if current_memory > recent_avg * 1.5:  # 50% spike
            signals.append('memory_spike_detected')

        return signals

    def get_memory_statistics(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics"""
        if not self.memory_history:
            return {}

        recent_sample = self.memory_history[-1]
        stats = {
            'current_chrome_memory_mb': recent_sample['chrome_memory'],
            'current_js_heap_mb': recent_sample['js_heap'],
            'baseline_chrome_memory_mb': self.baseline_chrome_memory,
            'baseline_js_heap_mb': self.baseline_js_heap,
            'total_samples': len(self.memory_history),
            'reload_boundaries_tracked': len(self.reload_boundaries),
            'last_gc_time': self.last_gc_time.isoformat() if self.last_gc_time else None,
            'leak_alerts_count': len(self.leak_alerts)
        }

        if self.baseline_established:
            stats['chrome_memory_growth_mb'] = (recent_sample['chrome_memory'] -
                                               self.baseline_chrome_memory)
            stats['js_heap_growth_mb'] = (recent_sample['js_heap'] -
                                         self.baseline_js_heap)

        return stats

    def reset_detector(self):
        """Reset the detector state (useful for new monitoring sessions)"""
        self.memory_history.clear()
        self.reload_boundaries.clear()
        self.baseline_chrome_memory = None
        self.baseline_js_heap = None
        self.baseline_established = False
        self.leak_alerts.clear()
        self.last_gc_time = None

        self.logger.info("Memory leak detector reset")