from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import List, Optional
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from app.routers import devices, documents, chat, templates, auth, enhanced_csv_router, robust_csv_router, file_history, favorites
from app.database import connect_to_mongo, close_mongo_connection, user_repo
from app.services.pinecone_service import pinecone_service
from app.core.auth import get_password_hash

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    startup_errors = []
    startup_warnings = []
    mongodb_connected = False
    
    # Initialize MongoDB connection
    try:
        await connect_to_mongo()
        # Check if MongoDB is actually connected
        from app.database import mongodb
        if mongodb.client is not None:
            print("✅ MongoDB connected successfully")
            mongodb_connected = True
        else:
            print("📝 MongoDB: Using local storage (no MongoDB URL configured)")
    except Exception as e:
        startup_errors.append(f"MongoDB: {e}")
        print(f"❌ MongoDB connection failed: {e}")
    
    # Initialize Pinecone
    pinecone_available = False
    try:
        await pinecone_service.initialize_pinecone()
        # Check if Pinecone is actually available
        if pinecone_service.index is not None:
            pinecone_available = True
            print("✅ Pinecone service initialized successfully")
        else:
            startup_warnings.append("Pinecone: Using local vector storage fallback")
    except Exception as e:
        startup_warnings.append(f"Pinecone: {e}")
    
    # Create first user if it doesn't exist
    try:
        email = "gaurav@gmail.com"
        password = "hindustan1"
        
        existing_user = await user_repo.get_user_by_email(email)
        if not existing_user:
            hashed_password = get_password_hash(password)
            user_data = {
                "email": email,
                "hashed_password": hashed_password
            }
            user_id = await user_repo.create_user(user_data)
            print(f"✅ Created first user: {email}")
            print(f"🔐 Login credentials - Email: {email}, Password: {password}")
        else:
            print(f"✅ First user already exists: {email}")
    except Exception as e:
        print(f"⚠️  Could not create first user: {e}")
    
    # Report startup status
    if startup_errors:
        print("❌ Critical services failed to initialize:")
        for error in startup_errors:
            print(f"   - {error}")
    
    if startup_warnings:
        print("⚠️  Some services are using fallback mode:")
        for warning in startup_warnings:
            print(f"   - {warning}")
    
    if not startup_errors and not startup_warnings:
        print("✅ All services initialized successfully")
    elif not startup_errors:
        print("⚠️  Application running with some services in fallback mode")
        if not mongodb_connected:
            print("📝 MongoDB: Using local storage")
        if not pinecone_available:
            print("📝 Pinecone: Using local vector storage")
    else:
        print("📝 Application will continue with limited functionality")
    
    yield
    
    # Shutdown
    try:
        # Close MongoDB connection
        await close_mongo_connection()
        print("✅ Services shut down successfully")
    except Exception as e:
        print(f"❌ Error shutting down services: {e}")

app = FastAPI(
    title="Multi-Device RAG System API",
    description="API for managing device-isolated RAG knowledge bases",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(devices.router, prefix="/api/devices", tags=["devices"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(templates.router, prefix="/api/templates", tags=["templates"])
app.include_router(enhanced_csv_router.router, tags=["enhanced-csv"])
app.include_router(robust_csv_router.router, tags=["robust-csv"])
app.include_router(file_history.router, prefix="/api/file-history", tags=["file-history"])
app.include_router(favorites.router)  # Include favorites router (router in favorites.py already defines its own prefix)

@app.get("/")
async def root():
    return {"message": "Multi-Device RAG System API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "services": "operational"}

@app.get("/api/device-vectors")
async def get_device_vectors():
    json_path = os.path.join(os.path.dirname(__file__), "device_DB_vectors.json")
    return FileResponse(json_path, media_type="application/json")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
