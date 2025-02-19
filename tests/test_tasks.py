from app.tasks.tasks import add
import time

def run_test_tasks():
    print("Starting test tasks...")
    
    # Successful tasks
    for i in range(5):
        print(f"Submitting successful task {i+1}/5")
        result = add.delay(i, i+1)
        print(f"Task ID: {result.id}")
        time.sleep(1)  # Space them out by 1 second

    # Tasks with delay
    for i in range(3):
        print(f"Submitting delayed task {i+1}/3")
        result = add.delay(i, i+1, delay=2)
        print(f"Task ID: {result.id}")
        time.sleep(1)

    # Failed tasks
    for i in range(2):
        print(f"Submitting failing task {i+1}/2")
        result = add.delay(i, i+1, failure=True)
        print(f"Task ID: {result.id}")
        time.sleep(1)

    print("All test tasks submitted. Check Grafana for metrics.")

if __name__ == "__main__":
    run_test_tasks() 