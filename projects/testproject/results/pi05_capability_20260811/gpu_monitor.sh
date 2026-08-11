#!/usr/bin/env bash
# GPU telemetry for training runs. Low cadence, negligible cost, safe shutdown.
#
#   ./gpu_monitor.sh start <telemetry_dir> [interval_s]   default 5s
#   ./gpu_monitor.sh stop  <telemetry_dir>
#   ./gpu_monitor.sh report <telemetry_dir>
#
# ⚠ telemetry_dir must NOT be lerobot's --output_dir. This script creates the
#   directory, and lerobot refuses to start if its output_dir already exists
#   ("already exists and resume is False"). Use a sibling, e.g. <out>_gpu.
#
# Why this exists rather than an ad-hoc `nvidia-smi -l 1 &` per run:
#   · short probes hide thermal throttling and clock drift; only a long run
#     shows them, and only if something was recording
#   · per-process memory separates TRAINING from the ~1.4 GiB desktop, instead
#     of subtracting it by hand afterwards
#   · shutdown is by recorded PID. A broad `pkill -f nvidia-smi ...` can match
#     more than intended.
set -uo pipefail

CMD="${1:-}"; OUTDIR="${2:-}"; INTERVAL="${3:-5}"
[ -z "$CMD" ] || [ -z "$OUTDIR" ] && { sed -n '2,12p' "$0"; exit 2; }

GPU_CSV="$OUTDIR/gpu.csv"
PROC_CSV="$OUTDIR/gpu_procs.csv"
PIDFILE="$OUTDIR/gpu_monitor.pid"

FIELDS='timestamp,memory.used,memory.free,utilization.gpu,utilization.memory,temperature.gpu,clocks.current.sm,clocks.max.sm,power.draw,pstate,clocks_throttle_reasons.active,clocks_throttle_reasons.hw_thermal_slowdown,clocks_throttle_reasons.sw_power_cap'

case "$CMD" in
  start)
    mkdir -p "$OUTDIR"
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
      echo "already running (pid $(cat "$PIDFILE"))"; exit 0
    fi
    # stdbuf: nvidia-smi -l BLOCK-BUFFERS when redirected to a file, so without
    # this the CSV stays empty until the process exits and a killed monitor
    # yields ~1 row. Cost us a run once; do not remove.
    stdbuf -oL nvidia-smi --query-gpu="$FIELDS" --format=csv -l "$INTERVAL" > "$GPU_CSV" 2>&1 &
    echo $! > "$PIDFILE"
    # per-process stream: which PID holds what, so training is separable from desktop
    ( while :; do
        ts=$(date -Iseconds)
        nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader 2>/dev/null \
          | sed "s|^|$ts, |" >> "$PROC_CSV"
        sleep "$INTERVAL"
      done ) &
    echo $! >> "$PIDFILE"
    echo "monitoring -> $GPU_CSV (${INTERVAL}s), pids $(tr '\n' ' ' < "$PIDFILE")"
    ;;

  stop)
    [ -f "$PIDFILE" ] || { echo "no pidfile in $OUTDIR"; exit 1; }
    while read -r p; do kill "$p" 2>/dev/null && echo "stopped $p"; done < "$PIDFILE"
    rm -f "$PIDFILE"
    ;;

  report)
    [ -f "$GPU_CSV" ] || { echo "no $GPU_CSV"; exit 1; }
    python3 - "$GPU_CSV" "$PROC_CSV" <<'PY'
import csv, sys, os

def num(s):
    s = s.strip().split(' ')[0]
    try: return float(s)
    except ValueError: return None

rows = list(csv.DictReader(open(sys.argv[1])))
rows = [r for r in rows if r and list(r.values())[0] and 'timestamp' not in list(r.values())[0]]
if not rows:
    print("no samples"); sys.exit(0)
k = {c.split(' [')[0].strip(): c for c in rows[0]}

def col(name):
    return [num(r[k[name]]) for r in rows if k.get(name) and num(r[k[name]]) is not None]

used, temp, sm, pwr, util = (col(x) for x in
    ('memory.used','temperature.gpu','clocks.current.sm','power.draw','utilization.gpu'))
smmax = col('clocks.max.sm')

print(f"samples {len(rows)}   span {rows[0][k['timestamp']].strip()} -> {rows[-1][k['timestamp']].strip()}")
def line(label, v, unit, fmt="{:.1f}"):
    if not v: return
    print(f"  {label:22s} min {fmt.format(min(v))}{unit}  mean {fmt.format(sum(v)/len(v))}{unit}  MAX {fmt.format(max(v))}{unit}")
line("memory.used", [x/1024 for x in used], " GiB", "{:.2f}")
line("temperature", temp, " C")
line("clocks.sm", sm, " MHz")
line("power.draw", pwr, " W")
line("utilization.gpu", util, " %")

# drift: is peak memory creeping over the run? fragmentation / leak signal.
if len(used) > 20:
    n = len(used)//4
    a, b = max(used[:n])/1024, max(used[-n:])/1024
    print(f"  memory drift           first quarter peak {a:.2f} GiB -> last quarter peak {b:.2f} GiB  "
          f"({'+' if b>=a else ''}{b-a:.2f} GiB)")

# throttling: the thing a short probe cannot see
thr = [r for r in rows if k.get('clocks_throttle_reasons.hw_thermal_slowdown')
       and 'Active' == r[k['clocks_throttle_reasons.hw_thermal_slowdown']].strip()]
cap = [r for r in rows if k.get('clocks_throttle_reasons.sw_power_cap')
       and 'Active' == r[k['clocks_throttle_reasons.sw_power_cap']].strip()]
print(f"  THERMAL throttle       {len(thr)}/{len(rows)} samples" + ("  <- INVESTIGATE" if thr else "  (none)"))
print(f"  power-cap throttle     {len(cap)}/{len(rows)} samples" + ("  <- power limited" if cap else "  (none)"))
if sm and smmax:
    print(f"  clock headroom         sustained {sum(sm)/len(sm):.0f} of {max(smmax):.0f} MHz max")

pf = sys.argv[2] if len(sys.argv) > 2 else None
if pf and os.path.exists(pf):
    peak = {}
    for ln in open(pf):
        p = [x.strip() for x in ln.split(',')]
        if len(p) >= 3 and p[1].isdigit():
            peak[p[1]] = max(peak.get(p[1], 0), num(p[2]) or 0)
    if peak:
        print("\n  per-process PEAK (separates training from desktop):")
        for pid, mb in sorted(peak.items(), key=lambda x: -x[1])[:6]:
            print(f"    pid {pid:>8}  {mb/1024:.2f} GiB")
PY
    ;;
  *) sed -n '2,12p' "$0"; exit 2 ;;
esac
