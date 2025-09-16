# Website Performance Monitoring

A Python-based website monitoring tool using Playwright to track and analyze website performance issues.

## Features

- Automated website performance monitoring
- Performance metrics collection using Playwright
- Performance issue detection and reporting
- Customizable monitoring intervals
- Data export and analysis capabilities

## Prerequisites

- Python 3.8 or higher
- Node.js (for Playwright browser installation)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd website-monitoring
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install playwright
playwright install
```

## Configuration

Create a `.env` file in the project root:
```
TARGET_URL=https://example.com
MONITORING_INTERVAL=300
TIMEOUT=30000
```

## Usage

Run the monitoring script:
```bash
python monitor.py
```

## Performance Metrics

The tool monitors:
- Page load times
- Time to First Byte (TTFB)
- First Contentful Paint (FCP)
- Largest Contentful Paint (LCP)
- Cumulative Layout Shift (CLS)
- First Input Delay (FID)

## Output

Results are saved to:
- `reports/` - Performance reports
- `logs/` - Monitoring logs
- `screenshots/` - Page screenshots (if enabled)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

MIT License