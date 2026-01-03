#!/bin/bash
#
# OCC Dashboard Starter
# Run this to start the dashboard server
#

PORT=${1:-8080}
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=================================="
echo "  OCC - Ops Command Centre"
echo "=================================="
echo ""
echo "Starting server on port $PORT..."
echo "Dashboard URL: http://localhost:$PORT"
echo ""
echo "Press Ctrl+C to stop"
echo ""

cd "$DIR"
python3 -m http.server $PORT
