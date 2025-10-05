#!/bin/bash

# IT Inventory Dashboard Startup Script

echo "🚀 Starting IT Inventory Dashboard..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed. Please install Python3 first."
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Please install pip3 first."
    exit 1
fi

# Install dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "📦 Installing Python dependencies..."
    pip3 install -r requirements.txt
else
    echo "⚠️  requirements.txt not found. Please ensure all dependencies are installed."
fi

# Check if parsed_inventory.json exists
if [ ! -f "parsed_inventory.json" ]; then
    echo "⚠️  parsed_inventory.json not found. Using sample data."
fi

# Start Flask API in background
echo "🔧 Starting Flask API server..."
python3 app.py &
FLASK_PID=$!

# Wait a moment for Flask to start
sleep 3

# Check if Flask is running
if ! kill -0 $FLASK_PID 2>/dev/null; then
    echo "❌ Failed to start Flask API server"
    exit 1
fi

echo "✅ Flask API server started (PID: $FLASK_PID)"

# Start Streamlit app
echo "🌐 Starting Streamlit dashboard..."
echo "📊 Dashboard will be available at: http://localhost:8501"
echo "🔌 API will be available at: http://localhost:5001"
echo ""
echo "Press Ctrl+C to stop both servers"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down servers..."
    kill $FLASK_PID 2>/dev/null
    echo "✅ Servers stopped"
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

# Start Streamlit (this will block)
streamlit run streamlit_app.py

# Cleanup if streamlit exits
cleanup
