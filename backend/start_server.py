"""
Startup script for the RAG system.
Initializes the database and creates the first user if it doesn't exist.
"""

import asyncio
import uvicorn
import os
from dotenv import load_dotenv

from app.database import connect_to_mongo, close_mongo_connection, user_repo
from app.core.auth import get_password_hash

load_dotenv()

async def ensure_first_user():
    """Ensure the first user exists in the system"""
    
    # Default user credentials
    email = "gaurav@gmail.com"
    password = "hindustan1"
    
    try:
        # Initialize database connection
        await connect_to_mongo()
        
        # Check if user already exists
        existing_user = await user_repo.get_user_by_email(email)
        if existing_user:
            print(f"✅ First user {email} already exists")
            return
        
        # Hash the password
        hashed_password = get_password_hash(password)
        
        # Create user data
        user_data = {
            "email": email,
            "hashed_password": hashed_password
        }
        
        # Create the user
        user_id = await user_repo.create_user(user_data)
        
        print(f"✅ Created first user!")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        
    except Exception as e:
        print(f"❌ Error ensuring first user: {e}")
        # Don't fail the startup, just log the error
    
    finally:
        # Close database connection (will be reopened by FastAPI)
        await close_mongo_connection()

def start_server():
    """Start the FastAPI server with user initialization"""
    print("🚀 Starting RAG System...")
    
    # Ensure first user exists
    asyncio.run(ensure_first_user())
    
    # Start the server
    print("🌐 Starting FastAPI server...")
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    start_server()
