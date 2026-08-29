"""
FinSight AI - Production Auto-Restart Server Supervisor.
Automatically monitors the FastAPI Uvicorn process and restarts on any crash, failure, or exit.
"""
import sys
import time
import subprocess
import os

PORT = 8000
HOST = "127.0.0.1"
RESTART_DELAY_SECONDS = 2


def run_supervisor():
    """
    Supervises the uvicorn process, automatically restarting it if it ever halts or crashes.
    """
    python_exe = sys.executable
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    print("=" * 65, flush=True)
    print("🚀 FinSight AI Server Supervisor Initialized", flush=True)
    print(f"📡 Serving on http://{HOST}:{PORT}", flush=True)
    print("🛡️ Auto-Restart Guard: ENABLED (Restarts immediately on any crash)", flush=True)
    print("=" * 65, flush=True)

    restart_count = 0

    while True:
        try:
            cmd = [
                python_exe,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                HOST,
                "--port",
                str(PORT),
                "--reload",
                "--log-level",
                "info"
            ]

            process = subprocess.Popen(cmd, cwd=script_dir)
            exit_code = process.wait()

            if exit_code == 0:
                print("\n[Supervisor] Server stopped cleanly. Exiting.", flush=True)
                break
            else:
                restart_count += 1
                print(f"\n⚠️ [Supervisor Alert] Server exited with code {exit_code} (Crash #{restart_count}).", flush=True)
                print(f"🔄 Auto-restarting FinSight AI backend in {RESTART_DELAY_SECONDS} seconds...", flush=True)
                time.sleep(RESTART_DELAY_SECONDS)

        except KeyboardInterrupt:
            print("\n[Supervisor] Received termination signal (Ctrl+C). Shutting down gracefully.", flush=True)
            if 'process' in locals() and process:
                process.terminate()
            break
        except Exception as e:
            restart_count += 1
            print(f"\n❌ [Supervisor Error]: {str(e)}. Restarting in {RESTART_DELAY_SECONDS}s...", flush=True)
            time.sleep(RESTART_DELAY_SECONDS)


if __name__ == "__main__":
    run_supervisor()
