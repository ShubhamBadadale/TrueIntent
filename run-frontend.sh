#!/usr/bin/env bash
# Start the TrueIntent React (Vite) portal on http://localhost:5173
set -euo pipefail
cd "$(dirname "$0")/frontend"
echo "Starting TrueIntent React (Vite) frontend on http://localhost:5173..."
exec npm run dev