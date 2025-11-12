# Epic 3.4: Kubernetes Deployment & Security

**Phase:** 3 - Production Deployment
**Epic:** 3.4 - Kubernetes Deployment & Security
**Story Points:** 34
**Status:** ✅ IMPLEMENTED
**Date Completed:** November 5, 2025

---

## Overview

Epic 3.4 implements production-ready Kubernetes deployment with comprehensive security measures and NDPR compliance for the ExamsTutor AI API.

### Key Achievements

✅ **Docker Containerization** - Multi-stage builds for optimized images
✅ **Kubernetes Manifests** - Complete K8s resource definitions
✅ **Kustomize Overlays** - Environment-specific configurations
✅ **Horizontal Pod Autoscaler** - Automatic scaling based on load
✅ **Security Policies** - NetworkPolicy, RBAC, Pod Security
✅ **NDPR Compliance** - Data encryption, audit logging, retention policies
✅ **Helm Chart** - Production-grade Helm deployment
✅ **Deployment Automation** - Automated deployment scripts

---

## 1. Docker Containerization

### Dockerfile

**Location:** `docker/Dockerfile`

#### Features:
- **Multi-stage build** for reduced image size
- **Non-root user** (UID 1000) for security
- **Health checks** built-in
- **Optimized layers** for caching
- **Security scanning** ready

#### Build Configuration:

```bash
# Build image
docker build -f docker/Dockerfile -t examstutor-api:0.4.0 .

# Run container
docker run -p 8000:8000 examstutor-api:0.4.0
```

#### Image Specifications:
- Base: `python:3.10-slim`
- Size: ~800MB (optimized)
- Security: Non-root, minimal attack surface
- Health Check: `/health/live` endpoint

### Docker Compose

#### Development (`docker-compose.yml`)
- Full stack with all dependencies
- PostgreSQL, Redis, Monitoring
- Volume mounts for development
- Hot-reload enabled

#### Production (`docker-compose.prod.yml`)
- Optimized for production
- Resource limits configured
- Nginx reverse proxy
- Persistent volumes

### Usage:

```bash
# Development
docker-compose up -d

# Production
docker-compose -f docker-compose.prod.yml up -d
```

---

## 2. Kubernetes Base Manifests

**Location:** `k8s/base/`

### Resources Created:

| Resource | File | Description |
|----------|------|-------------|
| Namespace | `namespace.yaml` | Isolated namespace |
| ServiceAccount | `serviceaccount.yaml` | RBAC service account |
| ConfigMap | `configmap.yaml` | Non-sensitive config |
| Secrets | `secrets.yaml` | Sensitive credentials |
| Deployment | `deployment.yaml` | API deployment |
| Service | `service.yaml` | ClusterIP service |
| Ingress | `ingress.yaml` | HTTPS ingress |
| PVC | `pvc.yaml` | Persistent volumes |

### Deployment Configuration:

#### Replicas
- **Development:** 1 replica
- **Staging:** 2 replicas
- **Production:** 3+ replicas (HPA managed)

#### Resources:

```yaml
requests:
  memory: "2Gi"
  cpu: "1000m"
limits:
  memory: "4Gi"
  cpu: "2000m"
```

#### Health Checks:

```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8000
  initialDelaySeconds: 60
  periodSeconds: 30

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
```

### Security Context:

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  allowPrivilegeEscalation: false
  capabilities:
    drop:
    - ALL
```

---

## 3. Kustomize Overlays

**Location:** `k8s/overlays/{dev,staging,prod}/`

### Environment-Specific Configurations:

#### Development Overlay
- 1 replica
- Reduced resources
- Debug logging
- NodePort service
- No TLS

#### Staging Overlay
- 2 replicas
- Moderate resources
- Info logging
- TLS enabled
- Pre-production testing

#### Production Overlay
- 3+ replicas (HPA)
- Full resources
- Info/Warning logging
- TLS enforced
- Network policies
- Pod disruption budgets

### Deployment Commands:

```bash
# Development
kubectl apply -k k8s/overlays/dev/

# Staging
kubectl apply -k k8s/overlays/staging/

# Production
kubectl apply -k k8s/overlays/prod/
```

---

## 4. Horizontal Pod Autoscaler (HPA)

**Location:** `k8s/overlays/prod/hpa-patch.yaml`

### Configuration:

```yaml
minReplicas: 3
maxReplicas: 10
metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Scaling Behavior:

#### Scale Up:
- Fast response to increased load
- Max 100% increase in 30s
- Or +2 pods in 30s

