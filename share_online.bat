@echo off
title MediShield AI - Public Cloudflare Tunnel
echo ===================================================
echo MediShield AI - Public Sharing Tunnel
echo Exposing local server on the internet via Cloudflare
echo ===================================================
"d:\Git\TE_project\cloudflared.exe" tunnel --url http://127.0.0.1:8000
pause

