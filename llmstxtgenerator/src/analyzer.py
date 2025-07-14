import re
from typing import Dict, List, Tuple, Optional
from collections import defaultdict, Counter
import logging
from urllib.parse import urlparse
import openai
import anthropic
import os

logger = logging.getLogger(__name__)


class ContentAnalyzer:
    def __init__(self, config_manager):
        self.config = config_manager
        self.ai_client = None
        
        if self.config.use_ai_descriptions:
            self._initialize_ai_client()
    
    def _initialize_ai_client(self):
        model = self.config.ai_model
        if 'gpt' in model.lower():
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                self.ai_client = openai.OpenAI(api_key=api_key)
                self.ai_type = 'openai'
            else:
                logger.warning("OpenAI API key not found. AI descriptions will be disabled.")
                self.config.update('analysis.use_ai_descriptions', False)
        elif 'claude' in model.lower():
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key:
                self.ai_client = anthropic.Client(api_key=api_key)
                self.ai_type = 'anthropic'
            else:
                logger.warning("Anthropic API key not found. AI descriptions will be disabled.")
                self.config.update('analysis.use_ai_descriptions', False)
    
    def analyze_site_structure(self, pages: Dict[str, Dict]) -> Dict:
        logger.info("Analyzing site structure...")
        
        analysis = {
            'site_name': self._detect_site_name(pages),
            'site_description': self._detect_site_description(pages),
            'sections': self._organize_by_sections(pages),
            'key_pages': self._identify_key_pages(pages),
            'navigation_structure': self._analyze_navigation(pages),
            'content_categories': self._categorize_content(pages)
        }
        
        return analysis
    
    def _detect_site_name(self, pages: Dict[str, Dict]) -> str:
        # If configured, use it
        if self.config.website_name:
            return self.config.website_name
        
        # Try to detect from homepage
        homepage_url = self.config.website_url
        if homepage_url in pages:
            homepage = pages[homepage_url]
            
            # Try title
            if homepage.get('title'):
                # Clean common patterns
                title = homepage['title']
                title = re.sub(r'\s*[\-\|]\s*Home.*$', '', title)
                title = re.sub(r'^Home\s*[\-\|]\s*', '', title)
                return title.strip()
            
            # Try meta site name
            if homepage.get('meta', {}).get('og:site_name'):
                return homepage['meta']['og:site_name']
        
        # Fallback to domain name
        return urlparse(self.config.website_url).netloc
    
    def _detect_site_description(self, pages: Dict[str, Dict]) -> str:
        # If configured, use it
        if self.config.website_description:
            return self.config.website_description
        
        # Try to detect from homepage
        homepage_url = self.config.website_url
        if homepage_url in pages:
            homepage = pages[homepage_url]
            if homepage.get('description'):
                return homepage['description']
        
        # If AI is enabled, generate a description
        if self.config.use_ai_descriptions and self.ai_client:
            return self._generate_site_description(pages)
        
        return ""
    
    def _generate_site_description(self, pages: Dict[str, Dict]) -> str:
        # Gather context from top pages
        context_pages = list(pages.values())[:10]
        context = "\n".join([
            f"Page: {p['title']}\nDescription: {p.get('description', '')}"
            for p in context_pages
        ])
        
        prompt = f"""Based on these pages from the website, write a concise one-sentence description of what this website/project is about:

{context}

Description:"""
        
        try:
            if self.ai_type == 'openai':
                response = self.ai_client.chat.completions.create(
                    model=self.config.ai_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=100,
                    temperature=0.3
                )
                return response.choices[0].message.content.strip()
            elif self.ai_type == 'anthropic':
                response = self.ai_client.messages.create(
                    model=self.config.ai_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=100,
                    temperature=0.3
                )
                return response.content[0].text.strip()
        except Exception as e:
            logger.warning(f"Failed to generate AI description: {e}")
        
        return ""
    
    def _organize_by_sections(self, pages: Dict[str, Dict]) -> Dict[str, List[Dict]]:
        sections = defaultdict(list)
        
        # First, collect all pages by section
        for url, page in pages.items():
            section = page.get('section', 'general')
            sections[section].append({
                'url': url,
                'title': page.get('title', ''),
                'description': page.get('description', ''),
                'depth': page.get('depth', 0)
            })
        
        # Filter sections by minimum page count
        min_pages = self.config.get('generation.min_pages_per_section', 2)
        filtered_sections = {}
        
        for section, pages_list in sections.items():
            # Keep sections that meet the minimum page requirement
            # Always keep 'general' if it's the only section
            if len(pages_list) >= min_pages or (section == 'general' and len(sections) == 1):
                # Sort pages within section by depth and title
                pages_list.sort(key=lambda x: (x['depth'], x['title']))
                
                # Limit to max links per section
                max_links = self.config.max_links_per_section
                filtered_sections[section] = pages_list[:max_links]
        
        # If no sections meet the criteria, include top pages from general
        if not filtered_sections and 'general' in sections:
            general_pages = sections['general']
            general_pages.sort(key=lambda x: (x['depth'], x['title']))
            filtered_sections['general'] = general_pages[:self.config.max_links_per_section]
        
        return filtered_sections
    
    def _identify_key_pages(self, pages: Dict[str, Dict]) -> List[Dict]:
        # Identify important pages based on various criteria
        scored_pages = []
        
        for url, page in pages.items():
            score = 0
            
            # Homepage gets high score
            if url == self.config.website_url:
                score += 100
            
            # Low depth is good
            score += (5 - page.get('depth', 5)) * 10
            
            # Documentation sections are important
            if page.get('section') in ['docs', 'api', 'guides']:
                score += 20
            
            # Pages with many headings are likely comprehensive
            score += min(len(page.get('headings', [])), 10) * 2
            
            # Longer descriptions might indicate important pages
            if page.get('description'):
                score += min(len(page['description']) // 50, 10)
            
            scored_pages.append({
                'url': url,
                'title': page.get('title', ''),
                'description': page.get('description', ''),
                'section': page.get('section', 'general'),
                'score': score
            })
        
        # Sort by score and return top pages
        scored_pages.sort(key=lambda x: x['score'], reverse=True)
        return scored_pages[:20]
    
    def _analyze_navigation(self, pages: Dict[str, Dict]) -> Dict:
        # Analyze the navigation structure
        nav_structure = {
            'total_pages': len(pages),
            'max_depth_reached': max(p.get('depth', 0) for p in pages.values()),
            'sections_found': list(set(p.get('section', 'general') for p in pages.values())),
            'average_links_per_page': sum(len(p.get('links', [])) for p in pages.values()) / max(len(pages), 1)
        }
        
        return nav_structure
    
    def _categorize_content(self, pages: Dict[str, Dict]) -> Dict[str, int]:
        # Count pages by section
        categories = Counter()
        
        for page in pages.values():
            section = page.get('section', 'general')
            categories[section] += 1
        
        return dict(categories)
    
    def generate_link_descriptions(self, links: List[Dict], pages: Dict[str, Dict]) -> List[Dict]:
        # Generate or enhance descriptions for links
        enhanced_links = []
        
        for link in links:
            url = link['url']
            page = pages.get(url, {})
            
            # Use existing description or generate one
            if link.get('description'):
                description = link['description']
            elif page.get('description'):
                description = page['description']
            elif self.config.use_ai_descriptions and self.ai_client and page.get('title'):
                description = self._generate_link_description(page)
            else:
                description = ""
            
            enhanced_links.append({
                'url': url,
                'title': link.get('title', page.get('title', '')),
                'description': description
            })
        
        return enhanced_links
    
    def _generate_link_description(self, page: Dict) -> str:
        # Generate a brief description for a link
        prompt = f"""Write a very brief (5-10 words) description of what this page is about based on its title:

Title: {page.get('title', '')}
URL: {page.get('url', '')}

Description:"""
        
        try:
            if self.ai_type == 'openai':
                response = self.ai_client.chat.completions.create(
                    model=self.config.ai_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=20,
                    temperature=0.3
                )
                return response.choices[0].message.content.strip()
            elif self.ai_type == 'anthropic':
                response = self.ai_client.messages.create(
                    model=self.config.ai_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=20,
                    temperature=0.3
                )
                return response.content[0].text.strip()
        except Exception as e:
            logger.warning(f"Failed to generate AI link description: {e}")
        
        return ""