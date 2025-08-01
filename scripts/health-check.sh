#!/bin/bash

# Oracle Chatbot System Health Check Script
# This script checks the health of all services

set -e

echo "🏥 Oracle Chatbot System Health Check"
echo "======================================"

# Load environment variables if .env exists
if [ -f .env ]; then
    source .env
fi

# Default ports
BACKEND_PORT=${BACKEND_PORT:-8000}
FRONTEND_PORT=${FRONTEND_PORT:-3000}
NEO4J_HTTP_PORT=${NEO4J_HTTP_PORT:-7474}
CHROMADB_PORT=${CHROMADB_PORT:-8002}
VLLM_PORT=${VLLM_PORT:-8001}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check service health
check_service() {
    local service_name=$1
    local url=$2
    local timeout=${3:-10}
    
    echo -n "Checking $service_name... "
    
    if curl -f -s --max-time $timeout "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Healthy${NC}"
        return 0
    else
        echo -e "${RED}❌ Unhealthy${NC}"
        return 1
    fi
}

# Function to check Docker container status
check_container() {
    local container_name=$1
    echo -n "Checking container $container_name... "
    
    if docker ps --filter "name=$container_name" --filter "status=running" | grep -q "$container_name"; then
        echo -e "${GREEN}✅ Running${NC}"
        return 0
    else
        echo -e "${RED}❌ Not running${NC}"
        return 1
    fi
}

# Check Docker containers
echo "📦 Container Status:"
check_container "oracle-backend"
check_container "oracle-frontend" 
check_container "oracle-vllm"
check_container "oracle-neo4j"
check_container "oracle-chromadb"

echo ""

# Check service health endpoints
echo "🌐 Service Health:"
check_service "Backend API" "http://localhost:$BACKEND_PORT/health"
check_service "Frontend" "http://localhost:$FRONTEND_PORT"
check_service "Neo4j" "http://localhost:$NEO4J_HTTP_PORT"
check_service "ChromaDB" "http://localhost:$CHROMADB_PORT/api/v1/heartbeat"
check_service "vLLM" "http://localhost:$VLLM_PORT/health" 30

echo ""

# Check Docker Compose services
echo "🐳 Docker Compose Status:"
docker-compose ps

echo ""

# Check system resources
echo "💾 System Resources:"
echo "Memory usage:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

echo ""

# Check logs for errors (last 10 lines)
echo "📋 Recent Logs (errors only):"
for service in oracle-backend oracle-frontend oracle-vllm oracle-neo4j oracle-chromadb; do
    echo "--- $service ---"
    docker-compose logs --tail=5 "$service" 2>/dev/null | grep -i error || echo "No recent errors"
done

echo ""
echo "🏁 Health check complete!"