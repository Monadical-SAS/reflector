#!/bin/bash

echo "Adding jitsi.local to /etc/hosts..."
echo ""
echo "Please run this command manually (requires sudo password):"
echo ""
echo "sudo sh -c 'echo \"127.0.0.1 jitsi.local\" >> /etc/hosts'"
echo ""
echo "After running the command, you can access Jitsi at:"
echo "  - https://jitsi.local (will show certificate warning - accept it)"
echo "  - http://localhost:3000/jitsi-test?local=true (for testing)"