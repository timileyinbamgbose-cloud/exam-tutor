#!/bin/bash
# ExamsTutor AI - Build and Push Docker Image
# Epic 3.4: Kubernetes Deployment & Security

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_REGISTRY="${DOCKER_REGISTRY:-docker.io}"
IMAGE_NAME="${DOCKER_REGISTRY}/examstutor/ai-api"
VERSION="${1:-0.4.0}"

log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

main() {
    log_info "Building Docker image..."

    cd "$PROJECT_ROOT"

    # Build image
    docker build \
        -f docker/Dockerfile \
        -t "${IMAGE_NAME}:${VERSION}" \
        -t "${IMAGE_NAME}:latest" \
        .

    log_success "Image built: ${IMAGE_NAME}:${VERSION}"

    # Push to registry
    log_info "Pushing to registry..."
    docker push "${IMAGE_NAME}:${VERSION}"
    docker push "${IMAGE_NAME}:latest"

    log_success "Image pushed to registry"

    # Display size
    SIZE=$(docker images "${IMAGE_NAME}:${VERSION}" --format "{{.Size}}")
    log_info "Image size: ${SIZE}"
}

main "$@"
