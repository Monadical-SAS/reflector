#!/bin/bash

echo "🔍 Testing Jitsi Local Setup"
echo "================================"

# Test 1: Check Docker containers
echo -e "\n1. Docker Containers Status:"
if command -v docker &> /dev/null; then
    docker ps --format "table {{.Names}}\t{{.Status}}" | grep jitsi || echo "No Jitsi containers found"
else
    echo "❌ Docker not available"
fi

# Test 2: Check ports
echo -e "\n2. Port Availability:"
for port in 8080 8443 10000 4443 6380 3002; do
    if lsof -i :$port > /dev/null 2>&1; then
        echo "✅ Port $port is in use"
    else
        echo "❌ Port $port is not in use"
    fi
done

# Test 3: Test event collector
echo -e "\n3. Event Collector:"
if curl -s http://localhost:3002/health | grep -q "ok"; then
    echo "✅ Event collector is healthy"
else
    echo "❌ Event collector not responding"
fi

# Test 4: Test Jitsi web
echo -e "\n4. Jitsi Web Interface:"
if timeout 2 curl -s http://localhost:8080 > /dev/null 2>&1; then
    echo "✅ Jitsi web is accessible"
else
    echo "❌ Jitsi web not accessible on port 8080"
fi

# Test 5: Test Redis
echo -e "\n5. Redis Connection:"
if redis-cli -p 6380 ping 2>/dev/null | grep -q "PONG"; then
    echo "✅ Redis is responding"
else
    echo "❌ Redis not responding on port 6380"
fi

echo -e "\n================================"
echo "Test complete!"