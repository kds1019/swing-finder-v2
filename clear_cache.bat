@echo off
REM === Clear Streamlit cache and restart ===
echo Clearing Streamlit cache...

REM Delete cache directory
if exist "%USERPROFILE%\.streamlit\cache" (
    rmdir /s /q "%USERPROFILE%\.streamlit\cache"
    echo ✅ Cache cleared
) else (
    echo ℹ️ No cache found
)

REM Delete pycache files in project
if exist "__pycache__" rmdir /s /q "__pycache__"
if exist "utils\__pycache__" rmdir /s /q "utils\__pycache__"
echo ✅ Python cache cleared

echo.
echo Ready to run! Now execute: run-swing-finder.bat
pause

