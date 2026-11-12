#!/usr/bin/env bash
# Collect machine facts only. Does not install packages, open cameras/serial
# devices, enable torque, start servers, or load a model.
set -eu
if [[ $# -ne 1 || "$1" == --help || "$1" == -h ]]; then
  echo "Usage: bash collect_machine_profile.sh NEW_OUTPUT_DIRECTORY"
  echo "Creates a private directory containing host, GPU, storage and USB listings."
  exit 0
fi
umask 077
mkdir -- "$1"
OUT=$(cd -- "$1" && pwd)
capture() {
  local name=$1
  shift
  if "$@" >"$OUT/$name.txt" 2>&1; then
    echo "$name OK" >>"$OUT/status.txt"
  else
    local result=$?
    echo "$name FAILED ($result); inspect $name.txt" >>"$OUT/status.txt"
  fi
}
capture timestamp date --iso-8601=seconds
capture hostname hostname
capture username id
capture os cat /etc/os-release
capture kernel uname -a
capture cpu lscpu
capture memory free -h
capture disks lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS,MODEL
capture free-space df -hT
capture gpu nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv
capture pci lspci -nn
capture usb lsusb
capture addresses ip -brief address
capture serial-names ls -l /dev/serial/by-id /dev/serial/by-path
capture camera-names ls -l /dev/v4l/by-id /dev/v4l/by-path
capture python python3 --version
capture uv uv --version
capture git git --version
printf 'Profile saved to %s\n' "$OUT"
cat "$OUT/status.txt"
