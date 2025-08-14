"""
Initialize the first user in the system.
This script creates a default user with the provided credentials.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the parent directory to the path so we can import from app
sys.path.append(str(Path(__file__).parent))

from app.database import connect_to_mongo, close_mongo_connection, user_repo
from app.core.auth import get_password_hash

async def create_first_user():
    """Create the first user in the system"""
    
    # Default user credentials
    email = "gaurav@gmail.com"
    password = "hindustan1"
    
    print("🔄 Initializing database connection...")
    
    try:
        # Initialize database connection
        await connect_to_mongo()
        
        # Check if user already exists
        existing_user = await user_repo.get_user_by_email(email)
        if existing_user:
            print(f"✅ User {email} already exists!")
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
        
        print(f"✅ Successfully created first user!")
        print(f"   Email: {email}")
        print(f"   User ID: {user_id}")
        print(f"   Password: {password}")
        print()
        print("🔐 You can now login with these credentials:")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        
    except Exception as e:
        print(f"❌ Error creating first user: {e}")
        raise
    
    finally:
        # Close database connection
        await close_mongo_connection()

if __name__ == "__main__":
    print("🚀 Setting up first user...")
    asyncio.run(create_first_user())
    print("✅ Setup complete!")
