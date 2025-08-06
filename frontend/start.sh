#!/bin/bash

# Multi-Device RAG System Quick Start Script

echo "🚀 Starting Multi-Device RAG System"
echo "=================================="

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Install frontend dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    npm install
fi

# Check if backend directory exists
if [ ! -d "backend" ]; then
    echo "❌ Error: Backend directory not found"
    exit 1
fi

# Setup backend
echo "🐍 Setting up backend..."
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🔧 Creating Python virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate 2>/dev/null || venv\Scripts\activate.bat

# Install backend dependencies
echo "📦 Installing backend dependencies..."
pip install -r requirements.txt

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found. Please copy .env.example to .env and configure your API keys."
    echo "   Required: PINECONE_API_KEY, GOOGLE_API_KEY, MONGODB_URL"
fi

cd ..

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Configure your .env file in the backend directory"
echo "2. Start MongoDB (if using local instance)"
echo "3. Run the development servers:"
echo ""
echo "   Frontend: npm run dev"
echo "   Backend:  cd backend && python main.py"
echo ""
echo "🌐 URLs:"
echo "   Frontend: http://localhost:3000"
echo "   Backend:  https://rag-fill2-1.onrender.com"
echo "   API Docs: https://rag-fill2-1.onrender.com/docs"
echo ""
