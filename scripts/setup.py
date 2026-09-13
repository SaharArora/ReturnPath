"""Dependency installation only; never load application configuration."""
import pathlib
import subprocess
import sys

if sys.version_info[:2] != (3, 12):
    raise SystemExit("Python 3.12 required. With existing Homebrew: brew install python@3.12")
root = pathlib.Path(__file__).resolve().parents[1]
venv = root / ".venv"
if not venv.exists():
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
python = str(venv / "bin/python")
subprocess.run([python, "-c", "import sys; assert sys.version_info[:2] == (3,12), 'Existing .venv must use Python 3.12'"], check=True)
subprocess.run([python, "-m", "pip", "install", "--require-hashes", "-r", str(root / "requirements.lock")], check=True)
subprocess.run([python, "-m", "pip", "install", "--no-deps", "--no-build-isolation", "-e", str(root)], check=True)
