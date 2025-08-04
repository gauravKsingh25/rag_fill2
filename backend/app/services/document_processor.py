import os
import uuid
import aiofiles
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
from docx import Document
import PyPDF2
from io import BytesIO
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
            logger.info(f"🚀 Starting to process document: {filename} for device: {device_id}")
            
            # Generate unique document ID
            document_id = str(uuid.uuid4())
            
            # Extract text from file
            text_content = await self._extract_text(file_content, filename)
            if not text_content:
                raise ValueError("Could not extract text from file")
            
            # Create chunks
            chunks = self._create_chunks(text_content)
            if not chunks:
                raise ValueError("No chunks were created from the document")
            
            logger.info(f"📦 Created {len(chunks)} chunks from document")
            
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
            
            logger.info(f"✅ Successfully processed document {filename} for device {device_id} - Created {len(chunks)} chunks")
            
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
            logger.info(f"📄 Extracting text from {filename} (type: {file_extension})")
            
            extracted_text = ""
            
            if file_extension == '.txt':
                extracted_text = file_content.decode('utf-8')
            
            elif file_extension == '.pdf':
                extracted_text = self._extract_text_from_pdf(file_content)
            
            elif file_extension == '.docx':
                extracted_text = self._extract_text_from_docx(file_content)
            
            elif file_extension == '.md':
                extracted_text = file_content.decode('utf-8')
            
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")
            
            # Clean up the extracted text
            cleaned_text = extracted_text.strip()
            if not cleaned_text:
                raise ValueError(f"No text content found in file {filename}")
            
            logger.info(f"✅ Extracted {len(cleaned_text)} characters from {filename}")
            return cleaned_text
                
        except Exception as e:
            logger.error(f"❌ Failed to extract text from {filename}: {e}")
            raise
    
    def _extract_text_from_pdf(self, file_content: bytes) -> str:
        """Extract text from PDF file"""
        try:
            pdf_file = BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            if len(pdf_reader.pages) == 0:
                raise ValueError("PDF file contains no pages")
            
            text_parts = []
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text.strip():
                        text_parts.append(page_text)
                    logger.debug(f"📄 Extracted text from PDF page {page_num + 1}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to extract text from PDF page {page_num + 1}: {e}")
                    continue
            
            if not text_parts:
                raise ValueError("No text could be extracted from PDF pages")
            
            full_text = "\n".join(text_parts)
            logger.info(f"✅ Extracted text from {len(pdf_reader.pages)} PDF pages")
            return full_text.strip()
            
        except Exception as e:
            logger.error(f"❌ Failed to extract text from PDF: {e}")
            raise
    
    def _extract_text_from_docx(self, file_content: bytes) -> str:
        """Extract text from DOCX file"""
        try:
            docx_file = BytesIO(file_content)
            doc = Document(docx_file)
            
            text_parts = []
            
            # Extract text from paragraphs
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text)
            
            # Extract text from tables
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            text_parts.append(cell.text)
            
            if not text_parts:
                raise ValueError("No text content found in DOCX file")
            
            full_text = "\n".join(text_parts)
            logger.info(f"✅ Extracted text from DOCX with {len(doc.paragraphs)} paragraphs and {len(doc.tables)} tables")
            return full_text.strip()
            
        except Exception as e:
            logger.error(f"❌ Failed to extract text from DOCX: {e}")
            raise
    
    def _create_chunks(self, text: str) -> List[Dict[str, Any]]:
        """Create overlapping chunks from text"""
        try:
            if not text or len(text.strip()) == 0:
                logger.warning("⚠️ Empty or whitespace-only text provided for chunking")
                return []
            
            chunks = []
            start = 0
            chunk_id = 0
            text_length = len(text)
            
            logger.info(f"📊 Creating chunks from text of length {text_length} characters")
            logger.info(f"🔧 Chunk size: {self.chunk_size}, overlap: {self.chunk_overlap}")
            
            while start < text_length:
                end = min(start + self.chunk_size, text_length)
                chunk_text = text[start:end]
                
                # Try to break at sentence boundary for better chunks
                if end < text_length:
                    last_period = chunk_text.rfind('.')
                    last_newline = chunk_text.rfind('\n')
                    last_space = chunk_text.rfind(' ')
                    
                    # Find the best break point
                    break_point = max(last_period, last_newline, last_space)
                    
                    # Only use break point if it's not too close to the start
                    if break_point > start + self.chunk_size // 2:
                        chunk_text = text[start:start + break_point + 1]
                        end = start + break_point + 1
                
                # Only add non-empty chunks
                chunk_content = chunk_text.strip()
                if chunk_content and len(chunk_content) > 10:  # Minimum 10 characters
                    chunks.append({
                        "chunk_id": chunk_id,
                        "content": chunk_content,
                        "start_index": start,
                        "end_index": end
                    })
                    logger.debug(f"📦 Created chunk {chunk_id}: {len(chunk_content)} chars")
                    chunk_id += 1
                elif chunk_content:
                    logger.debug(f"⏭️ Skipped short chunk ({len(chunk_content)} chars): {chunk_content[:50]}...")
                
                # Move to next chunk with overlap
                next_start = max(end - self.chunk_overlap, start + 1)
                
                # Prevent infinite loop
                if next_start <= start:
                    start += 1
                else:
                    start = next_start
                
                if start >= text_length:
                    break
            
            logger.info(f"✅ Created {len(chunks)} chunks from document")
            
            if len(chunks) == 0:
                logger.error(f"❌ ZERO CHUNKS CREATED! Text length: {text_length}")
                logger.error(f"❌ First 500 chars of text: {text[:500]}")
                logger.error(f"❌ Text is all whitespace: {text.isspace()}")
                logger.error(f"❌ Text stripped length: {len(text.strip())}")
            
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
            logger.info(f"🔗 Storing {len(chunks)} chunks in vector database for document {filename}")
            
            vectors = []
            
            for i, chunk in enumerate(chunks):
                try:
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
                    
                    if (i + 1) % 10 == 0:
                        logger.debug(f"📊 Processed {i + 1}/{len(chunks)} embeddings")
                        
                except Exception as e:
                    logger.error(f"❌ Failed to create embedding for chunk {i}: {e}")
                    raise
            
            # Store in Pinecone
            if vectors:
                await pinecone_service.upsert_vectors(vectors, device_id)
                logger.info(f"✅ Successfully stored {len(vectors)} vectors in Pinecone for device {device_id}")
            else:
                raise ValueError("No vectors were created for storage")
            
        except Exception as e:
            logger.error(f"❌ Failed to store chunks in Pinecone: {e}")
            raise
    
    async def delete_document(self, document_id: str, device_id: str) -> bool:
        """Delete document and all its chunks"""
        try:
            # Get document metadata to verify it exists
            document = await document_repo.get_document_by_id(document_id)
            if not document:
                logger.warning(f"⚠️ Document {document_id} not found in database")
                # Continue with cleanup attempt anyway
            
            # Method 1: Delete all vectors for this document using metadata filtering (more reliable)
            logger.info(f"🗑️ Deleting all vectors for document {document_id} from device {device_id}")
            deletion_success = await pinecone_service.delete_document_vectors(document_id, device_id)
            
            # Method 2: Fallback - try to delete by chunk IDs if metadata filtering failed
            if not deletion_success and document and "chunk_count" in document:
                logger.info(f"🔄 Fallback: Attempting deletion by chunk IDs for document {document_id}")
                chunk_ids = [f"{document_id}_{i}" for i in range(document["chunk_count"])]
                deletion_success = await pinecone_service.delete_vectors(chunk_ids, device_id)
            
            # Delete from MongoDB
            await document_repo.delete_document(document_id)
            
            # Delete file from disk
            try:
                if document:
                    file_path = self.upload_dir / f"{document_id}_{document['filename']}"
                    if file_path.exists():
                        file_path.unlink()
                        logger.info(f"🗑️ Deleted file from disk: {file_path}")
            except Exception as e:
                logger.warning(f"⚠️ Could not delete file from disk: {e}")
            
            if deletion_success:
                logger.info(f"✅ Successfully deleted document {document_id} and all its chunks for device {device_id}")
            else:
                logger.warning(f"⚠️ Document {document_id} metadata deleted, but vector cleanup may have failed")
            
            return True  # Return True even if vector deletion failed, since metadata is cleaned up
            
        except Exception as e:
            logger.error(f"❌ Failed to delete document {document_id}: {e}")
            return False

# Global instance
document_processor = DocumentProcessor()
