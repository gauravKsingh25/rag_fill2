@echo off
REM Multi-Device RAG System Quick Start Script for Windows

echo 🚀 Starting Multi-Device RAG System
echo ==================================

REM Check if we're in the right directory
if not exist "package.json" (
    echo ❌ Error: Please run this script from the project root directory
    exit /b 1
)

REM Install frontend dependencies if needed
if not exist "node_modules" (
    echo 📦 Installing frontend dependencies...
    npm install
)

REM Check if backend directory exists
if not exist "backend" (
    echo ❌ Error: Backend directory not found
    exit /b 1
)

REM Setup backend
echo 🐍 Setting up backend...
cd backend

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo 🔧 Creating Python virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install backend dependencies
echo 📦 Installing backend dependencies...
pip install -r requirements.txt

REM Check for .env file
if not exist ".env" (
    echo ⚠️  Warning: .env file not found. Please copy .env.example to .env and configure your API keys.
    echo    Required: PINECONE_API_KEY, GOOGLE_API_KEY, MONGODB_URL
)

cd ..

echo.
echo ✅ Setup complete!
echo.
echo 📋 Next Steps:
echo 1. Configure your .env file in the backend directory
echo 2. Start MongoDB (if using local instance)
echo 3. Run the development servers:
echo.
echo    Frontend: npm run dev
echo    Backend:  cd backend ^& python main.py
echo.
echo 🌐 URLs:
echo    Frontend: http://localhost:3000
echo    Backend:  https://rag-fill2-1.onrender.com
echo    API Docs: https://rag-fill2-1.onrender.com/docs
echo.

pause
