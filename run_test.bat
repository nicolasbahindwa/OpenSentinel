@echo off
REM OpenSentinel Test Runner for Windows

echo ============================================================
echo OpenSentinel Agent Test Runner
echo ============================================================
echo.

REM Set environment variables directly (backup if .env doesn't load)
set OPENSENTINEL_MODEL_NAME=gemini-1.5-flash
set OPENSENTINEL_MODEL_TEMPERATURE=0.3
set OPENSENTINEL_MODEL_MAX_TOKENS=8192
set GOOGLE_API_KEY=AIzaSyCYg2X3Zr7yNkWmdp1dkXzooDE3x89TEW8

echo Environment configured:
echo   Model: %OPENSENTINEL_MODEL_NAME%
echo   Provider: Google Gemini 1.5 Flash
echo.

echo Running test...
echo ============================================================
echo.

uv run python test_agent.py

echo.
echo ============================================================
echo Test complete!
echo ============================================================
pause
