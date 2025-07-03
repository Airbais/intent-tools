import networkx as nx
from urllib.parse import urlparse, urljoin
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from .crawler import CrawledPage
import re

@dataclass
class SiteSection:
    name: str
    pages: List[CrawledPage]
    url_pattern: str
    depth: int
    parent_section: Optional[str] = None
    subsections: List[str] = None

class SiteStructureAnalyzer:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.sections: Dict[str, SiteSection] = {}
        self.navigation_patterns = [
            r'nav', r'navigation', r'menu', r'header', r'navbar',
            r'sidebar', r'breadcrumb', r'sitemap'
        ]
    
    def _extract_url_hierarchy(self, url: str) -> List[str]:
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        
        if not path:
            return ['home']
        
        parts = path.split('/')
        hierarchy = ['home']
        
        for i, part in enumerate(parts):
            if part and part not in ['index.html', 'index.php', 'default.html']:
                hierarchy.append(part)
        
        return hierarchy
    
    def _detect_section_patterns(self, pages: List[CrawledPage]) -> Dict[str, List[str]]:
        section_patterns = {}
        
        for page in pages:
            hierarchy = self._extract_url_hierarchy(page.url)
            
            if len(hierarchy) > 1:
                section = hierarchy[1]
                if section not in section_patterns:
                    section_patterns[section] = []
                section_patterns[section].append(page.url)
        
        return section_patterns
    
    def _analyze_navigation_structure(self, pages: List[CrawledPage]) -> Dict[str, Set[str]]:
        navigation_links = {}
        
        for page in pages:
            page_links = set()
            
            for link in page.links:
                if self._is_internal_link(link, page.url):
                    page_links.add(link)
            
            navigation_links[page.url] = page_links
        
        return navigation_links
    
    def _is_internal_link(self, link: str, base_url: str) -> bool:
        link_domain = urlparse(link).netloc
        base_domain = urlparse(base_url).netloc
        return link_domain == base_domain
    
    def _calculate_page_importance(self, page: CrawledPage, all_pages: List[CrawledPage]) -> float:
        importance = 0.0
        
        url_depth = len(self._extract_url_hierarchy(page.url))
        importance += max(0, 5 - url_depth)
        
        inbound_links = sum(1 for p in all_pages if page.url in p.links)
        importance += inbound_links * 0.5
        
        if page.metadata and 'content_length' in page.metadata:
            content_length = page.metadata['content_length']
            importance += min(content_length / 1000, 3)
        
        url_keywords = ['about', 'contact', 'home', 'index', 'main', 'products', 'services']
        for keyword in url_keywords:
            if keyword in page.url.lower():
                importance += 1.0
                break
        
        return importance
    
    def _identify_main_sections(self, pages: List[CrawledPage]) -> Dict[str, SiteSection]:
        section_patterns = self._detect_section_patterns(pages)
        sections = {}
        
        for section_name, urls in section_patterns.items():
            section_pages = [p for p in pages if p.url in urls]
            
            if len(section_pages) >= 1:
                avg_depth = sum(len(self._extract_url_hierarchy(p.url)) for p in section_pages) / len(section_pages)
                
                url_pattern = f"/{section_name}/*"
                
                sections[section_name] = SiteSection(
                    name=section_name,
                    pages=section_pages,
                    url_pattern=url_pattern,
                    depth=int(avg_depth),
                    subsections=[]
                )
        
        home_pages = [p for p in pages if len(self._extract_url_hierarchy(p.url)) == 1]
        if home_pages:
            sections['home'] = SiteSection(
                name='home',
                pages=home_pages,
                url_pattern='/',
                depth=1,
                subsections=[]
            )
        
        return sections
    
    def _build_site_graph(self, pages: List[CrawledPage]) -> nx.DiGraph:
        graph = nx.DiGraph()
        
        for page in pages:
            importance = self._calculate_page_importance(page, pages)
            graph.add_node(page.url, 
                          title=page.title,
                          section=page.section,
                          importance=importance,
                          page=page)
        
        for page in pages:
            for link in page.links:
                if link in graph.nodes:
                    graph.add_edge(page.url, link)
        
        return graph
    
    def analyze_site_structure(self, pages: List[CrawledPage]) -> Dict[str, SiteSection]:
        if not pages:
            return {}
        
        self.graph = self._build_site_graph(pages)
        self.sections = self._identify_main_sections(pages)
        
        self._analyze_section_relationships()
        
        return self.sections
    
    def _analyze_section_relationships(self):
        for section_name, section in self.sections.items():
            if section.depth > 2:
                potential_parents = [
                    s for s in self.sections.values() 
                    if s.depth < section.depth and s.name != section_name
                ]
                
                if potential_parents:
                    closest_parent = min(potential_parents, key=lambda x: section.depth - x.depth)
                    section.parent_section = closest_parent.name
                    
                    if closest_parent.subsections is None:
                        closest_parent.subsections = []
                    closest_parent.subsections.append(section_name)
    
    def get_section_hierarchy(self) -> Dict[str, Dict]:
        hierarchy = {}
        
        for section_name, section in self.sections.items():
            hierarchy[section_name] = {
                'name': section.name,
                'page_count': len(section.pages),
                'depth': section.depth,
                'parent': section.parent_section,
                'subsections': section.subsections or [],
                'url_pattern': section.url_pattern,
                'importance': sum(
                    self.graph.nodes[p.url]['importance'] 
                    for p in section.pages 
                    if p.url in self.graph.nodes
                )
            }
        
        return hierarchy
    
    def get_navigation_map(self) -> Dict[str, List[str]]:
        nav_map = {}
        
        for section_name, section in self.sections.items():
            main_pages = sorted(
                section.pages,
                key=lambda p: self.graph.nodes[p.url]['importance'] if p.url in self.graph.nodes else 0,
                reverse=True
            )[:5]
            
            nav_map[section_name] = [
                {'url': p.url, 'title': p.title, 'importance': self.graph.nodes[p.url]['importance']}
                for p in main_pages if p.url in self.graph.nodes
            ]
        
        return nav_map
    
    def export_structure_data(self) -> Dict:
        return {
            'sections': self.get_section_hierarchy(),
            'navigation': self.get_navigation_map(),
            'total_pages': len(self.graph.nodes),
            'total_sections': len(self.sections),
            'graph_metrics': {
                'density': nx.density(self.graph),
                'average_clustering': nx.average_clustering(self.graph.to_undirected()),
                'number_of_components': nx.number_weakly_connected_components(self.graph)
            }
        }