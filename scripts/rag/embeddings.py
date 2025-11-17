"""
RAG and embedding generation utilities.

Place your RAG-related scripts here.
Example functions:
- generate_embeddings(text)
- chunk_document(document, chunk_size)
- retrieve_similar_documents(query_embedding)
"""

from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)

# Initialize embedding model (lazy loading)
_embedding_model = None


def get_embedding_model(model_name='all-MiniLM-L6-v2'):
    """
    Get or initialize the embedding model.
    
    Args:
        model_name: Name of the sentence transformer model
    
    Returns:
        SentenceTransformer model
    """
    global _embedding_model
    
    if _embedding_model is None:
        try:
            _embedding_model = SentenceTransformer(model_name)
            logger.info(f"Loaded embedding model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {str(e)}")
            raise
    
    return _embedding_model


def generate_embedding(text, model_name='all-MiniLM-L6-v2'):
    """
    Generate embedding vector for text.
    
    Args:
        text: Text to embed
        model_name: Name of the embedding model
    
    Returns:
        Embedding vector as list
    """
    try:
        model = get_embedding_model(model_name)
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        return None


def chunk_text(text, chunk_size=500, overlap=50):
    """
    Split text into chunks for embedding.
    
    Args:
        text: Text to chunk
        chunk_size: Maximum characters per chunk
        overlap: Number of overlapping characters between chunks
    
    Returns:
        List of text chunks
    """
    if not text:
        return []
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    
    return chunks


# Add your existing RAG functions here
