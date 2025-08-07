"""Website crawler for content ingestion"""

import logging
import httpx
from typing import List, Dict, Any, Set, Optional, Tuple
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser
import time
from bs4 import BeautifulSoup
import hashlib
from datetime import datetime

from .content_ingestor import ContentSource, ContentItem, ContentProcessor

logger = logging.getLogger(__name__)


class WebsiteCrawler(ContentSource):
    """Crawl and ingest content from websites"""
    
    def __init__(self, config: Dict[str, Any]):
        logger.debug(f"WebsiteCrawler received config: {config}")
        self.start_url = config.get('url', '')
        logger.debug(f"WebsiteCrawler start_url: {self.start_url}")
        self.max_pages = config.get('max_pages', 50)
        self.crawl_depth = config.get('crawl_depth', 3)
        self.respect_robots = config.get('respect_robots', True)
        self.delay = config.get('delay_between_requests', 1.0)
        
        self.visited_urls: Set[str] = set()
        self.robot_parser: Optional[RobotFileParser] = None
        self.processor = ContentProcessor()
        self.base_domain = urlparse(self.start_url).netloc
        
        # HTTP client with timeout
        self.client = httpx.Client(
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
            headers={
                'User-Agent': 'RulesEvaluator/1.0 (compatible; Airbais bot)'
            }
        )
    
    def validate_config(self) -> Tuple[bool, List[str]]:
        """Validate website crawler configuration"""
        errors = []
        
        if not self.start_url:
            errors.append("No URL specified")
        else:
            parsed = urlparse(self.start_url)
            if not parsed.scheme or not parsed.netloc:
                errors.append(f"Invalid URL: {self.start_url}")
        
        if self.max_pages < 1:
            errors.append("max_pages must be at least 1")
        
        if self.crawl_depth < 1:
            errors.append("crawl_depth must be at least 1")
        
        if self.delay < 0:
            errors.append("delay_between_requests cannot be negative")
        
        return len(errors) == 0, errors
    
    def ingest(self) -> List[ContentItem]:
        """Crawl website and ingest content"""
        items = []
        
        logger.info(f"Starting website crawl from: {self.start_url}")
        
        # Initialize robots.txt parser
        if self.respect_robots:
            self._init_robots_parser()
        
        # Start crawling
        to_visit = [(self.start_url, 0)]  # (url, depth)
        
        while to_visit and len(self.visited_urls) < self.max_pages:
            url, depth = to_visit.pop(0)
            
            if url in self.visited_urls:
                continue
            
            if not self._can_fetch(url):
                logger.debug(f"Robots.txt disallows: {url}")
                continue
            
            # Crawl the page
            content_item, new_urls = self._crawl_page(url)
            
            if content_item:
                items.append(content_item)
                self.visited_urls.add(url)
                
                # Add new URLs if within depth limit
                if depth < self.crawl_depth:
                    for new_url in new_urls:
                        if new_url not in self.visited_urls:
                            to_visit.append((new_url, depth + 1))
                
                # Respect crawl delay
                if self.delay > 0:
                    time.sleep(self.delay)
        
        logger.info(f"Crawled {len(self.visited_urls)} pages, extracted {len(items)} content items")
        return items
    
    def _init_robots_parser(self) -> None:
        """Initialize robots.txt parser"""
        try:
            robots_url = urljoin(self.start_url, '/robots.txt')
            self.robot_parser = RobotFileParser()
            self.robot_parser.set_url(robots_url)
            self.robot_parser.read()
            logger.debug(f"Loaded robots.txt from {robots_url}")
        except Exception as e:
            logger.warning(f"Failed to load robots.txt: {e}")
            self.robot_parser = None
    
    def _can_fetch(self, url: str) -> bool:
        """Check if URL can be fetched according to robots.txt"""
        if not self.respect_robots or not self.robot_parser:
            return True
        
        try:
            return self.robot_parser.can_fetch('RulesEvaluator', url)
        except:
            return True
    
    def _crawl_page(self, url: str) -> Tuple[Optional[ContentItem], List[str]]:
        """Crawl a single page and extract content + links"""
        try:
            logger.debug(f"Crawling: {url}")
            response = self.client.get(url)
            
            if response.status_code != 200:
                logger.warning(f"HTTP {response.status_code} for {url}")
                return None, []
            
            # Check content type
            content_type = response.headers.get('content-type', '')
            if 'text/html' not in content_type:
                logger.debug(f"Skipping non-HTML content: {content_type}")
                return None, []
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract text content
            text_content = self.processor.process_html(response.text)
            
            if not text_content or len(text_content.strip()) < 100:
                logger.debug(f"Insufficient content on {url}")
                return None, []
            
            # Extract metadata
            title = soup.find('title')
            title_text = title.text.strip() if title else ''
            
            description = ''
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                description = meta_desc.get('content', '')
            
            # Create content item
            metadata = {
                'source': 'website',
                'url': url,
                'title': title_text,
                'description': description,
                'content_type': content_type,
                'crawled_at': datetime.now().isoformat(),
                'content_length': len(text_content)
            }
            
            content_item = ContentItem(text_content, metadata)
            
            # Extract links
            new_urls = self._extract_links(soup, url)
            
            return content_item, new_urls
            
        except Exception as e:
            logger.error(f"Error crawling {url}: {e}")
            return None, []
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract and filter links from page"""
        links = []
        
        for tag in soup.find_all(['a', 'link']):
            href = tag.get('href')
            if not href:
                continue
            
            # Make absolute URL
            absolute_url = urljoin(base_url, href)
            
            # Parse and clean URL
            parsed = urlparse(absolute_url)
            
            # Skip non-HTTP(S) URLs
            if parsed.scheme not in ['http', 'https']:
                continue
            
            # Skip external domains if configured
            if parsed.netloc != self.base_domain:
                continue
            
            # Remove fragment
            clean_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                ''
            ))
            
            # Skip certain file types
            if any(parsed.path.endswith(ext) for ext in ['.pdf', '.jpg', '.png', '.gif', '.zip']):
                continue
            
            links.append(clean_url)
        
        return list(set(links))  # Remove duplicates
    
    def __del__(self):
        """Clean up HTTP client"""
        if hasattr(self, 'client'):
            self.client.close()