#!/bin/bash
# Stream Ralph Mode Dashboard to YouTube Live
#
# Usage: ./stream-to-youtube.sh
#
# Requires in .env:
#   YOUTUBE_STREAM_KEY=xxxx-xxxx-xxxx-xxxx

set -e

# Load environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
fi

# YouTube RTMP settings
YOUTUBE_STREAM_KEY="${YOUTUBE_STREAM_KEY:-}"
YOUTUBE_URL="rtmp://a.rtmp.youtube.com/live2"

# Display settings
DISPLAY_NUM=99
SCREEN_WIDTH=1920
SCREEN_HEIGHT=1080

# Dashboard settings
DASHBOARD_PORT=5555
DASHBOARD_URL="http://localhost:$DASHBOARD_PORT"

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  Ralph Mode - YouTube Stream                              ║"
echo "╚═══════════════════════════════════════════════════════════╝"

if [ -z "$YOUTUBE_STREAM_KEY" ]; then
    echo "ERROR: YOUTUBE_STREAM_KEY not set in .env"
    echo "Get your stream key from YouTube Studio > Go Live"
    exit 1
fi

# Cleanup function
cleanup() {
    echo "Cleaning up..."
    pkill -f "Xvfb :$DISPLAY_NUM" 2>/dev/null || true
    pkill -f "chromium.*$DASHBOARD_PORT" 2>/dev/null || true
    pkill -f "stream_dashboard.py" 2>/dev/null || true
    pkill -f "ffmpeg.*rtmp" 2>/dev/null || true
    echo "Cleanup done"
}

trap cleanup EXIT

# Kill any existing streams
cleanup

echo "Starting virtual display..."
Xvfb :$DISPLAY_NUM -screen 0 ${SCREEN_WIDTH}x${SCREEN_HEIGHT}x24 &
sleep 2

export DISPLAY=:$DISPLAY_NUM

echo "Starting dashboard server..."
cd "$SCRIPT_DIR"
./venv/bin/python stream_dashboard.py > /tmp/dashboard.log 2>&1 &
DASHBOARD_PID=$!
sleep 3

# Check dashboard is running
if ! curl -s "$DASHBOARD_URL/health" > /dev/null 2>&1; then
    echo "ERROR: Dashboard failed to start"
    cat /tmp/dashboard.log
    exit 1
fi

echo "Dashboard running at $DASHBOARD_URL"

echo "Starting Chromium in kiosk mode..."
chromium-browser \
    --no-sandbox \
    --disable-gpu \
    --disable-software-rasterizer \
    --kiosk \
    --start-fullscreen \
    --window-size=${SCREEN_WIDTH},${SCREEN_HEIGHT} \
    --disable-infobars \
    --hide-scrollbars \
    --autoplay-policy=no-user-gesture-required \
    "$DASHBOARD_URL" &
CHROME_PID=$!
sleep 5

echo "Starting ffmpeg stream to YouTube..."
echo "Stream Key: ${YOUTUBE_STREAM_KEY:0:8}..."
echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  🔴 STREAMING LIVE TO YOUTUBE                             ║"
echo "║                                                           ║"
echo "║  Dashboard: $DASHBOARD_URL                        ║"
echo "║  Suggest:   $DASHBOARD_URL/suggest                ║"
echo "║                                                           ║"
echo "║  Press Ctrl+C to stop                                     ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Stream with ffmpeg
# - Capture screen at 30fps
# - Encode with x264 at decent quality
# - Stream to YouTube RTMP
ffmpeg \
    -f x11grab \
    -framerate 30 \
    -video_size ${SCREEN_WIDTH}x${SCREEN_HEIGHT} \
    -i :$DISPLAY_NUM \
    -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=44100 \
    -c:v libx264 \
    -preset veryfast \
    -maxrate 3000k \
    -bufsize 6000k \
    -pix_fmt yuv420p \
    -g 60 \
    -c:a aac \
    -b:a 128k \
    -ar 44100 \
    -f flv \
    "${YOUTUBE_URL}/${YOUTUBE_STREAM_KEY}"

echo "Stream ended"
