"""
RAG Service with ChromaDB: Semantic retrieval using dense vectors (ChromaDB HNSW).
"""
import hashlib
import json
import os
import time
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np
import requests

from sentence_transformers import SentenceTransformer
from django.conf import settings
from django.core.cache import cache
import chromadb
from difflib import SequenceMatcher

CHROMA_HOST = getattr(settings, 'CHROMA_HOST', '127.0.0.1')

_RAG_SYSTEM_PROMPT = """You are a professional competitive intelligence assistant for TrackRival, a competitor monitoring platform.

=== LANGUAGE RULES ===
Detect the language used in the question and respond in the SAME language.
Supported: English, Urdu script, Roman Urdu.
If language is unclear, respond in English.
Use Pakistani vocabulary only.
BANNED words: kripya, dhanyavaad, namaskar, pranaam.
Allowed Urdu words: shukriya, meherbani, bilkul, zaroor.

=== ROLE ===
You help users understand data about their competitors including products, services, pricing, website content, and business activities — across any industry. Answer based solely on the scraped competitor data provided in the context.

=== RESPONSE RULES ===
- Answer using ONLY the provided context. Never fabricate or assume information.
- If the context does not contain enough information to answer, say: "I don't have enough information about that in the current knowledge base."
- Keep responses concise and under 300 words unless the question requires listing multiple items.
- Always cite sources using the exact Page URL from the context, shown as plain text. Never use markdown hyperlinks like [text](url).
- Never use labels like "Document 1" or "Source 1" — always show the actual URL.
- Use single asterisks for emphasis only (*important*).
- Do not use tables, horizontal bars, or dashes as separators.
- Be professional, concise, and helpful.

=== OUT OF SCOPE ===
If the question is completely unrelated to the user's competitors or business intelligence:
Reply: "I can only assist with questions about your monitored competitors and their data."

=== PROHIBITED TOPICS ===
Politics, religion, medical/legal/financial advice, personal opinions, or any content unrelated to competitive intelligence."""
CHROMA_PORT = getattr(settings, 'CHROMA_PORT', 8001)
RAG_TOP_K = getattr(settings, 'RAG_TOP_K', 10)
RAG_CACHE_TTL = getattr(settings, 'RAG_CACHE_TTL', 7200)

# Loaded once at import time, shared across all RAGServiceChroma instances and workers
_embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')