#### Scale Down:
- Gradual reduction
- Max 50% decrease in 60s
- Or -1 pod in 60s
- 5-minute stabilization window

### Monitoring HPA:

```bash
# Check HPA status
kubectl get hpa -n examstutor

# Describe HPA
kubectl describe hpa examstutor-api-hpa -n examstutor

# Watch scaling events
kubectl get hpa -n examstutor --watch
```

---

## 5. Security Policies

### Network Policy

**Location:** `k8s/overlays/prod/network-policy.yaml`

#### Features:
- Restricts ingress to ingress controller and monitoring
- Controls egress to databases and external APIs
- Denies all other traffic by default

#### Rules:

```yaml
# Allow ingress from NGINX
- from:
  - namespaceSelector:
      matchLabels:
        name: ingress-nginx
  ports:
  - protocol: TCP
    port: 8000

# Allow egress to PostgreSQL
- to:
  - podSelector:
      matchLabels:
        app: postgres
  ports:
  - protocol: TCP
    port: 5432
```

### RBAC (Role-Based Access Control)

**Location:** `k8s/base/serviceaccount.yaml`

#### Components:
1. **ServiceAccount:** `examstutor-api-sa`
2. **Role:** Limited read access to ConfigMaps and Secrets
3. **RoleBinding:** Binds role to service account

#### Permissions:
- Read ConfigMaps
- Read specific Secrets
- Create Events (for logging)

### Pod Security Standards

#### Security Context:
- Non-root execution (UID 1000)
- Read-only root filesystem (where possible)
- No privilege escalation
- Drop all capabilities
- seccomp profile applied

---

## 6. NDPR Compliance Implementation

### Data Encryption

**Location:** `src/core/encryption.py`

#### Features:
- **Fernet encryption** (AES-256 symmetric)
- **PII masking** utilities
- **Secure hashing** (SHA-256/SHA-512)
- **Key derivation** from passwords (PBKDF2)

#### Usage:

```python
from src.core.encryption import encryption, pii_masker

# Encrypt sensitive data
encrypted = encryption.encrypt("Sensitive student data")
decrypted = encryption.decrypt(encrypted)

# Mask PII
masked_email = pii_masker.mask_email("student@examstutor.ng")
# Result: s*****@e***.ng
```

#### Encryption Scope:
- Student personal information
- Authentication credentials
- Financial data
- Medical/health records (if applicable)

### Audit Logging

**Location:** `src/core/audit.py`

#### Event Types:
- **Authentication:** Login, logout, password changes
- **Data Access:** Read, create, update, delete, export
- **Student Activities:** Registration, questions, practice
- **Administrative:** Config changes, role assignments
- **NDPR Events:** Consent, erasure requests, access requests
- **Security:** Alerts, rate limiting, suspicious activity

#### Log Format:

```json
{
  "timestamp": "2025-11-05T12:34:56.789Z",
  "event_type": "data.read",
  "user_id": "s*****@e***.ng",
  "resource": "student_profile",
  "action": "view",
  "result": "success",
  "severity": "low",
  "ip_address": "192.168.1.100",
  "details": {}
}
```

#### Compliance Features:
- **Immutable logs** (append-only)
- **7-year retention** for audit logs
- **PII masking** in logs
- **Secure storage** with encryption
- **Export capability** for compliance audits

### Data Retention

**Location:** `src/core/data_retention.py`

#### Retention Policies:

| Data Category | Retention Period | Legal Basis |
|---------------|------------------|-------------|
| User Profile | 2 years | Contract fulfillment |
| User Credentials | 2 years | Security audit |
| Student Questions | 3 years | Education quality |
| Student Practice | 3 years | Progress tracking |
| Audit Logs | 7 years | Legal obligation |
| Security Logs | 5 years | Security compliance |
| Sessions | 30 days | Technical necessity |
| Cache | 7 days | Performance |
| Temp Files | 24 hours | Technical necessity |

#### Right to Erasure:

```python
from src.core.data_retention import retention_manager

# Handle erasure request
result = await retention_manager.handle_erasure_request(
    user_id="student@examstutor.ng"
)

# Result: Deletes or anonymizes user data
```

#### Features:
- Automatic deletion after retention period
- Right to be forgotten implementation
- Data anonymization for legally required data
- Scheduled deletion queue
- Audit trail of all deletions

---

## 7. Helm Chart

**Location:** `helm/examstutor-api/`

### Chart Structure:

