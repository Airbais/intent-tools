"""Tests for RAG database"""

import pytest
import tempfile
from pathlib import Path
import os

from src.rag_database import RAGDatabase
from src.content_ingestor import ContentItem


class TestRAGDatabase:
    """Test RAG database functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Skip if no OpenAI API key
        if not os.getenv('OPENAI_API_KEY'):
            pytest.skip("OpenAI API key required for RAG database tests")
        
        # Use temporary directory
        self.temp_dir = tempfile.mkdtemp()
        
        self.config = {
            'persist_directory': self.temp_dir,
            'collection_name': 'test_collection',
            'embedding_model': 'text-embedding-3-small',
            'chunk_size': 100,
            'chunk_overlap': 20,
            'openai_api_key': os.getenv('OPENAI_API_KEY')
        }
        
        self.rag_db = RAGDatabase(self.config)
    
    def teardown_method(self):
        """Clean up test fixtures"""
        # Clean up temp directory
        import shutil
        if hasattr(self, 'temp_dir') and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_database_initialization(self):
        """Test database initialization"""
        assert self.rag_db is not None
        assert self.rag_db.client is not None
        assert self.rag_db.collection_name == 'test_collection'
    
    def test_collection_creation(self):
        """Test collection creation"""
        collection = self.rag_db.get_or_create_collection()
        assert collection is not None
        assert collection.name == 'test_collection'
    
    def test_content_chunking(self):
        """Test content chunking functionality"""
        # Create test content item
        long_content = "This is a test content. " * 20  # Make it long enough to chunk
        metadata = {'source': 'test', 'path': 'test.txt'}
        content_item = ContentItem(long_content, metadata)
        
        # Test chunking
        chunks = self.rag_db._chunk_content(content_item)
        
        assert len(chunks) > 1  # Should be chunked
        assert all('text' in chunk for chunk in chunks)
        assert all(len(chunk['text']) <= self.config['chunk_size'] + 50 for chunk in chunks)  # Allow some flexibility
    
    def test_add_content(self):
        """Test adding content to database"""
        # Create test content items
        content_items = [
            ContentItem("Test content about return policies.", {'source': 'test', 'path': 'test1.txt'}),
            ContentItem("Information about premium subscriptions.", {'source': 'test', 'path': 'test2.txt'})
        ]
        
        # Add content
        chunks_added = self.rag_db.add_content(content_items, reset=True)
        
        assert chunks_added > 0
        
        # Verify content was added
        stats = self.rag_db.get_statistics()
        assert stats['total_chunks'] > 0
        assert stats['total_documents'] == 2
    
    def test_query_functionality(self):
        """Test querying the database"""
        # Add some test content first
        content_items = [
            ContentItem("Our 30-day return policy allows returns within thirty days.", 
                       {'source': 'test', 'path': 'policy.txt'}),
            ContentItem("Premium subscription includes unlimited access and priority support.", 
                       {'source': 'test', 'path': 'premium.txt'})
        ]
        
        self.rag_db.add_content(content_items, reset=True)
        
        # Test query
        results = self.rag_db.query("return policy", n_results=2)
        
        assert len(results) > 0
        assert any("return" in result['text'].lower() for result in results)
        assert all('metadata' in result for result in results)
        assert all('distance' in result for result in results)
    
    def test_get_context_for_prompt(self):
        """Test getting context for a prompt"""
        # Add content
        content_items = [
            ContentItem("Our company offers a 30-day return policy for all products.", 
                       {'source': 'test', 'path': 'returns.txt'}),
            ContentItem("Premium features include advanced analytics and priority support.", 
                       {'source': 'test', 'path': 'premium.txt'})
        ]
        
        self.rag_db.add_content(content_items, reset=True)
        
        # Get context
        context = self.rag_db.get_context_for_prompt("What is the return policy?")
        
        assert len(context) > 0
        assert "return" in context.lower()
        assert "[Source:" in context  # Should include source information
    
    def test_statistics(self):
        """Test getting database statistics"""
        # Add some content
        content_items = [
            ContentItem("Test content 1", {'source': 'local', 'path': 'test1.txt'}),
            ContentItem("Test content 2", {'source': 'website', 'url': 'http://example.com'})
        ]
        
        self.rag_db.add_content(content_items, reset=True)
        
        # Get statistics
        stats = self.rag_db.get_statistics()
        
        assert 'total_chunks' in stats
        assert 'total_documents' in stats
        assert 'sources' in stats
        assert stats['total_documents'] == 2
        assert 'local' in stats['sources']
        assert 'website' in stats['sources']
    
    def test_reset_collection(self):
        """Test resetting collection"""
        # Add initial content
        content_items = [
            ContentItem("Initial content", {'source': 'test', 'path': 'initial.txt'})
        ]
        
        self.rag_db.add_content(content_items, reset=True)
        initial_stats = self.rag_db.get_statistics()
        
        # Reset and add different content
        new_content_items = [
            ContentItem("New content after reset", {'source': 'test', 'path': 'new.txt'})
        ]
        
        self.rag_db.add_content(new_content_items, reset=True)
        new_stats = self.rag_db.get_statistics()
        
        # Should have replaced, not added to existing
        assert new_stats['total_documents'] == 1
        
        # Query should only return new content
        results = self.rag_db.query("content", n_results=5)
        assert all("new content" in result['text'].lower() for result in results)