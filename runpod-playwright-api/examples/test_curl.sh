#!/bin/bash
# Test deployed RunPod endpoint with curl

# Set your RunPod credentials here or via environment variables
if [ -z "$RUNPOD_API_KEY" ]; then
    echo "Error: RUNPOD_API_KEY environment variable not set"
    echo "Usage: export RUNPOD_API_KEY='your_api_key'"
    exit 1
fi

if [ -z "$RUNPOD_ENDPOINT_ID" ]; then
    echo "Error: RUNPOD_ENDPOINT_ID environment variable not set"
    echo "Usage: export RUNPOD_ENDPOINT_ID='your_endpoint_id'"
    exit 1
fi

echo "========================================="
echo "Testing RunPod Endpoint"
echo "========================================="
echo "Endpoint: https://api.runpod.ai/v2/$RUNPOD_ENDPOINT_ID/runsync"
echo ""

# Test with dealer workflow
curl -X POST "https://api.runpod.ai/v2/$RUNPOD_ENDPOINT_ID/runsync" \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d @dealer_workflow.json \
  | python -m json.tool

echo ""
echo "========================================="
echo "Test Complete"
echo "========================================="
