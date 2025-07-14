import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
import re
import time
from typing import Set, Dict, List, Optional, Tuple
from collections import deque
import logging
from tqdm import tqdm

logger = logging.getLogger(__name__)


class WebsiteCrawler:
    def __init__(self, config_manager):
        self.config = config_manager
        self.base_url = self.config.website_url
        self.domain = urlparse(self.base_url).netloc
        self.visited_urls: Set[str] = set()
        self.pages: Dict[str, Dict] = {}
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.config.user_agent})
        
    def crawl(self) -> Dict[str, Dict]:
        logger.info(f"Starting crawl of {self.base_url}")
        
        queue = deque([(self.base_url, 0)])
        pbar = tqdm(total=self.config.max_pages, desc="Crawling pages")
        
        while queue and len(self.visited_urls) < self.config.max_pages:
            url, depth = queue.popleft()
            
            if url in self.visited_urls or depth > self.config.max_depth:
                continue
            
            if not self._should_crawl_url(url):
                continue
            
            page_data = self._crawl_page(url, depth)
            if page_data:
                self.pages[url] = page_data
                self.visited_urls.add(url)
                pbar.update(1)
                
                # Add discovered links to queue
                for link in page_data.get('links', []):
                    if link not in self.visited_urls:
                        queue.append((link, depth + 1))
                
                # Respect crawl delay
                time.sleep(self.config.request_delay)
        
        pbar.close()
        logger.info(f"Crawl complete. Found {len(self.pages)} pages")
        return self.pages
    
    def _crawl_page(self, url: str, depth: int) -> Optional[Dict]:
        try:
            response = self.session.get(
                url, 
                timeout=self.config.request_timeout,
                verify=self.config.get('crawling.verify_ssl', True),
                allow_redirects=self.config.get('crawling.follow_redirects', True)
            )
            response.raise_for_status()
            
            # Check if content is HTML
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' not in content_type:
                return None
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Extract page data
            page_data = {
                'url': url,
                'depth': depth,
                'title': self._extract_title(soup),
                'description': self._extract_description(soup),
                'headings': self._extract_headings(soup),
                'links': self._extract_links(soup, url),
                'section': self._determine_section(url),
                'content_length': len(response.text),
                'meta': self._extract_meta(soup) if self.config.get('analysis.extract_meta', True) else {}
            }
            
            return page_data
            
        except Exception as e:
            logger.warning(f"Error crawling {url}: {str(e)}")
            return None
    
    def _should_crawl_url(self, url: str) -> bool:
        # Check if URL is within the same domain
        parsed = urlparse(url)
        if parsed.netloc != self.domain:
            return False
        
        # Check include patterns
        include_match = False
        for pattern in self.config.include_patterns:
            if re.match(pattern, url):
                include_match = True
                break
        
        if not include_match:
            return False
        
        # Check exclude patterns
        for pattern in self.config.exclude_patterns:
            if re.match(pattern, url):
                return False
        
        return True
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        # Try multiple sources for title
        title = soup.find('title')
        if title:
            return title.text.strip()
        
        h1 = soup.find('h1')
        if h1:
            return h1.text.strip()
        
        og_title = soup.find('meta', property='og:title')
        if og_title:
            return og_title.get('content', '').strip()
        
        return ''
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        # Try multiple sources for description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            return meta_desc.get('content', '').strip()
        
        og_desc = soup.find('meta', property='og:description')
        if og_desc:
            return og_desc.get('content', '').strip()
        
        # Try to get first paragraph
        p = soup.find('p')
        if p:
            return p.text.strip()[:200]
        
        return ''
    
    def _extract_headings(self, soup: BeautifulSoup) -> List[Dict]:
        headings = []
        if self.config.get('analysis.extract_headings', True):
            for tag in ['h1', 'h2', 'h3']:
                for heading in soup.find_all(tag):
                    headings.append({
                        'level': tag,
                        'text': heading.text.strip()
                    })
        return headings
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            # Convert relative URLs to absolute
            absolute_url = urljoin(base_url, href)
            # Remove fragments and query parameters for cleaner URLs
            parsed = urlparse(absolute_url)
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if self._should_crawl_url(clean_url):
                links.append(clean_url)
        return list(set(links))  # Remove duplicates
    
    def _extract_meta(self, soup: BeautifulSoup) -> Dict[str, str]:
        meta_data = {}
        
        # Extract common meta tags
        meta_tags = ['author', 'keywords', 'generator', 'robots']
        for tag in meta_tags:
            meta = soup.find('meta', attrs={'name': tag})
            if meta:
                meta_data[tag] = meta.get('content', '')
        
        # Extract Open Graph data
        og_tags = ['og:type', 'og:site_name', 'og:locale']
        for tag in og_tags:
            meta = soup.find('meta', property=tag)
            if meta:
                meta_data[tag] = meta.get('content', '')
        
        return meta_data
    
    def _determine_section(self, url: str) -> str:
        path = urlparse(url).path.lower()
        
        # Dynamic section detection based on URL structure
        # Split path into segments and look for meaningful section indicators
        segments = [s for s in path.split('/') if s]
        
        if not segments:
            return 'general'
        
        # Get ignored segments from config
        ignore_segments = self.config.get('generation.ignore_segments', ['p', 'c', 's', 'id', 'category', 'page'])
        
        # Look for the first meaningful segment that could be a section
        for i, segment in enumerate(segments):
            # Skip if it's in the ignore list
            if segment in ignore_segments:
                continue
            
            # Skip if it's numeric or looks like an ID
            if segment.isdigit() or len(segment) <= 2:
                continue
            
            # Skip if it contains file extensions
            if '.' in segment:
                continue
            
            # This looks like a meaningful section name
            # Common patterns: /help/something, /docs/something, /company/about
            if i == 0 or (i == 1 and segments[0] in ['en', 'fr', 'de', 'es']):  # Handle language prefixes
                return segment
        
        return 'general'