```
helm/examstutor-api/
├── Chart.yaml              # Chart metadata
├── values.yaml             # Default values
└── templates/
    ├── NOTES.txt          # Post-install notes
    ├── _helpers.tpl       # Template helpers
    ├── deployment.yaml    # Deployment template
    ├── service.yaml       # Service template
    ├── ingress.yaml       # Ingress template
    └── ...
```

### Installation:

```bash
# Install with default values
helm install examstutor-api ./helm/examstutor-api --namespace examstutor --create-namespace

# Install with custom values
helm install examstutor-api ./helm/examstutor-api \
  --namespace examstutor \
  --set image.tag=0.4.0 \
  --set config.environment=production \
  --values custom-values.yaml

# Upgrade release
helm upgrade examstutor-api ./helm/examstutor-api \
  --namespace examstutor \
  --set image.tag=0.4.1

# Rollback
helm rollback examstutor-api 1 --namespace examstutor

# Uninstall
helm uninstall examstutor-api --namespace examstutor
```

### Custom Values:

Create `custom-values.yaml`:

```yaml
replicaCount: 5

resources:
  requests:
    memory: "3Gi"
    cpu: "1500m"
  limits:
    memory: "6Gi"
    cpu: "3000m"

autoscaling:
  enabled: true
  minReplicas: 5
  maxReplicas: 20

ingress:
  hosts:
    - host: api.examstutor.ng
      paths:
        - path: /
          pathType: Prefix
```

---

## 8. Deployment Automation

### Deployment Script

**Location:** `scripts/deploy.sh`

#### Features:
- Prerequisites checking (kubectl, Docker)
- Docker image building and pushing
- Namespace creation
- Kustomize or Helm deployment
- Health check validation
- Deployment information display

#### Usage:

```bash
# Deploy to development
./scripts/deploy.sh dev

# Deploy to staging
./scripts/deploy.sh staging 0.4.0

# Deploy to production
./scripts/deploy.sh prod 0.4.0
```

### Rollback Script

**Location:** `scripts/rollback.sh`

#### Features:
- View rollout history
- Rollback to previous or specific revision
- Wait for rollback completion
- Health verification

#### Usage:

```bash
# Rollback to previous version
./scripts/rollback.sh prod

# Rollback to specific revision
./scripts/rollback.sh prod 3
```

### Build and Push Script

**Location:** `scripts/build_and_push.sh`

#### Usage:

```bash
# Build and push version 0.4.0
./scripts/build_and_push.sh 0.4.0

# Build and push latest
./scripts/build_and_push.sh latest
```

---

## 9. Production Deployment Guide

### Prerequisites:

1. **Kubernetes Cluster** (v1.24+)
   - Minimum 3 nodes
   - 8GB RAM per node
   - SSD storage

2. **Tools:**
   - kubectl (v1.24+)
   - Helm (v3.10+)
   - Docker (v20.10+)

3. **Cluster Add-ons:**
   - NGINX Ingress Controller
   - cert-manager (for TLS)
   - Prometheus (for metrics)
   - External Secrets Operator (optional)

### Step-by-Step Deployment:

#### 1. Prepare Secrets:

```bash
# Generate encryption keys
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Create secrets
kubectl create secret generic examstutor-secrets \
  --from-literal=SECRET_KEY='your-secret-key' \
  --from-literal=JWT_SECRET_KEY='your-jwt-key' \
  --from-literal=PII_ENCRYPTION_KEY='your-encryption-key' \
  --from-literal=DATABASE_URL='postgresql://...' \
  --from-literal=REDIS_URL='redis://...' \
  --namespace examstutor
```

#### 2. Configure Ingress:

Ensure NGINX Ingress Controller is installed:

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/cloud/deploy.yaml
```

#### 3. Setup cert-manager:

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
```

#### 4. Deploy Application:

Using Kustomize:
```bash
kubectl apply -k k8s/overlays/prod/
```

Using Helm:
```bash
helm install examstutor-api ./helm/examstutor-api \
  --namespace examstutor \
  --create-namespace \
  --values production-values.yaml
```

#### 5. Verify Deployment:

```bash
# Check pods
kubectl get pods -n examstutor

# Check services
kubectl get svc -n examstutor

# Check ingress
kubectl get ingress -n examstutor

# View logs
kubectl logs -n examstutor -l app=examstutor-api --tail=100
```

#### 6. Monitor:

```bash
# Check HPA
kubectl get hpa -n examstutor

# Check metrics
kubectl top pods -n examstutor

# Access metrics endpoint
kubectl port-forward -n examstutor svc/examstutor-api-service 8000:80
curl http://localhost:8000/metrics
```

