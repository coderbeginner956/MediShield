@echo off
title MediShield AI - Local Server
echo ===================================================
echo Starting MediShield AI Local Server on port 8000...
echo ===================================================
set PYTHONDONTWRITEBYTECODE=1
"d:\Git\Solar_Project\.venv\Scripts\python.exe" -B -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause
