#!/usr/bin/env python3
import json
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import argparse
import os

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

    def generate_report(self):
        """Generate a comprehensive crash analysis report"""
        report_path = os.path.join(self.data_dir, 'reports', 'crash_analysis_report.txt')

        with open(report_path, 'w') as f:
            f.write("WEBSITE CRASH ANALYSIS REPORT\n")
            f.write("=" * 50 + "\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")

            # Summary statistics
            f.write(f"Total crashes detected: {len(self.crash_data)}\n")
            f.write(f"Total monitoring sessions: {len(self.performance_data)}\n")
            f.write(f"System metric records: {len(self.system_metrics)}\n\n")

            # Crash frequency analysis
            if self.crash_data:
                crash_times = [datetime.fromisoformat(c['timestamp'].replace('Z', '+00:00')) for c in self.crash_data]
                if len(crash_times) > 1:
                    time_between_crashes = []
                    for i in range(1, len(crash_times)):
                        time_diff = (crash_times[i] - crash_times[i-1]).total_seconds()
                        time_between_crashes.append(time_diff)

                    avg_time_between = sum(time_between_crashes) / len(time_between_crashes)
                    f.write(f"Average time between crashes: {avg_time_between:.2f} seconds\n")

            # Suspected culprits analysis
            f.write("\nSUSPECT ANALYSIS:\n")
            f.write("-" * 20 + "\n")

            culprit_scores = {'curator': 0, 'cookieyes': 0, 'serviceforce': 0}

            for crash in self.crash_data:
                error_details = crash.get('error_details', '').lower()
                for culprit in culprit_scores:
                    if culprit in error_details:
                        culprit_scores[culprit] += 1

            for culprit, score in sorted(culprit_scores.items(), key=lambda x: x[1], reverse=True):
                f.write(f"{culprit.upper()}: {score} crash mentions\n")

            f.write("\nRECOMMENDations:\n")
            f.write("-" * 15 + "\n")

            max_culprit = max(culprit_scores, key=culprit_scores.get)
            if culprit_scores[max_culprit] > 0:
                f.write(f"1. Focus investigation on {max_culprit.upper()} service\n")

            f.write("2. Monitor memory usage patterns before crashes\n")
            f.write("3. Check network requests to suspect services\n")
            f.write("4. Consider implementing circuit breakers for suspect services\n")

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