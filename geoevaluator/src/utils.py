"""
Utility functions for the GEO Evaluator
"""

import logging
import re
import urllib.parse
from typing import Optional, Dict, Any, List
from datetime import datetime
import requests
from pathlib import Path


def setup_logging(level: int = logging.INFO) -> None:
    """Setup logging configuration."""
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Reduce noise from external libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('chardet').setLevel(logging.WARNING)


def validate_url(url: str) -> Dict[str, Any]:
    """
    Validate and normalize a URL.
    
    Args:
        url: URL to validate
        
    Returns:
        Dict with validation results
    """
    
    result = {
        'valid': False,
        'url': url,
        'normalized_url': '',
        'errors': []
    }
    
    if not url:
        result['errors'].append("URL cannot be empty")
        return result
    
    # Add protocol if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    try:
        parsed = urllib.parse.urlparse(url)
        
        # Validate components
        if not parsed.netloc:
            result['errors'].append("Invalid domain")
            return result
        
        if not parsed.scheme in ('http', 'https'):
            result['errors'].append("Only HTTP and HTTPS schemes are supported")
            return result
        
        # Normalize URL
        normalized = urllib.parse.urlunparse((
            parsed.scheme,
            parsed.netloc.lower(),
            parsed.path or '/',
            parsed.params,
            parsed.query,
            ''  # Remove fragment
        ))
        
        result['valid'] = True
        result['normalized_url'] = normalized
        
    except Exception as e:
        result['errors'].append(f"URL parsing error: {str(e)}")
    
    return result


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urllib.parse.urlparse(url)
        return parsed.netloc.lower()
    except:
        return ''


def is_same_domain(url1: str, url2: str) -> bool:
    """Check if two URLs belong to the same domain."""
    return extract_domain(url1) == extract_domain(url2)


def normalize_path(path: str) -> str:
    """Normalize URL path for comparison."""
    if not path:
        return '/'
    
    # Remove trailing slash except for root
    if path != '/' and path.endswith('/'):
        path = path[:-1]
    
    return path


def create_timestamped_directory(base_path: str) -> Path:
    """Create a timestamped directory for results."""
    timestamp = datetime.now().strftime('%Y-%m-%d')
    result_dir = Path(base_path) / timestamp
    result_dir.mkdir(parents=True, exist_ok=True)
    return result_dir


def safe_filename(text: str, max_length: int = 50) -> str:
    """Create a safe filename from text."""
    # Remove or replace unsafe characters
    safe = re.sub(r'[^\w\-_.]', '_', text)
    # Remove multiple underscores
    safe = re.sub(r'_+', '_', safe)
    # Trim length
    if len(safe) > max_length:
        safe = safe[:max_length].rstrip('_')
    return safe


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def calculate_text_statistics(text: str) -> Dict[str, Any]:
    """Calculate basic text statistics."""
    if not text:
        return {
            'character_count': 0,
            'word_count': 0,
            'sentence_count': 0,
            'paragraph_count': 0,
            'avg_words_per_sentence': 0,
            'avg_chars_per_word': 0
        }
    
    # Clean text
    clean_text = re.sub(r'\s+', ' ', text.strip())
    
    # Count characters
    char_count = len(clean_text)
    
    # Count words
    words = clean_text.split()
    word_count = len(words)
    
    # Count sentences (basic approach)
    sentences = re.split(r'[.!?]+', clean_text)
    sentence_count = len([s for s in sentences if s.strip()])
    
    # Count paragraphs (double newlines in original text)
    paragraphs = text.split('\n\n')
    paragraph_count = len([p for p in paragraphs if p.strip()])
    
    # Calculate averages
    avg_words_per_sentence = word_count / sentence_count if sentence_count > 0 else 0
    avg_chars_per_word = char_count / word_count if word_count > 0 else 0
    
    return {
        'character_count': char_count,
        'word_count': word_count,
        'sentence_count': sentence_count,
        'paragraph_count': paragraph_count,
        'avg_words_per_sentence': round(avg_words_per_sentence, 2),
        'avg_chars_per_word': round(avg_chars_per_word, 2)
    }


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for text.
    Uses approximation: ~4 characters per token for English text.
    """
    if not text:
        return 0
    
    # Clean whitespace
    clean_text = re.sub(r'\s+', ' ', text.strip())
    char_count = len(clean_text)
    
    # Rough estimation: 4 characters per token
    estimated_tokens = char_count / 4
    
    return max(1, int(estimated_tokens))


def get_content_type_from_response(response: requests.Response) -> str:
    """Extract content type from HTTP response."""
    content_type = response.headers.get('content-type', '').lower()
    # Extract main type, ignore charset etc.
    return content_type.split(';')[0].strip()


def is_html_content(response: requests.Response) -> bool:
    """Check if HTTP response contains HTML content."""
    content_type = get_content_type_from_response(response)
    return 'text/html' in content_type


def clean_text_content(text: str) -> str:
    """Clean text content for analysis."""
    if not text:
        return ''
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove common non-content patterns
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)  # HTML comments
    text = re.sub(r'<script.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    return text.strip()


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to specified length with suffix."""
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    """Recursively merge two dictionaries."""
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result


def get_url_depth(url: str, base_url: str) -> int:
    """Calculate URL depth relative to base URL."""
    try:
        base_parsed = urllib.parse.urlparse(base_url)
        url_parsed = urllib.parse.urlparse(url)
        
        # Must be same domain
        if base_parsed.netloc != url_parsed.netloc:
            return -1
        
        base_path = base_parsed.path.strip('/')
        url_path = url_parsed.path.strip('/')
        
        if not url_path:
            return 0
        
        if not base_path:
            # Base is root, count segments in URL
            return len(url_path.split('/'))
        
        # URL must start with base path
        if not url_path.startswith(base_path):
            return -1
        
        # Count additional segments
        remaining = url_path[len(base_path):].strip('/')
        if not remaining:
            return 0
        
        return len(remaining.split('/'))
        
    except Exception:
        return -1


def format_duration(seconds: float) -> str:
    """Format duration in human readable format."""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.0f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"