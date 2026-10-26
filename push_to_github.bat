@echo off
title Push MediShield AI to GitHub
echo ===================================================
echo Pushing MediShield AI to GitHub...
echo ===================================================
cd /d "%~dp0"
git add .
git commit -m "Update MediShield AI"
git push origin main
echo ===================================================
echo Push complete!
echo ===================================================
pause
