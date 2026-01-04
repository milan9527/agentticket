#!/bin/bash
# Quick Start Script for Customer Frontend Demo

echo "🚀 Starting Customer Frontend Demo"
echo "=================================="

# Check if we're in the right directory
if [ ! -d "frontend" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

# Navigate to frontend
cd frontend

# Check if dependencies are installed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Start the development server
echo "🌟 Starting React development server..."
echo "Frontend will be available at: http://localhost:3000"
echo ""
echo "Demo Credentials:"
echo "Email: testuser@example.com"
echo "Password: TempPass123!"
echo ""
echo "Test Ticket ID: 550e8400-e29b-41d4-a716-446655440002"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

npm start
