"""
Web crawler for the GEO Evaluator
Handles website crawling, sitemap parsing, and content extraction
"""

import requests
import time
import logging
from urllib.parse import urljoin, urlparse, parse_qs
from urllib.robotparser import RobotFileParser
from typing import List, Dict, Any, Optional, Set, Tuple
from pathlib import Path
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import re
from datetime import datetime

from utils import (
    validate_url, extract_domain, is_same_domain, normalize_path,
    get_url_depth, is_html_content, clean_text_content, format_duration
)


class WebCrawler:
    """
    Web crawler that respects robots.txt, follows sitemaps, and extracts content.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.base_url = config['website']['url']
        self.max_pages = config['website']['max_pages']
        self.max_depth = config['website']['crawl_depth']
        self.excluded_paths = config['website']['excluded_paths']
        self.delay = config['crawling']['delay_seconds']
        self.timeout = config['crawling']['timeout_seconds']
        self.max_retries = config['crawling']['max_retries']
        self.user_agent = config['crawling']['user_agent']
        self.respect_robots = config['crawling']['respect_robots_txt']
        self.follow_sitemaps = config['crawling']['follow_sitemaps']
        self.max_file_size = config['crawling']['max_file_size_mb'] * 1024 * 1024
        
        # State
        self.domain = extract_domain(self.base_url)
        self.visited_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        self.robots_parser: Optional[RobotFileParser] = None
        
        # Statistics
        self.stats = {
            'pages_crawled': 0,
            'pages_failed': 0,
            'total_size_bytes': 0,
            'crawl_start_time': None,
            'crawl_duration': 0
        }
        
        # Setup session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
    
    def crawl(self) -> List[Dict[str, Any]]:
        """
        Main crawling method. Returns list of page data.
        """
        
        self.logger.info(f"Starting crawl of {self.base_url}")
        self.logger.info(f"Max pages: {self.max_pages}, Max depth: {self.max_depth}")
        
        self.stats['crawl_start_time'] = datetime.now()
        
        # Initialize robots.txt parser
        if self.respect_robots:
            self._load_robots_txt()
        
        # Discover URLs
        urls_to_crawl = self._discover_urls()
        
        if not urls_to_crawl:
            self.logger.warning("No URLs discovered for crawling")
            return []
        
        self.logger.info(f"Discovered {len(urls_to_crawl)} URLs to crawl")
        
        # Crawl pages
        pages = []
        
        for i, (url, depth) in enumerate(urls_to_crawl[:self.max_pages]):
            if self._should_stop_crawling():
                break
            
            self.logger.info(f"Crawling {i+1}/{min(len(urls_to_crawl), self.max_pages)}: {url}")
            
            page_data = self._crawl_page(url, depth)
            if page_data:
                pages.append(page_data)
                self.stats['pages_crawled'] += 1
            else:
                self.stats['pages_failed'] += 1
            
            # Respectful delay
            if i < len(urls_to_crawl) - 1:  # Don't delay after last page
                time.sleep(self.delay)
        
        # Calculate final stats
        self.stats['crawl_duration'] = (datetime.now() - self.stats['crawl_start_time']).total_seconds()
        
        self.logger.info(f"Crawl completed: {self.stats['pages_crawled']} pages crawled, "
                        f"{self.stats['pages_failed']} failed in {format_duration(self.stats['crawl_duration'])}")
        
        return pages
    
    def _discover_urls(self) -> List[Tuple[str, int]]:
        """Discover URLs to crawl from sitemaps and base URL."""
        
        urls = []
        
        # Start with base URL
        base_validation = validate_url(self.base_url)
        if base_validation['valid']:
            urls.append((base_validation['normalized_url'], 0))
        
        # Try to find URLs from sitemap
        if self.follow_sitemaps:
            sitemap_urls = self._discover_from_sitemap()
            for url in sitemap_urls:
                depth = get_url_depth(url, self.base_url)
                if depth >= 0 and depth <= self.max_depth:
                    urls.append((url, depth))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url, depth in urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append((url, depth))
        
        # Filter by robots.txt and exclusions
        filtered_urls = []
        for url, depth in unique_urls:
            if self._should_crawl_url(url):
                filtered_urls.append((url, depth))
            else:
                self.logger.debug(f"Skipping URL (robots.txt or exclusion): {url}")
        
        # Sort by depth and URL for consistent ordering
        filtered_urls.sort(key=lambda x: (x[1], x[0]))
        
        return filtered_urls
    
    def _discover_from_sitemap(self) -> List[str]:
        """Discover URLs from sitemap.xml."""
        
        urls = []
        
        # Common sitemap locations
        sitemap_urls = [
            urljoin(self.base_url, '/sitemap.xml'),
            urljoin(self.base_url, '/sitemap_index.xml'),
            urljoin(self.base_url, '/sitemap.txt')
        ]
        
        for sitemap_url in sitemap_urls:
            try:
                self.logger.debug(f"Checking sitemap: {sitemap_url}")
                
                response = self.session.get(sitemap_url, timeout=self.timeout)
                if response.status_code == 200:
                    if sitemap_url.endswith('.txt'):
                        # Plain text sitemap
                        sitemap_urls_found = self._parse_text_sitemap(response.text)
                    else:
                        # XML sitemap
                        sitemap_urls_found = self._parse_xml_sitemap(response.text)
                    
                    if sitemap_urls_found:
                        urls.extend(sitemap_urls_found)
                        self.logger.info(f"Found {len(sitemap_urls_found)} URLs in {sitemap_url}")
                        break  # Use first successful sitemap
                
            except Exception as e:
                self.logger.debug(f"Failed to fetch sitemap {sitemap_url}: {e}")
        
        # Filter to same domain and valid URLs
        valid_urls = []
        for url in urls:
            if is_same_domain(url, self.base_url):
                validation = validate_url(url)
                if validation['valid']:
                    valid_urls.append(validation['normalized_url'])
        
        return valid_urls
    
    def _parse_xml_sitemap(self, xml_content: str) -> List[str]:
        """Parse XML sitemap and extract URLs."""
        
        urls = []
        
        try:
            root = ET.fromstring(xml_content)
            
            # Handle sitemap index files
            for sitemap in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap'):
                loc_elem = sitemap.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                if loc_elem is not None and loc_elem.text:
                    # Recursively parse sub-sitemaps
                    sub_urls = self._fetch_and_parse_sitemap(loc_elem.text)
                    urls.extend(sub_urls)
            
            # Handle regular sitemap files
            for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                loc_elem = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                if loc_elem is not None and loc_elem.text:
                    urls.append(loc_elem.text.strip())
            
        except ET.ParseError as e:
            self.logger.debug(f"XML parsing error in sitemap: {e}")
        except Exception as e:
            self.logger.debug(f"Error parsing XML sitemap: {e}")
        
        return urls
    
    def _parse_text_sitemap(self, text_content: str) -> List[str]:
        """Parse plain text sitemap."""
        
        urls = []
        
        for line in text_content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                # Basic URL validation
                if line.startswith(('http://', 'https://')):
                    urls.append(line)
        
        return urls
    
    def _fetch_and_parse_sitemap(self, sitemap_url: str) -> List[str]:
        """Fetch and parse a sitemap file."""
        
        try:
            response = self.session.get(sitemap_url, timeout=self.timeout)
            if response.status_code == 200:
                if sitemap_url.endswith('.txt'):
                    return self._parse_text_sitemap(response.text)
                else:
                    return self._parse_xml_sitemap(response.text)
        except Exception as e:
            self.logger.debug(f"Failed to fetch sub-sitemap {sitemap_url}: {e}")
        
        return []
    
    def _load_robots_txt(self) -> None:
        """Load and parse robots.txt."""
        
        robots_url = urljoin(self.base_url, '/robots.txt')
        
        try:
            self.robots_parser = RobotFileParser()
            self.robots_parser.set_url(robots_url)
            self.robots_parser.read()
            self.logger.debug(f"Loaded robots.txt from {robots_url}")
            
        except Exception as e:
            self.logger.debug(f"Failed to load robots.txt: {e}")
            self.robots_parser = None
    
    def _should_crawl_url(self, url: str) -> bool:
        """Check if URL should be crawled based on robots.txt and exclusions."""
        
        # Check same domain
        if not is_same_domain(url, self.base_url):
            return False
        
        # Check robots.txt
        if self.robots_parser:
            if not self.robots_parser.can_fetch(self.user_agent, url):
                return False
        
        # Check excluded paths
        parsed = urlparse(url)
        path = parsed.path
        
        for excluded in self.excluded_paths:
            if path.startswith(excluded):
                return False
        
        # Check file extensions (exclude common non-HTML files)
        excluded_extensions = [
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.zip', '.tar', '.gz', '.rar', '.7z',
            '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp',
            '.mp3', '.mp4', '.avi', '.mov', '.wmv',
            '.css', '.js', '.json', '.xml', '.txt'
        ]
        
        for ext in excluded_extensions:
            if path.lower().endswith(ext):
                return False
        
        return True
    
    def _should_stop_crawling(self) -> bool:
        """Check if crawling should be stopped."""
        
        # Check if we've hit max pages
        if self.stats['pages_crawled'] >= self.max_pages:
            return True
        
        # Check if too many failures
        total_attempts = self.stats['pages_crawled'] + self.stats['pages_failed']
        if total_attempts > 0:
            failure_rate = self.stats['pages_failed'] / total_attempts
            if failure_rate > 0.5 and total_attempts > 10:  # Stop if >50% failure rate after 10 attempts
                self.logger.warning(f"High failure rate ({failure_rate:.1%}), stopping crawl")
                return True
        
        return False
    
    def _crawl_page(self, url: str, depth: int) -> Optional[Dict[str, Any]]:
        """Crawl a single page and extract content."""
        
        if url in self.visited_urls:
            return None
        
        self.visited_urls.add(url)
        
        try:
            # Make request with retries
            response = None
            last_error = None
            
            for attempt in range(self.max_retries + 1):
                try:
                    response = self.session.get(
                        url,
                        timeout=self.timeout,
                        stream=True  # Stream to check content size
                    )
                    
                    # Check content size
                    content_length = response.headers.get('content-length')
                    if content_length and int(content_length) > self.max_file_size:
                        self.logger.warning(f"Page too large ({content_length} bytes): {url}")
                        return None
                    
                    # Download content with size check
                    content = b''
                    for chunk in response.iter_content(chunk_size=8192):
                        content += chunk
                        if len(content) > self.max_file_size:
                            self.logger.warning(f"Page too large (>{self.max_file_size} bytes): {url}")
                            return None
                    
                    response._content = content
                    break
                    
                except Exception as e:
                    last_error = e
                    if attempt < self.max_retries:
                        self.logger.debug(f"Retry {attempt + 1} for {url}: {e}")
                        time.sleep(1)  # Brief delay before retry
            
            if not response:
                self.logger.warning(f"Failed to fetch {url}: {last_error}")
                self.failed_urls.add(url)
                return None
            
            # Check response
            if response.status_code != 200:
                self.logger.warning(f"HTTP {response.status_code} for {url}")
                self.failed_urls.add(url)
                return None
            
            # Check content type
            if not is_html_content(response):
                self.logger.debug(f"Non-HTML content for {url}")
                return None
            
            # Update stats
            self.stats['total_size_bytes'] += len(response.content)
            
            # Parse content
            return self._extract_page_data(url, response.text, depth)
            
        except Exception as e:
            self.logger.warning(f"Error crawling {url}: {e}")
            self.failed_urls.add(url)
            return None
    
    def _extract_page_data(self, url: str, html_content: str, depth: int) -> Dict[str, Any]:
        """Extract relevant data from HTML page."""
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Basic page information
            title = ''
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text().strip()
            
            # Meta description
            description = ''
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                description = meta_desc.get('content', '').strip()
            
            # Extract text content
            # Remove script and style elements
            for script in soup(['script', 'style', 'noscript']):
                script.decompose()
            
            # Get main content areas
            main_content = ''
            for selector in ['main', 'article', '.content', '#content', '.main', '#main']:
                main_elem = soup.select_one(selector)
                if main_elem:
                    main_content = main_elem.get_text()
                    break
            
            # Fallback to body content
            if not main_content:
                body = soup.find('body')
                if body:
                    main_content = body.get_text()
            
            # Clean content
            main_content = clean_text_content(main_content)
            
            # Extract headings
            headings = []
            for i in range(1, 7):
                for heading in soup.find_all(f'h{i}'):
                    headings.append({
                        'level': i,
                        'text': heading.get_text().strip(),
                        'id': heading.get('id', ''),
                        'class': heading.get('class', [])
                    })
            
            # Extract links
            links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                absolute_url = urljoin(url, href)
                
                # Only include same-domain links
                if is_same_domain(absolute_url, self.base_url):
                    links.append({
                        'url': absolute_url,
                        'text': link.get_text().strip(),
                        'title': link.get('title', ''),
                        'rel': link.get('rel', [])
                    })
            
            # Extract images
            images = []
            for img in soup.find_all('img'):
                src = img.get('src', '')
                if src:
                    images.append({
                        'src': urljoin(url, src),
                        'alt': img.get('alt', ''),
                        'title': img.get('title', ''),
                        'width': img.get('width', ''),
                        'height': img.get('height', '')
                    })
            
            # Check for structured data
            structured_data = []
            
            # JSON-LD
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    import json
                    data = json.loads(script.string or '')
                    structured_data.append({
                        'type': 'json-ld',
                        'data': data
                    })
                except:
                    pass
            
            # Microdata and RDFa would require more complex parsing
            # For now, just detect presence
            has_microdata = bool(soup.find(attrs={'itemscope': True}))
            has_rdfa = bool(soup.find(attrs={'property': True}))
            
            if has_microdata:
                structured_data.append({'type': 'microdata', 'detected': True})
            if has_rdfa:
                structured_data.append({'type': 'rdfa', 'detected': True})
            
            # Page data
            page_data = {
                'url': url,
                'title': title,
                'description': description,
                'content': main_content,
                'headings': headings,
                'links': links,
                'images': images,
                'structured_data': structured_data,
                'depth': depth,
                'html_size': len(html_content),
                'content_size': len(main_content),
                'crawled_at': datetime.now().isoformat(),
                'raw_html': html_content  # Keep for detailed analysis
            }
            
            return page_data
            
        except Exception as e:
            self.logger.error(f"Error extracting data from {url}: {e}")
            return None
    
    def get_crawl_stats(self) -> Dict[str, Any]:
        """Get crawling statistics."""
        return self.stats.copy()