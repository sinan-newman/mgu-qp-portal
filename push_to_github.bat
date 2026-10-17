@echo off
title Push MGU Portal to GitHub
cd /d "%~dp0"

echo ================================================================
echo       Deploy MGU Question Papers Portal to GitHub
echo ================================================================
echo.

set /p REPO_URL="Enter your GitHub Repository URL (e.g., https://github.com/USERNAME/mgu-qp-portal.git): "

if "%REPO_URL%"=="" (
    echo [ERROR] No URL provided. Please create a repository on https://github.com/new and rerun this script.
    pause
    exit /b
)

set GIT_CMD="..\mingit\cmd\git.exe"

echo.
echo [1/3] Setting remote origin to %REPO_URL%...
%GIT_CMD% remote remove origin >nul 2>&1
%GIT_CMD% remote add origin %REPO_URL%

echo [2/3] Setting default branch to main...
%GIT_CMD% branch -M main

echo [3/3] Pushing to GitHub...
%GIT_CMD% push -u origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ================================================================
    echo [SUCCESS] Code successfully pushed to GitHub!
    echo.
    echo To activate your live website on GitHub Pages:
    echo  1. Open your repository on GitHub in your browser.
    echo  2. Click on "Settings" (gear icon) -^> "Pages" (left sidebar).
    echo  3. Under "Build and deployment" -^> Source: select "Deploy from a branch".
    echo  4. Under "Branch", select "main" and folder "/ (root)", then click "Save".
    echo.
    echo Your site will be live at:
    echo   https://YOUR_USERNAME.github.io/YOUR_REPO_NAME/
    echo ================================================================
) else (
    echo.
    echo [ERROR] Push failed. Make sure:
    echo  - You created the repository on GitHub (https://github.com/new)
    echo  - You are signed in to GitHub when prompted.
)

pause
