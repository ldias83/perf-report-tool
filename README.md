# Perf-Report-Tool

**A performance reporting toolkit for C++ projects**

---

## 1 · What it does

1. **Records**  
   `perf-record.sh` runs `perf record`, collapses stacks, and builds a flamegraph — all saved under  
   `perf-report-tool/gen/{perfdata,collapsed,flamegraph,stat}`.

2. **Reports**  
   `perf-report.sh` converts that raw data into a stand-alone **HTML report** with:

| Section | Details |
|---------|---------|
| Cache / branch counters | Plotly bar chart from `perf stat`            |
| Top hot functions       | Plotly bar chart from collapsed stacks       |
| Flamegraph link         | Points to the newest SVG in *gen/flamegraph* |

The report is written to **any project you name** under  
`<project-root>/rpt/<version>/report.html` (folder auto-created, timestamp suffix added if a clash occurs).

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
git clone https://github.com/your-user/perf-report-tool.git
cd perf-report-tool
python3 -m venv .venv
. .venv/bin/activate
pip install -q pandas plotly jinja2
```

## Directory Structure required (for the project which has the performance reports to be read).

```bash
perf-report-tool/
├─ bin/
│  ├─ perf-record.sh      # collect data
│  └─ perf-report.sh      # build HTML
├─ cfg/
│  └─ default.json        # generic, relative paths
├─ gen/                   # raw perf output (shared by all projects)
│  ├─ collapsed/   
│  ├─ perfdata/   
│  ├─ flamegraph/   
│  └─ stat/
└─ tpl/
   └─ report.html         # Jinja2 template
```


## Usage
```bash
# 1. record perf (still inside perf-report-tool)
./bin/perf-record.sh ../target/binary

# 3. generate report
./bin/perf-report.sh    \n
    -t ../ChronoCache   \n        # --dst  (required)
    -v v1.0.01          \n        # --ver  (required)
    -n nightly                    # --report-name (optional)
```
