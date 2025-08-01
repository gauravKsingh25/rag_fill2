import os
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('PINECONE_API_KEY')
index_name = os.getenv('PINECONE_INDEX_NAME', 'rag-system-index')

print(f'Checking Pinecone setup...')
print(f'API Key: {api_key[:10]}...{api_key[-4:] if api_key else None}')
print(f'Index Name: {index_name}')

try:
    # Initialize Pinecone with v3+ API
    pc = Pinecone(api_key=api_key)
    
    # List existing indexes
    existing_indexes = [index.name for index in pc.list_indexes()]
    print(f'Existing indexes: {existing_indexes}')
    
    if index_name not in existing_indexes:
        print(f'Index {index_name} does not exist. Creating serverless index...')
        # Create serverless index with 1024 dimensions (for llama-text-embed-v2)
        pc.create_index(
            name=index_name,
            dimension=1024,
            metric='cosine',
            spec=ServerlessSpec(
                cloud='aws',
                region='us-east-1'
            )
        )
        print(f'✅ Index {index_name} created successfully!')
    else:
        print(f'✅ Index {index_name} already exists!')
        
    # Test connection to the index
    try:
        index = pc.Index(index_name)
        stats = index.describe_index_stats()
        print(f'Index stats: {stats}')
    except Exception as index_error:
        print(f'⚠️  Could not connect to index: {index_error}')
        
except Exception as e:
    print(f'❌ Error: {e}')