@echo off
set CONDA_BASE=%USERPROFILE%\miniforge3
set PROJECT_DIR=%~dp0

start "Backend" cmd /k "call %CONDA_BASE%\Scripts\activate.bat %CONDA_BASE% && conda activate video-semantic-search && cd /d %PROJECT_DIR%backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

start "Frontend" cmd /k "cd /d %PROJECT_DIR%frontend && npm run dev"
