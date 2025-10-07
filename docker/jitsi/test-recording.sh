#!/bin/bash

echo "🎥 Jitsi Recording Test"
echo "======================="

# Check if Jibri is running
echo -e "\n1. Jibri Status:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep jibri

# Check Jibri logs for registration
echo -e "\n2. Jibri Registration Status:"
docker logs jitsi_jibri 2>&1 | grep -i "registered" | tail -2 || echo "Checking registration..."

# Check recording directory
echo -e "\n3. Recording Directory:"
ls -la ./recordings/ 2>/dev/null || echo "No recordings yet"

# Test Instructions
echo -e "\n📋 To Test Recording:"
echo "1. Open: http://localhost:3000/jitsi-test?local=true"
echo "2. Enter room details and click 'Join Meeting'"
echo "3. Once in meeting, click the 'Record' button (three dots menu -> Start Recording)"
echo "4. Recording will start after a few seconds"
echo "5. Stop recording when done"
echo ""
echo "📁 Recordings will appear in: ./recordings/"
echo "📊 Monitor events at: http://localhost:3002/events"
echo ""
echo "🔍 To monitor Jibri logs:"
echo "   docker logs -f jitsi_jibri"