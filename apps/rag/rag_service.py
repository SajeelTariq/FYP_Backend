"""
RAG Service: Handles document ingestion, chunking, embedding, and retrieval.
"""
import json
import os
import time
from pathlib import Path
from typing import List, Dict, Tuple
import numpy as np

from sentence_transformers import SentenceTransformer
from django.conf import settings
from django.db import transaction

from .rag_models import DocumentChunk, RAGQuery


class RAGService:
    """Service for RAG operations: ingestion, retrieval, and generation."""
    
    def __init__(self):
        """Initialize embedding model."""
        # Using a lightweight but effective model
        self.embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        self.chunk_size = 500  # characters
        self.chunk_overlap = 50  # characters
        
    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks for better context preservation.
        
        Args:
            text: Input text to chunk
            
        Returns:
            List of text chunks
        """
        chunks = []
        text_length = len(text)
        start = 0
        
        while start < text_length:
            end = min(start + self.chunk_size, text_length)
            chunk = text[start:end].strip()
            
            if chunk and len(chunk) > 20:  # Only add meaningful chunks
                chunks.append(chunk)
            
            # Move forward with overlap
            start += self.chunk_size - self.chunk_overlap
            
            if start >= text_length:
                break
        
        return chunks
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding vector for text.
        
        Args:
            text: Input text
            
        Returns:
            384-dimensional embedding vector
        """
        embedding = self.embedding_model.encode(text, convert_to_numpy=True)
        return embedding
    
    def ingest_json_file(self, filepath: Path, competitor_name: str) -> int:
        """
        Ingest a single JSON file into the database.
        
        Args:
            filepath: Path to JSON file
            competitor_name: Name of competitor (honda, suzuki, kia)
            
        Returns:
            Number of chunks created
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract data
            filename = data.get('filename', filepath.name)
            url = data.get('url', '')
            title = data.get('title', '')
            content = data.get('content', '')
            
            if not content or len(content.strip()) < 50:
                print(f"⚠️  Skipping {filename} - content too short")
                return 0
            
            # Chunk the content
            chunks = self.chunk_text(content)
            
            # Check if already exists
            existing_count = DocumentChunk.objects.filter(
                source_file=filename,
                competitor_name=competitor_name
            ).count()
            
            if existing_count > 0:
                print(f"⚠️  Skipping {filename} - already ingested ({existing_count} chunks)")
                return 0
            
            # Create chunks with embeddings
            created_chunks = []
            for idx, chunk_text in enumerate(chunks):
                embedding = self.generate_embedding(chunk_text)
                
                chunk = DocumentChunk(
                    source_file=filename,
                    competitor_name=competitor_name,
                    url=url,
                    title=title,
                    chunk_text=chunk_text,
                    chunk_index=idx,
                    chunk_size=len(chunk_text),
                    embedding=embedding.tolist()
                )
                created_chunks.append(chunk)
            
            # Bulk create
            DocumentChunk.objects.bulk_create(created_chunks)
            
            print(f"✅ Ingested {filename}: {len(created_chunks)} chunks")
            return len(created_chunks)
            
        except Exception as e:
            print(f"❌ Error ingesting {filepath}: {str(e)}")
            return 0
    
    def ingest_all_data(self, data_dir: str = None) -> Dict[str, int]:
        """
        Ingest all JSON files from data directory.
        
        Args:
            data_dir: Path to data directory (defaults to settings.BASE_DIR / 'data')
            
        Returns:
            Dictionary with competitor names and chunk counts
        """
        if data_dir is None:
            data_dir = Path(settings.BASE_DIR) / 'data'
        else:
            data_dir = Path(data_dir)
        
        results = {}
        
        # Map folder names to competitor names
        competitor_folders = {
            'honda': 'Honda',
            'suzukipakistan': 'Suzuki',
            'kia-luckymotorcorp': 'Kia'
        }
        
        for folder_name, competitor_name in competitor_folders.items():
            folder_path = data_dir / folder_name
            
            if not folder_path.exists():
                print(f"⚠️  Folder not found: {folder_path}")
                continue
            
            print(f"\n📁 Processing {competitor_name} from {folder_name}...")
            
            json_files = list(folder_path.glob('*.json'))
            total_chunks = 0
            
            for json_file in json_files:
                chunks_created = self.ingest_json_file(json_file, competitor_name)
                total_chunks += chunks_created
            
            results[competitor_name] = total_chunks
            print(f"✅ {competitor_name}: {total_chunks} total chunks created")
        
        return results
    
    def semantic_search(self, query: str, top_k: int = 5, competitor_filter: str = None) -> List[Dict]:
        """
        Perform semantic search on document chunks using cosine similarity.
        
        Args:
            query: Search query
            top_k: Number of results to return
            competitor_filter: Optional competitor name to filter by
            
        Returns:
            List of matching chunks with metadata and scores
        """
        start_time = time.time()
        
        # Generate query embedding
        query_embedding = self.generate_embedding(query)
        
        # Build queryset
        queryset = DocumentChunk.objects.all()
        if competitor_filter:
            queryset = queryset.filter(competitor_name__icontains=competitor_filter)
        
        # Get all chunks and compute similarity in memory
        # (For large datasets, consider using FAISS or Milvus)
        all_chunks = list(queryset)
        
        if not all_chunks:
            return [], time.time() - start_time
        
        # Compute cosine similarities
        results_with_scores = []
        for chunk in all_chunks:
            chunk_embedding = np.array(chunk.embedding)
            similarity = self._cosine_similarity(query_embedding, chunk_embedding)
            results_with_scores.append((chunk, similarity))
        
        # Sort by similarity (descending) and take top_k
        results_with_scores.sort(key=lambda x: x[1], reverse=True)
        top_results = results_with_scores[:top_k]
        
        # Format results
        formatted_results = []
        for chunk, similarity_score in top_results:
            formatted_results.append({
                'id': chunk.id,
                'competitor': chunk.competitor_name,
                'title': chunk.title,
                'url': chunk.url,
                'text': chunk.chunk_text,
                'chunk_index': chunk.chunk_index,
                'similarity': float(similarity_score),
                'source_file': chunk.source_file
            })
        
        retrieval_time = time.time() - start_time
        
        return formatted_results, retrieval_time
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        return dot_product / (norm1 * norm2) if norm1 and norm2 else 0.0
    
    def generate_answer(self, query: str, context_chunks: List[Dict]) -> Tuple[str, float]:
        """
        Generate answer using OpenRouter GPT-4o-mini with retrieved context.
        
        Args:
            query: User query
            context_chunks: Retrieved relevant chunks
            
        Returns:
            Tuple of (generated_answer, generation_time)
        """
        import requests
        
        start_time = time.time()
        
        # Build context from chunks
        context = "\n\n".join([
            f"[{chunk['competitor']} - {chunk['title']}]\n{chunk['text']}"
            for chunk in context_chunks
        ])
        
        # Create prompt
        system_prompt = """You are an expert automotive assistant with deep knowledge about Honda, Suzuki, and Kia vehicles in Pakistan. 

