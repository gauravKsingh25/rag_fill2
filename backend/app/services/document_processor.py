import os
import uuid
import aiofiles
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
from docx import Document
import PyPDF2
from io import BytesIO

from app.services.gemini_service import gemini_service
from app.services.pinecone_service import pinecone_service
from app.database import document_repo

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self):
        self.upload_dir = Path(os.getenv("UPLOAD_DIR", "./uploads"))
        self.upload_dir.mkdir(exist_ok=True)
        self.chunk_size = 1000  # Characters per chunk
        self.chunk_overlap = 200  # Overlap between chunks
    
    async def process_uploaded_file(
        self, 
        file_content: bytes, 
        filename: str, 
        device_id: str
    ) -> Dict[str, Any]:
        """Process uploaded file and store in vector database"""
        try:
            # Generate unique document ID
            document_id = str(uuid.uuid4())
            
            # Extract text from file
            text_content = await self._extract_text(file_content, filename)
            if not text_content:
                raise ValueError("Could not extract text from file")
            
            # Create chunks
            chunks = self._create_chunks(text_content)
            
            # Generate embeddings and store in Pinecone
            await self._store_chunks_in_pinecone(chunks, document_id, device_id, filename)
            
            # Store metadata in MongoDB
            document_metadata = {
                "document_id": document_id,
                "filename": filename,
                "file_size": len(file_content),
                "file_type": Path(filename).suffix.lower(),
                "device_id": device_id,
                "chunk_count": len(chunks),
                "processed": True
            }
            
            await document_repo.create_document(document_metadata)
            
            # Save file to disk (optional, for backup)
            file_path = self.upload_dir / f"{document_id}_{filename}"
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(file_content)
            
            logger.info(f"✅ Processed document {filename} for device {device_id}")
            
            return {
                "document_id": document_id,
                "filename": filename,
                "device_id": device_id,
                "chunks_created": len(chunks),
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to process document {filename}: {e}")
            raise
    
    async def _extract_text(self, file_content: bytes, filename: str) -> str:
        """Extract text from different file types"""
        try:
            file_extension = Path(filename).suffix.lower()
            
            if file_extension == '.txt':
                return file_content.decode('utf-8')
            
            elif file_extension == '.pdf':
                return self._extract_text_from_pdf(file_content)
            
            elif file_extension == '.docx':
                return self._extract_text_from_docx(file_content)
            
            elif file_extension == '.md':
                return file_content.decode('utf-8')
            
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")
                
        except Exception as e:
            logger.error(f"❌ Failed to extract text from {filename}: {e}")
            raise
    
    def _extract_text_from_pdf(self, file_content: bytes) -> str:
        """Extract text from PDF file"""
        try:
            pdf_file = BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"❌ Failed to extract text from PDF: {e}")
            raise
    
    def _extract_text_from_docx(self, file_content: bytes) -> str:
        """Extract text from DOCX file"""
        try:
            docx_file = BytesIO(file_content)
            doc = Document(docx_file)
            
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"❌ Failed to extract text from DOCX: {e}")
            raise
    
    def _create_chunks(self, text: str) -> List[Dict[str, Any]]:
        """Create overlapping chunks from text"""
        try:
            chunks = []
            start = 0
            chunk_id = 0
            
            while start < len(text):
                end = start + self.chunk_size
                chunk_text = text[start:end]
                
                # Try to break at sentence boundary
                if end < len(text):
                    last_period = chunk_text.rfind('.')
                    last_newline = chunk_text.rfind('\n')
                    break_point = max(last_period, last_newline)
                    
                    if break_point > start + self.chunk_size // 2:
                        chunk_text = text[start:start + break_point + 1]
                        end = start + break_point + 1
                
                chunks.append({
                    "chunk_id": chunk_id,
                    "content": chunk_text.strip(),
                    "start_index": start,
                    "end_index": end
                })
                
                chunk_id += 1
                start = end - self.chunk_overlap
            
            return chunks
            
        except Exception as e:
            logger.error(f"❌ Failed to create chunks: {e}")
            raise
    
    async def _store_chunks_in_pinecone(
        self, 
        chunks: List[Dict[str, Any]], 
        document_id: str, 
        device_id: str, 
        filename: str
    ):
        """Generate embeddings and store chunks in Pinecone"""
        try:
            vectors = []
            
            for chunk in chunks:
                # Generate embedding for chunk
                embedding = await gemini_service.get_embedding(chunk["content"])
                
                # Create vector with metadata
                vector = {
                    "id": f"{document_id}_{chunk['chunk_id']}",
                    "values": embedding,
                    "metadata": {
                        "document_id": document_id,
                        "chunk_id": chunk["chunk_id"],
                        "content": chunk["content"][:500],  # Truncate for metadata storage
                        "filename": filename,
                        "device_id": device_id,
                        "start_index": chunk["start_index"],
                        "end_index": chunk["end_index"]
                    }
                }
                vectors.append(vector)
            
            # Store in Pinecone
            await pinecone_service.upsert_vectors(vectors, device_id)
            
        except Exception as e:
            logger.error(f"❌ Failed to store chunks in Pinecone: {e}")
            raise
    
    async def delete_document(self, document_id: str, device_id: str) -> bool:
        """Delete document and all its chunks"""
        try:
            # Get document metadata to find all chunk IDs
            document = await document_repo.get_document_by_id(document_id)
            if not document:
                return False
            
            # Generate all chunk IDs for this document
            chunk_ids = [f"{document_id}_{i}" for i in range(document["chunk_count"])]
            
            # Delete from Pinecone
            await pinecone_service.delete_vectors(chunk_ids, device_id)
            
            # Delete from MongoDB
            await document_repo.delete_document(document_id)
            
            # Delete file from disk
            try:
                file_path = self.upload_dir / f"{document_id}_{document['filename']}"
                if file_path.exists():
                    file_path.unlink()
            except Exception as e:
                logger.warning(f"⚠️ Could not delete file from disk: {e}")
            
            logger.info(f"✅ Deleted document {document_id} for device {device_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete document {document_id}: {e}")
            return False

# Global instance
document_processor = DocumentProcessor()
