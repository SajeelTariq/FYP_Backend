"""
Milvus vector database connection and operations.
"""
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class MilvusClient:
    """Client for interacting with Milvus vector database."""
    
    def __init__(self):
        self.host = settings.MILVUS_CONFIG['HOST']
        self.port = settings.MILVUS_CONFIG['PORT']
        self.collection_name = settings.MILVUS_CONFIG['COLLECTION_NAME']
        self.dimension = settings.MILVUS_CONFIG['DIMENSION']
        self.collection = None
    
    def connect(self):
        """Establish connection to Milvus."""
        try:
            connections.connect(
                alias="default",
                host=self.host,
                port=self.port
            )
            logger.info(f"Connected to Milvus at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {str(e)}")
            return False
    
    def create_collection(self):
        """Create collection if it doesn't exist."""
        try:
            # Define collection schema
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="vector_id", dtype=DataType.VARCHAR, max_length=255),
                FieldSchema(name="competitor_id", dtype=DataType.INT64),
                FieldSchema(name="data_type", dtype=DataType.VARCHAR, max_length=50),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dimension),
            ]
            
            schema = CollectionSchema(
                fields=fields,
                description="Competitor data embeddings"
            )
            
            self.collection = Collection(
                name=self.collection_name,
                schema=schema
            )
            
            # Create index
            index_params = {
                "metric_type": "L2",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128}
            }
            self.collection.create_index(
                field_name="embedding",
                index_params=index_params
            )
            
            logger.info(f"Collection '{self.collection_name}' created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create collection: {str(e)}")
            return False
    
    def insert_vectors(self, data):
        """
        Insert vectors into Milvus.
        
        Args:
            data: List of dictionaries with keys: vector_id, competitor_id, data_type, embedding
        """
        try:
            if not self.collection:
                self.collection = Collection(self.collection_name)
            
            # Prepare data for insertion
            entities = [
                [item['vector_id'] for item in data],
                [item['competitor_id'] for item in data],
                [item['data_type'] for item in data],
                [item['embedding'] for item in data],
            ]
            
            insert_result = self.collection.insert(entities)
            self.collection.flush()
            
            logger.info(f"Inserted {len(data)} vectors into Milvus")
            return insert_result
            
        except Exception as e:
            logger.error(f"Failed to insert vectors: {str(e)}")
            return None
    
    def search(self, query_vectors, top_k=5, filters=None):
        """
        Search for similar vectors.
        
        Args:
            query_vectors: List of query embedding vectors
            top_k: Number of top results to return
            filters: Optional filters (e.g., competitor_id)
        """
        try:
            if not self.collection:
                self.collection = Collection(self.collection_name)
            
            self.collection.load()
            
            search_params = {
                "metric_type": "L2",
                "params": {"nprobe": 10}
            }
            
            results = self.collection.search(
                data=query_vectors,
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                expr=filters
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            return None
    
    def disconnect(self):
        """Disconnect from Milvus."""
        try:
            connections.disconnect(alias="default")
            logger.info("Disconnected from Milvus")
        except Exception as e:
            logger.error(f"Failed to disconnect: {str(e)}")


# Singleton instance
milvus_client = MilvusClient()
