#!/bin/bash

# Function to trigger task with parameters
trigger_task() {
    local delay=$1
    local failure=$2
    curl "http://localhost:8787/trigger/?delay=$delay&failure=$failure"
    echo ""
}

# echo "Phase 1: Normal operation (1 minute)"
# end=$((SECONDS + 60))
# while [ $SECONDS -lt $end ]; do
#     trigger_task 0 false
#     sleep 2
# done

echo "Phase 2: High failure rate (1 minute)"
end=$((SECONDS + 120))
while [ $SECONDS -lt $end ]; do
    # 60% failure rate
    if [ $((RANDOM % 10)) -lt 6 ]; then
        trigger_task 0 true
    else
        trigger_task 0 false
    fi
    sleep 2
done

# echo "Phase 3: High latency (1 minute)"
# end=$((SECONDS + 60))
# while [ $SECONDS -lt $end ]; do
#     trigger_task 12 false  # 12 second delay to ensure p95 > 10s
#     sleep 2
# done

# echo "Phase 4: Back to normal operation (1 minute)"
# end=$((SECONDS + 60))
# while [ $SECONDS -lt $end ]; do
#     trigger_task 0 false
#     sleep 2
# done

echo "Demo complete!" 