import os, sys, subprocess, time, webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
VENV = BACKEND / ".venv"

def run_py(python, args):
    cmd = [str(python)] + args
    print("[$]", " ".join(cmd))
    return subprocess.run(cmd, check=True)

def ensure_venv():
    if not VENV.exists():
        print("[*] Creating venv:", VENV)
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
    py = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    try:
        run_py(py, ["-m", "pip", "--version"])
    except subprocess.CalledProcessError:
        print("[*] Bootstrapping pip via ensurepip...")
        run_py(py, ["-m", "ensurepip", "--upgrade"])
    req = BACKEND / "requirements.txt"
    print("[*] Installing dependencies from", req)
    run_py(py, ["-m", "pip", "install", "--upgrade", "setuptools", "wheel"])
    run_py(py, ["-m", "pip", "install", "-r", str(req)])
    return py

def start_services(py):
    backend_cmd = [str(py), "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "8000", "--app-dir", "backend"]
    front_cmd = [str(py), "-m", "http.server", "5173", "--bind", "127.0.0.1"]
    backend_proc = subprocess.Popen(backend_cmd, cwd=str(ROOT))
    front_proc = subprocess.Popen(front_cmd, cwd=str(FRONTEND))
    return backend_proc, front_proc

def main():
    if not (BACKEND / "app.py").exists() or not (FRONTEND / "index.html").exists():
        print("Project structure missing"); sys.exit(1)
    py = ensure_venv()
    b, f = start_services(py)
    time.sleep(1.5)
    try: webbrowser.open("http://127.0.0.1:5173/")
    except Exception: pass
    print("[*] Running. Press Ctrl+C to stop.")
    try:
        b.wait()
    except KeyboardInterrupt:
        pass
    finally:
        for p in (b, f):
            try: p.terminate()
            except Exception: pass

if __name__ == "__main__":
    main()
