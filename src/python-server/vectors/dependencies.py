# resolve path to parent
from pathlib import Path
import sys
# Add the current directory to Python path
current_dir = Path(__file__).parent.absolute()
sys.path.append(str(current_dir))
# Now import using relative path from vectors
from embeddings.chunk_embedder import ChunkEmbedder
from store.embedding_storage import EmbeddingStorage
from search.faiss_chunk_retriever import FAISSChunkRetriever

# Global instances
embedder_instance = None
storage_instance = None
retriever_instance = None

def get_embedder():
    global embedder_instance
    if not embedder_instance:
        embedder_instance = ChunkEmbedder(model_name="msmarco-MiniLM-L6-v3")
    return embedder_instance

def get_storage():
    global storage_instance
    if not storage_instance:
        storage_instance = EmbeddingStorage("./excel_embeddings.db")
    return storage_instance

def get_retriever():
    global retriever_instance
    if not retriever_instance:
        retriever_instance = FAISSChunkRetriever(get_storage(), get_embedder())
    return retriever_instance