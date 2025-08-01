# Multi-Device RAG System

A modular and scalable RAG (Retrieval-Augmented Generation) system built with Next.js frontend, FastAPI backend, Pinecone vector database, and MongoDB for metadata management. The system supports multiple devices, each with its own isolated knowledge base and interaction pipeline.

## 🏗️ Architecture

- **Frontend**: Next.js with TypeScript, Tailwind CSS, and App Router
- **Backend**: FastAPI with Python for the RAG pipeline
- **Vector Database**: Pinecone for document embeddings with device isolation
- **Metadata Storage**: MongoDB for document metadata and conversation history
- **AI Model**: Google Gemini Flash 1.5 for embeddings and text generation

## 🚀 Features

### Device Configuration
- Centralized device management via `devices.json`
- Strict data isolation across devices using Pinecone namespaces
- Support for devices: DA, DB, DC, DD, DE

### Document Processing
- Upload documents (PDF, DOCX, TXT, MD) per device
- Automatic text extraction and chunking
- Embedding generation using Gemini Flash 1.5
- Vector storage in Pinecone with device-specific metadata

### RAG Chat Interface
- Device-specific conversational chat
- Context-aware responses with source attribution
- Conversation history storage
- Real-time streaming responses

### Template Processing
- Upload Word templates with placeholders
- Automatic field extraction and analysis
- Smart template filling using device knowledge
- Download filled templates

## 🛠️ Setup Instructions

### Prerequisites
- Node.js 18+ 
- Python 3.9+
- Pinecone account and API key
- MongoDB instance (local or cloud)
- Google AI API key for Gemini

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment:
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file from `.env.example`:
```bash
cp .env.example .env
```

5. Configure environment variables in `.env`:
```env
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_ENVIRONMENT=your_pinecone_environment
PINECONE_INDEX_NAME=rag-system-index
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=rag_system
GOOGLE_API_KEY=your_google_api_key_here
SECRET_KEY=your_secret_key_here
FRONTEND_URL=http://localhost:3000
```

6. Start the backend server:
```bash
python main.py
```

The backend API will be available at `http://localhost:8000`

### Frontend Setup

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

3. Open [http://localhost:3000](http://localhost:3000) with your browser.

## 📖 Usage

### 1. Select a Device
Choose a device (DA, DB, DC, DD, DE) from the dropdown in the header.

### 2. Upload Documents
- Go to the "Document Upload" tab
- Upload PDF, DOCX, TXT, or MD files
- Documents are automatically processed and embedded

### 3. Chat Interface
- Use the "Chat Interface" tab
- Ask questions about uploaded documents
- Get context-aware responses with source attribution

### 4. Template Processing
- Go to "Template Processor" tab
- Analyze templates to see fillable fields
- Upload templates for automatic filling
- Download completed templates

## 🔧 API Endpoints

### Devices
- `GET /api/devices/` - List all devices
- `GET /api/devices/{device_id}` - Get device details
- `GET /api/devices/{device_id}/stats` - Get device statistics

### Documents
- `POST /api/documents/upload` - Upload document
- `GET /api/documents/device/{device_id}` - List device documents
- `DELETE /api/documents/{document_id}` - Delete document

### Chat
- `POST /api/chat/` - Send chat message
- `POST /api/chat/search` - Search device knowledge base

### Templates
- `POST /api/templates/analyze` - Analyze template fields
- `POST /api/templates/upload-and-fill` - Process template
- `GET /api/templates/download/{filename}` - Download filled template

## 🏃‍♂️ Development

### Running in Development Mode

1. Start the backend:
```bash
cd backend
python main.py
```

2. Start the frontend:
```bash
npm run dev
```

### Project Structure
```
/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── routers/        # API endpoints
│   │   ├── services/       # Business logic
│   │   ├── models.py       # Pydantic models
│   │   └── database.py     # MongoDB connection
│   ├── devices.json        # Device configuration
│   ├── main.py            # FastAPI app
│   └── requirements.txt   # Python dependencies
├── src/
│   ├── app/               # Next.js app directory
│   └── components/        # React components
├── .github/
│   └── copilot-instructions.md
└── README.md
```

## 🔐 Security Features

- Device isolation ensures data separation
- Input validation for file uploads
- Environment variable configuration
- CORS protection
- File type and size validation

## 📝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
