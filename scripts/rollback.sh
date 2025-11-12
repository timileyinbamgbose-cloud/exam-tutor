#!/bin/bash
# ExamsTutor AI - Rollback Script
# Epic 3.4: Kubernetes Deployment & Security
# Rollback deployment to previous version

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
ENVIRONMENT="${1:-dev}"
NAMESPACE="examstutor-${ENVIRONMENT}"
REVISION="${2:-0}"

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

show_rollout_history() {
    log_info "Deployment history:"
    kubectl rollout history deployment/examstutor-api -n "${NAMESPACE}"
}

perform_rollback() {
    if [ "${REVISION}" = "0" ]; then
        log_info "Rolling back to previous revision..."
        kubectl rollout undo deployment/examstutor-api -n "${NAMESPACE}"
    else
        log_info "Rolling back to revision ${REVISION}..."
        kubectl rollout undo deployment/examstutor-api -n "${NAMESPACE}" --to-revision="${REVISION}"
    fi

    log_success "Rollback initiated"
}

wait_for_rollback() {
    log_info "Waiting for rollback to complete..."
    kubectl rollout status deployment/examstutor-api -n "${NAMESPACE}" --timeout=5m
    log_success "Rollback completed"
}

verify_rollback() {
    log_info "Verifying rollback..."

    # Get pod name
    POD_NAME=$(kubectl get pods -n "${NAMESPACE}" \
        -l app=examstutor-api \
        -o jsonpath="{.items[0].metadata.name}")

    # Check health
    HEALTH_STATUS=$(kubectl exec -n "${NAMESPACE}" "$POD_NAME" -- \
        curl -s http://localhost:8000/health/live || echo "failed")

    if echo "$HEALTH_STATUS" | grep -q "alive"; then
        log_success "Health check passed"
    else
        log_error "Health check failed"
        return 1
    fi
}

# Main
main() {
    log_info "ExamsTutor AI - Rollback Script"
    log_info "Environment: ${ENVIRONMENT}"
    echo ""

    # Validate environment
    if [[ ! "${ENVIRONMENT}" =~ ^(dev|staging|prod)$ ]]; then
        log_error "Invalid environment: ${ENVIRONMENT}"
        log_info "Usage: $0 <dev|staging|prod> [revision]"
        exit 1
    fi

    show_rollout_history
    echo ""

    read -p "Are you sure you want to rollback? (yes/no): " -r
    echo
    if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
        log_info "Rollback cancelled"
        exit 0
    fi

    perform_rollback
    echo ""

    wait_for_rollback
    echo ""

    verify_rollback
    echo ""

    log_success "Rollback completed successfully!"
}

main "$@"
