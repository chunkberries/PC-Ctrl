@echo off
cd /d "C:\remotethingy"
start "" wscript info.vbs
start "" pythonw remote_server.py