"""
RAG Service with ChromaDB: Hybrid retrieval using dense vectors + BM25
"""
import json
import os
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import numpy as np
import requests

from sentence_transformers import SentenceTransformer
from django.conf import settings
import chromadb
from chromadb.config import Settings as ChromaSettings
from rank_bm25 import BM25Okapi
from difflib import SequenceMatcher


class RAGServiceChroma:
    """Service for RAG operations with ChromaDB and hybrid retrieval."""
    
    def __init__(self):
        """Initialize ChromaDB client and embedding model."""
        # Initialize embedding model
        self.embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        self.chunk_size = 1500  # characters
        self.chunk_overlap = 150  # characters
        
        # Initialize ChromaDB persistent client
        chroma_db_path = os.path.join(settings.BASE_DIR, 'chroma_db')
        self.client = chromadb.PersistentClient(
            path=chroma_db_path,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="competitor_documents",
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )
        
        # BM25 index (will be loaded when needed)
        self._bm25_index = None
        self._bm25_documents = []
        self._bm25_metadata = []
        
    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of text chunks
        """
        if not text or len(text) < self.chunk_size:
            return [text] if text else []
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            
            # Only add non-empty chunks
            if chunk.strip():
                chunks.append(chunk.strip())
            
            start += (self.chunk_size - self.chunk_overlap)
        
        return chunks
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text.
        
        Args:
            text: Input text
            
        Returns:
            384-dimensional embedding vector
        """
        embedding = self.embedding_model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def ingest_json_file(self, filepath: str, competitor_name: str) -> int:
        """
        Ingest a single JSON file into ChromaDB (legacy method, no deduplication).
        
        Args:
            filepath: Path to JSON file
            competitor_name: Name of competitor (honda, suzuki, kia)
            
        Returns:
            Number of chunks created
        """
        result = self._ingest_json_file_deduplicated(filepath, competitor_name, '', [])
        return result['added']
    
    def _ingest_json_file_deduplicated(
        self, 
        filepath: str, 
        competitor_name: str,
        base_url: str,
        existing_chunks: List[str]
    ) -> Dict[str, int]:
        """
        Ingest a single JSON file with deduplication.
        
        Args:
            filepath: Path to JSON file
            competitor_name: Name of competitor
            base_url: Normalized base URL for grouping
            existing_chunks: List of existing chunk texts for this base URL
            
        Returns:
            Dict with 'added' and 'duplicates' counts
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract content
            if isinstance(data, dict):
                # Handle different JSON structures
                if 'markdown' in data:
                    content = data['markdown']
                elif 'content' in data:
                    content = data['content']
                elif 'text' in data:
                    content = data['text']
                else:
                    # Try to concatenate all string values
                    content = ' '.join(str(v) for v in data.values() if isinstance(v, str))
                
                url = data.get('url', '') or data.get('sourceURL', '') or os.path.basename(filepath)
                title = data.get('title', '') or data.get('ogTitle', '') or url
            elif isinstance(data, list):
                # If it's a list, concatenate all items
                content = ' '.join(str(item) for item in data)
                url = os.path.basename(filepath)
                title = url
            else:
                content = str(data)
                url = os.path.basename(filepath)
                title = url
            
            if not content or len(content.strip()) < 50:
                return {'added': 0, 'duplicates': 0}
            
            # Chunk the content
            chunks = self.chunk_text(content)
            
            # Prepare data for ChromaDB
            chunk_ids = []
            embeddings = []
            documents = []
            metadatas = []
            duplicates = 0
            
            for idx, chunk_text in enumerate(chunks):
                # Check for duplicates
                if self._is_duplicate_chunk(chunk_text, existing_chunks, threshold=0.85):
                    duplicates += 1
                    continue
                
                # Add to existing chunks for future comparison
                existing_chunks.append(chunk_text)
                
                # Generate unique ID
                chunk_id = f"{competitor_name}_{os.path.basename(filepath)}_{idx}_{int(time.time() * 1000)}"
                
                # Generate embedding
                embedding = self.generate_embedding(chunk_text)
                
                # Metadata
                metadata = {
                    "competitor_name": competitor_name,
                    "source_file": os.path.basename(filepath),
                    "url": url,
                    "title": title,
                    "chunk_index": idx,
                    "chunk_size": len(chunk_text),
                    "base_url": base_url
                }
                
                chunk_ids.append(chunk_id)
                embeddings.append(embedding)
                documents.append(chunk_text)
                metadatas.append(metadata)
            
            # Add to ChromaDB collection
            if chunk_ids:
                self.collection.add(
                    ids=chunk_ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas
                )
            
            return {'added': len(chunk_ids), 'duplicates': duplicates}
            
        except Exception as e:
            print(f"Error ingesting {filepath}: {str(e)}")
            return {'added': 0, 'duplicates': 0}
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL to base form for deduplication."""
        # Remove common suffixes and parameters
        url = url.lower()
        # Remove .php, _feed, query params
        url = url.split('?')[0].split('#')[0]
        url = url.replace('.php', '').replace('_feed', '').replace('-php', '')
        return url.strip('/')
    
    def _is_duplicate_chunk(self, chunk_text: str, existing_chunks: List[str], threshold: float = 0.85) -> bool:
        """Check if chunk is duplicate of existing chunks."""
        for existing in existing_chunks:
            # Use SequenceMatcher to calculate similarity
            similarity = SequenceMatcher(None, chunk_text.lower(), existing.lower()).ratio()
            if similarity >= threshold:
                return True
        return False
    
    def ingest_all_data(self, data_dir: Optional[str] = None) -> Dict[str, int]:
        """
        Ingest all JSON files from data directory with deduplication.
        
        Args:
            data_dir: Path to data directory (default: BASE_DIR/data)
            
        Returns:
            Dictionary with competitor names and chunk counts
        """
        if data_dir is None:
            data_dir = os.path.join(settings.BASE_DIR, 'data')
        
        # Clear existing collection
        try:
            self.client.delete_collection("competitor_documents")
        except:
            pass  # Collection might not exist
        
        self.collection = self.client.get_or_create_collection(
            name="competitor_documents",
            metadata={"hnsw:space": "cosine"}
        )
        
        stats = {}
        
        # Process each competitor folder
        competitor_folders = {
            'honda': 'honda',
            'suzuki': 'suzukipakistan',
            'kia': 'kia-luckymotorcorp'
        }
        
        # Track chunks by base URL for deduplication
        url_chunks_map = {}  # base_url -> list of chunk texts
        
        for competitor_name, folder_name in competitor_folders.items():
            folder_path = os.path.join(data_dir, folder_name)
            
            if not os.path.exists(folder_path):
                print(f"Folder not found: {folder_path}")
                continue
            
            json_files = list(Path(folder_path).glob('*.json'))
            print(f"\nProcessing {competitor_name} ({len(json_files)} files)...")
            
            # First pass: Group files by base URL
            url_files_map = {}
            for json_file in json_files:
                base_url = self._normalize_url(str(json_file.stem))
                if base_url not in url_files_map:
                    url_files_map[base_url] = []
                url_files_map[base_url].append(json_file)
            
            total_chunks = 0
            total_duplicates = 0
            
            # Second pass: Process files with deduplication
            for base_url, files in url_files_map.items():
                url_chunks_map[base_url] = []
                
                for json_file in files:
                    chunks = self._ingest_json_file_deduplicated(
                        str(json_file), 
                        competitor_name, 
                        base_url,
                        url_chunks_map[base_url]
                    )
                    total_chunks += chunks['added']
                    total_duplicates += chunks['duplicates']
            
            stats[competitor_name] = total_chunks
            print(f"✓ {competitor_name}: {total_chunks} chunks (removed {total_duplicates} duplicates)")
        
        # Rebuild BM25 index after ingestion
        self._build_bm25_index()
        
        return stats
    
    def _build_bm25_index(self):
        """Build BM25 index from all documents in ChromaDB."""
        print("\nBuilding BM25 index...")
        
        # Get all documents from ChromaDB
        results = self.collection.get(include=['documents', 'metadatas'])
        
        if not results or not results['documents']:
            print("No documents found for BM25 indexing")
            return
        
        # Store documents and metadata
        self._bm25_documents = results['documents']
        self._bm25_metadata = results['metadatas']
        
        # Tokenize documents for BM25 (simple whitespace tokenization)
        tokenized_docs = [doc.lower().split() for doc in self._bm25_documents]
        
        # Create BM25 index
        self._bm25_index = BM25Okapi(tokenized_docs)
        
        print(f"✓ BM25 index built with {len(self._bm25_documents)} documents")
    
    def _ensure_bm25_index(self):
        """Ensure BM25 index is loaded."""
        if self._bm25_index is None:
            self._build_bm25_index()
    
    def semantic_search(
        self,
        query: str,
        top_k: int = 5,
        competitor_filter: Optional[str] = None
    ) -> List[Dict]:
        """
        Perform hybrid search (dense + sparse retrieval).
        
        Args:
            query: Search query
            top_k: Number of results to return
            competitor_filter: Filter by competitor name (honda, suzuki, kia)
            
        Returns:
            List of search results with metadata
        """
        start_time = time.time()
        
        # Ensure BM25 index is loaded
        self._ensure_bm25_index()
        
        # 1. Dense vector search (semantic similarity)
        query_embedding = self.generate_embedding(query)
        
        where_filter = None
        if competitor_filter and competitor_filter.lower() != 'all':
            where_filter = {"competitor_name": competitor_filter.lower()}
        
        dense_results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k * 2,  # Get more results for fusion
            where=where_filter,
            include=['documents', 'metadatas', 'distances']
        )
        
        # 2. Sparse BM25 search (keyword matching)
        query_tokens = query.lower().split()
        
        # Get BM25 scores for all documents
        bm25_scores = self._bm25_index.get_scores(query_tokens)
        
        # Filter by competitor if needed
        filtered_indices = []
        if competitor_filter and competitor_filter.lower() != 'all':
            for idx, metadata in enumerate(self._bm25_metadata):
                if metadata.get('competitor_name', '').lower() == competitor_filter.lower():
                    filtered_indices.append(idx)
        else:
            filtered_indices = list(range(len(bm25_scores)))
        
        # Get top BM25 results
        filtered_scores = [(idx, bm25_scores[idx]) for idx in filtered_indices]
        filtered_scores.sort(key=lambda x: x[1], reverse=True)
        top_bm25_indices = [idx for idx, _ in filtered_scores[:top_k * 2]]
        
        # 3. Fusion: Combine dense and sparse results
        # Using reciprocal rank fusion (RRF)
        k = 60  # RRF constant
        fusion_scores = {}
        
        # Add dense results (semantic gets higher weight: 2.5x)
        if dense_results['ids'] and len(dense_results['ids'][0]) > 0:
            for rank, (doc_id, distance) in enumerate(zip(dense_results['ids'][0], dense_results['distances'][0])):
                # Convert distance to similarity (ChromaDB returns distances)
                similarity = 1 / (1 + distance)
                # Semantic search weighted 2.5x higher for better semantic understanding
                fusion_scores[doc_id] = fusion_scores.get(doc_id, 0) + (2.5 / (k + rank + 1))
        
        # Add BM25 results (keyword gets standard weight: 1.0x)
        all_ids = self.collection.get(include=['metadatas'])['ids']
        for rank, idx in enumerate(top_bm25_indices):
            if idx < len(all_ids):
                doc_id = all_ids[idx]
                # BM25 keyword matching weighted 1.0x
                fusion_scores[doc_id] = fusion_scores.get(doc_id, 0) + (1.0 / (k + rank + 1))
        
        # Sort by fusion score
        sorted_results = sorted(fusion_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        
        # Retrieve full documents for top results
        final_results = []
        if sorted_results:
            top_ids = [doc_id for doc_id, _ in sorted_results]
            retrieved = self.collection.get(
                ids=top_ids,
                include=['documents', 'metadatas']
            )
            
            for doc_id, fusion_score in sorted_results:
                idx = retrieved['ids'].index(doc_id)
                final_results.append({
                    'id': doc_id,
                    'text': retrieved['documents'][idx],
                    'metadata': retrieved['metadatas'][idx],
                    'fusion_score': fusion_score
                })
        
        retrieval_time = time.time() - start_time
        
        return {
            'results': final_results,
            'retrieval_time': retrieval_time,
            'query': query,
            'total_results': len(final_results)
        }
    
    def generate_answer(self, query: str, context_chunks: List[Dict]) -> str:
        """
        Generate answer using OpenRouter API (GPT-4o-mini).
        
        Args:
            query: User query
            context_chunks: Retrieved context chunks
            
        Returns:
            Generated answer
        """
        # Prepare context (show full chunks for better accuracy)
        context = "\n\n".join([
            f"[Document {i+1}]\n"
            f"Source: {chunk['metadata'].get('title', 'Unknown')}\n"
            f"URL: {chunk['metadata'].get('url', 'N/A')}\n"
            f"Content:\n{chunk['text']}"
            for i, chunk in enumerate(context_chunks[:5])  # Use top 5 chunks
        ])
        
        # Prepare prompt
        prompt = f"""You are a helpful assistant that answers questions based on the provided context documents.

Context:
{context}

Question: {query}

Instructions:
- Provide a comprehensive and accurate answer based ONLY on the context above
- If the context contains relevant information, synthesize it into a clear answer
- If the context lacks sufficient information to answer the question, clearly state that
- Cite which document(s) support your answer when possible

Answer:"""

        # Call OpenRouter API
        api_key = settings.OPENROUTER_API_KEY
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "openai/gpt-4o-mini",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            answer = result['choices'][0]['message']['content']
            return answer
            
        except Exception as e:
            return f"Error generating answer: {str(e)}"
    
    def query(
        self,
        query_text: str,
        top_k: int = 5,
        competitor_filter: Optional[str] = None
    ) -> Dict:
        """
        Complete RAG pipeline: retrieve + generate.
        
        Args:
            query_text: User query
            top_k: Number of chunks to retrieve
            competitor_filter: Filter by competitor
            
        Returns:
            Dictionary with answer and metadata
        """
        start_time = time.time()
        
        # Retrieval
        search_results = self.semantic_search(query_text, top_k, competitor_filter)
        retrieval_time = search_results['retrieval_time']
        
        # Generation
        gen_start = time.time()
        answer = self.generate_answer(query_text, search_results['results'])
        generation_time = time.time() - gen_start
        
        total_time = time.time() - start_time
        
        return {
            'query': query_text,
            'answer': answer,
            'retrieved_chunks': [
                {
                    'text': chunk['text'][:200] + '...',
                    'metadata': chunk['metadata'],
                    'score': chunk['fusion_score']
                }
                for chunk in search_results['results']
            ],
            'retrieval_time': retrieval_time,
            'generation_time': generation_time,
            'total_time': total_time,
            'top_k': top_k,
            'competitor_filter': competitor_filter or 'all'
        }
    
    def get_stats(self) -> Dict:
        """Get statistics about the RAG system."""
        # Get collection stats
        collection_count = self.collection.count()
        
        # Get competitor counts
        competitor_counts = {}
        for competitor in ['honda', 'suzuki', 'kia']:
            results = self.collection.get(
                where={"competitor_name": competitor},
                include=['metadatas']
            )
            competitor_counts[competitor] = len(results['ids']) if results['ids'] else 0
        
        return {
            'total_chunks': collection_count,
            'competitor_chunks': competitor_counts,
            'embedding_dimension': 384,
            'model': 'sentence-transformers/all-MiniLM-L6-v2',
            'retrieval_method': 'hybrid (dense + BM25)',
            'database': 'ChromaDB'
        }
    
    def get_competitors(self) -> List[Dict]:
        """Get list of competitors with chunk counts."""
        stats = self.get_stats()
        
        competitors = []
        for name, count in stats['competitor_chunks'].items():
            competitors.append({
                'name': name.capitalize(),
                'value': name,
                'chunk_count': count
            })
        
        return competitors

    def ingest_competitor_from_db(self, competitor) -> Dict[str, int]:
        """
        Ingest a single competitor's data from DB (CompetitorMetadata) into ChromaDB.
        Deletes existing chunks for this competitor first, then re-ingests.

        Args:
            competitor: Competitor model instance

        Returns:
            Dict with 'added' and 'deleted' counts
        """
        from apps.monitoring.models import CompetitorMetadata

        competitor_name = competitor.name.lower().replace(" ", "_")

        # Delete existing chunks for this competitor
        existing = self.collection.get(
            where={"competitor_name": competitor_name},
            include=["metadatas"],
        )
        deleted = 0
        if existing and existing["ids"]:
            self.collection.delete(ids=existing["ids"])
            deleted = len(existing["ids"])

        # Fetch all metadata records for this competitor from DB
        metadata_qs = CompetitorMetadata.objects.filter(competitor=competitor)
        if not metadata_qs.exists():
            self._build_bm25_index()
            return {"added": 0, "deleted": deleted}

        chunk_ids = []
        embeddings = []
        documents = []
        metadatas = []
        existing_chunks: List[str] = []

        for meta_obj in metadata_qs:
            meta = meta_obj.metadata
            content = meta.get("content", "")
            url = meta.get("url", meta_obj.url)
            title = meta.get("title", "") or url

            if not content or len(content.strip()) < 50:
                continue

            chunks = self.chunk_text(content)
            for idx, chunk_text in enumerate(chunks):
                if self._is_duplicate_chunk(chunk_text, existing_chunks, threshold=0.85):
                    continue
                existing_chunks.append(chunk_text)

                chunk_id = (
                    f"{competitor_name}_db_{meta_obj.pk}_{idx}_{int(time.time() * 1000)}"
                )
                embedding = self.generate_embedding(chunk_text)
                metadata_entry = {
                    "competitor_name": competitor_name,
                    "source_file": f"db_meta_{meta_obj.pk}",
                    "url": url,
                    "title": title,
                    "chunk_index": idx,
                    "chunk_size": len(chunk_text),
                    "base_url": self._normalize_url(url),
                }

                chunk_ids.append(chunk_id)
                embeddings.append(embedding)
                documents.append(chunk_text)
                metadatas.append(metadata_entry)

        if chunk_ids:
            # ChromaDB add in batches to avoid oversized requests
            batch_size = 500
            for i in range(0, len(chunk_ids), batch_size):
                self.collection.add(
                    ids=chunk_ids[i : i + batch_size],
                    embeddings=embeddings[i : i + batch_size],
                    documents=documents[i : i + batch_size],
                    metadatas=metadatas[i : i + batch_size],
                )

        # Rebuild BM25 index
        self._build_bm25_index()

        return {"added": len(chunk_ids), "deleted": deleted}
