#!/bin/bash
# Build worker Docker image

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_NAME="codestat-worker:latest"

echo "Building worker image: ${IMAGE_NAME}"
docker build -t "${IMAGE_NAME}" "${SCRIPT_DIR}"

echo ""
echo "Image built successfully!"
echo "Image name: ${IMAGE_NAME}"
docker images "${IMAGE_NAME}"
