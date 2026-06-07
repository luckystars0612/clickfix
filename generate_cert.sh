#!/bin/bash
# Generate self-signed SSL certificate
# Usage: bash generate_cert.sh yourdomain.com

DOMAIN=${1:-localhost}

echo "Generating self-signed certificate for: $DOMAIN"

openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem \
  -days 365 -nodes \
  -subj "/CN=$DOMAIN"

echo ""
echo "Generated files:"
echo "  - cert.pem (certificate)"
echo "  - key.pem  (private key)"
echo ""
echo "Add to config/config.yaml:"
echo "  server:"
echo "    port: 443"
echo "    ssl: true"
echo "    cert_file: cert.pem"
echo "    key_file: key.pem"
