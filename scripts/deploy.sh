#!/bin/bash
# ExamsTutor AI - Deployment Script
# Epic 3.4: Kubernetes Deployment & Security
# Automated deployment to Kubernetes

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${1:-dev}"
NAMESPACE="examstutor-${ENVIRONMENT}"
DOCKER_REGISTRY="${DOCKER_REGISTRY:-docker.io}"
IMAGE_NAME="${DOCKER_REGISTRY}/examstutor/ai-api"
IMAGE_TAG="${2:-latest}"

# Functions
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found. Please install kubectl."
        exit 1
    fi
    log_success "kubectl is installed"

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker not found. Please install Docker."
        exit 1
    fi
    log_success "Docker is installed"

    # Check kubectl context
    CURRENT_CONTEXT=$(kubectl config current-context)
    log_info "Current kubectl context: $CURRENT_CONTEXT"

    # Check if kubectl can connect to cluster
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    log_success "Connected to Kubernetes cluster"
}

build_docker_image() {
    log_info "Building Docker image..."

    cd "$PROJECT_ROOT"

    docker build \
        -f docker/Dockerfile \
        -t "${IMAGE_NAME}:${IMAGE_TAG}" \
        -t "${IMAGE_NAME}:${ENVIRONMENT}-latest" \
        .

    log_success "Docker image built: ${IMAGE_NAME}:${IMAGE_TAG}"
}

push_docker_image() {
    log_info "Pushing Docker image to registry..."

    docker push "${IMAGE_NAME}:${IMAGE_TAG}"
    docker push "${IMAGE_NAME}:${ENVIRONMENT}-latest"

    log_success "Docker image pushed to registry"
}

create_namespace() {
    log_info "Creating namespace: ${NAMESPACE}"

    if kubectl get namespace "${NAMESPACE}" &> /dev/null; then
        log_warning "Namespace ${NAMESPACE} already exists"
    else
        kubectl create namespace "${NAMESPACE}"
        kubectl label namespace "${NAMESPACE}" environment="${ENVIRONMENT}"
        log_success "Namespace ${NAMESPACE} created"
    fi
}

deploy_with_kustomize() {
    log_info "Deploying with Kustomize..."

    cd "$PROJECT_ROOT/k8s/overlays/${ENVIRONMENT}"

    # Apply kustomization
    kubectl apply -k . --namespace="${NAMESPACE}"

    log_success "Deployment applied with Kustomize"
}

deploy_with_helm() {
    log_info "Deploying with Helm..."

    cd "$PROJECT_ROOT/helm"

    # Check if Helm is installed
    if ! command -v helm &> /dev/null; then
        log_error "Helm not found. Using Kustomize instead."
        deploy_with_kustomize
        return
    fi

    # Check if release exists
    if helm list -n "${NAMESPACE}" | grep -q "examstutor-api"; then
        log_info "Upgrading existing Helm release..."
        helm upgrade examstutor-api ./examstutor-api \
            --namespace "${NAMESPACE}" \
            --set image.tag="${IMAGE_TAG}" \
            --set config.environment="${ENVIRONMENT}" \
            --wait \
            --timeout 10m
    else
        log_info "Installing new Helm release..."
        helm install examstutor-api ./examstutor-api \
            --namespace "${NAMESPACE}" \
            --set image.tag="${IMAGE_TAG}" \
            --set config.environment="${ENVIRONMENT}" \
            --wait \
            --timeout 10m \
            --create-namespace
    fi

    log_success "Deployment applied with Helm"
}

wait_for_deployment() {
    log_info "Waiting for deployment to be ready..."

    kubectl rollout status deployment/examstutor-api \
        --namespace="${NAMESPACE}" \
        --timeout=10m

    log_success "Deployment is ready"
}

run_health_check() {
    log_info "Running health check..."

    # Get pod name
    POD_NAME=$(kubectl get pods -n "${NAMESPACE}" \
        -l app=examstutor-api \
        -o jsonpath="{.items[0].metadata.name}" \
        2>/dev/null || echo "")

    if [ -z "$POD_NAME" ]; then
        log_error "No pods found"
        return 1
    fi

    # Check health endpoint
    HEALTH_STATUS=$(kubectl exec -n "${NAMESPACE}" "$POD_NAME" -- \
        curl -s http://localhost:8000/health/live || echo "failed")

    if echo "$HEALTH_STATUS" | grep -q "alive"; then
        log_success "Health check passed"
    else
        log_error "Health check failed"
        return 1
    fi
}

display_deployment_info() {
    log_info "Deployment Information:"
    echo ""
    echo "  Environment: ${ENVIRONMENT}"
    echo "  Namespace: ${NAMESPACE}"
    echo "  Image: ${IMAGE_NAME}:${IMAGE_TAG}"
    echo ""

    log_info "Pods:"
    kubectl get pods -n "${NAMESPACE}" -l app=examstutor-api

    echo ""
    log_info "Services:"
    kubectl get services -n "${NAMESPACE}"

    echo ""
    if [ "${ENVIRONMENT}" = "prod" ] || [ "${ENVIRONMENT}" = "staging" ]; then
        log_info "Ingress:"
        kubectl get ingress -n "${NAMESPACE}"
    fi

    echo ""
    log_info "Useful commands:"
    echo "  View logs:"
    echo "    kubectl logs -n ${NAMESPACE} -l app=examstutor-api --tail=100 -f"
    echo ""
    echo "  Port forward:"
    echo "    kubectl port-forward -n ${NAMESPACE} svc/examstutor-api-service 8000:80"
    echo ""
    echo "  Delete deployment:"
    echo "    kubectl delete -k k8s/overlays/${ENVIRONMENT}/"
}

# Main execution
main() {
    log_info "ExamsTutor AI - Kubernetes Deployment Script"
    log_info "Environment: ${ENVIRONMENT}"
    echo ""

    # Validate environment
    if [[ ! "${ENVIRONMENT}" =~ ^(dev|staging|prod)$ ]]; then
        log_error "Invalid environment: ${ENVIRONMENT}"
        log_info "Usage: $0 <dev|staging|prod> [image-tag]"
        exit 1
    fi

    # Execute deployment steps
    check_prerequisites
    echo ""

    # Build and push image (skip for dev if using local registry)
    if [ "${ENVIRONMENT}" != "dev" ] || [ -n "${DOCKER_REGISTRY}" ]; then
        build_docker_image
        echo ""
        push_docker_image
        echo ""
    fi

    create_namespace
    echo ""

    # Deploy (choose method)
    if [ -f "$PROJECT_ROOT/helm/examstutor-api/Chart.yaml" ]; then
        deploy_with_helm
    else
        deploy_with_kustomize
    fi
    echo ""

    wait_for_deployment
    echo ""

    run_health_check
    echo ""

    display_deployment_info
    echo ""

    log_success "Deployment completed successfully!"
}

# Run main function
main "$@"
