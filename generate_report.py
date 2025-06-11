#!/usr/bin/env python3
# Full Phase 1 Implementation of Perf-Report-Tool

import os
import json
from datetime import datetime
import pandas as pd
import plotly.express as px
from jinja2 import Environment, FileSystemLoader, select_autoescape

REPORT_TEMPLATE = '''
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
  {% for label, link in flamegraph_links.items() %}
    <p><a href="{{ link }}" target="_blank">Flamegraph: {{ label }}</a></p>
  {% endfor %}

  <h2>Cache & Branch Statistics</h2>
  <div class="chart-container">{{ cache_stats_div | safe }}</div>

  <h2>Top Sampled Functions</h2>
  <div class="chart-container">{{ top_funcs_div | safe }}</div>

  <h2>Google Benchmark Results</h2>
  <div class="chart-container">{{ gb_chart_div | safe }}</div>

  <h2>Valgrind Heap Allocations</h2>
  <div class="chart-container">{{ heap_chart_div | safe }}</div>
</body>
</html>
'''

def parse_perf_stat(stat_path):
    rows = []
    with open(stat_path, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 2:
                continue
            try:
                val = parts[0].replace(",", "")
                if '<' in val or not any(c.isdigit() for c in val):
                    continue
                value = float(val)
                metric = parts[1]
                rows.append((metric, value))
            except ValueError:
                continue
    return pd.DataFrame(rows, columns=["Metric", "Value"])


def parse_collapsed_stacks(collapsed_path, top_n=15):
    stack_counts = {}
    with open(collapsed_path, 'r') as f:
        for line in f:
            if ' ' not in line:
                continue
            try:
                stack, count_str = line.rsplit(' ', 1)
                count = int(count_str)
                stack_counts[stack] = stack_counts.get(stack, 0) + count
            except ValueError:
                continue
    func_counts = {}
    for stack, count in stack_counts.items():
        funcs = stack.split(';')
        for func in funcs:
            func_counts[func] = func_counts.get(func, 0) + count
    df = pd.DataFrame(list(func_counts.items()), columns=["Function", "Samples"])
    return df.sort_values("Samples", ascending=False).head(top_n)


def parse_google_benchmark(benchmark_path):
    try:
        with open(benchmark_path, 'r') as f:
            data = json.load(f)
        records = []
        for bench in data.get("benchmarks", []):
            if "name" in bench and "cpu_time" in bench:
                records.append((bench["name"], bench["cpu_time"]))
        return pd.DataFrame(records, columns=["Benchmark", "CPU Time (ns)"])
    except Exception:
        return pd.DataFrame(columns=["Benchmark", "CPU Time (ns)"])


def parse_valgrind_massif(massif_file):
    sizes = []
    with open(massif_file, 'r') as f:
        for line in f:
            if line.startswith("mem_heap_B="):
                sizes.append(int(line.strip().split('=')[1]))
    return pd.DataFrame({"Heap Size (Bytes)": sizes, "Snapshot": range(len(sizes))})


def generate_bar_chart(df, x_col, y_col, title):
    if df.empty:
        return "<p>No data available for {}</p>".format(title)
    fig = px.bar(df, x=x_col, y=y_col, title=title)
    fig.update_layout(margin=dict(l=40, r=40, t=60, b=40))
    return fig.to_html(full_html=False, include_plotlyjs='cdn')


def generate_report(config_path, version):
    with open(config_path) as f:
        config = json.load(f)

    root = os.path.abspath(config["project_root"])
    stat_dir = os.path.join(root, config.get("perf_stat_path", "prf/stat"))
    collapsed_dir = os.path.join(root, config.get("collapsed_path", "prf/collapsed"))
    flamegraph_dir = os.path.join(root, config.get("flamegraph_path", "prf/flamegraph"))
    gb_path = os.path.join(root, config.get("google_benchmark_path", "benchmarks/benchmark.json"))
    #valgrind_path = os.path.join(root, config.get("valgrind_massif_path", "valgrind/massif.out"))
    report_dir = os.path.join(root, config.get("report_output", "reports"), version)

    os.makedirs(report_dir, exist_ok=True)

    stat_file = sorted([f for f in os.listdir(stat_dir) if "perf-stat" in f], key=lambda x: os.path.getmtime(os.path.join(stat_dir, x)))[-1]
    collapsed_file = sorted([f for f in os.listdir(collapsed_dir) if f.endswith(".txt")], key=lambda x: os.path.getmtime(os.path.join(collapsed_dir, x)))[-1]
    flamegraph_files = {f.replace("flamegraph-", "").replace(".svg", ""): os.path.relpath(os.path.join(flamegraph_dir, f), report_dir)
                        for f in os.listdir(flamegraph_dir) if f.endswith(".svg")}

    stat_df = parse_perf_stat(os.path.join(stat_dir, stat_file))
    top_funcs_df = parse_collapsed_stacks(os.path.join(collapsed_dir, collapsed_file))
    gb_df = parse_google_benchmark(gb_path)
    # heap_df = parse_valgrind_massif(valgrind_path)

    env = Environment(loader=FileSystemLoader("."), autoescape=select_autoescape(['html']))
    template = env.from_string(REPORT_TEMPLATE)

    html = template.render(
        project_name=config.get("project_name", "UnnamedProject"),
        version=version,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        flamegraph_links=flamegraph_files,
        cache_stats_div=generate_bar_chart(stat_df, "Metric", "Value", "Cache/Branch/CPU Stats"),
        top_funcs_div=generate_bar_chart(top_funcs_df, "Function", "Samples", "Top Hot Functions"),
        gb_chart_div=generate_bar_chart(gb_df, "Benchmark", "CPU Time (ns)", "Google Benchmark Results"),
        # heap_chart_div=generate_bar_chart(heap_df, "Snapshot", "Heap Size (Bytes)", "Heap Allocation Over Time")
    )

    output_path = os.path.join(report_dir, "report.html")
    with open(output_path, "w") as f:
        f.write(html)
    return output_path


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        print("Usage: python3 generate_report_v2.py <config.json> <version>")
        sys.exit(1)
    config_path = sys.argv[1]
    version = sys.argv[2]
    path = generate_report(config_path, version)
    print(f"Report generated at: {path}")