---

## 10. Security Best Practices

### Image Security:
- ✅ Use minimal base images
- ✅ Scan for vulnerabilities
- ✅ Sign images
- ✅ Use specific tags (not `latest`)
- ✅ Regular updates

### Secrets Management:
- ✅ Use Kubernetes Secrets
- ✅ Consider External Secrets Operator
- ✅ Rotate secrets regularly
- ✅ Never commit secrets to Git
- ✅ Use sealed secrets for GitOps

### Network Security:
- ✅ Implement NetworkPolicies
- ✅ Use TLS for all external traffic
- ✅ Limit service exposure
- ✅ Use private networks for databases

### Access Control:
- ✅ RBAC for all service accounts
- ✅ Principle of least privilege
- ✅ Regular access audits
- ✅ MFA for cluster access

### Monitoring & Alerting:
- ✅ Monitor security events
- ✅ Alert on suspicious activity
- ✅ Regular security scans
- ✅ Incident response plan

---

## 11. NDPR Compliance Checklist

### Data Protection:
- ✅ Encryption at rest (PVC encryption)
- ✅ Encryption in transit (TLS)
- ✅ PII masking in logs
- ✅ Secure key management

### Data Subject Rights:
- ✅ Right to access (API endpoints)
- ✅ Right to erasure (automated)
- ✅ Right to portability (data export)
- ✅ Right to rectification (update APIs)

### Accountability:
- ✅ Comprehensive audit logs
- ✅ Data processing records
- ✅ Privacy by design
- ✅ Regular compliance audits

### Data Retention:
- ✅ Defined retention periods
- ✅ Automated deletion
- ✅ Backup retention policies
- ✅ Legal hold capabilities

---

## 12. Troubleshooting

### Common Issues:

#### Pods Not Starting:

```bash
# Check pod status
kubectl describe pod <pod-name> -n examstutor

# Check logs
kubectl logs <pod-name> -n examstutor

# Common fixes:
# - Check image pull secrets
# - Verify resource limits
# - Check dependencies (DB, Redis)
```

#### Ingress Not Working:

```bash
# Check ingress
kubectl describe ingress -n examstutor

# Check ingress controller
kubectl get pods -n ingress-nginx

# Verify DNS records
# Check TLS certificates
```

#### HPA Not Scaling:

```bash
# Check metrics server
kubectl get apiservice v1beta1.metrics.k8s.io -o yaml

# Check HPA status
kubectl describe hpa examstutor-api-hpa -n examstutor

# Verify metrics
kubectl top pods -n examstutor
```

---

## 13. Performance Tuning

### Resource Optimization:

```yaml
# Development
requests:
  memory: "1Gi"
  cpu: "500m"
limits:
  memory: "2Gi"
  cpu: "1000m"

# Production
requests:
  memory: "2Gi"
  cpu: "1000m"
limits:
  memory: "4Gi"
  cpu: "2000m"
```

### Autoscaling Tuning:

```yaml
# Aggressive scaling
minReplicas: 5
maxReplicas: 20
targetCPUUtilizationPercentage: 60

# Conservative scaling
minReplicas: 3
maxReplicas: 10
targetCPUUtilizationPercentage: 75
```

---

## Acceptance Criteria

| Criteria | Target | Status |
|----------|--------|--------|
| Docker Image | Optimized | ✅ |
| K8s Manifests | Complete | ✅ |
| Kustomize Overlays | 3 environments | ✅ |
| HPA | Functional | ✅ |
| Security Policies | Implemented | ✅ |
| NDPR Compliance | Complete | ✅ |
| Helm Chart | Production-ready | ✅ |
| Automation | Scripts created | ✅ |
| Documentation | Comprehensive | ✅ |

---

## Summary

Epic 3.4 has successfully established production-ready Kubernetes deployment:

✅ **Containerization** with multi-stage Docker builds
✅ **Kubernetes resources** for complete deployment
✅ **Environment management** with Kustomize
✅ **Auto-scaling** with HPA
✅ **Security hardening** with NetworkPolicy and RBAC
✅ **NDPR compliance** with encryption, audit, and retention
✅ **Helm packaging** for easy deployment
✅ **Deployment automation** with scripts

The ExamsTutor AI API is now **production-ready** and deployable to any Kubernetes cluster with comprehensive security and compliance measures.

---

**Epic 3.4 Status:** ✅ **COMPLETE** (34/34 story points)
**Completion Date:** November 5, 2025
**Phase 3 Status:** ✅ **COMPLETE** (All 4 epics done)
