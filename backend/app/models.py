from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class DeviceStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"

class Device(BaseModel):
    id: str = Field(..., description="Unique device identifier")
    name: str = Field(..., description="Human-readable device name")
    description: str = Field(..., description="Device description")
    namespace: str = Field(..., description="Pinecone namespace for device isolation")
    allowed_file_types: List[str] = Field(default=[".pdf", ".docx", ".txt"], description="Allowed file extensions")
    max_documents: int = Field(default=100, description="Maximum number of documents per device")
    embedding_model: str = Field(default="models/embedding-001", description="Embedding model to use")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)

class DocumentMetadata(BaseModel):
    filename: str
    file_size: int
    file_type: str
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)
    device_id: str
    document_id: str
    chunk_count: int = 0
    processed: bool = False

class ChatMessage(BaseModel):
    role: str = Field(..., description="Role of the message sender (user/assistant)")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ChatRequest(BaseModel):
    device_id: str = Field(..., description="Device ID for context isolation")
    message: str = Field(..., description="User message")
    conversation_history: List[ChatMessage] = Field(default=[], description="Previous conversation messages")

class ChatResponse(BaseModel):
    response: str = Field(..., description="AI assistant response")
    sources: List[Dict[str, Any]] = Field(default=[], description="Source documents used for response")
    device_id: str = Field(..., description="Device ID used for response")

class FactVerificationRequest(BaseModel):
    device_id: str = Field(..., description="Device ID for context isolation")
    claim: str = Field(..., description="Fact or claim to verify")

class FactVerificationResponse(BaseModel):
    device_id: str = Field(..., description="Device ID used")
    claim: str = Field(..., description="Original claim")
    verification_status: str = Field(..., description="SUPPORTED/CONTRADICTED/PARTIALLY_SUPPORTED/NO_EVIDENCE_FOUND")
    verification_result: str = Field(..., description="Detailed verification analysis")
    evidence_count: int = Field(..., description="Number of evidence pieces found")
    avg_confidence: float = Field(..., description="Average confidence score of evidence")
    evidence: List[Dict[str, Any]] = Field(default=[], description="Supporting evidence documents")

class TemplateRequest(BaseModel):
    device_id: str = Field(..., description="Device ID for context")
    template_filename: str = Field(..., description="Name of the template file")
    
class TemplateResponse(BaseModel):
    filled_template_url: str = Field(..., description="URL to download filled template")
    filled_fields: Dict[str, str] = Field(..., description="Fields that were filled")
    missing_fields: List[str] = Field(default=[], description="Fields that couldn't be filled")

class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    device_id: str
    status: str
    message: str

class VectorSearchResult(BaseModel):
    content: str
    metadata: Dict[str, Any]
    score: float

class EmbeddingRequest(BaseModel):
    text: str
    device_id: str

class EmbeddingResponse(BaseModel):
    embedding: List[float]
    device_id: str
