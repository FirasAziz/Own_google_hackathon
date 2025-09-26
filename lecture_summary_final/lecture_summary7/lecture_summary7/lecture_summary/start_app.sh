#!/bin/bash

# Lecture Assist Startup Script

echo "🎓 Starting Lecture Assist..."

# Check if we're in the right directory
if [ ! -f "backend/app.py" ]; then
    echo "❌ Error: Please run this script from the lecture-assist root directory"
    exit 1
fi

# Check if Google Cloud credentials are set
if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo "⚠️  Warning: GOOGLE_APPLICATION_CREDENTIALS environment variable not set"
    echo "   Please set it to your Google Cloud service account key file"
    echo "   Example: export GOOGLE_APPLICATION_CREDENTIALS='/path/to/key.json'"
    echo ""
fi

# Install dependencies if needed
echo "📦 Checking dependencies..."
cd backend
pip install -r requirements.txt > /dev/null 2>&1

# Start the Flask application
echo "🚀 Starting Flask application..."
echo "   Open your browser and go to: http://localhost:5000"
echo "   Press Ctrl+C to stop the application"
echo ""
echo "🎓 AI Tutor Feature:"
echo "   - Upload audio and generate notes first"
echo "   - Click 'Speak with AI Tutor' for interactive Arabic tutoring"
echo "   - Live audio conversation with OpenAI Realtime API"
echo ""

python3 app.py