class RAGServiceChroma:
    """Service for RAG operations with ChromaDB HTTP client."""

    def __init__(self):
        """Initialize ChromaDB HTTP client and embedding model."""
        self.embedding_model = _embedding_model
        self.chunk_size = 1500  # characters
        self.chunk_overlap = 150  # characters

        # HttpClient — safe for concurrent access from multiple processes
        self.client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="competitor_documents",
            metadata={"hnsw:space": "cosine"}
        )
        
        
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
        
        return stats

    def semantic_search(
        self,
        query: str,
        top_k: int = 5,
        competitor_filter: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> List[Dict]:
        """
        Perform semantic search using ChromaDB dense vector retrieval.

        Args:
            query: Search query
            top_k: Number of results to return
            competitor_filter: Filter by competitor name
            user_id: Scope results to this user only

        Returns:
            Dict with results list and metadata
        """
        start_time = time.time()

        query_embedding = self.generate_embedding(query)

        has_comp = competitor_filter and competitor_filter.lower() != 'all'
        comp_name = competitor_filter.lower().replace(" ", "_") if has_comp else None
        if user_id and has_comp:
            where_filter = {"$and": [
                {"user_id": int(user_id)},
                {"competitor_name": comp_name},
            ]}
        elif user_id:
            where_filter = {"user_id": int(user_id)}
        elif has_comp:
            where_filter = {"competitor_name": comp_name}
        else:
            where_filter = None

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter,
            include=['documents', 'metadatas', 'distances']
        )

        final_results = []
        if results['ids'] and results['ids'][0]:
            for doc_id, document, metadata, distance in zip(
                results['ids'][0],
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0],
            ):
                final_results.append({
                    'id': doc_id,
                    'text': document,
                    'metadata': metadata,
                    'fusion_score': round(1 / (1 + distance), 4),
                })

        return {
            'results': final_results,
            'retrieval_time': round(time.time() - start_time, 3),
            'query': query,
            'total_results': len(final_results),
        }
    
    def generate_answer(self, query: str, context_chunks: List[Dict]) -> str:
        """Generate answer using GPT-4o-mini with retrieved context."""

        context = "\n\n".join([
            f"[Source {i+1}]\n"
            f"Page Title: {chunk['metadata'].get('title', 'Unknown')}\n"
            f"Page URL: {chunk['metadata'].get('url', 'N/A')}\n"
            f"Content:\n{chunk['text']}"
            for i, chunk in enumerate(context_chunks)
        ])

        system_prompt = _RAG_SYSTEM_PROMPT

        user_prompt = f"""Context from competitor websites:

{context}

---

Question: {query}

Answer based strictly on the context above. Cite the exact Page URL (plain text) for each piece of information you use."""

        api_key = settings.OPENAI_API_KEY
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.5,
            "max_tokens": 800
        }

        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            return f"Error generating answer: {str(e)}"
    
    def generate_answer_stream(self, query: str, context_chunks: List[Dict]):
        """
        Stream answer tokens from GPT-4o-mini one chunk at a time.
        Yields plain text deltas (not SSE-formatted — the view handles that).
        """
        context = "\n\n".join([
            f"[Source {i+1}]\n"
            f"Page Title: {chunk['metadata'].get('title', 'Unknown')}\n"
            f"Page URL: {chunk['metadata'].get('url', 'N/A')}\n"
            f"Content:\n{chunk['text']}"
            for i, chunk in enumerate(context_chunks)
        ])

        system_prompt = _RAG_SYSTEM_PROMPT

        user_prompt = f"""Context from competitor websites:

{context}

---

Question: {query}

Answer based strictly on the context above. Cite the exact Page URL (plain text) for each piece of information you use."""

        api_key = settings.OPENAI_API_KEY
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.5,
            "max_tokens": 800,
            "stream": True,
        }

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            stream=True,
            timeout=60,
        )
        response.raise_for_status()

        for line in response.iter_lines():
            if not line:
                continue
            line = line.decode("utf-8")
            if not line.startswith("data: "):
                continue
            data = line[6:]
            if data == "[DONE]":
                return
            try:
                chunk = json.loads(data)
                delta = chunk["choices"][0]["delta"].get("content", "")
                if delta:
                    yield delta
            except (json.JSONDecodeError, KeyError, IndexError):
                continue

    def query(
        self,
        query_text: str,
        top_k: int = None,
        competitor_filter: Optional[str] = None,
        user_id: Optional[int] = None,
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
        top_k = top_k or RAG_TOP_K

        # Cache lookup (skip if TTL is 0)
        cache_key = None
        if RAG_CACHE_TTL > 0:
            raw_key = f"rag:{user_id or 'anon'}:{query_text.strip().lower()}:{competitor_filter or 'all'}:{top_k}"
            cache_key = "rag_" + hashlib.md5(raw_key.encode()).hexdigest()
            cached = cache.get(cache_key)
            if cached is not None:
                cached['cache_hit'] = True
                cached['total_time'] = round(time.time() - start_time, 3)
                return cached

        # Retrieval
        search_results = self.semantic_search(query_text, top_k, competitor_filter, user_id=user_id)
        retrieval_time = search_results['retrieval_time']

        # Short-circuit: no indexed content found for this user/filter
        if not search_results['results']:
            comp_label = competitor_filter if (competitor_filter and competitor_filter != 'all') else 'your competitors'
            no_data_answer = (
                f"No website content has been indexed for {comp_label} yet. "
                "This usually means the website couldn't be accessed during onboarding "
                "(bot protection), or indexing is still in progress. "
                "Try re-adding the competitor or contact support if the issue persists."
            )
            result = {
                'query': query_text,
                'answer': no_data_answer,
                'retrieved_chunks': [],
                'retrieval_time': retrieval_time,
                'generation_time': 0,
                'total_time': round(time.time() - start_time, 3),
                'top_k': top_k,
                'competitor_filter': competitor_filter or 'all',
                'cache_hit': False,
            }
            return result

        # Generation
        gen_start = time.time()
        answer = self.generate_answer(query_text, search_results['results'])
        generation_time = time.time() - gen_start
        
        total_time = time.time() - start_time
        
        result = {
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
            'competitor_filter': competitor_filter or 'all',
            'cache_hit': False,
        }

        if cache_key:
            cache.set(cache_key, result, RAG_CACHE_TTL)

        return result
    
    def get_stats(self, user_id: Optional[int] = None) -> Dict:
        """Get statistics about the RAG system, scoped to a user when provided."""
        collection_count = self.collection.count()
        competitor_counts = {}

        if user_id:
            from apps.monitoring.models import Competitor
            user_comps = Competitor.objects.filter(user_id=user_id, is_deleted=False)
            for comp in user_comps:
                comp_name = comp.name.lower().replace(" ", "_")
                results = self.collection.get(
                    where={"$and": [{"user_id": int(user_id)}, {"competitor_name": comp_name}]},
                    include=['metadatas'],
                )
                competitor_counts[comp_name] = len(results['ids']) if results['ids'] else 0
        else:
            # Fallback for management commands (no user context)
            all_meta = self.collection.get(include=['metadatas'])
            for meta in (all_meta.get('metadatas') or []):
                name = meta.get('competitor_name', 'unknown')
                competitor_counts[name] = competitor_counts.get(name, 0) + 1

        return {
            'total_chunks': collection_count,
            'competitor_chunks': competitor_counts,
            'embedding_dimension': 384,
            'model': 'sentence-transformers/all-MiniLM-L6-v2',
            'retrieval_method': 'dense (ChromaDB HNSW cosine)',
            'database': 'ChromaDB',
        }

    def get_competitors(self, user_id: Optional[int] = None) -> List[Dict]:
        """Get list of competitors with chunk counts, scoped to a user."""
        stats = self.get_stats(user_id=user_id)
        return [
            {'name': name.replace('_', ' ').title(), 'value': name, 'chunk_count': count}
            for name, count in stats['competitor_chunks'].items()
        ]

    def ingest_competitor_from_db(self, competitor, user_id: Optional[int] = None) -> Dict[str, int]:
        """
        Ingest a single competitor's data from DB (CompetitorMetadata) into ChromaDB.
        Deletes only THIS user's existing chunks for this competitor, then re-ingests.

        Args:
            competitor: Competitor model instance
            user_id: Owner user ID (falls back to competitor.user_id)

        Returns:
            Dict with 'added' and 'deleted' counts
        """
        from apps.monitoring.models import CompetitorMetadata

        uid = int(user_id if user_id is not None else competitor.user_id)
        competitor_name = competitor.name.lower().replace(" ", "_")

        # Delete only THIS user's chunks for this competitor (not other users' data)
        existing = self.collection.get(
            where={"$and": [{"user_id": uid}, {"competitor_name": competitor_name}]},
            include=["metadatas"],
        )
        deleted = 0
        if existing and existing["ids"]:
            self.collection.delete(ids=existing["ids"])
            deleted = len(existing["ids"])

        # Fetch all metadata records for this competitor from DB
        metadata_qs = CompetitorMetadata.objects.filter(competitor=competitor)
        if not metadata_qs.exists():
            return {"added": 0, "deleted": deleted}

        chunk_ids = []
        embeddings = []
        documents = []
        metadatas = []
        seen_hashes: set = set()  # O(1) dedup using MD5 hash

        for meta_obj in metadata_qs:
            meta = meta_obj.metadata
            content = meta.get("content", "")
            url = meta.get("url", meta_obj.url)
            title = meta.get("title", "") or url

            if not content or len(content.strip()) < 50:
                continue

            chunks = self.chunk_text(content)
            for idx, chunk_text in enumerate(chunks):
                chunk_hash = hashlib.md5(chunk_text.strip().lower().encode()).hexdigest()
                if chunk_hash in seen_hashes:
                    continue
                seen_hashes.add(chunk_hash)

                chunk_id = f"u{uid}_{competitor_name}_db_{meta_obj.pk}_{idx}_{int(time.time() * 1000)}"
                embedding = self.generate_embedding(chunk_text)
                metadata_entry = {
                    "user_id": uid,
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
            batch_size = 500
            for i in range(0, len(chunk_ids), batch_size):
                self.collection.add(
                    ids=chunk_ids[i : i + batch_size],
                    embeddings=embeddings[i : i + batch_size],
                    documents=documents[i : i + batch_size],
                    metadatas=metadatas[i : i + batch_size],
                )

        return {"added": len(chunk_ids), "deleted": deleted}
