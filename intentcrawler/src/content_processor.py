import trafilatura
from newspaper import Article
import html2text
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from dataclasses import dataclass
import re
import logging

@dataclass
class ProcessedContent:
    title: str
    summary: str
    content: str
    keywords: List[str]
    word_count: int
    readability_score: Optional[float] = None

class ContentProcessor:
    def __init__(self, max_summary_length: int = 500, min_content_length: int = 100):
        self.max_summary_length = max_summary_length
        self.min_content_length = min_content_length
        self.logger = logging.getLogger(__name__)
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = True
        self.html_converter.ignore_images = True
    
    def _clean_text(self, text: str) -> str:
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s\.,!?\-]', '', text)
        return text.strip()
    
    def _extract_keywords(self, text: str) -> List[str]:
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        return sorted(word_freq.keys(), key=lambda x: word_freq[x], reverse=True)[:10]
    
    def _create_summary(self, content: str, title: str) -> str:
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        if not sentences:
            return title[:self.max_summary_length]
        
        summary = sentences[0]
        for sentence in sentences[1:]:
            if len(summary + ' ' + sentence) <= self.max_summary_length:
                summary += ' ' + sentence
            else:
                break
        
        return summary
    
    def process_with_trafilatura(self, html_content: str, url: str) -> Optional[ProcessedContent]:
        try:
            extracted = trafilatura.extract(
                html_content,
                include_comments=False,
                include_tables=False,
                with_metadata=True,
                output_format='txt'
            )
            
            if not extracted or len(extracted) < self.min_content_length:
                return None
            
            metadata = trafilatura.extract_metadata(html_content)
            title = metadata.title if metadata and metadata.title else url
            
            cleaned_content = self._clean_text(extracted)
            summary = self._create_summary(cleaned_content, title)
            keywords = self._extract_keywords(cleaned_content)
            
            return ProcessedContent(
                title=title,
                summary=summary,
                content=cleaned_content,
                keywords=keywords,
                word_count=len(cleaned_content.split())
            )
            
        except Exception as e:
            self.logger.error(f"Trafilatura processing failed for {url}: {e}")
            return None
    
    def process_with_newspaper(self, url: str) -> Optional[ProcessedContent]:
        try:
            article = Article(url)
            article.download()
            article.parse()
            article.nlp()
            
            if not article.text or len(article.text) < self.min_content_length:
                return None
            
            cleaned_content = self._clean_text(article.text)
            title = article.title or url
            summary = article.summary or self._create_summary(cleaned_content, title)
            
            if len(summary) > self.max_summary_length:
                summary = summary[:self.max_summary_length] + "..."
            
            keywords = list(article.keywords) if article.keywords else self._extract_keywords(cleaned_content)
            
            return ProcessedContent(
                title=title,
                summary=summary,
                content=cleaned_content,
                keywords=keywords[:10],
                word_count=len(cleaned_content.split())
            )
            
        except Exception as e:
            self.logger.error(f"Newspaper processing failed for {url}: {e}")
            return None
    
    def process_with_beautifulsoup(self, html_content: str, url: str) -> Optional[ProcessedContent]:
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
                script.decompose()
            
            title_tag = soup.find('title')
            title = title_tag.get_text(strip=True) if title_tag else url
            
            main_content = (soup.find('main') or 
                          soup.find('article') or 
                          soup.find('div', class_=re.compile(r'content|main|body', re.I)) or
                          soup.find('body'))
            
            if not main_content:
                return None
            
            text_content = main_content.get_text(separator=' ', strip=True)
            cleaned_content = self._clean_text(text_content)
            
            if len(cleaned_content) < self.min_content_length:
                return None
            
            summary = self._create_summary(cleaned_content, title)
            keywords = self._extract_keywords(cleaned_content)
            
            return ProcessedContent(
                title=title,
                summary=summary,
                content=cleaned_content,
                keywords=keywords,
                word_count=len(cleaned_content.split())
            )
            
        except Exception as e:
            self.logger.error(f"BeautifulSoup processing failed for {url}: {e}")
            return None
    
    def process_content(self, html_content: str, url: str) -> Optional[ProcessedContent]:
        methods = [
            self.process_with_trafilatura,
            lambda html, url: self.process_with_newspaper(url),
            self.process_with_beautifulsoup
        ]
        
        for method in methods:
            try:
                result = method(html_content, url)
                if result and result.word_count >= 10:
                    return result
            except Exception as e:
                self.logger.warning(f"Content processing method failed: {e}")
                continue
        
        return None