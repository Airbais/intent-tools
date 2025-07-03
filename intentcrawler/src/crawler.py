import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
import time
from typing import List, Set, Dict, Optional
from dataclasses import dataclass
import logging
import xml.etree.ElementTree as ET

@dataclass
class CrawledPage:
    url: str
    title: str
    content: str
    links: List[str]
    section: Optional[str] = None
    metadata: Dict = None
    raw_html: Optional[str] = None

class WebCrawler:
    def __init__(self, base_url: str, max_pages: int = 1000, rate_limit: float = 2.0, 
                 respect_robots: bool = True, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.domain = urlparse(base_url).netloc
        self.max_pages = max_pages
        self.rate_limit = rate_limit
        self.respect_robots = respect_robots
        self.timeout = timeout
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'IntentCrawler/1.0 (Website Intent Analysis Tool)'
        })
        
        self.visited_urls: Set[str] = set()
        self.pages: List[CrawledPage] = []
        self.robots_parser = None
        
        self.logger = logging.getLogger(__name__)
        
        if respect_robots:
            self._load_robots_txt()
    
    def _load_robots_txt(self):
        try:
            robots_url = urljoin(self.base_url, '/robots.txt')
            self.robots_parser = RobotFileParser()
            self.robots_parser.set_url(robots_url)
            self.robots_parser.read()
        except Exception as e:
            self.logger.warning(f"Could not load robots.txt: {e}")
            self.robots_parser = None
    
    def _can_fetch(self, url: str) -> bool:
        if not self.robots_parser:
            return True
        return self.robots_parser.can_fetch(self.session.headers['User-Agent'], url)
    
    def _is_same_domain(self, url: str) -> bool:
        return urlparse(url).netloc == self.domain
    
    def _normalize_url(self, url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
        if main_content:
            return main_content.get_text(strip=True, separator=' ')
        
        return soup.get_text(strip=True, separator=' ')
    
    def _extract_links(self, soup: BeautifulSoup, current_url: str) -> List[str]:
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(current_url, href)
            normalized_url = self._normalize_url(full_url)
            
            if (self._is_same_domain(normalized_url) and 
                normalized_url not in self.visited_urls and
                not href.startswith('#') and
                not href.startswith('mailto:') and
                not href.startswith('tel:')):
                links.append(normalized_url)
        
        return links
    
    def _get_page_section(self, url: str, soup: BeautifulSoup) -> Optional[str]:
        path = urlparse(url).path.strip('/')
        if not path:
            return 'home'
        
        path_parts = path.split('/')
        if path_parts:
            return path_parts[0]
        
        return None
    
    def _parse_sitemap(self, sitemap_url: str) -> List[str]:
        """Parse XML sitemap and extract URLs"""
        urls = []
        try:
            response = self.session.get(sitemap_url, timeout=self.timeout)
            response.raise_for_status()
            
            # Parse XML
            root = ET.fromstring(response.content)
            
            # Handle both regular sitemaps and sitemap index files
            namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            # Check if this is a sitemap index
            sitemap_tags = root.findall('ns:sitemap', namespace)
            if sitemap_tags:
                # This is a sitemap index, recursively parse each sitemap
                for sitemap in sitemap_tags:
                    loc = sitemap.find('ns:loc', namespace)
                    if loc is not None and loc.text:
                        self.logger.info(f"Found sub-sitemap: {loc.text}")
                        urls.extend(self._parse_sitemap(loc.text))
            else:
                # Regular sitemap with URLs
                url_tags = root.findall('ns:url', namespace)
                for url_tag in url_tags:
                    loc = url_tag.find('ns:loc', namespace)
                    if loc is not None and loc.text:
                        normalized_url = self._normalize_url(loc.text)
                        if self._is_same_domain(normalized_url):
                            urls.append(normalized_url)
                
                self.logger.info(f"Found {len(urls)} URLs in sitemap {sitemap_url}")
            
        except Exception as e:
            self.logger.warning(f"Could not parse sitemap {sitemap_url}: {e}")
        
        return urls
    
    def _discover_urls(self) -> List[str]:
        """Discover URLs from sitemap.xml and robots.txt"""
        discovered_urls = []
        
        # Try sitemap.xml
        sitemap_url = urljoin(self.base_url, '/sitemap.xml')
        self.logger.info(f"Checking for sitemap at {sitemap_url}")
        sitemap_urls = self._parse_sitemap(sitemap_url)
        discovered_urls.extend(sitemap_urls)
        
        # Check robots.txt for additional sitemaps
        if self.robots_parser:
            try:
                # Get sitemap URLs from robots.txt
                robots_content = self.session.get(urljoin(self.base_url, '/robots.txt')).text
                for line in robots_content.split('\n'):
                    if line.lower().startswith('sitemap:'):
                        sitemap_url = line.split(':', 1)[1].strip()
                        self.logger.info(f"Found sitemap in robots.txt: {sitemap_url}")
                        discovered_urls.extend(self._parse_sitemap(sitemap_url))
            except Exception as e:
                self.logger.warning(f"Could not check robots.txt for sitemaps: {e}")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in discovered_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
        
        self.logger.info(f"Discovered {len(unique_urls)} unique URLs from sitemaps")
        return unique_urls
    
    def crawl_page(self, url: str) -> Optional[CrawledPage]:
        if not self._can_fetch(url):
            self.logger.info(f"Robots.txt disallows crawling: {url}")
            return None
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            title = soup.find('title')
            title_text = title.get_text(strip=True) if title else url
            
            content = self._extract_content(soup)
            links = self._extract_links(soup, url)
            section = self._get_page_section(url, soup)
            
            metadata = {
                'status_code': response.status_code,
                'content_type': response.headers.get('content-type', ''),
                'last_modified': response.headers.get('last-modified', ''),
                'content_length': len(content)
            }
            
            return CrawledPage(
                url=url,
                title=title_text,
                content=content,
                links=links,
                section=section,
                metadata=metadata,
                raw_html=response.text
            )
            
        except Exception as e:
            self.logger.error(f"Error crawling {url}: {e}")
            return None
    
    def crawl(self, start_url: Optional[str] = None, use_sitemap: bool = True) -> List[CrawledPage]:
        if start_url is None:
            start_url = self.base_url
        
        urls_to_visit = []
        
        # Discover URLs from sitemap first if enabled
        if use_sitemap:
            sitemap_urls = self._discover_urls()
            if sitemap_urls:
                self.logger.info(f"Starting with {len(sitemap_urls)} URLs from sitemap")
                urls_to_visit.extend(sitemap_urls)
            else:
                self.logger.info("No sitemap found, falling back to regular crawling")
                urls_to_visit.append(start_url)
        else:
            urls_to_visit.append(start_url)
        
        # Crawl discovered URLs
        while urls_to_visit and len(self.visited_urls) < self.max_pages:
            current_url = urls_to_visit.pop(0)
            
            if current_url in self.visited_urls:
                continue
            
            self.visited_urls.add(current_url)
            self.logger.info(f"Crawling: {current_url} ({len(self.visited_urls)}/{self.max_pages})")
            
            page = self.crawl_page(current_url)
            if page and len(page.content) > 100:
                self.pages.append(page)
                
                # Only add discovered links if we're not using sitemap
                # or if we've visited all sitemap URLs
                if not use_sitemap or len(urls_to_visit) < 10:
                    urls_to_visit.extend(page.links)
            
            time.sleep(1.0 / self.rate_limit)
        
        self.logger.info(f"Crawled {len(self.pages)} pages out of {len(self.visited_urls)} visited")
        return self.pages