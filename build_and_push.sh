#!/bin/bash

# Define the repository and image name
# Docker Hub registry is just 'docker.io' or omitted, but specifying is explicit.
REGISTRY="docker.io"
# Replace with your actual Docker Hub username!
USERNAME="dajda2371" 
IMAGE_NAME="colordays"
TAG="latest"

IMAGE_URL="${USERNAME}/${IMAGE_NAME}:${TAG}"

echo "🚀 Building Docker image: ${IMAGE_URL}"
docker build -t ${IMAGE_URL} .

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    echo "☁️  Pushing image to Docker Hub..."
    
    # You might need to run 'docker login' first if you haven't!
    docker push ${IMAGE_URL}

    if [ $? -eq 0 ]; then
        echo "🎉 Successfully pushed ${IMAGE_URL} to Docker Hub"
    else
        echo "❌ Failed to push the image. Are you logged in? (Run: docker login)"
        exit 1
    fi
else
    echo "❌ Build failed!"
    exit 1
fi
