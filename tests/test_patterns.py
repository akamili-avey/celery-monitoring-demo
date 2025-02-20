import time
import requests
import random
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get port from environment variables
DJANGO_PORT = os.getenv('DJANGO_PORT', '8787')

def send_task(failure=False, delay=0):
    response = requests.get(f"http://localhost:{DJANGO_PORT}/trigger/?delay={delay}&failure={failure}")
    return response.status_code == 200

def run_pattern_test():
    print("Starting 3-minute pattern test...")
    
    # Phase 1 (0-30s): Steady rate of successful tasks
    print("\nPhase 1: Steady rate (30s)")
    for i in range(6):  # 1 task every 5 seconds
        send_task(failure=False)
        print(f"Sent steady task {i+1}/6")
        time.sleep(5)

    # Phase 2 (30-60s): Burst of tasks
    print("\nPhase 2: Burst (30s)")
    for i in range(10):  # 10 tasks in quick succession
        send_task(failure=False)
        print(f"Sent burst task {i+1}/10")
        time.sleep(0.5)
    time.sleep(20)  # Wait for the remainder of the 30s

    # Phase 3 (60-90s): Mix of success and failure
    print("\nPhase 3: Mixed success/failure (30s)")
    for i in range(6):
        failure = random.choice([True, False])
        send_task(failure=failure)
        print(f"Sent mixed task {i+1}/6 (failure={failure})")
        time.sleep(5)

    # Phase 4 (90-120s): No tasks, then delayed tasks
    print("\nPhase 4: Quiet period + delayed tasks (30s)")
    time.sleep(15)  # No tasks for 15 seconds
    for i in range(3):
        send_task(failure=False, delay=2)
        print(f"Sent delayed task {i+1}/3")
        time.sleep(5)
    time.sleep(10)

    # Phase 5 (120-150s): Rapid success/fail alternation
    print("\nPhase 5: Alternating success/fail (30s)")
    for i in range(10):
        failure = i % 2 == 0  # Alternate between success and failure
        send_task(failure=failure)
        print(f"Sent alternating task {i+1}/10 (failure={failure})")
        time.sleep(3)

    # Phase 6 (150-180s): Final burst with mixed delays
    print("\nPhase 6: Mixed delays burst (30s)")
    for i in range(8):
        delay = random.choice([0, 1, 2])
        send_task(failure=False, delay=delay)
        print(f"Sent final burst task {i+1}/8 (delay={delay}s)")
        time.sleep(2)

    print("\nTest complete! Check Grafana dashboard for results.")

if __name__ == "__main__":
    run_pattern_test() 