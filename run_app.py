import subprocess
import sys
import os
import time

def run_streamlit():
    print("Launching Streamlit app...")
    
    # Files for logging
    stdout_file = open("bbt10/app.out", "w")
    stderr_file = open("bbt10/app.err", "w")

    # Command to run
    cmd = [
        sys.executable, "-m", "streamlit", "run", "bbt10/app_modular.py",
        "--server.headless=true",
        "--server.runOnSave=true",
        "--server.port=8501",
        "--server.address=0.0.0.0"
    ]

    # Windows specific flags to detach process
    # CREATE_NEW_PROCESS_GROUP = 0x00000200
    # DETACHED_PROCESS = 0x00000008
    creationflags = 0x00000008 | 0x00000200

    try:
        process = subprocess.Popen(
            cmd,
            stdout=stdout_file,
            stderr=stderr_file,
            creationflags=creationflags,
            close_fds=True 
        )
        print(f"Streamlit launched with PID: {process.pid}")
        print("Redirecting output to bbt10/app.out and bbt10/app.err")
        return process.pid
    except Exception as e:
        print(f"Failed to launch: {e}")
        return None

if __name__ == "__main__":
    run_streamlit()
