from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import List, Optional
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from app.routers import devices, documents, chat, templates
from app.database import connect_to_mongo, close_mongo_connection
from app.services.pinecone_service import pinecone_service

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
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(devices.router, prefix="/api/devices", tags=["devices"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(templates.router, prefix="/api/templates", tags=["templates"])

@app.get("/")
async def root():
    return {"message": "Multi-Device RAG System API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "services": "operational"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