Your role is to provide accurate, detailed, and helpful information based on the provided context from official vehicle documentation and specifications.

Guidelines:
- Answer based ONLY on the provided context
- If the context doesn't contain the answer, say "I don't have enough information about that in my current knowledge base"
- Be specific and cite which brand/model you're referring to
- Compare brands/models when relevant
- Provide numerical specs when available (prices, engine specs, etc.)
- Be conversational but professional"""

        user_prompt = f"""Context from vehicle documentation:

{context}

---

User Question: {query}

Please provide a detailed answer based on the above context."""

        # Call OpenRouter API
        try:
            api_key = settings.OPENROUTER_API_KEY
            
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "openai/gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1000
                }
            )
            
            response.raise_for_status()
            answer = response.json()['choices'][0]['message']['content']
            
        except Exception as e:
            answer = f"Error generating answer: {str(e)}"
        
        generation_time = time.time() - start_time
        
        return answer, generation_time
    
    def query(self, query_text: str, top_k: int = 5, competitor_filter: str = None) -> Dict:
        """
        Complete RAG pipeline: retrieve + generate.
        
        Args:
            query_text: User query
            top_k: Number of chunks to retrieve
            competitor_filter: Optional competitor name filter
            
        Returns:
            Dictionary with answer and metadata
        """
        total_start = time.time()
        
        # Retrieve relevant chunks
        retrieved_chunks, retrieval_time = self.semantic_search(
            query_text, 
            top_k=top_k, 
            competitor_filter=competitor_filter
        )
        
        # Generate answer
        answer, generation_time = self.generate_answer(query_text, retrieved_chunks)
        
        total_time = time.time() - total_start
        
        # Log query
        RAGQuery.objects.create(
            query_text=query_text,
            retrieved_chunks=[
                {'id': chunk['id'], 'similarity': chunk['similarity'], 'competitor': chunk['competitor']}
                for chunk in retrieved_chunks
            ],
            generated_answer=answer,
            retrieval_time=retrieval_time,
            generation_time=generation_time,
            total_time=total_time,
            top_k=top_k,
            model_used="gpt-4o-mini"
        )
        
        return {
            'query': query_text,
            'answer': answer,
            'sources': retrieved_chunks,
            'metrics': {
                'retrieval_time': round(retrieval_time, 3),
                'generation_time': round(generation_time, 3),
                'total_time': round(total_time, 3),
                'chunks_retrieved': len(retrieved_chunks)
            }
        }
