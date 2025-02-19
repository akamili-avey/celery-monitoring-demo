#!/bin/bash

echo "Starting to send trigger requests every second..."
echo "Press Ctrl+C to stop"

while true; do
    # Send the request
    curl -s "http://localhost:8787/trigger/" | jq
    
    # Wait 1 second before next request
    sleep 1
done 