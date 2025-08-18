#!/bin/bash
# Start script for Certificate Microservice

# Change to certificate directory
cd /app/modules/certificate

echo "Starting Certificate Microservice..."

# Start PDF service in background
echo "Starting PDF service on port 3001..."
cd pdf-service
node src/app.js > pdf-service.log 2>&1 &
PDF_PID=$!
echo "PDF service started with PID: $PDF_PID"

# Go back to certificate directory
cd /app/modules/certificate

# Start FastAPI service
echo "Starting Certificate API service on port 8006..."
python app.py > certificate-service.log 2>&1 &
API_PID=$!
echo "Certificate API service started with PID: $API_PID"

# Store PIDs for cleanup
echo "$PDF_PID" > pdf-service.pid
echo "$API_PID" > certificate-service.pid

echo "Certificate Microservice started successfully!"
echo "PDF Service: http://localhost:3001"
echo "Certificate API: http://localhost:8006"
echo "Health Check: http://localhost:8006/health"
echo "API Documentation: http://localhost:8006/docs"

# Wait for processes
wait