@echo off
title Library Web App Server
cd /d "%~dp0"
echo ========================================================
echo  Starting Library Management System Web Server...
echo  Local URL: http://localhost:5000
echo ========================================================
python web_app.py
pause
