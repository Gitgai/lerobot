#!/usr/bin/env bash
# Transcode a LeRobot dataset's videos from AV1 to H.264, in place.
#
# WHY
# ---
# LightwheelAI/leisaac-pick-orange stores video as AV1. That breaks GR00T's
# training dataloader in three different ways on this machine, and none of the
# error messages mention video or codecs:
#
#   torchcodec (the DEFAULT)  fails to IMPORT - torchcodec 0.4.0 links FFmpeg
#       4-6 (libavutil.so.56/57/58) and this machine has FFmpeg 8. Even
#       torchcodec 0.8.0 only claims FFmpeg 4-7.
#   -> resolve_backend() then falls back to pyav, which get_frames_by_indices
#      does NOT implement, so training dies on a bare NotImplementedError.
#   decord                    imports fine but cannot demux AV1:
#       "cannot find video stream with wanted index: -1"
#   ffmpeg (CLI)              WORKS - system FFmpeg 8 decodes AV1 - but it
#       spawns a subprocess per fetch: 153 ms per 3-frame read, which starves
#       the GPU (observed 4% utilisation, 0 steps completed).
#
# H.264 is understood by every backend, and decord then decodes it in-process.
# Videos are re-downloadable from the Hub, so transcoding in place is safe.
# Frames are preserved exactly in count and order; only the codec changes.
#
# Usage: transcode_dataset_av1_to_h264.sh <dataset_dir> [jobs]

set -uo pipefail

DS="${1:?usage: $0 <dataset_dir> [jobs]}"
JOBS="${2:-6}"
VID="$DS/videos"

[ -d "$VID" ] || { echo "no videos/ under $DS"; exit 1; }

total=$(find "$VID" -name "*.mp4" | wc -l)
echo "[transcode] $total files under $VID, $JOBS parallel jobs"

transcode_one() {
    f="$1"
    codec=$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of csv=p=0 "$f")
    [ "$codec" = "av1" ] || { echo "  skip (already $codec): $(basename "$f")"; return 0; }
    tmp="${f%.mp4}.h264.tmp.mp4"
    # -crf 18 is visually lossless for policy training; -preset fast keeps this
    # to minutes. Frame count and order are preserved.
    if ffmpeg -nostdin -v error -y -i "$f" -c:v libx264 -crf 18 -preset fast \
              -pix_fmt yuv420p -an "$tmp" 2>/dev/null; then
        a=$(ffprobe -v error -count_frames -select_streams v:0 \
              -show_entries stream=nb_read_frames -of csv=p=0 "$f")
        b=$(ffprobe -v error -count_frames -select_streams v:0 \
              -show_entries stream=nb_read_frames -of csv=p=0 "$tmp")
        if [ "$a" = "$b" ]; then
            mv "$tmp" "$f"
        else
            echo "  FRAME COUNT MISMATCH ($a vs $b), keeping original: $(basename "$f")"
            rm -f "$tmp"
        fi
    else
        echo "  FAILED: $(basename "$f")"; rm -f "$tmp"
    fi
}
export -f transcode_one

find "$VID" -name "*.mp4" -print0 | xargs -0 -P "$JOBS" -I{} bash -c 'transcode_one "$@"' _ {}

echo "[transcode] done. codecs now:"
find "$VID" -name "*.mp4" -exec ffprobe -v error -select_streams v:0 \
    -show_entries stream=codec_name -of csv=p=0 {} \; | sort | uniq -c
