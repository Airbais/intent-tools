import re
import spacy
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.cluster import KMeans, DBSCAN
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from collections import Counter, defaultdict
import logging
import json

# Try to import optional dependencies
try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False
    
try:
    from gensim import corpora, models
    from gensim.parsing.preprocessing import STOPWORDS
    HAS_GENSIM = True
except ImportError:
    HAS_GENSIM = False
    # Define basic stopwords if gensim is not available
    STOPWORDS = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                 'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
                 'before', 'after', 'above', 'below', 'between', 'under', 'again', 'further',
                 'then', 'once', 'is', 'are', 'was', 'were', 'been', 'be', 'have', 'has',
                 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'ought',
                 'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your',
                 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she',
                 'her', 'hers', 'herself', 'it', 'its', 'itself', 'they', 'them', 'their',
                 'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'this', 'that',
                 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'been', 'being',
                 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing'}

from .content_processor import ProcessedContent

@dataclass
class DynamicIntent:
    id: str
    name: str
    confidence: float
    keywords: List[str]
    representative_phrases: List[str]
    pages: List[str]
    page_count: int
    method: str  # 'lda', 'embeddings', 'keywords'

class EnhancedIntentExtractor:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Load spaCy model for NLP
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            self.logger.warning("spaCy model not found. Some features will be limited.")
            self.nlp = None
        
        # Initialize sentence transformer for embeddings
        self.embeddings_model = None
        if self.config.get('use_embeddings', True) and HAS_SENTENCE_TRANSFORMERS:
            try:
                model_name = self.config.get('embeddings_model', 'sentence-transformers/all-MiniLM-L6-v2')
                self.embeddings_model = SentenceTransformer(model_name)
            except Exception as e:
                self.logger.warning(f"Failed to load embeddings model: {e}")
        elif self.config.get('use_embeddings', True) and not HAS_SENTENCE_TRANSFORMERS:
            self.logger.warning("sentence-transformers not installed. Embeddings-based extraction disabled.")
        
        # Fallback keywords configuration
        self.use_fallback_keywords = self.config.get('fallback_keywords', True)
        self.custom_keywords = self.config.get('custom_keywords', {})
        self.baseline_categories = self.config.get('baseline_categories', 
                                                  ['informational', 'navigational', 'transactional'])
    
    def _preprocess_text(self, text: str) -> str:
        """Clean and preprocess text for analysis."""
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)
        # Remove special characters but keep spaces
        text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)
        # Remove extra whitespace
        text = ' '.join(text.split())
        return text.lower()
    
    def _extract_key_phrases(self, text: str, max_phrases: int = 10) -> List[str]:
        """Extract key phrases using NLP techniques."""
        if not self.nlp:
            return []
        
        doc = self.nlp(text[:1000000])  # Limit text length for spaCy
        
        # Extract noun phrases
        noun_phrases = []
        for chunk in doc.noun_chunks:
            if 2 <= len(chunk.text.split()) <= 4:  # Phrases between 2-4 words
                noun_phrases.append(chunk.text.lower())
        
        # Extract verb phrases with objects
        verb_phrases = []
        for token in doc:
            if token.pos_ == "VERB" and token.dep_ == "ROOT":
                phrase_parts = [token.text]
                for child in token.children:
                    if child.dep_ in ["dobj", "pobj", "attr"]:
                        phrase_parts.append(child.text)
                if len(phrase_parts) > 1:
                    verb_phrases.append(" ".join(phrase_parts).lower())
        
        all_phrases = noun_phrases + verb_phrases
        # Count frequencies and return top phrases
        phrase_counts = Counter(all_phrases)
        return [phrase for phrase, _ in phrase_counts.most_common(max_phrases)]
    
    def _extract_with_lda(self, texts: List[str], urls: List[str], 
                         num_topics: Optional[int] = None) -> List[DynamicIntent]:
        """Extract intents using Latent Dirichlet Allocation."""
        if not HAS_GENSIM:
            self.logger.warning("gensim not installed. LDA extraction will use sklearn instead.")
        
        if num_topics is None:
            num_topics = self.config.get('lda_topics', 10)
        
        # Ensure num_topics is an int
        if not isinstance(num_topics, int):
            num_topics = 10
        
        self.logger.info(f"Extracting intents with LDA ({num_topics} topics)")
        
        # Preprocess texts
        processed_texts = [self._preprocess_text(text) for text in texts]
        
        # Create document-term matrix
        vectorizer = CountVectorizer(
            max_features=500,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=2
        )
        
        try:
            doc_term_matrix = vectorizer.fit_transform(processed_texts)
            feature_names = list(vectorizer.get_feature_names_out())
            
            # Apply LDA
            lda = LatentDirichletAllocation(
                n_components=num_topics,
                random_state=42,
                max_iter=100
            )
            lda.fit(doc_term_matrix)
            
            # Extract topics and create intents
            intents = []
            for topic_idx in range(num_topics):
                # Get top words for this topic
                top_word_indices = lda.components_[topic_idx].argsort()[-20:][::-1]
                top_words = [feature_names[i] for i in top_word_indices]
                
                # Get documents most associated with this topic
                doc_topic_dist = lda.transform(doc_term_matrix)
                topic_docs = np.where(doc_topic_dist[:, topic_idx] > 0.3)[0]
                
                if len(topic_docs) == 0:
                    continue
                
                # Generate intent name from top words
                intent_name = self._generate_intent_name_from_words(top_words[:5])
                
                # Get representative phrases from top documents
                rep_phrases = []
                for doc_idx in topic_docs[:5]:
                    phrases = self._extract_key_phrases(texts[doc_idx])
                    rep_phrases.extend(phrases[:2])
                
                intent = DynamicIntent(
                    id=f"lda_{topic_idx}",
                    name=intent_name,
                    confidence=float(np.mean(doc_topic_dist[topic_docs, topic_idx])),
                    keywords=top_words[:10],
                    representative_phrases=list(set(rep_phrases))[:5],
                    pages=[urls[i] for i in topic_docs],
                    page_count=len(topic_docs),
                    method='lda'
                )
                intents.append(intent)
            
            return intents
            
        except Exception as e:
            self.logger.error(f"LDA extraction failed: {e}")
            return []
    
    def _extract_with_embeddings(self, texts: List[str], urls: List[str]) -> List[DynamicIntent]:
        """Extract intents using sentence embeddings and clustering."""
        if not self.embeddings_model:
            return []
        
        self.logger.info("Extracting intents with embeddings")
        
        try:
            # Generate embeddings
            embeddings = self.embeddings_model.encode(texts, show_progress_bar=False)
            
            # Cluster using DBSCAN for dynamic number of clusters
            clustering = DBSCAN(
                eps=0.3,
                min_samples=max(2, int(len(texts) * 0.05)),
                metric='cosine'
            )
            labels = clustering.fit_predict(embeddings)
            
            # Process clusters
            intents = []
            unique_labels = set(labels.tolist())  # Convert numpy array to Python list first
            unique_labels.discard(-1)  # Remove noise label
            
            for label in unique_labels:
                cluster_indices = np.where(labels == label)[0]
                if len(cluster_indices) < 2:
                    continue
                
                # Get cluster texts
                cluster_texts = [texts[i] for i in cluster_indices]
                cluster_urls = [urls[i] for i in cluster_indices]
                
                # Extract common keywords from cluster
                all_text = " ".join(cluster_texts)
                keywords = self._extract_common_terms(all_text, num_terms=15)
                
                # Generate intent name
                intent_name = self._generate_intent_name_from_context(cluster_texts[:5])
                
                # Get representative phrases
                rep_phrases = []
                for text in cluster_texts[:3]:
                    phrases = self._extract_key_phrases(text)
                    rep_phrases.extend(phrases[:2])
                
                # Calculate cluster cohesion as confidence
                cluster_embeddings = embeddings[cluster_indices]
                centroid = np.mean(cluster_embeddings, axis=0)
                distances = cosine_similarity([centroid], cluster_embeddings)[0]
                confidence = float(np.mean(distances))
                
                intent = DynamicIntent(
                    id=f"emb_{label}",
                    name=intent_name,
                    confidence=confidence,
                    keywords=keywords,
                    representative_phrases=list(set(rep_phrases))[:5],
                    pages=cluster_urls,
                    page_count=len(cluster_urls),
                    method='embeddings'
                )
                intents.append(intent)
            
            return intents
            
        except Exception as e:
            self.logger.error(f"Embeddings extraction failed: {e}")
            return []
    
    def _extract_with_keywords(self, processed_contents: Dict[str, ProcessedContent]) -> List[DynamicIntent]:
        """Fallback extraction using predefined keywords."""
        if not self.use_fallback_keywords:
            return []
        
        self.logger.info("Using keyword-based fallback extraction")
        
        intent_pages = defaultdict(list)
        intent_scores = defaultdict(list)
        
        for url, content in processed_contents.items():
            text = f"{content.title} {content.summary} {content.content}".lower()
            
            for intent_name, keywords in self.custom_keywords.items():
                score = sum(1 for keyword in keywords if keyword.lower() in text)
                if score > 0:
                    intent_pages[intent_name].append(url)
                    intent_scores[intent_name].append(score / len(keywords))
        
        intents = []
        for intent_name, pages in intent_pages.items():
            if len(pages) >= 2:
                # Extract representative content
                sample_texts = []
                for page in pages[:5]:
                    if page in processed_contents:
                        sample_texts.append(processed_contents[page].summary)
                
                rep_phrases = []
                if sample_texts:
                    combined_text = " ".join(sample_texts)
                    rep_phrases = self._extract_key_phrases(combined_text)
                
                intent = DynamicIntent(
                    id=f"kw_{intent_name}",
                    name=intent_name,
                    confidence=float(np.mean(intent_scores[intent_name])),
                    keywords=self.custom_keywords[intent_name],
                    representative_phrases=rep_phrases[:5],
                    pages=pages,
                    page_count=len(pages),
                    method='keywords'
                )
                intents.append(intent)
        
        return intents
    
    def _extract_common_terms(self, text: str, num_terms: int = 10) -> List[str]:
        """Extract most common meaningful terms from text."""
        words = self._preprocess_text(text).split()
        # Filter out stop words and short words
        meaningful_words = [w for w in words if w not in STOPWORDS and len(w) > 3]
        word_counts = Counter(meaningful_words)
        return [word for word, _ in word_counts.most_common(num_terms)]
    
    def _generate_intent_name_from_words(self, words: List[str]) -> str:
        """Generate a meaningful intent name from top words."""
        # Look for action words
        action_words = ['learn', 'buy', 'find', 'get', 'compare', 'explore', 'discover']
        for word in words:
            for action in action_words:
                if action in word:
                    return f"{action}_{words[0]}"
        
        # Look for category indicators
        if any(w in words for w in ['product', 'item', 'catalog']):
            return 'product_discovery'
        elif any(w in words for w in ['help', 'support', 'faq']):
            return 'support'
        elif any(w in words for w in ['api', 'integration', 'developer']):
            return 'technical_integration'
        elif any(w in words for w in ['price', 'cost', 'plan']):
            return 'pricing_info'
        
        # Default: combine top 2 words
        return "_".join(words[:2])
    
    def _generate_intent_name_from_context(self, texts: List[str]) -> str:
        """Generate intent name by analyzing context of multiple texts."""
        all_text = " ".join(texts).lower()
        
        # Check for question patterns
        if re.search(r'how to|how do|how can', all_text):
            return 'how_to_guide'
        elif re.search(r'what is|what are|what does', all_text):
            return 'explanation'
        elif re.search(r'why should|why do|why is', all_text):
            return 'reasoning'
        
        # Extract common terms and generate name
        common_terms = self._extract_common_terms(all_text, num_terms=5)
        if common_terms:
            return self._generate_intent_name_from_words(common_terms)
        
        return 'general_content'
    
    def _merge_similar_intents(self, intents: List[DynamicIntent], 
                              similarity_threshold: float = 0.7) -> List[DynamicIntent]:
        """Merge intents that are very similar."""
        if len(intents) <= 1:
            return intents
        
        # Create intent vectors based on keywords
        intent_texts = []
        for intent in intents:
            text = " ".join(intent.keywords + intent.representative_phrases)
            intent_texts.append(text)
        
        # Vectorize and compute similarities
        vectorizer = TfidfVectorizer(max_features=100)
        try:
            tfidf_matrix = vectorizer.fit_transform(intent_texts)
            similarities = cosine_similarity(tfidf_matrix)
            
            # Find groups to merge
            merged = set()
            final_intents = []
            
            for i in range(len(intents)):
                if i in merged:
                    continue
                
                # Find similar intents
                similar_indices = np.where(similarities[i] > similarity_threshold)[0]
                similar_indices = [idx for idx in similar_indices if idx != i and idx not in merged]
                
                if similar_indices:
                    # Merge intents
                    merged_intent = self._merge_intent_group(
                        [intents[i]] + [intents[idx] for idx in similar_indices]
                    )
                    final_intents.append(merged_intent)
                    merged.update(similar_indices)
                else:
                    final_intents.append(intents[i])
                
                merged.add(i)
            
            return final_intents
            
        except Exception as e:
            self.logger.error(f"Failed to merge similar intents: {e}")
            return intents
    
    def _merge_intent_group(self, intent_group: List[DynamicIntent]) -> DynamicIntent:
        """Merge a group of similar intents into one."""
        # Combine all data
        all_keywords = []
        all_phrases = []
        all_pages = []
        
        for intent in intent_group:
            all_keywords.extend(intent.keywords)
            all_phrases.extend(intent.representative_phrases)
            all_pages.extend(intent.pages)
        
        # Get most common keywords and phrases
        keyword_counts = Counter(all_keywords)
        phrase_counts = Counter(all_phrases)
        
        # Choose the most descriptive name
        names = [intent.name for intent in intent_group]
        name_counts = Counter(names)
        primary_name = name_counts.most_common(1)[0][0]
        
        # Average confidence
        avg_confidence = np.mean([intent.confidence for intent in intent_group])
        
        return DynamicIntent(
            id=f"merged_{intent_group[0].id}",
            name=primary_name,
            confidence=float(avg_confidence),
            keywords=[kw for kw, _ in keyword_counts.most_common(10)],
            representative_phrases=[ph for ph, _ in phrase_counts.most_common(5)],
            pages=list(set(all_pages)),
            page_count=len(set(all_pages)),
            method='merged'
        )
    
    def extract_intents(self, processed_contents: Dict[str, ProcessedContent]) -> Dict:
        """Main method to extract intents using multiple approaches."""
        self.logger.info(f"Starting enhanced intent extraction for {len(processed_contents)} pages")
        
        # Prepare texts and URLs
        urls = list(processed_contents.keys())
        texts = []
        for url in urls:
            content = processed_contents[url]
            text = f"{content.title} {content.summary} {content.content}"
            texts.append(text)
        
        all_intents = []
        
        # Extract using LDA if enabled
        if self.config.get('use_lda', True) and len(texts) >= 10:
            lda_intents = self._extract_with_lda(texts, urls)
            all_intents.extend(lda_intents)
        
        # Extract using embeddings if enabled and available
        if self.config.get('use_embeddings', True) and self.embeddings_model and len(texts) >= 5:
            embedding_intents = self._extract_with_embeddings(texts, urls)
            all_intents.extend(embedding_intents)
        
        # Extract using keywords as fallback
        if self.use_fallback_keywords:
            keyword_intents = self._extract_with_keywords(processed_contents)
            all_intents.extend(keyword_intents)
        
        # Merge similar intents
        similarity_threshold = self.config.get('similarity_threshold', 0.7)
        merged_intents = self._merge_similar_intents(all_intents, similarity_threshold)
        
        # Sort by page count
        merged_intents.sort(key=lambda x: x.page_count, reverse=True)
        
        # Prepare output format
        return self._format_output(merged_intents, processed_contents)
    
    def _format_output(self, intents: List[DynamicIntent], 
                      processed_contents: Dict[str, ProcessedContent]) -> Dict:
        """Format intents for output."""
        # Convert intents to output format
        discovered_intents = []
        for intent in intents:
            discovered_intents.append({
                'primary_intent': intent.name,
                'confidence': intent.confidence,
                'keywords': intent.keywords,
                'representative_phrases': intent.representative_phrases,
                'page_count': intent.page_count,
                'extraction_method': intent.method,
                'pages': intent.pages
            })
        
        # Group by sections
        by_section = defaultdict(list)
        for intent in intents:
            for page_url in intent.pages:
                if page_url in processed_contents:
                    section = self._get_section_from_url(page_url)
                    content = processed_contents[page_url]
                    by_section[section].append({
                        'intent': intent.name,
                        'confidence': intent.confidence,
                        'keywords': intent.keywords[:5],
                        'page_url': page_url,
                        'page_title': content.title
                    })
        
        return {
            'discovered_intents': discovered_intents,
            'by_section': dict(by_section),
            'total_intents_discovered': len(discovered_intents),
            'total_pages_analyzed': len(processed_contents),
            'extraction_methods_used': list(set(intent.method for intent in intents))
        }
    
    def _get_section_from_url(self, url: str) -> str:
        """Extract section name from URL."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split('/') if p]
        
        if not path_parts:
            return 'home'
        
        # Use first meaningful path component as section
        section = path_parts[0].lower()
        
        # Clean up common suffixes
        section = re.sub(r'\.(html?|php|aspx?)$', '', section)
        
        # Convert hyphens/underscores to spaces and title case
        section = section.replace('-', ' ').replace('_', ' ').title()
        
        return section