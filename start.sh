#!/bin/bash

# Simple startup script for IT Inventory Dashboard

echo "🚀 Starting IT Inventory Dashboard..."

# Kill any existing processes on our ports
echo "🧹 Cleaning up existing processes..."
lsof -ti:5001 | xargs kill -9 2>/dev/null || true
lsof -ti:8501 | xargs kill -9 2>/dev/null || true

# Wait a moment
sleep 2

# Start Flask API
echo "🔧 Starting Flask API on port 5001..."
python3 app.py &
FLASK_PID=$!

# Wait for Flask to start
sleep 3

# Start Streamlit
echo "🌐 Starting Streamlit on port 8501..."
streamlit run streamlit_app.py --server.headless true --server.port 8501 &
STREAMLIT_PID=$!

# Wait for Streamlit to start
sleep 5

echo ""
echo "✅ Both servers are running!"
echo "📊 Dashboard: http://localhost:8501"
echo "🔌 API: http://localhost:5001"
echo ""
echo "Press Ctrl+C to stop both servers"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down servers..."
    kill $FLASK_PID 2>/dev/null
    kill $STREAMLIT_PID 2>/dev/null
    echo "✅ Servers stopped"
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

# Wait for user to stop
wait
