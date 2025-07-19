"""
Content extraction and cleaning utilities
"""

import re
from bs4 import BeautifulSoup, Comment
from typing import List, Optional


class ContentExtractor:
    """Extract and clean content from HTML"""
    
    def __init__(self):
        self.unwanted_tags = [
            'script', 'style', 'nav', 'footer', 'header', 
            'aside', 'noscript', 'iframe', 'object', 'embed'
        ]
    
    def extract_text(self, html: str) -> str:
        """Extract clean text content from HTML"""
        if not html:
            return ""
        
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # Remove unwanted elements
            self._remove_unwanted_elements(soup)
            
            # Extract text
            text = soup.get_text(separator=' ', strip=True)
            
            # Clean up whitespace
            text = self._clean_whitespace(text)
            
            return text
            
        except Exception as e:
            # Fallback to simple text extraction
            return self._simple_text_extraction(html)
    
    def _remove_unwanted_elements(self, soup: BeautifulSoup):
        """Remove unwanted HTML elements"""
        # Remove unwanted tags
        for tag_name in self.unwanted_tags:
            for tag in soup.find_all(tag_name):
                tag.decompose()
        
        # Remove comments
        for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
            comment.extract()
        
        # Remove hidden elements
        for element in soup.find_all(attrs={'style': re.compile(r'display\s*:\s*none')}):
            element.decompose()
    
    def _clean_whitespace(self, text: str) -> str:
        """Clean up whitespace in text"""
        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def _simple_text_extraction(self, html: str) -> str:
        """Simple fallback text extraction"""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html)
        
        # Clean up whitespace
        text = self._clean_whitespace(text)
        
        return text
    
    def extract_main_content(self, html: str) -> str:
        """Extract main content area from HTML"""
        if not html:
            return ""
        
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # Look for main content indicators
            main_selectors = [
                'main',
                '[role="main"]',
                '.main-content',
                '.content',
                '.post-content',
                '.entry-content',
                'article',
                '.article-content'
            ]
            
            for selector in main_selectors:
                main_element = soup.select_one(selector)
                if main_element:
                    # Remove unwanted elements from main content
                    self._remove_unwanted_elements(main_element)
                    text = main_element.get_text(separator=' ', strip=True)
                    return self._clean_whitespace(text)
            
            # Fallback to full page content
            return self.extract_text(html)
            
        except Exception:
            return self.extract_text(html)
    
    def extract_headings(self, html: str) -> List[dict]:
        """Extract headings with their levels"""
        if not html:
            return []
        
        try:
            soup = BeautifulSoup(html, 'lxml')
            headings = []
            
            for level in range(1, 7):  # h1 to h6
                for heading in soup.find_all(f'h{level}'):
                    text = heading.get_text(strip=True)
                    if text:
                        headings.append({
                            'level': level,
                            'text': text
                        })
            
            return headings
            
        except Exception:
            return []
    
    def count_words(self, text: str) -> int:
        """Count words in text"""
        if not text:
            return 0
        
        # Split on whitespace and filter empty strings
        words = [word for word in text.split() if word.strip()]
        return len(words)
    
    def count_sentences(self, text: str) -> int:
        """Count sentences in text"""
        if not text:
            return 0
        
        # Simple sentence counting based on punctuation
        sentence_endings = re.findall(r'[.!?]+', text)
        return len(sentence_endings)
    
    def extract_metadata(self, html: str) -> dict:
        """Extract metadata from HTML"""
        if not html:
            return {}
        
        try:
            soup = BeautifulSoup(html, 'lxml')
            metadata = {}
            
            # Extract title
            title_tag = soup.find('title')
            if title_tag:
                metadata['title'] = title_tag.get_text(strip=True)
            
            # Extract meta description
            desc_tag = soup.find('meta', attrs={'name': 'description'})
            if desc_tag:
                metadata['description'] = desc_tag.get('content', '')
            
            # Extract meta keywords
            keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
            if keywords_tag:
                metadata['keywords'] = keywords_tag.get('content', '')
            
            # Extract lang attribute
            html_tag = soup.find('html')
            if html_tag and html_tag.get('lang'):
                metadata['language'] = html_tag.get('lang')
            
            return metadata
            
        except Exception:
            return {}