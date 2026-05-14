"""Tests for content ingestion"""

import pytest
from pathlib import Path
import tempfile
import json

from src.content_ingestor import ContentIngestor, LocalFileSource, ContentProcessor


class TestContentProcessor:
    """Test content processing functions"""
    
    def test_process_markdown(self):
        """Test markdown processing"""
        processor = ContentProcessor()
        
        md_content = """# Title
        
This is **bold** and this is *italic*.

- Item 1
- Item 2
"""
        result = processor.process_markdown(md_content)
        
        assert "Title" in result
        assert "bold" in result
        assert "italic" in result
        assert "Item 1" in result
    
    def test_process_html(self):
        """Test HTML processing"""
        processor = ContentProcessor()
        
        html_content = """<html>
        <head><title>Test Page</title></head>
        <body>
            <h1>Header</h1>
            <p>This is a paragraph.</p>
            <script>console.log('ignored');</script>
        </body>
        </html>"""
        
        result = processor.process_html(html_content)
        
        assert "Header" in result
        assert "paragraph" in result
        assert "console.log" not in result  # Script should be removed
    
    def test_process_json(self):
        """Test JSON processing"""
        processor = ContentProcessor()
        
        json_content = '{"key": "value", "number": 123}'
        result = processor.process_json(json_content)
        
        assert "key" in result
        assert "value" in result
        assert "123" in result
    
    def test_process_csv(self):
        """Test CSV processing"""
        processor = ContentProcessor()
        
        csv_content = """Name,Age,City
John,30,New York
Jane,25,London"""
        
        result = processor.process_csv(csv_content)
        
        assert "Headers: Name, Age, City" in result
        assert "John | 30 | New York" in result
        assert "Jane | 25 | London" in result


class TestLocalFileSource:
    """Test local file ingestion"""
    
    def test_validate_config(self):
        """Test configuration validation"""
        # Valid config
        config = {'path': '.'}
        source = LocalFileSource(config)
        is_valid, errors = source.validate_config()
        assert is_valid is True
        
        # Invalid path
        config = {'path': '/nonexistent/path'}
        source = LocalFileSource(config)
        is_valid, errors = source.validate_config()
        assert is_valid is False
        assert any("does not exist" in e for e in errors)
    
    def test_ingest_files(self):
        """Test file ingestion"""
        # Use test_content directory
        test_dir = Path(__file__).parent.parent / "test_content"
        if not test_dir.exists():
            pytest.skip("test_content directory not found")
        
        config = {
            'path': str(test_dir),
            'recursive': False,
            'file_patterns': ['*.txt', '*.md']
        }
        
        source = LocalFileSource(config)
        items = source.ingest()
        
        assert len(items) > 0
        
        # Check metadata
        for item in items:
            assert item.metadata['source'] == 'local'
            assert 'path' in item.metadata
            assert 'file_type' in item.metadata
            assert len(item.content) > 0
    
    def test_recursive_scanning(self):
        """Test recursive directory scanning"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create nested structure
            Path(temp_dir, "subdir").mkdir()
            Path(temp_dir, "file1.txt").write_text("Content 1")
            Path(temp_dir, "subdir", "file2.txt").write_text("Content 2")
            
            # Non-recursive
            config = {
                'path': temp_dir,
                'recursive': False,
                'file_patterns': ['*.txt']
            }
            source = LocalFileSource(config)
            items = source.ingest()
            assert len(items) == 1
            
            # Recursive
            config['recursive'] = True
            source = LocalFileSource(config)
            items = source.ingest()
            assert len(items) == 2


class TestContentIngestor:
    """Test main content ingestor"""
    
    def test_create_local_source(self):
        """Test creating local source"""
        config = {
            'type': 'local',
            'local': {'path': '.'}
        }
        
        ingestor = ContentIngestor(config)
        assert isinstance(ingestor.source, LocalFileSource)
    
    def test_invalid_source_type(self):
        """Test invalid source type"""
        config = {'type': 'invalid'}
        
        with pytest.raises(ValueError) as exc_info:
            ContentIngestor(config)
        
        assert "Unknown source type" in str(exc_info.value)
    
    def test_website_source_creation(self):
        """Test website source creation"""
        config = {
            'type': 'website',
            'website': {'url': 'https://example.com'}
        }
        
        ingestor = ContentIngestor(config)
        from src.website_crawler import WebsiteCrawler
        assert isinstance(ingestor.source, WebsiteCrawler)
    
    def test_cloud_source_creation(self):
        """Test cloud source creation"""
        config = {
            'type': 'cloud',
            'cloud': {
                'provider': 'google_drive',
                'folder_id': 'test'
            }
        }
        
        ingestor = ContentIngestor(config)
        from src.cloud_storage import GoogleDriveSource
        assert isinstance(ingestor.source, GoogleDriveSource)