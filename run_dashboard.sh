#!/bin/bash
# Quick start script for TradingAgents Dashboard

echo "🚀 Starting TradingAgents Dashboard..."
echo ""

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "❌ Streamlit not found. Installing dashboard dependencies..."
    pip install -r dashboard/requirements.txt
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "Please create a .env file with your API keys."
    echo "See .env.example for reference."
    echo ""
fi

# Start the dashboard
echo "✅ Launching dashboard at http://localhost:8501"
echo ""
streamlit run dashboard/app.py
