"""Content ingestion module for multiple sources"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import mimetypes
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


class ContentItem:
    """Represents a single piece of content"""
    
    def __init__(self, content: str, metadata: Dict[str, Any]):
        self.content = content
        self.metadata = metadata
        self.id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Generate unique ID for content item"""
        source = self.metadata.get('source', '')
        path = self.metadata.get('path', '')
        content_hash = hashlib.md5(self.content.encode()).hexdigest()[:8]
        return f"{source}_{path}_{content_hash}".replace('/', '_')


class ContentSource(ABC):
    """Abstract base class for content sources"""
    
    @abstractmethod
    def ingest(self) -> List[ContentItem]:
        """Ingest content from source"""
        pass
    
    @abstractmethod
    def validate_config(self) -> Tuple[bool, List[str]]:
        """Validate source configuration"""
        pass


class ContentProcessor:
    """Process different content formats"""
    
    @staticmethod
    def process_text(content: str, file_type: str) -> str:
        """Process text content based on file type"""
        # For now, return as-is. Will add format-specific processing later
        return content.strip()
    
    @staticmethod
    def process_markdown(content: str) -> str:
        """Process markdown content"""
        import markdown2
        # Convert to plain text for RAG
        html = markdown2.markdown(content)
        # Simple HTML to text conversion
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        return soup.get_text().strip()
    
    @staticmethod
    def process_html(content: str) -> str:
        """Process HTML content"""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        
        # Break into lines and remove leading/trailing space
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    
    @staticmethod
    def process_json(content: str) -> str:
        """Process JSON content"""
        import json
        try:
            data = json.loads(content)
            # Convert to readable text format
            return json.dumps(data, indent=2)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON content, treating as text")
            return content
    
    @staticmethod
    def process_csv(content: str) -> str:
        """Process CSV content"""
        import csv
        import io
        
        reader = csv.reader(io.StringIO(content))
        lines = []
        
        try:
            headers = next(reader)
            lines.append("Headers: " + ", ".join(headers))
            
            for row in reader:
                lines.append(" | ".join(row))
        except:
            # If CSV parsing fails, return as-is
            return content
        
        return "\n".join(lines)
    
    @staticmethod
    def process_docx(file_path: str) -> str:
        """Process DOCX content"""
        try:
            from docx import Document
            doc = Document(file_path)
            
            full_text = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    full_text.append(paragraph.text)
            
            return '\n'.join(full_text)
        except Exception as e:
            logger.error(f"Error processing DOCX: {e}")
            return ""
    
    @staticmethod
    def process_pdf(file_path: str) -> str:
        """Process PDF content"""
        try:
            import PyPDF2
            
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = []
                
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text.append(page.extract_text())
                
                return '\n'.join(text)
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            return ""


class LocalFileSource(ContentSource):
    """Ingest content from local files"""
    
    def __init__(self, config: Dict[str, Any]):
        self.base_path = Path(config.get('path', '.'))
        self.recursive = config.get('recursive', True)
        self.max_depth = config.get('max_depth', 5)
        self.file_patterns = config.get('file_patterns', ['*.txt', '*.md', '*.html'])
        self.processor = ContentProcessor()
    
    def validate_config(self) -> Tuple[bool, List[str]]:
        """Validate local source configuration"""
        errors = []
        
        if not self.base_path.exists():
            errors.append(f"Path does not exist: {self.base_path}")
        elif not self.base_path.is_dir():
            errors.append(f"Path is not a directory: {self.base_path}")
        
        if self.max_depth < 1:
            errors.append("max_depth must be at least 1")
        
        if not self.file_patterns:
            errors.append("No file patterns specified")
        
        return len(errors) == 0, errors
    
    def ingest(self) -> List[ContentItem]:
        """Ingest content from local files"""
        items = []
        processed_files = 0
        
        logger.info(f"Ingesting from local path: {self.base_path}")
        
        for pattern in self.file_patterns:
            if self.recursive:
                files = self._find_files_recursive(pattern)
            else:
                files = list(self.base_path.glob(pattern))
            
            for file_path in files:
                try:
                    content = self._process_file(file_path)
                    if content:
                        metadata = {
                            'source': 'local',
                            'path': str(file_path.relative_to(self.base_path)),
                            'full_path': str(file_path),
                            'file_type': file_path.suffix.lower(),
                            'size': file_path.stat().st_size,
                            'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                            'ingested_at': datetime.now().isoformat()
                        }
                        
                        items.append(ContentItem(content, metadata))
                        processed_files += 1
                        
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {e}")
        
        logger.info(f"Processed {processed_files} files, extracted {len(items)} content items")
        return items
    
    def _find_files_recursive(self, pattern: str) -> List[Path]:
        """Find files recursively up to max_depth"""
        files = []
        
        def _walk_level(path: Path, level: int):
            if level > self.max_depth:
                return
            
            try:
                for item in path.iterdir():
                    if item.is_file() and item.match(pattern):
                        files.append(item)
                    elif item.is_dir() and not item.name.startswith('.'):
                        _walk_level(item, level + 1)
            except PermissionError:
                logger.warning(f"Permission denied: {path}")
        
        _walk_level(self.base_path, 1)
        return files
    
    def _process_file(self, file_path: Path) -> Optional[str]:
        """Process a single file based on its type"""
        file_type = file_path.suffix.lower()
        
        try:
            if file_type in ['.docx']:
                return self.processor.process_docx(str(file_path))
            elif file_type in ['.pdf']:
                return self.processor.process_pdf(str(file_path))
            else:
                # Text-based files
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if file_type == '.md':
                    return self.processor.process_markdown(content)
                elif file_type in ['.html', '.htm']:
                    return self.processor.process_html(content)
                elif file_type == '.json':
                    return self.processor.process_json(content)
                elif file_type == '.csv':
                    return self.processor.process_csv(content)
                else:
                    return self.processor.process_text(content, file_type)
                    
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return None


class ContentIngestor:
    """Main content ingestion orchestrator"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.source_type = config.get('type', 'local')
        self.source = self._create_source()
    
    def _create_source(self) -> ContentSource:
        """Create appropriate content source"""
        if self.source_type == 'local':
            return LocalFileSource(self.config.get('local', {}))
        elif self.source_type == 'website':
            from .website_crawler import WebsiteCrawler
            # Config is already flattened by get_content_config()
            website_config = {k: v for k, v in self.config.items() if k != 'type'}
            return WebsiteCrawler(website_config)
        elif self.source_type == 'cloud':
            cloud_config = self.config.get('cloud', {})
            provider = cloud_config.get('provider', 'google_drive')
            
            if provider == 'google_drive':
                from .cloud_storage import GoogleDriveSource
                return GoogleDriveSource(cloud_config)
            elif provider == 'onedrive':
                from .cloud_storage import OneDriveSource
                return OneDriveSource(cloud_config)
            elif provider == 'dropbox':
                from .cloud_storage import DropboxSource
                return DropboxSource(cloud_config)
            else:
                raise ValueError(f"Unknown cloud provider: {provider}")
        else:
            raise ValueError(f"Unknown source type: {self.source_type}")
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate content source configuration"""
        return self.source.validate_config()
    
    def ingest(self) -> List[ContentItem]:
        """Ingest content from configured source"""
        logger.info(f"Starting content ingestion from {self.source_type} source")
        
        is_valid, errors = self.validate()
        if not is_valid:
            raise ValueError(f"Invalid configuration: {errors}")
        
        items = self.source.ingest()
        logger.info(f"Ingestion complete. Retrieved {len(items)} content items")
        
        return items