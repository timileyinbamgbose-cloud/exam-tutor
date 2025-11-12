#!/bin/bash
# Start Monitoring Stack
# Epic 3.3: Monitoring & Observability

echo "=================================="
echo "ExamsTutor AI - Starting Monitoring Stack"
echo "=================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running"
    echo "Please start Docker and try again"
    exit 1
fi

echo "✓ Docker is running"
echo ""

# Check if docker-compose exists
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: docker-compose not found"
    echo "Please install docker-compose"
    exit 1
fi

echo "✓ docker-compose found"
echo ""

# Create required directories
echo "Creating required directories..."
mkdir -p config/prometheus
mkdir -p config/grafana/{provisioning/{datasources,dashboards},dashboards}
mkdir -p config/alertmanager

echo "✓ Directories created"
echo ""

# Start monitoring stack
echo "Starting monitoring stack..."
echo ""

docker-compose -f docker-compose.monitoring.yml up -d

if [ $? -eq 0 ]; then
    echo ""
    echo "=================================="
    echo "✅ Monitoring Stack Started Successfully!"
    echo "=================================="
    echo ""
    echo "Access the following services:"
    echo ""
    echo "📊 Grafana Dashboard:"
    echo "   http://localhost:3000"
    echo "   Username: admin"
    echo "   Password: admin123"
    echo ""
    echo "📈 Prometheus:"
    echo "   http://localhost:9090"
    echo ""
    echo "🔍 Jaeger Tracing:"
    echo "   http://localhost:16686"
    echo ""
    echo "🔔 AlertManager:"
    echo "   http://localhost:9093"
    echo ""
    echo "📊 Node Exporter:"
    echo "   http://localhost:9100"
    echo ""
    echo "=================================="
    echo ""
    echo "To view logs:"
    echo "  docker-compose -f docker-compose.monitoring.yml logs -f"
    echo ""
    echo "To stop:"
    echo "  docker-compose -f docker-compose.monitoring.yml down"
    echo ""
else
    echo ""
    echo "❌ Error: Failed to start monitoring stack"
    echo "Check the error messages above"
    exit 1
fi
