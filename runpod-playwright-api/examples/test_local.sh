#!/bin/bash
# Test RunPod handler locally without Docker
# This runs the handler with built-in RunPod API server

echo "========================================="
echo "Testing RunPod Handler Locally"
echo "========================================="
echo ""
echo "Starting local API server on http://localhost:8000"
echo "Press Ctrl+C to stop"
echo ""

cd ..
python handler.py --rp_serve_api --rp_serve_api_host 0.0.0.0 --rp_serve_api_port 8000
