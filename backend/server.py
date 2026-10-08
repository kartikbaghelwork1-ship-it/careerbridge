"""Run local development: python3 backend/server.py."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app import create_app
if __name__=='__main__':
    create_app().run(host='127.0.0.1',port=8000,debug=False)
