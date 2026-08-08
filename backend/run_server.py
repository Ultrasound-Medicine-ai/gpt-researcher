#!/usr/bin/env python3
"""
GPT-Researcher Backend Server Startup Script

Run this to start the research API server.
"""

import uvicorn
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = Path(backend_dir).resolve().parent
sys.path.insert(0, backend_dir)

load_dotenv(repo_root / ".env")

if __name__ == "__main__":
    # Change to backend directory
    os.chdir(backend_dir)
    
    # Start the server
    uvicorn.run(
        "server.app:app",
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )



