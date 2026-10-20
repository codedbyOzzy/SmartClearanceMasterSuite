@echo off
chcp 65001 >nul
title SmartClearance AI Asistan Test
python test_ai_assistant.py
if errorlevel 1 pause
