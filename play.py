import subprocess
import time
from databaseSendMSG import handle_error


# @brief: This function monitors the execution of "studio.py" and handles its termination.
# If the process exits unexpectedly, it will retry up to a maximum number of attempts.
def monitor_main():
    cpt = 0
    max_attempts = 10

    while True:
        print("Starting studio.py...")
        process = subprocess.Popen(["python3", "studio.py"])
        process.wait()

        # Check if the process has terminated
        if process.returncode != 0:
            cpt = cpt + 1
            handle_error(f"Strategy has been interrupted\nError N°{process.returncode}\nRelaunching, attempt N°{cpt}")

            # Check if the maximum number of attempts has been reached
            if cpt >= max_attempts:
                handle_error(f"Reached the maximum of {max_attempts} attempts. Strategy interrupted.")
                break
        else:
            print("Strategy has terminated correctly.")
            break

        # Wait for a few seconds before relaunching the process
        time.sleep(15)


if __name__ == "__main__":
    monitor_main()
