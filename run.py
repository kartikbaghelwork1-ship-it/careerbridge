"""One-command local setup: python3 run.py (Python 3.10+)."""
from pathlib import Path
import os,subprocess,sys,venv
root=Path(__file__).resolve().parent
folder=root/'.venv'
python=folder/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
if not python.exists():
 print('Creating project environment…',flush=True);venv.EnvBuilder(with_pip=True).create(folder)
check=subprocess.run([str(python),'-c','import flask'],capture_output=True)
if check.returncode:
 print('Installing project dependencies…',flush=True);subprocess.run([str(python),'-m','pip','install','-r',str(root/'requirements.txt')],check=True)
print('Open http://127.0.0.1:8000 in your browser. Press Ctrl+C to stop.',flush=True)
try:subprocess.run([str(python),str(root/'backend/server.py')],cwd=root,check=True)
except KeyboardInterrupt:pass
