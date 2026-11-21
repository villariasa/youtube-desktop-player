@echo off
title YouTube Desktop Widget
cd /d "%~dp0"
start /min powershell -WindowStyle Hidden -Command "python widget.py"
