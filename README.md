# Perf-Report-Tool

**A reusable, project-agnostic performance reporting tool for C++ projects**

---

## Overview

**Perf-Report-Tool** automates the collection and presentation of performance metrics (cache references, cache misses, branch misses, etc.) and flamegraphs for any C++ project that follows a simple directory layout. It parses raw `perf` outputs, collapses stack traces, and generates a polished HTML report with interactive Plotly charts—showing cache/branch statistics and the top sampled functions—alongside a link to your flamegraph.

By defining a small JSON configuration for each project, you can leverage this tool across multiple repositories without code duplication.

---

## Key Features

- **Project-agnostic**: Just point to any C++ project’s `prf/out/` directory (where `perf` artifacts reside).
- **Interactive Charts**: Automatically generates Plotly bar charts for cache & branch counters and top functions by sample count.
- **Flamegraph Link**: Embeds a relative link to your most recent flamegraph SVG.
- **HTML Output**: Produces a standalone, styled HTML report you can open in any browser or commit to Git alongside your release.
- **Simple Configuration**: A tiny `config.json` per project defines paths and project metadata—no code changes needed.
- **Versioned Reports**: Tie each report to a Git tag or release version.

---

## Getting Started

### Prerequisites

1. **Python 3.8+**
2. **pip**
3. **perf** (Linux profiling tool)
4. **inferno** (for generating collapsed stacks and flamegraphs)

```bash
# Install inferno (one-time):
sudo apt update
sudo apt install rustup
rustup default stable
cargo install inferno
```

## Installation

Clone this repository somewhere outside your C++ project directory:

```bash
cd ~/Documents/Projects
git clone https://github.com/your-username/perf-report-tool.git
cd perf-report-tool
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Directory Structure required (for the project which has the performance reports to be read).

```bash
prj/
└── prf/
    └── out/
        ├── collapsed/
        ├── flamegraph/
        ├── perfdata/
        └── stat/
```

## Usage
```bash
source .venv/bin/activate
python generate_report.py config/prj.json v1.0.00
```

## Versioning & Git Integration
- Tagging each release in Git (e.g., git tag v1.0.00)
- Generating the report with the same version number
- Committing the HTML report to your repository under prf/out/reports/
