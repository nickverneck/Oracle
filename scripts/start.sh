#!/bin/bash

# Oracle Chatbot System Startup Script
# This script ensures proper service startup order and health checks

set -e

echo "🚀 Starting Oracle Chatbot System..."

# Check if .env file exists, if not copy from example
if [ ! -f .env ]; then
    echo "📋 Creating .env file from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your configuration before continuing!"
    echo "   Especially set secure passwords and API keys."
    exit 1
fi

# Load environment variables
source .env

# Check for required environment variables
required_vars=("NEO4J_PASSWORD" "VLLM_API_KEY")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Error: $var is not set in .env file"
        exit 1
    fi
done

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Check for NVIDIA Docker support if GPU is requested
if [ "${CUDA_VISIBLE_DEVICES:-}" != "" ]; then
    if ! docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu20.04 nvidia-smi > /dev/null 2>&1; then
        echo "⚠️  Warning: NVIDIA Docker support not available. vLLM will run on CPU."
        echo "   To use GPU acceleration, install nvidia-docker2 and restart Docker."
    fi
fi

# Create necessary directories
mkdir -p logs

# Start services with proper dependency order
echo "🔧 Starting infrastructure services..."
docker-compose up -d oracle-neo4j oracle-chromadb

echo "⏳ Waiting for databases to be ready..."
# Wait for Neo4j
echo "   Waiting for Neo4j..."
timeout 120 bash -c 'until docker-compose exec oracle-neo4j cypher-shell -u ${NEO4J_USER:-neo4j} -p ${NEO4J_PASSWORD} "RETURN 1" > /dev/null 2>&1; do sleep 2; done'

# Wait for ChromaDB
echo "   Waiting for ChromaDB..."
timeout 60 bash -c 'until curl -f http://localhost:${CHROMADB_PORT:-8002}/api/v1/heartbeat > /dev/null 2>&1; do sleep 2; done'

echo "🤖 Starting model serving..."
docker-compose up -d oracle-vllm

echo "🔗 Starting backend API..."
docker-compose up -d oracle-backend

echo "⏳ Waiting for backend to be ready..."
timeout 60 bash -c 'until curl -f http://localhost:${BACKEND_PORT:-8000}/health > /dev/null 2>&1; do sleep 2; done'

echo "🎨 Starting frontend..."
docker-compose up -d oracle-frontend

echo "✅ Oracle Chatbot System started successfully!"
echo ""
echo "🌐 Access points:"
echo "   Frontend:  http://localhost:${FRONTEND_PORT:-3000}"
echo "   Backend:   http://localhost:${BACKEND_PORT:-8000}"
echo "   Neo4j:     http://localhost:${NEO4J_HTTP_PORT:-7474}"
echo "   ChromaDB:  http://localhost:${CHROMADB_PORT:-8002}"
echo ""
echo "📊 To view logs: docker-compose logs -f [service-name]"
echo "🛑 To stop: docker-compose down"
echo "🔄 To restart: docker-compose restart [service-name]"