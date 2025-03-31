#!/bin/bash

# Create directory for SSL certificates if it doesn't exist
mkdir -p ssl

# Generate a self-signed certificate for development
openssl req -x509 -newkey rsa:4096 -nodes -out ssl/cert.pem -keyout ssl/key.pem -days 365 \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

echo "Self-signed SSL certificate generated successfully!"
echo "Location: ./ssl/cert.pem and ./ssl/key.pem"
echo "Note: For production, replace these with real certificates from a trusted CA."