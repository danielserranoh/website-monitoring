#!/usr/bin/env python3
import json
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import argparse
import os
import numpy as np
import statistics

class CrashAnalyzer:
    def __init__(self, data_dir='.'):
        self.data_dir = data_dir
        self.crash_data = []
        self.performance_data = []
        self.system_metrics = []

    def load_data(self):
        """Load all monitoring data files"""

        # Load crash data
        crash_file = os.path.join(self.data_dir, 'reports', 'crash_data.json')
        if os.path.exists(crash_file):
            with open(crash_file, 'r') as f:
                for line in f:
                    self.crash_data.append(json.loads(line))

        # Load performance data
        perf_file = os.path.join(self.data_dir, 'reports', 'performance_data.jsonl')
        if os.path.exists(perf_file):
            with open(perf_file, 'r') as f:
                for line in f:
                    self.performance_data.append(json.loads(line))

        # Load system metrics
        sys_file = os.path.join(self.data_dir, 'system_metrics.log')
        if os.path.exists(sys_file):
            df = pd.read_csv(sys_file)
            self.system_metrics = df.to_dict('records')

        print(f"Loaded {len(self.crash_data)} crash events")
        print(f"Loaded {len(self.performance_data)} performance records")
        print(f"Loaded {len(self.system_metrics)} system metric records")

    def analyze_crash_patterns(self):
        """Analyze patterns in crash data"""
        if not self.crash_data:
            print("No crash data available for analysis")
            return

        print("\n=== CRASH ANALYSIS ===")

        # Group crashes by type
        crash_types = {}
        for crash in self.crash_data:
            crash_type = crash.get('crash_type', 'UNKNOWN')
            if crash_type not in crash_types:
                crash_types[crash_type] = []
            crash_types[crash_type].append(crash)

        # Analyze each crash type
        for crash_type, crashes in crash_types.items():
            print(f"\n{crash_type} crashes: {len(crashes)}")

            # Average session duration before crash
            durations = [c.get('session_duration', 0) for c in crashes]
            avg_duration = sum(durations) / len(durations) if durations else 0
            print(f"  Average session duration: {avg_duration:.2f} seconds")

            # Average reload count before crash
            reloads = [c.get('reload_count', 0) for c in crashes]
            avg_reloads = sum(reloads) / len(reloads) if reloads else 0
            print(f"  Average reloads before crash: {avg_reloads:.1f}")

            # System metrics at crash time
            if crashes and 'system_metrics' in crashes[0]:
                memory_at_crash = [c['system_metrics'].get('chrome_memory_mb', 0) for c in crashes]
                cpu_at_crash = [c['system_metrics'].get('chrome_cpu_percent', 0) for c in crashes]

                print(f"  Average Chrome memory at crash: {sum(memory_at_crash)/len(memory_at_crash):.2f}MB")
                print(f"  Average Chrome CPU at crash: {sum(cpu_at_crash)/len(cpu_at_crash):.2f}%")

    def find_pre_crash_patterns(self):
        """Find patterns in the data leading up to crashes"""
        if not self.crash_data or not self.performance_data:
            print("Insufficient data for pre-crash pattern analysis")
            return

        print("\n=== PRE-CRASH PATTERN ANALYSIS ===")

        for i, crash in enumerate(self.crash_data):
            crash_time = datetime.fromisoformat(crash['timestamp'].replace('Z', '+00:00'))

            # Find performance data in the 10 minutes before crash
            pre_crash_data = []
            for perf in self.performance_data:
                perf_time = datetime.fromisoformat(perf['timestamp'])
                time_diff = (crash_time - perf_time).total_seconds()

                # Data from 10 minutes before crash
                if 0 <= time_diff <= 600:
                    pre_crash_data.append((time_diff, perf))

            if pre_crash_data:
                print(f"\nCrash #{i+1} - {crash['crash_type']}")

                # Analyze memory trend
                memory_trend = [(td, d['system_metrics']['chrome_memory_mb']) for td, d in pre_crash_data]
                memory_trend.sort(key=lambda x: x[0], reverse=True)  # Most recent first

                if len(memory_trend) >= 2:
                    memory_change = memory_trend[0][1] - memory_trend[-1][1]
                    print(f"  Memory change in last 10 minutes: {memory_change:+.2f}MB")

                # Find suspect services active before crash
                suspect_activity = {}
                for td, data in pre_crash_data:
                    for service in ['curator', 'cookieyes', 'serviceforce']:
                        if service not in suspect_activity:
                            suspect_activity[service] = 0
                        # Check if service was mentioned in logs or network requests
                        # This would need to be enhanced based on actual data structure

                print(f"  Performance records in 10min before crash: {len(pre_crash_data)}")

    def analyze_performance_trends(self):
        """Analyze performance trends and memory patterns"""
        if not self.performance_data:
            print("No performance data available for trend analysis")
            return {}

        print("\n=== PERFORMANCE TREND ANALYSIS ===")

        # Extract time series data
        timestamps = [datetime.fromisoformat(d['timestamp']) for d in self.performance_data]
        chrome_memory = [d['system_metrics']['chrome_memory_mb'] for d in self.performance_data]
        js_heap = [d['system_metrics'].get('js_heap_mb', 0) for d in self.performance_data if 'js_heap_mb' in d['system_metrics']]
        load_times = [d['load_time'] for d in self.performance_data]

        analysis = {}

        # Time span analysis
        duration_minutes = (timestamps[-1] - timestamps[0]).total_seconds() / 60
        analysis['duration_minutes'] = duration_minutes
        analysis['data_points'] = len(self.performance_data)

        print(f"Analysis period: {duration_minutes:.1f} minutes")
        print(f"Data points: {len(self.performance_data)}")

        # Chrome memory analysis
        memory_initial = chrome_memory[0]
        memory_final = chrome_memory[-1]
        memory_peak = max(chrome_memory)
        memory_min = min(chrome_memory)
        memory_net_change = memory_final - memory_initial
        memory_growth_rate = memory_net_change / duration_minutes if duration_minutes > 0 else 0

        analysis['chrome_memory'] = {
            'initial_mb': memory_initial,
            'final_mb': memory_final,
            'peak_mb': memory_peak,
            'min_mb': memory_min,
            'net_change_mb': memory_net_change,
            'growth_rate_mb_per_min': memory_growth_rate
        }

        print(f"\nChrome Memory:")
        print(f"  Initial: {memory_initial:.1f} MB")
        print(f"  Final: {memory_final:.1f} MB")
        print(f"  Peak: {memory_peak:.1f} MB")
        print(f"  Net change: {memory_net_change:+.1f} MB")
        print(f"  Growth rate: {memory_growth_rate:.2f} MB/min")

        # Memory leak assessment using the same thresholds as MemoryLeakDetector
        leak_threshold = 10.0  # MB/min - matches memory leak detector threshold
        percentage_threshold = 200.0  # % - significant percentage growth
        total_growth_threshold = 500.0  # MB - absolute growth threshold

        memory_percentage_growth = (memory_net_change / memory_initial) * 100 if memory_initial > 0 else 0

        leak_signals = []
        if memory_growth_rate > leak_threshold:
            leak_signals.append(f"rapid_growth_{memory_growth_rate:.1f}MB/min")
        if abs(memory_net_change) > total_growth_threshold:
            leak_signals.append(f"large_growth_{memory_net_change:+.0f}MB")
        if memory_percentage_growth > percentage_threshold:
            leak_signals.append(f"percentage_growth_{memory_percentage_growth:.0f}%")

        if leak_signals:
            print(f"  ⚠️  MEMORY LEAK DETECTED: {', '.join(leak_signals)}")
            analysis['memory_leak_detected'] = True
            analysis['memory_leak_signals'] = leak_signals
        else:
            print(f"  ✅ No memory leak detected")
            analysis['memory_leak_detected'] = False
            analysis['memory_leak_signals'] = []

        # Additional leak analysis
        analysis['memory_percentage_growth'] = memory_percentage_growth

        # JS Heap analysis
        if js_heap:
            heap_initial = js_heap[0]
            heap_final = js_heap[-1]
            heap_peak = max(js_heap)
            heap_net_change = heap_final - heap_initial
            heap_growth_rate = heap_net_change / duration_minutes if duration_minutes > 0 else 0

            analysis['js_heap'] = {
                'initial_mb': heap_initial,
                'final_mb': heap_final,
                'peak_mb': heap_peak,
                'net_change_mb': heap_net_change,
                'growth_rate_mb_per_min': heap_growth_rate
            }

            print(f"\nJS Heap Memory:")
            print(f"  Initial: {heap_initial:.1f} MB")
            print(f"  Final: {heap_final:.1f} MB")
            print(f"  Peak: {heap_peak:.1f} MB")
            print(f"  Net change: {heap_net_change:+.1f} MB")
            print(f"  Growth rate: {heap_growth_rate:.2f} MB/min")

            # Detect GC events
            gc_events = 0
            if len(js_heap) > 1:
                for i in range(1, len(js_heap)):
                    if js_heap[i] < js_heap[i-1] * 0.9:  # 10% decrease
                        gc_events += 1

            analysis['gc_events'] = gc_events
            print(f"  Garbage collection events: {gc_events}")

            if heap_growth_rate < 0:
                print(f"  ✅ Healthy GC activity (negative growth)")
            else:
                print(f"  ⚠️  JS heap growing consistently")

        # Performance analysis
        avg_load_time = statistics.mean(load_times)
        load_time_variance = statistics.variance(load_times) if len(load_times) > 1 else 0

        analysis['performance'] = {
            'avg_load_time_s': avg_load_time,
            'load_time_variance': load_time_variance,
            'min_load_time_s': min(load_times),
            'max_load_time_s': max(load_times)
        }

        print(f"\nPerformance:")
        print(f"  Average load time: {avg_load_time:.2f}s")
        print(f"  Load time range: {min(load_times):.2f}s - {max(load_times):.2f}s")

        return analysis

    def generate_report(self):
        """Generate a comprehensive crash analysis report"""
        report_path = os.path.join(self.data_dir, 'reports', 'crash_analysis_report.txt')

        # Get performance trend analysis
        performance_analysis = self.analyze_performance_trends()

        with open(report_path, 'w') as f:
            f.write("WEBSITE CRASH ANALYSIS REPORT\n")
            f.write("=" * 50 + "\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")

            # Summary statistics
            f.write(f"Total crashes detected: {len(self.crash_data)}\n")
            f.write(f"Total monitoring sessions: {len(self.performance_data)}\n")
            f.write(f"System metric records: {len(self.system_metrics)}\n\n")

            # Performance trend analysis
            if performance_analysis:
                f.write("PERFORMANCE TREND ANALYSIS:\n")
                f.write("-" * 30 + "\n")
                f.write(f"Monitoring duration: {performance_analysis['duration_minutes']:.1f} minutes\n")
                f.write(f"Data points collected: {performance_analysis['data_points']}\n\n")

                if 'chrome_memory' in performance_analysis:
                    mem = performance_analysis['chrome_memory']
                    f.write(f"Chrome Memory Trends:\n")
                    f.write(f"  Initial: {mem['initial_mb']:.1f} MB\n")
                    f.write(f"  Final: {mem['final_mb']:.1f} MB\n")
                    f.write(f"  Peak: {mem['peak_mb']:.1f} MB\n")
                    f.write(f"  Net change: {mem['net_change_mb']:+.1f} MB\n")
                    f.write(f"  Growth rate: {mem['growth_rate_mb_per_min']:.2f} MB/min\n")

                    if performance_analysis.get('memory_leak_detected', False):
                        f.write(f"  ⚠️  MEMORY LEAK DETECTED\n")
                        signals = performance_analysis.get('memory_leak_signals', [])
                        if signals:
                            f.write(f"     Signals: {', '.join(signals)}\n")
                    else:
                        f.write(f"  ✅ No memory leak detected\n")

                    f.write(f"  Percentage growth: {performance_analysis.get('memory_percentage_growth', 0):.1f}%\n")
                    f.write("\n")

                if 'js_heap' in performance_analysis:
                    heap = performance_analysis['js_heap']
                    f.write(f"JavaScript Heap Trends:\n")
                    f.write(f"  Initial: {heap['initial_mb']:.1f} MB\n")
                    f.write(f"  Final: {heap['final_mb']:.1f} MB\n")
                    f.write(f"  Peak: {heap['peak_mb']:.1f} MB\n")
                    f.write(f"  Net change: {heap['net_change_mb']:+.1f} MB\n")
                    f.write(f"  Growth rate: {heap['growth_rate_mb_per_min']:.2f} MB/min\n")
                    f.write(f"  Garbage collection events: {performance_analysis.get('gc_events', 0)}\n\n")

                if 'performance' in performance_analysis:
                    perf = performance_analysis['performance']
                    f.write(f"Page Performance:\n")
                    f.write(f"  Average load time: {perf['avg_load_time_s']:.2f}s\n")
                    f.write(f"  Load time range: {perf['min_load_time_s']:.2f}s - {perf['max_load_time_s']:.2f}s\n\n")

            # Crash frequency analysis
            if self.crash_data:
                f.write("CRASH ANALYSIS:\n")
                f.write("-" * 15 + "\n")
                crash_times = [datetime.fromisoformat(c['timestamp'].replace('Z', '+00:00')) for c in self.crash_data]
                if len(crash_times) > 1:
                    time_between_crashes = []
                    for i in range(1, len(crash_times)):
                        time_diff = (crash_times[i] - crash_times[i-1]).total_seconds()
                        time_between_crashes.append(time_diff)

                    avg_time_between = sum(time_between_crashes) / len(time_between_crashes)
                    f.write(f"Average time between crashes: {avg_time_between:.2f} seconds\n\n")

            # Suspected culprits analysis
            f.write("SUSPECT ANALYSIS:\n")
            f.write("-" * 20 + "\n")

            culprit_scores = {'curator': 0, 'cookieyes': 0, 'serviceforce': 0}

            for crash in self.crash_data:
                error_details = crash.get('error_details', '').lower()
                for culprit in culprit_scores:
                    if culprit in error_details:
                        culprit_scores[culprit] += 1

            for culprit, score in sorted(culprit_scores.items(), key=lambda x: x[1], reverse=True):
                f.write(f"{culprit.upper()}: {score} crash mentions\n")

            f.write("\nRECOMMENDATIONS:\n")
            f.write("-" * 15 + "\n")

            # Memory-based recommendations
            if performance_analysis.get('memory_leak_detected', False):
                f.write("1. URGENT: Memory leak detected - investigate Chrome memory growth\n")
                signals = performance_analysis.get('memory_leak_signals', [])
                if any('rapid_growth' in signal for signal in signals):
                    f.write("   - High growth rate detected (>10MB/min)\n")
                if any('large_growth' in signal for signal in signals):
                    f.write("   - Significant absolute growth detected (>500MB)\n")
                if any('percentage_growth' in signal for signal in signals):
                    f.write("   - Memory usage increased by >200% from baseline\n")

                if 'js_heap' in performance_analysis and performance_analysis['js_heap']['growth_rate_mb_per_min'] > 1:
                    f.write("2. JavaScript heap growing - check for event listener leaks or DOM retention\n")
            else:
                f.write("1. Memory management appears healthy\n")
                if performance_analysis.get('memory_percentage_growth', 0) > 50:
                    f.write("   - Note: Moderate memory growth observed (>50%)\n")

            max_culprit = max(culprit_scores, key=culprit_scores.get) if culprit_scores else None
            if max_culprit and culprit_scores[max_culprit] > 0:
                f.write(f"2. Focus investigation on {max_culprit.upper()} service\n")

            f.write("3. Monitor memory usage patterns before crashes\n")
            f.write("4. Check network requests to suspect services\n")
            f.write("5. Consider implementing circuit breakers for suspect services\n")

        print(f"\nDetailed report saved to: {report_path}")

    def plot_metrics(self):
        """Create visualizations of the monitoring data"""
        if not self.system_metrics:
            print("No system metrics data available for plotting")
            return

        # Create plots directory
        plots_dir = os.path.join(self.data_dir, 'reports', 'plots')
        os.makedirs(plots_dir, exist_ok=True)

        # Convert to DataFrame for easier plotting
        df = pd.DataFrame(self.system_metrics)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Memory usage over time
        plt.figure(figsize=(12, 6))
        plt.plot(df['timestamp'], df['chrome_memory_mb'], label='Chrome Memory (MB)')
        plt.xlabel('Time')
        plt.ylabel('Memory (MB)')
        plt.title('Chrome Memory Usage Over Time')
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(plots_dir, 'memory_usage.png'))
        plt.close()

        # CPU usage over time
        plt.figure(figsize=(12, 6))
        plt.plot(df['timestamp'], df['chrome_cpu_percent'], label='Chrome CPU %')
        plt.plot(df['timestamp'], df['system_cpu_percent'], label='System CPU %')
        plt.xlabel('Time')
        plt.ylabel('CPU Usage (%)')
        plt.title('CPU Usage Over Time')
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(plots_dir, 'cpu_usage.png'))
        plt.close()

        print(f"Plots saved to: {plots_dir}")

def main():
    parser = argparse.ArgumentParser(description='Analyze website crash monitoring data')
    parser.add_argument('--data-dir', default='.', help='Directory containing monitoring data')
    parser.add_argument('--no-plots', action='store_true', help='Skip generating plots')

    args = parser.parse_args()

    analyzer = CrashAnalyzer(args.data_dir)
    analyzer.load_data()
    analyzer.analyze_crash_patterns()
    analyzer.find_pre_crash_patterns()
    analyzer.generate_report()

    if not args.no_plots:
        try:
            analyzer.plot_metrics()
        except ImportError:
            print("Matplotlib not available, skipping plots")

if __name__ == "__main__":
    main()