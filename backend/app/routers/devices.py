from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import json
import os
from pathlib import Path

from app.models import Device
from app.services.pinecone_service import pinecone_service

router = APIRouter()

def load_devices() -> List[Device]:
    """Load devices from devices.json file"""
    try:
        devices_file = Path(__file__).parent.parent.parent / "devices.json"
        with open(devices_file, 'r') as f:
            devices_data = json.load(f)
        
        return [Device(**device) for device in devices_data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load devices: {e}")

@router.get("/", response_model=List[Device])
async def get_all_devices():
    """Get all available devices"""
    return load_devices()

@router.get("/{device_id}", response_model=Device)
async def get_device(device_id: str):
    """Get specific device by ID"""
    devices = load_devices()
    
    for device in devices:
        if device.id == device_id:
            return device
    
    raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

@router.get("/{device_id}/stats")
async def get_device_stats(device_id: str):
    """Get statistics for a specific device"""
    # Verify device exists
    device = await get_device(device_id)
    
    try:
        # Get Pinecone stats
        pinecone_stats = await pinecone_service.get_index_stats(device_id)
        
        # TODO: Add MongoDB stats (document count, etc.)
        # For now, return basic stats
        return {
            "device_id": device_id,
            "device_name": device.name,
            "vector_count": pinecone_stats.get("total_vectors", 0),
            "namespace": pinecone_stats.get("namespace", f"device_{device_id}"),
            "status": "active" if device.is_active else "inactive"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get device stats: {e}")

@router.post("/{device_id}/activate")
async def activate_device(device_id: str):
    """Activate a device"""
    # Verify device exists
    device = await get_device(device_id)
    
    # TODO: Implement device activation logic
    # This would typically update the devices.json file or database
    
    return {"message": f"Device {device_id} activated", "device_id": device_id}

@router.post("/{device_id}/deactivate")
async def deactivate_device(device_id: str):
    """Deactivate a device"""
    # Verify device exists
    device = await get_device(device_id)
    
    # TODO: Implement device deactivation logic
    # This would typically update the devices.json file or database
    
    return {"message": f"Device {device_id} deactivated", "device_id": device_id}
