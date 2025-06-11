#!/usr/bin/env bash
# Perf-report-tool : record perf data for any C++ binary
# Usage:  bin/profile.sh <path-to-binary>

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <binary>"
  exit 1
fi

binary=$(realpath "$1")
[[ -x "$binary" ]] || { echo "$binary is not executable"; exit 1; }

timestamp=$(date "+%Y-%m-%d_%H-%M-%S")
repo_root="$(dirname "$(realpath "$0")")/.."        # perf-report-tool root
outdir="$repo_root/gen"

mkdir -p "$outdir"/{perfdata,collapsed,flamegraph,stat}

# ---------- 1. perf record ----------
perfdata="$outdir/perfdata/perf-$timestamp.data"
echo "► perf record → $perfdata"
perf record -F 99 -g -e cpu-clock -o "$perfdata" -- "$binary"

# ---------- 2. collapse ----------
collapsed="$outdir/collapsed/collapsed-$timestamp.txt"
perf script -i "$perfdata" | inferno-collapse-perf > "$collapsed"

# ---------- 3. flamegraph ----------
flame="$outdir/flamegraph/flamegraph-$timestamp.svg"
inferno-flamegraph < "$collapsed" > "$flame"

# ---------- 4. perf stat ----------
statfile="$outdir/stat/perf-stat-$timestamp.txt"
perf stat -e cache-references,cache-misses,branches,branch-misses \
          -- "$binary" 2> "$statfile"

echo -e "\nDone!\n  flamegraph : $flame\n  perf-stat  : $statfile"
