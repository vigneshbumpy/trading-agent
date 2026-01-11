#!/bin/bash
# Start multi-user TradingAgents platform

echo "🚀 Starting TradingAgents Multi-User Platform..."
echo ""

# Check if dependencies are installed
if ! command -v streamlit &> /dev/null; then
    echo "❌ Streamlit not found. Installing dependencies..."
    pip install -r requirements.txt
    pip install -r dashboard/multiuser/requirements.txt
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "Please create a .env file with your API keys."
    echo ""
fi

# Check for PostgreSQL (optional - can use SQLite for development)
if [ -z "$DATABASE_URL" ]; then
    echo "ℹ️  Using SQLite database (development mode)"
    echo "For production, set DATABASE_URL in .env"
    echo ""
fi

# Start the application
echo "✅ Launching multi-user platform at http://localhost:8501"
echo ""
streamlit run dashboard/app_multiuser.py
