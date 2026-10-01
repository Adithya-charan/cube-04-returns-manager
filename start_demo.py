import subprocess
import time
import os
import signal
import sys
import socket
import shutil

def get_lan_ip():
    """Get the LAN IP address of this machine."""
    try:
        # Connect to a remote address to determine the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None

def main():
    print("====================================")
    print(" CUBE Returns Manager: System Demo ")
    print("====================================")
    
    lan_ip = get_lan_ip()
    
    # 1. Start backend on 0.0.0.0 for LAN access
    backend_cmd = [sys.executable, "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
    print("[1/3] Starting backend on 0.0.0.0:8000 (LAN accessible)...")
    backend = subprocess.Popen(backend_cmd)
    
    # 2. Start frontend on 0.0.0.0 for LAN access  
    print("[2/3] Starting frontend on 0.0.0.0:5173 (LAN accessible)...")
    project_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(project_dir, "mobile")
    npm_command = shutil.which("npm.cmd") or shutil.which("npm")
    if not npm_command:
        backend.terminate()
        raise RuntimeError("npm is required to start the frontend")
    frontend_env = os.environ.copy()
    frontend_env["VITE_API_BASE"] = f"http://{lan_ip}:8000" if lan_ip else "http://localhost:8000"
    frontend = subprocess.Popen(
        [npm_command, "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"],
        cwd=frontend_dir,
        env=frontend_env,
    )
    
    # 3. Wait for services to start
    print("[3/3] Waiting for services to start...")
    time.sleep(3)
    
    print("\n" + "=" * 50)
    print(" SYSTEM ONLINE - READY FOR DEMO")
    print("=" * 50)
    print()
    print("🖥️  LOCAL ACCESS:")
    print(f"   Backend API:  http://localhost:8000/docs")
    print(f"   Frontend UI:  http://localhost:5173")
    print()
    if lan_ip:
        print("📱 LAN ACCESS (Phone on same Wi-Fi):")
        print(f"   Backend API:  http://{lan_ip}:8000/docs")
        print(f"   Frontend UI:  http://{lan_ip}:5173")
        print()
        print("   Frontend is configured to call the backend on this machine.")
    else:
        print("⚠️  Could not detect LAN IP. Check 'ipconfig' manually.")
    print()
    print("🔧 SETUP FOR PHONE DEMO:")
    print("   1. Connect phone to same Wi-Fi network")
    print("   2. Open Frontend URL on phone browser")
    print("   3. Allow camera permission when prompted")
    print("   4. Capture product image and submit")
    print("   5. Wait for Qwen inspection (~57-238s on CPU)")
    print()
    print("Press Ctrl+C to stop all services.")
    print("=" * 50)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        backend.terminate()
        frontend.terminate()
        sys.exit(0)

if __name__ == "__main__":
    main()
