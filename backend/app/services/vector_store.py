"""
Vector store service using pgvector (PostgreSQL extension)

TODO: Implement vector storage using pgvector
- Create embeddings table in PostgreSQL
- Store document chunks with vector embeddings
- Implement similarity search using pgvector operators
- Handle metadata filtering
"""
from typing import List, Dict, Any, Optional
import math
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import text
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings
from app.core.config import settings
from app.db.session import SessionLocal
import json


class VectorStore:
    """pgvector-based vector store for document embeddings"""
    
    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
        self.embeddings = self._initialize_embeddings()
        self._ensure_extension()
    
    def _initialize_embeddings(self):
        """Initialize embedding model"""
        if settings.OPENAI_API_KEY:
            return OpenAIEmbeddings(
                model=settings.OPENAI_EMBEDDING_MODEL,
                openai_api_key=settings.OPENAI_API_KEY
            )
        else:
            # Fallback to local embeddings
            return HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
    
    def _ensure_extension(self):
        """
        Ensure pgvector extension is enabled
        
        TODO: Implement this method
        - Execute: CREATE EXTENSION IF NOT EXISTS vector;
        - Create embeddings table if not exists
        """
        try:
            # Enable pgvector extension
            self.db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            self.db.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            
            # Create embeddings table
            # Dimension: 1536 for OpenAI, 384 for sentence-transformers
            dimension = 1536 if settings.OPENAI_API_KEY else 384
            
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS document_embeddings (
                id SERIAL PRIMARY KEY,
                document_id INTEGER,
                fund_id INTEGER,
                content TEXT NOT NULL,
                embedding vector({dimension}),
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS document_embeddings_embedding_idx 
            ON document_embeddings USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100);

            -- Full-text search index on content
            CREATE INDEX IF NOT EXISTS document_embeddings_tsv_idx
            ON document_embeddings USING GIN (to_tsvector('simple', content));

            -- Trigram index for fuzzy/pattern matching
            CREATE INDEX IF NOT EXISTS document_embeddings_trgm_idx
            ON document_embeddings USING GIN (content gin_trgm_ops);
            """
            
            self.db.execute(text(create_table_sql))
            self.db.commit()
        except Exception as e:
            print(f"Error ensuring pgvector extension: {e}")
            self.db.rollback()
    
    async def add_document(self, content: str, metadata: Dict[str, Any]):
        """
        Add a document to the vector store
        
        TODO: Implement this method
        - Generate embedding for content
        - Insert into document_embeddings table
        - Store metadata as JSONB
        """
        try:
            # Generate embedding
            embedding = await self._get_embedding(content)
            embedding_list = embedding.tolist()
            
            # Insert into database
            insert_sql = text("""
                INSERT INTO document_embeddings (document_id, fund_id, content, embedding, metadata)
                VALUES (:document_id, :fund_id, :content, CAST(:embedding AS vector), CAST(:metadata AS jsonb))
            """)
            
            self.db.execute(insert_sql, {
                "document_id": metadata.get("document_id"),
                "fund_id": metadata.get("fund_id"),
                "content": content,
                "embedding": str(embedding_list),
                "metadata": json.dumps(metadata)
            })
            self.db.commit()
        except Exception as e:
            print(f"Error adding document: {e}")
            self.db.rollback()
            raise
    
    async def similarity_search(
        self, 
        query: str, 
        k: int = 5, 
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents using cosine similarity
        
        TODO: Implement this method
        - Generate query embedding
        - Use pgvector's <=> operator for cosine distance
        - Apply metadata filters if provided
        - Return top k results
        
        Args:
            query: Search query
            k: Number of results to return
            filter_metadata: Optional metadata filters (e.g., {"fund_id": 1})
            
        Returns:
            List of similar documents with scores
        """
        try:
            # Generate query embedding
            query_embedding = await self._get_embedding(query)
            embedding_list = query_embedding.tolist()
            
            # Build query with optional filters
            where_clause = ""
            if filter_metadata:
                conditions = []
                for key, value in filter_metadata.items():
                    # Support filtering by single fund_id or document_id
                    if key in ["document_id", "fund_id"] and isinstance(value, (int, str)):
                        conditions.append(f"{key} = {value}")
                    # Support filtering by a list of document IDs
                    if key == "document_ids" and isinstance(value, list) and len(value) > 0:
                        # Ensure all values are ints
                        doc_ids = ",".join(str(int(v)) for v in value)
                        conditions.append(f"document_id IN ({doc_ids})")
                if conditions:
                    where_clause = "WHERE " + " AND ".join(conditions)
            
            # Search using cosine distance (<=> operator)
            search_sql = text(f"""
                SELECT 
                    id,
                    document_id,
                    fund_id,
                    content,
                    metadata,
                    1 - (embedding <=> CAST(:query_embedding AS vector)) as similarity_score
                FROM document_embeddings
                {where_clause}
                ORDER BY embedding <=> CAST(:query_embedding AS vector)
                LIMIT :k
            """)
            
            result = self.db.execute(search_sql, {
                "query_embedding": str(embedding_list),
                "k": k
            })
            
            # Format results
            results = []
            for row in result:
                results.append({
                    "id": row[0],
                    "document_id": row[1],
                    "fund_id": row[2],
                    "content": row[3],
                    "metadata": row[4],
                    "score": float(row[5])
                })
            
            return results
        except Exception as e:
            print(f"Error in similarity search: {e}")
            return []

    async def lexical_search(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
        language: str = 'simple'
    ) -> List[Dict[str, Any]]:
        """
        Lexical search using PostgreSQL full-text search

        Uses to_tsvector(content) and websearch_to_tsquery(query), ranked with ts_rank.
        """
        try:
            # Build optional filters
            conditions = []
            if filter_metadata:
                for key, value in filter_metadata.items():
                    if key in ["document_id", "fund_id"] and isinstance(value, (int, str)):
                        conditions.append(f"{key} = {value}")
                    if key == "document_ids" and isinstance(value, list) and len(value) > 0:
                        doc_ids = ",".join(str(int(v)) for v in value)
                        conditions.append(f"document_id IN ({doc_ids})")

            where_clause = ""
            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)

            sql = text(f"""
                SELECT 
                    id,
                    document_id,
                    fund_id,
                    content,
                    metadata,
                    ts_rank(to_tsvector('{language}', content), websearch_to_tsquery(:q)) AS score
                FROM document_embeddings
                {where_clause}
                ORDER BY score DESC
                LIMIT :k
            """)

            result = self.db.execute(sql, {"q": query, "k": k})
            rows = []
            for row in result:
                rows.append({
                    "id": row[0],
                    "document_id": row[1],
                    "fund_id": row[2],
                    "content": row[3],
                    "metadata": row[4],
                    "score": float(row[5]) if row[5] is not None else 0.0,
                })
            return rows
        except Exception as e:
            print(f"Error in lexical search: {e}")
            return []

    async def pattern_search(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
        similarity_threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Pattern/fuzzy search using pg_trgm similarity

        Filters using content % :q and ranks by similarity(content, :q).
        """
        try:
            conditions = []
            # Add fuzzy operator condition
            conditions.append("content % :q")

            if filter_metadata:
                for key, value in filter_metadata.items():
                    if key in ["document_id", "fund_id"] and isinstance(value, (int, str)):
                        conditions.append(f"{key} = {value}")
                    if key == "document_ids" and isinstance(value, list) and len(value) > 0:
                        doc_ids = ",".join(str(int(v)) for v in value)
                        conditions.append(f"document_id IN ({doc_ids})")

            where_clause = "WHERE " + " AND ".join(conditions)

            sql = text(f"""
                SELECT 
                    id,
                    document_id,
                    fund_id,
                    content,
                    metadata,
                    similarity(content, :q) AS score
                FROM document_embeddings
                {where_clause}
                AND similarity(content, :q) >= :threshold
                ORDER BY score DESC
                LIMIT :k
            """)

            result = self.db.execute(sql, {"q": query, "threshold": similarity_threshold, "k": k})
            rows = []
            for row in result:
                rows.append({
                    "id": row[0],
                    "document_id": row[1],
                    "fund_id": row[2],
                    "content": row[3],
                    "metadata": row[4],
                    "score": float(row[5]) if row[5] is not None else 0.0,
                })
            return rows
        except Exception as e:
            print(f"Error in pattern search: {e}")
            return []

    async def hybrid_search(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
        weights: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining dense, lexical, and pattern using Reciprocal Rank Fusion.
        """
        try:
            # Fetch candidates from each method
            k_each = max(k, 10)
            dense = await self.similarity_search(query, k_each, filter_metadata)
            lexical = await self.lexical_search(query, k_each, filter_metadata)
            pattern = await self.pattern_search(query, k_each, filter_metadata)

            # Build rank maps
            def rank_map(results: List[Dict[str, Any]]):
                return {res["id"]: idx for idx, res in enumerate(results)}

            r_dense = rank_map(dense)
            r_lex = rank_map(lexical)
            r_pat = rank_map(pattern)

            # Weights default
            w_dense = (weights or {}).get("dense", 1.0)
            w_lex = (weights or {}).get("lexical", 1.0)
            w_pat = (weights or {}).get("pattern", 1.0)

            k_rrf = 60.0
            scores: Dict[int, float] = {}
            items: Dict[int, Dict[str, Any]] = {}

            # Union of IDs
            all_ids = set(list(r_dense.keys()) + list(r_lex.keys()) + list(r_pat.keys()))

            for _id in all_ids:
                s = 0.0
                if _id in r_dense:
                    s += w_dense * (1.0 / (k_rrf + r_dense[_id] + 1))
                if _id in r_lex:
                    s += w_lex * (1.0 / (k_rrf + r_lex[_id] + 1))
                if _id in r_pat:
                    s += w_pat * (1.0 / (k_rrf + r_pat[_id] + 1))
                scores[_id] = s

            # Resolve item content (prefer dense, then lexical, then pattern)
            def get_item(_id: int) -> Dict[str, Any]:
                for coll in (dense, lexical, pattern):
                    for r in coll:
                        if r["id"] == _id:
                            return r
                return {}

            for _id in all_ids:
                items[_id] = get_item(_id)

            ranked = sorted(all_ids, key=lambda x: scores.get(x, 0.0), reverse=True)
            out: List[Dict[str, Any]] = []
            for _id in ranked[:k]:
                item = items[_id]
                # Attach fused score
                item = dict(item)
                item["score"] = float(scores[_id])
                out.append(item)
            return out
        except Exception as e:
            print(f"Error in hybrid search: {e}")
            return []
    
    async def _get_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for text"""
        if hasattr(self.embeddings, 'embed_query'):
            embedding = self.embeddings.embed_query(text)
        else:
            embedding = self.embeddings.encode(text)
        
        return np.array(embedding, dtype=np.float32)
    
    def clear(self, fund_id: Optional[int] = None):
        """
        Clear the vector store
        
        TODO: Implement this method
        - Delete all embeddings (or filter by fund_id)
        """
        try:
            if fund_id:
                delete_sql = text("DELETE FROM document_embeddings WHERE fund_id = :fund_id")
                self.db.execute(delete_sql, {"fund_id": fund_id})
            else:
                delete_sql = text("DELETE FROM document_embeddings")
                self.db.execute(delete_sql)
            
            self.db.commit()
        except Exception as e:
            print(f"Error clearing vector store: {e}")
            self.db.rollback()
