#!/usr/bin/env bash
# Sweep loose eval artifacts from the Acer home into ~/runs/, and clear regenerable
# scratch. ORGANIZE-ONLY for trial data (never deletes frames/traces/sheets/logs);
# deletes only always-regenerable scratch (run_frames, __pycache__, probe jpgs).
# Safe to run anytime the home root gets messy.  Usage: ./tidy.sh
set -u
cd ~ || exit 1
if pgrep -f "[r]ecord_wrapper|[n]16_realarm_client" >/dev/null; then
  echo "tidy: a recording/trial is running - aborting (run again when idle)"; exit 1
fi
mkdir -p ~/runs/trials ~/runs/logs
moved=0; del=0

# 1) trial artifacts -> ~/runs/trials/<N>/
nums=$(ls -d trial_*_frames trial_*_trace.jsonl trial_*_sheet.jpg trial_*.log 2>/dev/null \
       | sed -E "s#^trial_##; s#(_frames|_trace\.jsonl|_sheet\.jpg|\.log)\$##" | sort -u)
for N in $nums; do
  mkdir -p ~/runs/trials/"$N"
  [ -d trial_${N}_frames ]      && { mv trial_${N}_frames      ~/runs/trials/$N/frames;      moved=$((moved+1)); }
  [ -f trial_${N}_trace.jsonl ] && { mv trial_${N}_trace.jsonl ~/runs/trials/$N/trace.jsonl; moved=$((moved+1)); }
  [ -f trial_${N}_sheet.jpg ]   && { mv trial_${N}_sheet.jpg   ~/runs/trials/$N/sheet.jpg;   moved=$((moved+1)); }
  [ -f trial_${N}.log ]         && { mv trial_${N}.log         ~/runs/trials/$N/log;         moved=$((moved+1)); }
done

# 2) run/home logs -> ~/runs/logs/
for f in home_*.log recovery_batch.log viz_*.log srv_*.log n16_*.log realarm_run*.log; do
  [ -e "$f" ] && { mv "$f" ~/runs/logs/; moved=$((moved+1)); }
done

# 3) delete ALWAYS-regenerable scratch (never trial data)
for d in run_frames __pycache__; do [ -e "$d" ] && { rm -rf "$d"; del=$((del+1)); }; done
for f in cam_v*.jpg node_v*.jpg live_*.jpg live_now.jpg front_now.jpg wrist_now.jpg \
         front_latest.jpg graspframes_*.jpg *_start.jpg cam0.jpg cam2.jpg front_*.jpg \
         after*_*.jpg rec2.jpg all_nodes.jpg cam_probe.jpg positions_montage.jpg; do
  [ -e "$f" ] && { rm -f "$f"; del=$((del+1)); }
done

echo "tidy: filed $moved artifact(s) into ~/runs/, removed $del scratch item(s); trials now: $(ls ~/runs/trials 2>/dev/null | wc -l)"
