@echo off
setlocal

:: Define the repository and image name
:: Docker Hub registry is just 'docker.io' or omitted, but specifying is explicit.
set REGISTRY=docker.io
:: Replace with your actual Docker Hub username!
set USERNAME=davidbenes
set IMAGE_NAME=colordays
set TAG=latest

set IMAGE_URL=%USERNAME%/%IMAGE_NAME%:%TAG%

echo 🚀 Building Docker image: %IMAGE_URL%
docker build -t %IMAGE_URL% .

if %ERRORLEVEL% EQU 0 (
    echo ✅ Build successful!
    echo ☁️  Pushing image to Docker Hub...
    
    :: You might need to run 'docker login' first if you haven't!
    docker push %IMAGE_URL%

    if %ERRORLEVEL% EQU 0 (
        echo 🎉 Successfully pushed %IMAGE_URL% to Docker Hub
    ) else (
        echo ❌ Failed to push the image. Are you logged in? ^(Run: docker login^)
        exit /b 1
    )
) else (
    echo ❌ Build failed!
    exit /b 1
)
