# generate_report.py
import os
import sys
import json
from datetime import datetime

import pandas as pd
import plotly.express as px
from jinja2 import Environment, FileSystemLoader

# --------------------
# HTML Template (Jinja2)
# --------------------
REPORT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Performance Report - {{ project_name }} {{ version }}</title>
  <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
  <style>
    body { font-family: Arial, sans-serif; margin: 40px; }
    h1 { color: #2c3e50; }
    h2 { color: #34495e; margin-top: 40px; }
    .chart-container { width: 100%; height: 600px; margin-bottom: 40px; }
    a { color: #2980b9; text-decoration: none; }
    a:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <h1>Performance Report</h1>
  <p><strong>Project:</strong> {{ project_name }}<br>
     <strong>Release:</strong> {{ version }}<br>
     <strong>Generated:</strong> {{ timestamp }}</p>

  <h2>Flamegraph</h2>
  <p><a href="{{ flamegraph_link }}" target="_blank">Open Flamegraph (SVG)</a></p>

  <h2>Cache & Branch Statistics</h2>
  <div class="chart-container">
    {{ cache_stats_div | safe }}
  </div>

  <h2>Top Sampled Functions</h2>
  <div class="chart-container">
    {{ top_funcs_div | safe }}
  </div>

</body>
</html>
"""

# --------------------
# Parsing Helpers
# --------------------

def parse_perf_stat(stat_path):
    '''Parse a perf-stat output file into a DataFrame of Metric and Value.'''
    rows = []
    with open(stat_path, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines or headers
            if not line or 'Performance counter stats' in line:
                continue
            parts = line.split()
            # Expect format: value event_name
            try:
                # Remove commas from numbers, ignore lines with '<not' or non-digits
                value_str = parts[0].replace(',', '')
                if '<' in value_str or not value_str.isdigit():
                    continue
                value = int(value_str)
                metric = parts[1]
                rows.append((metric, value))
            except (IndexError, ValueError):
                continue
    df = pd.DataFrame(rows, columns=['Metric', 'Value'])
    return df


def parse_collapsed_stacks(collapsed_path, top_n=15):
    '''Parse collapsed stacks file and return a DataFrame of top_n functions by sample count.'''
    stack_counts = {}
    with open(collapsed_path, 'r') as f:
        for line in f:
            if ' ' not in line:
                continue
            try:
                stack, count_str = line.rsplit(' ', 1)
                count = int(count_str)
            except ValueError:
                continue
            stack_counts[stack] = stack_counts.get(stack, 0) + count
    func_counts = {}
    for stack, count in stack_counts.items():
        funcs = stack.split(';')
        for func in funcs:
            func_counts[func] = func_counts.get(func, 0) + count
    df = pd.DataFrame(list(func_counts.items()), columns=['Function', 'Samples'])
    df = df.sort_values('Samples', ascending=False).head(top_n)
    return df

# --------------------
# Plotting Helpers
# --------------------

def generate_bar_chart_html(df, x_col, y_col, title):
    '''Generate a Plotly bar chart and return HTML div snippet.'''
    fig = px.bar(df, x=x_col, y=y_col, title=title)
    fig.update_layout(margin=dict(l=40, r=40, t=60, b=40))
    return fig.to_html(full_html=False, include_plotlyjs='cdn')

# --------------------
# Main Report Generator
# --------------------

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 generate_report.py <config.json> <version>")
        sys.exit(1)

    config_path = sys.argv[1]
    version = sys.argv[2]

    # Load JSON config
    with open(config_path, 'r') as f:
        config = json.load(f)

    project_name = config.get('project_name', 'UnknownProject')
    project_root = os.path.abspath(config['project_root'])

    # Define paths under project_root
    stat_dir = os.path.join(project_root, 'prf', 'out', 'stat')
    collapsed_dir = os.path.join(project_root, 'prf', 'out', 'collapsed')
    flamegraph_dir = os.path.join(project_root, 'prf', 'out', 'flamegraph')
    report_dir = os.path.join(project_root, config.get('report_output', 'reports'), version)
    os.makedirs(os.path.join(report_dir, 'plots'), exist_ok=True)

    # Find latest files
    try:
        stat_file = sorted(
            [f for f in os.listdir(stat_dir) if f.startswith('perf-stat-')],
            key=lambda f: os.path.getmtime(os.path.join(stat_dir, f))
        )[-1]
    except IndexError:
        print(f"No perf-stat files in {stat_dir}")
        sys.exit(1)

    try:
        collapsed_file = sorted(
            [f for f in os.listdir(collapsed_dir) if f.endswith('.txt')],
            key=lambda f: os.path.getmtime(os.path.join(collapsed_dir, f))
        )[-1]
    except IndexError:
        print(f"No collapsed files in {collapsed_dir}")
        sys.exit(1)

    try:
        flamegraph_file = sorted(
            [f for f in os.listdir(flamegraph_dir) if f.endswith('.svg')],
            key=lambda f: os.path.getmtime(os.path.join(flamegraph_dir, f))
        )[-1]
    except IndexError:
        print(f"No flamegraph files in {flamegraph_dir}")
        sys.exit(1)

    # Parse data
    stat_df = parse_perf_stat(os.path.join(stat_dir, stat_file))
    top_funcs_df = parse_collapsed_stacks(os.path.join(collapsed_dir, collapsed_file))

    # Generate charts
    cache_stats_div = generate_bar_chart_html(stat_df, 'Metric', 'Value', 'Cache & Branch Stats')
    top_funcs_div = generate_bar_chart_html(top_funcs_df, 'Function', 'Samples', 'Top Sampled Functions')

    # Copy flamegraph.svg link relative to report.html
    rel_flamegraph = os.path.relpath(os.path.join(flamegraph_dir, flamegraph_file), report_dir)

    # Render HTML using Jinja2
    env = Environment(loader=FileSystemLoader(searchpath=os.path.dirname(__file__)))
    template = env.from_string(REPORT_TEMPLATE)
    rendered_html = template.render(
        project_name=project_name,
        version=version,
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        flamegraph_link=rel_flamegraph,
        cache_stats_div=cache_stats_div,
        top_funcs_div=top_funcs_div
    )

    # Write report.html
    report_path = os.path.join(report_dir, 'report.html')
    with open(report_path, 'w') as f:
        f.write(rendered_html)

    print(f"Report generated: {report_path}")

if __name__ == '__main__':
    main()
