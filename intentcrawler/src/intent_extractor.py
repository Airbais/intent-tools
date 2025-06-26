import re
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from collections import Counter, defaultdict
from .content_processor import ProcessedContent
import logging

@dataclass
class Intent:
    name: str
    confidence: float
    keywords: List[str]
    patterns: List[str]
    pages: List[str]
    category: str

@dataclass
class IntentCluster:
    id: int
    primary_intent: str
    intents: List[Intent]
    pages: List[str]
    keywords: List[str]
    confidence: float

class IntentExtractor:
    def __init__(self, baseline_categories: List[str] = None):
        self.baseline_categories = baseline_categories or ['informational', 'navigational', 'transactional']
        self.logger = logging.getLogger(__name__)
        
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            self.logger.warning("spaCy model not found. Falling back to rule-based extraction.")
            self.nlp = None
        
        self.action_patterns = {
            'transactional': [
                r'\b(?:buy|purchase|order|shop|cart|checkout|payment|price|cost|subscribe)\b',
                r'\b(?:download|get|install|trial|demo|free)\b',
                r'\b(?:contact|call|email|book|schedule|register|sign up)\b'
            ],
            'informational': [
                r'\b(?:learn|how to|what is|why|when|where|guide|tutorial|help)\b',
                r'\b(?:about|overview|introduction|explanation|definition)\b',
                r'\b(?:tips|advice|best practices|examples|case studies)\b'
            ],
            'navigational': [
                r'\b(?:home|menu|navigation|sitemap|directory)\b',
                r'\b(?:search|find|locate|browse|explore)\b',
                r'\b(?:login|account|dashboard|profile|settings)\b'
            ]
        }
        
        self.intent_keywords = {
            'product_discovery': ['products', 'catalog', 'browse', 'categories', 'inventory'],
            'comparison': ['compare', 'vs', 'versus', 'differences', 'alternatives'],
            'support': ['help', 'support', 'faq', 'documentation', 'troubleshooting'],
            'company_info': ['about', 'company', 'team', 'history', 'mission'],
            'news_updates': ['news', 'blog', 'updates', 'announcements', 'press'],
            'pricing': ['pricing', 'plans', 'cost', 'fees', 'subscription'],
            'integration': ['integration', 'api', 'developer', 'sdk', 'documentation'],
            'getting_started': ['getting started', 'quickstart', 'setup', 'installation'],
            'features': ['features', 'capabilities', 'functionality', 'specifications']
        }
    
    def _extract_action_verbs(self, text: str) -> List[str]:
        if self.nlp:
            doc = self.nlp(text)
            verbs = [token.lemma_ for token in doc if token.pos_ == 'VERB' and len(token.text) > 2]
        else:
            verb_pattern = r'\b(?:learn|buy|get|find|explore|discover|compare|download|contact|install|setup|configure|manage|create|build|develop|integrate|analyze|optimize|track|monitor|understand|implement|design|customize|automate|scale|secure)\b'
            verbs = re.findall(verb_pattern, text.lower())
        
        return list(set(verbs))
    
    def _extract_question_patterns(self, text: str) -> List[str]:
        question_patterns = [
            r'how (?:to|do|does|can|will|should) \w+',
            r'what (?:is|are|does|do|can|will) \w+',
            r'where (?:is|are|can|do|does) \w+',
            r'when (?:is|are|can|do|does) \w+',
            r'why (?:is|are|do|does|should) \w+',
            r'which (?:is|are|can|should) \w+'
        ]
        
        patterns = []
        for pattern in question_patterns:
            matches = re.findall(pattern, text.lower())
            patterns.extend(matches)
        
        return patterns
    
    def _classify_baseline_intent(self, text: str) -> Dict[str, float]:
        scores = {}
        text_lower = text.lower()
        
        for category, patterns in self.action_patterns.items():
            score = 0.0
            for pattern in patterns:
                matches = len(re.findall(pattern, text_lower))
                score += matches
            
            total_words = len(text.split())
            scores[category] = score / max(total_words, 1) if total_words > 0 else 0
        
        return scores
    
    def _extract_dynamic_intents(self, processed_contents: Dict[str, ProcessedContent]) -> Dict[str, List[Intent]]:
        dynamic_intents = defaultdict(list)
        
        for url, content in processed_contents.items():
            text = f"{content.title} {content.summary} {content.content}"
            
            baseline_scores = self._classify_baseline_intent(text)
            action_verbs = self._extract_action_verbs(text)
            question_patterns = self._extract_question_patterns(text)
            
            for intent_name, keywords in self.intent_keywords.items():
                keyword_score = sum(1 for keyword in keywords if keyword.lower() in text.lower())
                if keyword_score > 0:
                    confidence = min(keyword_score / len(keywords), 1.0)
                    
                    primary_category = max(baseline_scores, key=baseline_scores.get) if baseline_scores else 'informational'
                    
                    intent = Intent(
                        name=intent_name,
                        confidence=confidence,
                        keywords=keywords[:5],
                        patterns=question_patterns[:3],
                        pages=[url],
                        category=primary_category
                    )
                    
                    dynamic_intents[intent_name].append(intent)
            
            if action_verbs:
                verb_intent = Intent(
                    name=f"action_{action_verbs[0]}",
                    confidence=len(action_verbs) / 10.0,
                    keywords=action_verbs[:5],
                    patterns=[],
                    pages=[url],
                    category=max(baseline_scores, key=baseline_scores.get) if baseline_scores else 'informational'
                )
                dynamic_intents[f"action_{action_verbs[0]}"].append(verb_intent)
        
        return dynamic_intents
    
    def _cluster_similar_intents(self, intents: Dict[str, List[Intent]], 
                               similarity_threshold: float = 0.7) -> List[IntentCluster]:
        if not intents:
            return []
        
        intent_texts = []
        intent_metadata = []
        
        for intent_name, intent_list in intents.items():
            for intent in intent_list:
                text = f"{intent.name} {' '.join(intent.keywords)} {' '.join(intent.patterns)}"
                intent_texts.append(text)
                intent_metadata.append((intent_name, intent))
        
        if len(intent_texts) < 2:
            cluster = IntentCluster(
                id=0,
                primary_intent=list(intents.keys())[0],
                intents=list(intents.values())[0],
                pages=sum([intent.pages for intent_list in intents.values() for intent in intent_list], []),
                keywords=sum([intent.keywords for intent_list in intents.values() for intent in intent_list], [])[:10],
                confidence=sum([intent.confidence for intent_list in intents.values() for intent in intent_list]) / len(intent_texts)
            )
            return [cluster]
        
        try:
            vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
            tfidf_matrix = vectorizer.fit_transform(intent_texts)
            
            n_clusters = min(len(intent_texts) // 2, 10, len(set(intents.keys())))
            n_clusters = max(n_clusters, 1)
            
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(tfidf_matrix)
            
            clusters = []
            for cluster_id in range(n_clusters):
                cluster_intents = []
                cluster_pages = []
                cluster_keywords = []
                
                cluster_indices = [i for i, label in enumerate(cluster_labels) if label == cluster_id]
                
                for idx in cluster_indices:
                    intent_name, intent = intent_metadata[idx]
                    cluster_intents.append(intent)
                    cluster_pages.extend(intent.pages)
                    cluster_keywords.extend(intent.keywords)
                
                if cluster_intents:
                    primary_intent = Counter([intent.name for intent in cluster_intents]).most_common(1)[0][0]
                    avg_confidence = sum(intent.confidence for intent in cluster_intents) / len(cluster_intents)
                    
                    cluster = IntentCluster(
                        id=cluster_id,
                        primary_intent=primary_intent,
                        intents=cluster_intents,
                        pages=list(set(cluster_pages)),
                        keywords=list(set(cluster_keywords))[:10],
                        confidence=avg_confidence
                    )
                    clusters.append(cluster)
            
            return clusters
            
        except Exception as e:
            self.logger.error(f"Clustering failed: {e}")
            return []
    
    def extract_intents(self, processed_contents: Dict[str, ProcessedContent], 
                       min_cluster_size: int = 3, 
                       similarity_threshold: float = 0.7) -> Dict:
        self.logger.info(f"Extracting intents from {len(processed_contents)} pages")
        
        dynamic_intents = self._extract_dynamic_intents(processed_contents)
        
        filtered_intents = {
            name: intent_list for name, intent_list in dynamic_intents.items()
            if len(intent_list) >= min(min_cluster_size, 1)
        }
        
        intent_clusters = self._cluster_similar_intents(filtered_intents, similarity_threshold)
        
        section_intents = defaultdict(list)
        for cluster in intent_clusters:
            for page_url in cluster.pages:
                if page_url in processed_contents:
                    content = processed_contents[page_url]
                    section = self._get_section_from_url(page_url)
                    section_intents[section].append({
                        'intent': cluster.primary_intent,
                        'confidence': cluster.confidence,
                        'keywords': cluster.keywords[:5],
                        'page_url': page_url,
                        'page_title': content.title
                    })
        
        return {
            'discovered_intents': [
                {
                    'id': cluster.id,
                    'primary_intent': cluster.primary_intent,
                    'confidence': cluster.confidence,
                    'keywords': cluster.keywords,
                    'pages': cluster.pages,
                    'page_count': len(cluster.pages)
                }
                for cluster in intent_clusters
            ],
            'by_section': dict(section_intents),
            'intent_patterns': {
                intent_name: {
                    'keywords': list(set(sum([intent.keywords for intent in intent_list], []))),
                    'patterns': list(set(sum([intent.patterns for intent in intent_list], []))),
                    'pages': list(set(sum([intent.pages for intent in intent_list], [])))
                }
                for intent_name, intent_list in filtered_intents.items()
            },
            'total_intents': len(intent_clusters),
            'total_pages_analyzed': len(processed_contents)
        }
    
    def _get_section_from_url(self, url: str) -> str:
        from urllib.parse import urlparse
        path = urlparse(url).path.strip('/')
        if not path:
            return 'home'
        return path.split('/')[0]