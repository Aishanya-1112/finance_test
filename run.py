"""
Launch script to run both backend and frontend servers concurrently.
"""
import subprocess
import sys
import time
import os
from pathlib import Path

def main():
    # Get the project root directory
    project_root = Path(__file__).parent.absolute()
    backend_dir = project_root / "backend"
    frontend_dir = project_root / "frontend"
    
    print("Starting Finance Tracker Application...")
    print("=" * 50)
    
    # Start backend server
    print("\n Starting Backend Server (FastAPI)...")
    backend_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--reload", "--port", "8000"],
        cwd=backend_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # Give backend time to start
    time.sleep(2)
    
    # Start frontend server
    print("Starting Frontend Server (Streamlit)...")
    frontend_process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py", "--server.port", "8501"],
        cwd=frontend_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    print("\n" + "=" * 50)
    print(" Both servers are running!")
    print("=" * 50)
    print("\n Access your application:")
    print("    Frontend (Streamlit): http://localhost:8501")
    print("    Backend API (FastAPI): http://localhost:8000")
    print("    API Docs: http://localhost:8000/docs")
    print("\n  Press Ctrl+C to stop both servers")
    print("=" * 50 + "\n")
    
    try:
        # Keep the script running and monitor both processes
        while True:
            # Check if processes are still running
            backend_status = backend_process.poll()
            frontend_status = frontend_process.poll()
            
            if backend_status is not None:
                print(f"\n❌ Backend process exited with code {backend_status}")
                frontend_process.terminate()
                break
            
            if frontend_status is not None:
                print(f"\n❌ Frontend process exited with code {frontend_status}")
                backend_process.terminate()
                break
            
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n\n Shutting down servers...")
        backend_process.terminate()
        frontend_process.terminate()
        
        # Wait for processes to terminate
        backend_process.wait(timeout=5)
        frontend_process.wait(timeout=5)
        
        print("Servers stopped successfully!")
        sys.exit(0)

if __name__ == "__main__":
    main()
