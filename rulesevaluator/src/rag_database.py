"""RAG Database implementation using ChromaDB"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import hashlib
import json
from datetime import datetime
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import openai

from .content_ingestor import ContentItem

logger = logging.getLogger(__name__)


class RAGDatabase:
    """Manages vector database for RAG functionality"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize RAG database
        
        Args:
            config: RAG configuration from config.yaml
        """
        self.config = config
        self.persist_directory = Path(config.get('persist_directory', './chromadb_data'))
        self.collection_name = config.get('collection_name', 'rules_evaluator')
        self.embedding_model = config.get('embedding_model', 'text-embedding-3-small')
        self.chunk_size = config.get('chunk_size', 1000)
        self.chunk_overlap = config.get('chunk_overlap', 200)
        self.update_strategy = config.get('update_strategy', 'overwrite')
        
        self._init_database()
        self._init_embedding_function()
    
    def _init_database(self):
        """Initialize ChromaDB client"""
        try:
            # Ensure persist directory exists
            self.persist_directory.mkdir(parents=True, exist_ok=True)
            
            # Initialize ChromaDB with persistence
            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            logger.info(f"ChromaDB initialized at {self.persist_directory}")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
    
    def _init_embedding_function(self):
        """Initialize embedding function"""
        # Get OpenAI API key from environment or config
        api_key = self.config.get('openai_api_key')
        if not api_key:
            import os
            api_key = os.getenv('OPENAI_API_KEY')
        
        if not api_key:
            raise ValueError("OpenAI API key required for embeddings")
        
        # Use ChromaDB's OpenAI embedding function
        self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=api_key,
            model_name=self.embedding_model
        )
    
    def get_or_create_collection(self) -> chromadb.Collection:
        """Get or create the collection"""
        try:
            # Try to get existing collection
            collection = self.client.get_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function
            )
            logger.info(f"Using existing collection: {self.collection_name}")
            return collection
            
        except (ValueError, chromadb.errors.NotFoundError):
            # Collection doesn't exist, create it
            collection = self.client.create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
                metadata={"created_at": datetime.now().isoformat()}
            )
            logger.info(f"Created new collection: {self.collection_name}")
            return collection
    
    def reset_collection(self):
        """Reset the collection (delete and recreate)"""
        try:
            self.client.delete_collection(self.collection_name)
            logger.info(f"Deleted collection: {self.collection_name}")
        except:
            pass  # Collection might not exist
        
        return self.get_or_create_collection()
    
    def add_content(self, content_items: List[ContentItem], reset: bool = False) -> int:
        """Add content items to the database
        
        Args:
            content_items: List of content items to add
            reset: Whether to reset collection before adding
            
        Returns:
            Number of chunks added
        """
        if reset or self.update_strategy == 'overwrite':
            collection = self.reset_collection()
        else:
            collection = self.get_or_create_collection()
        
        total_chunks = 0
        
        for item in content_items:
            chunks = self._chunk_content(item)
            
            if not chunks:
                continue
            
            # Prepare data for ChromaDB
            ids = []
            texts = []
            metadatas = []
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{item.id}_{i}"
                ids.append(chunk_id)
                texts.append(chunk['text'])
                
                # Combine item metadata with chunk metadata
                metadata = {
                    **item.metadata,
                    'chunk_index': i,
                    'chunk_total': len(chunks),
                    'content_id': item.id
                }
                metadatas.append(metadata)
            
            # Add to collection
            try:
                collection.add(
                    ids=ids,
                    documents=texts,
                    metadatas=metadatas
                )
                total_chunks += len(chunks)
                logger.debug(f"Added {len(chunks)} chunks for content item {item.id}")
                
            except Exception as e:
                logger.error(f"Error adding chunks for {item.id}: {e}")
        
        # PersistentClient automatically persists changes
        
        logger.info(f"Added {total_chunks} chunks from {len(content_items)} content items")
        return total_chunks
    
    def _chunk_content(self, content_item: ContentItem) -> List[Dict[str, Any]]:
        """Split content into chunks with overlap
        
        Args:
            content_item: Content item to chunk
            
        Returns:
            List of chunk dictionaries
        """
        text = content_item.content
        
        if not text or len(text.strip()) == 0:
            return []
        
        # Simple character-based chunking with word boundaries
        chunks = []
        start = 0
        
        while start < len(text):
            # Find chunk end
            end = start + self.chunk_size
            
            # If not at the end of text, try to break at word boundary
            if end < len(text):
                # Look for last space before chunk_size
                last_space = text.rfind(' ', start, end)
                if last_space > start:
                    end = last_space
            
            # Extract chunk
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                chunks.append({
                    'text': chunk_text,
                    'start': start,
                    'end': end
                })
            
            # Move start position with overlap
            start = end - self.chunk_overlap
            
            # Ensure we make progress
            if start <= chunks[-1]['start'] if chunks else start <= 0:
                start = end
        
        return chunks
    
    def query(self, query_text: str, n_results: int = 5, 
              filter_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Query the database for relevant content
        
        Args:
            query_text: Query string
            n_results: Number of results to return
            filter_dict: Optional metadata filters
            
        Returns:
            List of relevant chunks with metadata
        """
        try:
            collection = self.get_or_create_collection()
            
            # Build where clause from filter_dict
            where = None
            if filter_dict:
                where = filter_dict
            
            # Query the collection
            results = collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Format results
            formatted_results = []
            
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        'id': results['ids'][0][i],
                        'text': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'distance': results['distances'][0][i]
                    })
            
            logger.debug(f"Query returned {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error querying database: {e}")
            return []
    
    def get_context_for_prompt(self, prompt: str, max_context_length: int = 3000) -> str:
        """Get relevant context for a prompt
        
        Args:
            prompt: The prompt to find context for
            max_context_length: Maximum total length of context
            
        Returns:
            Concatenated relevant context
        """
        # Query for relevant chunks
        results = self.query(prompt, n_results=10)
        
        if not results:
            logger.warning(f"No relevant context found for prompt: {prompt[:50]}...")
            return ""
        
        # Build context from results
        context_parts = []
        total_length = 0
        
        for result in results:
            text = result['text']
            metadata = result['metadata']
            
            # Add source information
            source = metadata.get('source', 'unknown')
            if source == 'website':
                source_info = f"[Source: {metadata.get('url', 'unknown')}]"
            elif source == 'local':
                source_info = f"[Source: {metadata.get('path', 'unknown')}]"
            else:
                source_info = f"[Source: {source}]"
            
            # Check if adding this would exceed limit
            chunk_with_source = f"{source_info}\n{text}\n"
            if total_length + len(chunk_with_source) > max_context_length:
                break
            
            context_parts.append(chunk_with_source)
            total_length += len(chunk_with_source)
        
        context = "\n---\n".join(context_parts)
        
        logger.info(f"Built context of {len(context)} characters from {len(context_parts)} chunks")
        return context
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics
        
        Returns:
            Dictionary with database stats
        """
        try:
            collection = self.get_or_create_collection()
            
            # Get collection count
            count = collection.count()
            
            # Get metadata about sources
            all_results = collection.get(include=['metadatas'])
            
            source_counts = {}
            content_ids = set()
            
            for metadata in all_results['metadatas']:
                source = metadata.get('source', 'unknown')
                source_counts[source] = source_counts.get(source, 0) + 1
                content_ids.add(metadata.get('content_id'))
            
            stats = {
                'total_chunks': count,
                'total_documents': len(content_ids),
                'sources': source_counts,
                'collection_name': self.collection_name,
                'embedding_model': self.embedding_model,
                'chunk_size': self.chunk_size,
                'chunk_overlap': self.chunk_overlap
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {
                'error': str(e),
                'total_chunks': 0,
                'total_documents': 0
            }