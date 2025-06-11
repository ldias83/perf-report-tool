#!/usr/bin/env python3
# Full Phase 1 Implementation of Perf-Report-Tool

import os
import json
from datetime import datetime
import argparse
import pandas as pd
import plotly.express as px
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path



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


from pathlib import Path
import os, json
from datetime import datetime
import pandas as pd
import plotly.express as px
from jinja2 import Environment, FileSystemLoader, select_autoescape

def _unique_version_dir(base_dir: Path, requested: str) -> Path:
    """
    Return base_dir/requested unless it exists. If it exists, append a timestamp for uniqueness.
    """
    candidate = base_dir / requested
    if not candidate.exists():
        return candidate

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return base_dir / f"{requested}_{timestamp}"


# ------------------------------------------------------------
# helpers (unchanged)
# ------------------------------------------------------------
# … parse_perf_stat, parse_collapsed_stacks, parse_google_benchmark,
#    parse_valgrind_massif, generate_bar_chart stay exactly as before …
# ------------------------------------------------------------

def generate_report(config_path: str,
                    data_root: str | Path,
                    dst_root:  str | Path,
                    version:   str) -> str:
    """
    Build an HTML performance report.

    :param config_path: path to cfg/chronocache.json
    :param data_root:   directory that contains gen/{stat,collapsed,flamegraph}
    :param dst_root:    destination project root (will receive rpt/<version>/report.html)
    :param version:     release tag (folder name under rpt/)
    :return:            full path to the generated HTML file
    """
    # ----- load config -------------------------------------------------------
    with open(config_path) as f:
        cfg = json.load(f)

    data_root = Path(data_root).resolve()
    dst_root  = Path(dst_root).resolve()

    # ----- resolve directories ----------------------------------------------
    if "paths" in cfg:  # new, tidy JSON style
        p = cfg["paths"]
        stat_dir       = data_root / p["perf_stat"]
        collapsed_dir  = data_root / p["collapsed"]
        flamegraph_dir = data_root / p["flamegraph"]
        base_dir       = dst_root / p["report_output"]
        report_dir     = _unique_version_dir(base_dir, version)
        report_dir.mkdir(parents=True, exist_ok=True)
        gb_path        = dst_root  / p.get("google_benchmark", "benchmarks/benchmark.json")
        # valgrind_path  = dst_root  / p.get("valgrind_massif",  "valgrind/massif.out")
    else:               # backward-compatibility with old absolute keys
        stat_dir       = Path(cfg["perf_stat_path"]).expanduser().resolve()
        collapsed_dir  = Path(cfg["collapsed_path"]).expanduser().resolve()
        flamegraph_dir = Path(cfg["flamegraph_path"]).expanduser().resolve()
        gb_path        = Path(cfg.get("google_benchmark_path", "benchmarks/benchmark.json")).expanduser().resolve()
        # valgrind_path  = Path(cfg.get("valgrind_massif_path",
        #                               "valgrind/massif.out")).expanduser().resolve()

    report_dir.mkdir(parents=True, exist_ok=True)

    # ----- locate newest input files ----------------------------------------
    stat_file = max(
        (f for f in stat_dir.iterdir() if f.name.startswith("perf-stat")),
        key=lambda f: f.stat().st_mtime)
    collapsed_file = max(
        (f for f in collapsed_dir.iterdir() if f.suffix == ".txt"),
        key=lambda f: f.stat().st_mtime)

    flamegraph_files = {
        f.name.replace("flamegraph-", "").replace(".svg", ""):
        os.path.relpath(f, start=report_dir)
        for f in flamegraph_dir.iterdir() if f.suffix == ".svg"
    }

    # ----- build dataframes --------------------------------------------------
    stat_df      = parse_perf_stat(stat_file)
    top_funcs_df = parse_collapsed_stacks(collapsed_file)
    gb_df        = parse_google_benchmark(gb_path)
    # heap_df     = parse_valgrind_massif(valgrind_path)

    # ----- render HTML via Jinja2 -------------------------------------------
    tpl_dir = Path(__file__).resolve().parent.parent / "tpl"
    env = Environment(
        loader=FileSystemLoader(tpl_dir),
        autoescape=select_autoescape(['html'])
    )
    template = env.get_template("report.html")

    html = template.render(
        project_name=cfg.get("project_name", "UnnamedProject"),
        version=version,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        flamegraph_links=flamegraph_files,
        cache_stats_div=generate_bar_chart(stat_df, "Metric", "Value", "Cache / Branch / CPU Stats"),
        top_funcs_div=generate_bar_chart(top_funcs_df, "Function", "Samples", "Top Hot Functions"),
        gb_chart_div=generate_bar_chart(gb_df, "Benchmark", "CPU Time (ns)", "Google Benchmark Results"),
        # heap_chart_div=generate_bar_chart(heap_df, "Snapshot",
        #                                   "Heap Size (Bytes)",
        #                                   "Heap Allocation Over Time")
    )

    output_path = report_dir / "report.html"
    output_path.write_text(html, encoding="utf-8")
    return str(output_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Generate HTML performance report"
    )
    parser.add_argument('--config', '-c', default=str(Path(__file__).parent.parent/'cfg/default.json'))
    parser.add_argument('--data',   '-d', default=str(Path(__file__).parent.parent))
    parser.add_argument('--dst',    '-t', required=True)
    parser.add_argument('--ver',    '-v', required=True)
    parser.add_argument('--report-name', '-n', default=None)

    args = parser.parse_args()
    folder_name = args.report_name or args.ver

    report_path = generate_report(
        config_path=args.config,
        data_root=args.data,
        dst_root=args.dst,
        version=args.ver if args.report_name is None else args.report_name
    )
    # ↓ print **only** the path (no prefix text)
    print(report_path)
