#!/bin/bash

# Define the repository and image name
# Replace 'YOUR_GITHUB_USERNAME' with your actual username if using GHCR
# Or replace the whole URL if you are pushing to Docker Hub or AWS, etc.
REGISTRY="ghcr.io"
USERNAME="davidbenes" # Feel free to change this!
IMAGE_NAME="colordays"
TAG="latest"

IMAGE_URL="${REGISTRY}/${USERNAME}/${IMAGE_NAME}:${TAG}"

echo "🚀 Building Docker image: ${IMAGE_URL}"
docker build -t ${IMAGE_URL} .

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    echo "☁️  Pushing image to registry..."
    
    # You might need to run 'docker login ghcr.io' first if you haven't!
    docker push ${IMAGE_URL}

    if [ $? -eq 0 ]; then
        echo "🎉 Successfully pushed ${IMAGE_URL}"
    else
        echo "❌ Failed to push the image. Are you logged in? (Run: docker login ${REGISTRY})"
        exit 1
    fi
else
    echo "❌ Build failed!"
    exit 1
fi
