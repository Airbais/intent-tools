from typing import List, Dict, Optional
from urllib.parse import urlparse
import os
from dataclasses import dataclass
from .crawler import CrawledPage
from .content_processor import ProcessedContent

@dataclass
class LLMSTXTSection:
    name: str
    pages: List[Dict[str, str]]
    description: Optional[str] = None

class LLMSTXTFormatter:
    def __init__(self, site_name: str, site_description: Optional[str] = None):
        self.site_name = site_name
        self.site_description = site_description
    
    def _get_site_name_from_url(self, url: str) -> str:
        domain = urlparse(url).netloc
        return domain.replace('www.', '').replace('.com', '').replace('.org', '').replace('.net', '').title()
    
    def _group_pages_by_section(self, pages: List[CrawledPage]) -> Dict[str, List[CrawledPage]]:
        sections = {}
        
        for page in pages:
            section = page.section or 'Main'
            if section not in sections:
                sections[section] = []
            sections[section].append(page)
        
        return sections
    
    def _create_page_entry(self, page: CrawledPage, processed_content: Optional[ProcessedContent] = None) -> Dict[str, str]:
        title = processed_content.title if processed_content else page.title
        summary = processed_content.summary if processed_content else ""
        
        if not title:
            title = page.url.split('/')[-1] or 'Page'
        
        entry = {
            'title': title,
            'url': page.url,
            'summary': summary
        }
        
        if processed_content and processed_content.keywords:
            entry['keywords'] = ', '.join(processed_content.keywords[:5])
        
        return entry
    
    def format_as_llmstxt(self, pages: List[CrawledPage], 
                         processed_contents: Dict[str, ProcessedContent] = None) -> str:
        if processed_contents is None:
            processed_contents = {}
        
        if not self.site_name and pages:
            self.site_name = self._get_site_name_from_url(pages[0].url)
        
        sections = self._group_pages_by_section(pages)
        
        llmstxt = f"# {self.site_name}\n\n"
        
        if self.site_description:
            llmstxt += f"> {self.site_description}\n\n"
        
        home_pages = sections.get('home', [])
        if home_pages:
            home_page = home_pages[0]
            processed = processed_contents.get(home_page.url)
            if processed and processed.summary:
                llmstxt += f"{processed.summary}\n\n"
        
        section_order = ['home', 'about', 'products', 'services', 'docs', 'blog', 'contact']
        ordered_sections = []
        
        for section_name in section_order:
            if section_name in sections:
                ordered_sections.append((section_name, sections[section_name]))
        
        for section_name, section_pages in sections.items():
            if section_name not in section_order:
                ordered_sections.append((section_name, section_pages))
        
        for section_name, section_pages in ordered_sections:
            if section_name == 'home' and len(section_pages) == 1:
                continue
            
            section_title = section_name.title().replace('_', ' ')
            llmstxt += f"## {section_title}\n\n"
            
            for page in section_pages[:10]:
                processed = processed_contents.get(page.url)
                entry = self._create_page_entry(page, processed)
                
                if entry['summary']:
                    llmstxt += f"- [{entry['title']}]({entry['url']}): {entry['summary']}\n"
                else:
                    llmstxt += f"- [{entry['title']}]({entry['url']})\n"
            
            llmstxt += "\n"
        
        return llmstxt.strip()
    
    def save_llmstxt(self, content: str, output_dir: str, filename: str = "llms.txt") -> str:
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filepath
    
    def create_section_files(self, pages: List[CrawledPage], 
                           processed_contents: Dict[str, ProcessedContent],
                           output_dir: str) -> Dict[str, str]:
        sections = self._group_pages_by_section(pages)
        section_files = {}
        
        pages_dir = os.path.join(output_dir, 'pages')
        os.makedirs(pages_dir, exist_ok=True)
        
        for section_name, section_pages in sections.items():
            section_content = f"# {section_name.title()}\n\n"
            
            for page in section_pages:
                processed = processed_contents.get(page.url)
                if processed:
                    section_content += f"## {processed.title}\n\n"
                    section_content += f"URL: {page.url}\n\n"
                    section_content += f"{processed.content}\n\n"
                    
                    if processed.keywords:
                        section_content += f"Keywords: {', '.join(processed.keywords)}\n\n"
                    
                    section_content += "---\n\n"
            
            filename = f"{section_name.lower().replace(' ', '_')}.txt"
            filepath = os.path.join(pages_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(section_content)
            
            section_files[section_name] = filepath
        
        return section_files