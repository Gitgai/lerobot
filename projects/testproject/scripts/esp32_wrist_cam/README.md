# ESP32-S3 wrist camera

Firmware for a Seeed XIAO ESP32-S3 Sense used as a wrist camera. Serves the
same interface the SO-101 client already speaks, so adopting it changes only
`--wrist_url` - no robot-side code change.

    GET /frame    640x480 JPEG + X-Frame-Age-Seconds
    GET /stream   MJPEG, plays in a browser
    GET /health   rssi, ip, uptime
    GET /         viewer page

Measured on the arm 2026-09-01: 46 ms median latency, 10/10 unique frames,
3 h continuous uptime, view confirmed to track arm motion.

## Before flashing

Fill in WIFI_SSID and WIFI_PASS - they are placeholders here deliberately.

## Build and flash (arduino-cli lives at ~/esp32work/bin on the arm laptop)

    arduino-cli compile --fqbn esp32:esp32:XIAO_ESP32S3:PSRAM=opi <dir>
    arduino-cli upload -p /dev/ttyACM0 --fqbn esp32:esp32:XIAO_ESP32S3:PSRAM=opi <dir>

PSRAM=opi is required - the camera cannot allocate frame buffers without it.

## Notes

- Powered by USB only (no battery). A phone charger is enough; a data cable is
  needed only for flashing.
- DHCP, so the address moves. Find it with a scan of port 8092.
- The sensor is mounted upside down, corrected in firmware with
  vflip + hmirror.
- NOT a drop-in replacement for the OV5647: different sensor, visibly different
  images, and this policy is highly sensitive to that. Adopt only when
  re-recording demonstrations. See docs/plate_v2_and_hardware_20260901.md.
