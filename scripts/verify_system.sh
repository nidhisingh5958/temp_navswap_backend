#!/bin/bash

# NavSwap Backend - System Verification Script

echo "🚀 NavSwap Backend - System Verification"
echo "========================================"
echo ""

# Check if Docker is running
echo "1️⃣  Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop."
    exit 1
fi
echo "✅ Docker is running"
echo ""

# Check if docker-compose is installed
echo "2️⃣  Checking docker-compose..."
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed"
    exit 1
fi
echo "✅ docker-compose is installed"
echo ""

# Check if services are running
echo "3️⃣  Checking services..."
if docker-compose ps | grep -q "Up"; then
    echo "✅ Services are running"
    docker-compose ps
else
    echo "⚠️  Services are not running. Starting them..."
    docker-compose up -d
    echo "⏳ Waiting for services to start (30 seconds)..."
    sleep 30
fi
echo ""

# Check backend health
echo "4️⃣  Checking backend health..."
HEALTH_CHECK=$(curl -s http://localhost:8000/health)
if [ $? -eq 0 ]; then
    echo "✅ Backend is healthy"
    echo "$HEALTH_CHECK" | jq '.'
else
    echo "❌ Backend health check failed"
    echo "💡 Try: docker-compose logs backend"
    exit 1
fi
echo ""

# Check MongoDB connection
echo "5️⃣  Checking MongoDB..."
if docker-compose exec -T mongo mongosh --quiet --eval "db.adminCommand('ping')" > /dev/null 2>&1; then
    echo "✅ MongoDB is connected"
else
    echo "❌ MongoDB connection failed"
fi
echo ""

# Check Redis
echo "6️⃣  Checking Redis..."
if docker-compose exec -T redis redis-cli ping | grep -q "PONG"; then
    echo "✅ Redis is connected"
else
    echo "❌ Redis connection failed"
fi
echo ""

# Check if database is seeded
echo "7️⃣  Checking database..."
USER_COUNT=$(docker-compose exec -T mongo mongosh navswap --quiet --eval "db.users.countDocuments()" 2>/dev/null | tail -n 1)
if [ "$USER_COUNT" -gt 0 ]; then
    echo "✅ Database is seeded ($USER_COUNT users)"
else
    echo "⚠️  Database is empty. Run: docker-compose exec backend python scripts/seed_data.py"
fi
echo ""

# Check if models are present
echo "8️⃣  Checking ML models..."
MODEL_COUNT=$(ls -1 models/*.pkl 2>/dev/null | wc -l | tr -d ' ')
if [ "$MODEL_COUNT" -gt 0 ]; then
    echo "✅ Found $MODEL_COUNT model files"
    ls -1 models/*.pkl
else
    echo "⚠️  No model files found in models/ directory"
    echo "💡 Place your .pkl files in models/ and restart backend"
fi
echo ""

# Test API endpoints
echo "9️⃣  Testing API endpoints..."

# Test root endpoint
if curl -s http://localhost:8000/ | grep -q "NavSwap"; then
    echo "✅ Root endpoint working"
else
    echo "❌ Root endpoint failed"
fi

# Test docs endpoint
if curl -s http://localhost:8000/docs | grep -q "Swagger"; then
    echo "✅ API docs available"
else
    echo "❌ API docs failed"
fi

# Test station list endpoint
if curl -s http://localhost:8000/station/list | grep -q "stations"; then
    echo "✅ Station API working"
else
    echo "❌ Station API failed"
fi

echo ""
echo "========================================"
echo "📊 System Status Summary"
echo "========================================"
echo ""

# Final summary
if docker-compose ps | grep -q "Up"; then
    echo "✅ All services running"
    echo "✅ Backend: http://localhost:8000"
    echo "✅ API Docs: http://localhost:8000/docs"
    echo "✅ Health: http://localhost:8000/health"
    echo ""
    echo "🎉 System is ready for use!"
    echo ""
    echo "📚 Next steps:"
    echo "   1. Add ML models to models/ directory"
    echo "   2. Visit http://localhost:8000/docs to explore APIs"
    echo "   3. Run seed script if database is empty"
    echo "   4. Read QUICKSTART.md for usage examples"
else
    echo "❌ Some services are not running"
    echo "💡 Try: docker-compose up -d"
fi

echo ""
