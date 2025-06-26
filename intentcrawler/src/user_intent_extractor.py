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

from .content_processor import ProcessedContent

@dataclass
class UserIntent:
    id: str
    intent_type: str  # e.g., "research", "purchase", "learn", "solve_problem"
    user_goal: str    # e.g., "understand how to integrate API", "compare pricing options"
    confidence: float
    signal_phrases: List[str]  # Phrases that indicate this intent
    action_verbs: List[str]    # What users want to do
    pain_points: List[str]     # Problems users are trying to solve
    pages: List[str]
    page_count: int
    evidence: Dict[str, any]   # Supporting evidence for the intent

class UserIntentExtractor:
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
        
        # User intent patterns focused on what users want to accomplish
        self.intent_patterns = {
            'research_and_compare': {
                'signals': [
                    r'\b(?:compare|comparison|vs|versus|difference|alternative|option|choice)\b',
                    r'\b(?:pros and cons|advantages|disadvantages|benefits|drawbacks)\b',
                    r'\b(?:which is better|best option|recommend|suggestion)\b',
                    r'\b(?:reviews?|ratings?|testimonials?|feedback)\b'
                ],
                'user_goals': ['compare options', 'evaluate alternatives', 'make informed decision'],
                'pain_points': ['too many choices', 'unclear differences', 'need validation']
            },
            'learn_and_understand': {
                'signals': [
                    r'\b(?:how to|how do|how can|how does|tutorial|guide|step by step)\b',
                    r'\b(?:learn|understand|explain|definition|meaning|what is)\b',
                    r'\b(?:beginner|getting started|introduction|basics|fundamentals)\b',
                    r'\b(?:examples?|case studies?|best practices?|tips)\b'
                ],
                'user_goals': ['acquire new skills', 'understand concepts', 'get practical knowledge'],
                'pain_points': ['lack of knowledge', 'confusion', 'need guidance']
            },
            'solve_problem': {
                'signals': [
                    r'\b(?:troubleshoot|fix|solve|error|issue|problem|bug)\b',
                    r'\b(?:not working|broken|failed|help|support)\b',
                    r'\b(?:why is|why does|why won\'t|why can\'t)\b',
                    r'\b(?:faq|frequently asked|common issues?|known problems?)\b'
                ],
                'user_goals': ['fix issues', 'resolve problems', 'get unblocked'],
                'pain_points': ['system not working', 'stuck on task', 'need immediate help']
            },
            'evaluate_and_purchase': {
                'signals': [
                    r'\b(?:price|pricing|cost|fee|subscription|plan)\b',
                    r'\b(?:buy|purchase|order|checkout|payment|trial)\b',
                    r'\b(?:demo|trial|free|discount|offer|deal)\b',
                    r'\b(?:features?|specifications?|capabilities?|included)\b'
                ],
                'user_goals': ['evaluate cost', 'understand value', 'make purchase'],
                'pain_points': ['budget constraints', 'unclear pricing', 'need ROI justification']
            },
            'implement_and_integrate': {
                'signals': [
                    r'\b(?:setup|install|configure|implement|integrate)\b',
                    r'\b(?:api|sdk|documentation|code|developer)\b',
                    r'\b(?:deployment|installation|configuration|settings)\b',
                    r'\b(?:connect|sync|import|export|migration)\b'
                ],
                'user_goals': ['implement solution', 'integrate systems', 'deploy product'],
                'pain_points': ['technical complexity', 'integration challenges', 'time constraints']
            },
            'optimize_and_improve': {
                'signals': [
                    r'\b(?:optimize|improve|enhance|upgrade|performance)\b',
                    r'\b(?:faster|better|more efficient|scalable|secure)\b',
                    r'\b(?:best practices?|optimization|tuning|configuration)\b',
                    r'\b(?:advanced|pro tips?|expert|professional)\b'
                ],
                'user_goals': ['improve performance', 'optimize usage', 'advance skills'],
                'pain_points': ['suboptimal performance', 'inefficient processes', 'scaling issues']
            },
            'stay_informed': {
                'signals': [
                    r'\b(?:news|updates?|announcements?|releases?|changelog)\b',
                    r'\b(?:new features?|latest|recent|upcoming|roadmap)\b',
                    r'\b(?:blog|newsletter|notifications?|alerts?)\b',
                    r'\b(?:trends?|industry|market|insights?)\b'
                ],
                'user_goals': ['stay current', 'track changes', 'plan future'],
                'pain_points': ['information overload', 'missing updates', 'planning uncertainty']
            },
            'connect_and_communicate': {
                'signals': [
                    r'\b(?:contact|support|help|community|forum)\b',
                    r'\b(?:feedback|suggestions?|request|report)\b',
                    r'\b(?:team|experts?|consultants?|sales)\b',
                    r'\b(?:partnership|collaboration|network)\b'
                ],
                'user_goals': ['get human help', 'build relationships', 'provide feedback'],
                'pain_points': ['need human interaction', 'complex requirements', 'relationship building']
            }
        }
    
    def _extract_user_signals(self, text: str) -> Dict[str, List[str]]:
        """Extract signals that indicate user intent from text."""
        text_lower = text.lower()
        detected_signals = defaultdict(list)
        
        for intent_type, patterns in self.intent_patterns.items():
            for pattern in patterns['signals']:
                matches = re.findall(pattern, text_lower)
                if matches:
                    detected_signals[intent_type].extend(matches)
        
        return dict(detected_signals)
    
    def _extract_action_sequences(self, text: str) -> List[str]:
        """Extract sequences of actions users want to perform."""
        if not self.nlp:
            return []
        
        doc = self.nlp(text[:1000000])  # Limit for performance
        action_sequences = []
        
        # Look for imperative sentences (instructions/actions)
        for sent in doc.sents:
            # Check if sentence starts with a verb (imperative)
            if sent[0].pos_ == "VERB" and sent[0].dep_ == "ROOT":
                action_sequences.append(sent.text.strip())
            
            # Look for "to" + verb constructions
            for token in sent:
                if token.text.lower() == "to" and token.i + 1 < len(doc):
                    next_token = doc[token.i + 1]
                    if next_token.pos_ == "VERB":
                        # Extract the phrase
                        phrase_end = min(token.i + 5, len(doc))
                        phrase = doc[token.i:phrase_end].text
                        action_sequences.append(phrase)
        
        return action_sequences[:10]  # Limit to top 10
    
    def _extract_pain_indicators(self, text: str) -> List[str]:
        """Extract indicators of user pain points or challenges."""
        pain_patterns = [
            r'\b(?:difficult|hard|challenging|complex|confusing|frustrating)\b',
            r'\b(?:can\'t|cannot|unable to|doesn\'t work|not working|failed)\b',
            r'\b(?:slow|expensive|time-consuming|inefficient|limited)\b',
            r'\b(?:need help|struggling|stuck|blocked|confused)\b',
            r'\b(?:why doesn\'t|why can\'t|why won\'t|how come)\b'
        ]
        
        pain_indicators = []
        text_lower = text.lower()
        
        for pattern in pain_patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                # Extract surrounding context
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].strip()
                pain_indicators.append(context)
        
        return pain_indicators[:5]  # Limit to top 5
    
    def _extract_outcome_indicators(self, text: str) -> List[str]:
        """Extract what users hope to achieve (outcomes/goals)."""
        outcome_patterns = [
            r'\b(?:achieve|accomplish|reach|attain|obtain|gain)\b[^.]{0,50}',
            r'\b(?:want to|need to|trying to|hoping to|planning to)\b[^.]{0,50}',
            r'\b(?:goal|objective|target|aim|purpose)\b[^.]{0,50}',
            r'\b(?:so that|in order to|to help|to enable)\b[^.]{0,50}'
        ]
        
        outcomes = []
        text_lower = text.lower()
        
        for pattern in outcome_patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                outcomes.append(match.group())
        
        return outcomes[:5]  # Limit to top 5
    
    def _analyze_page_intent(self, content: ProcessedContent) -> Dict[str, any]:
        """Analyze a single page to extract user intent indicators."""
        full_text = f"{content.title} {content.summary} {content.content}"
        
        # Extract various intent signals
        user_signals = self._extract_user_signals(full_text)
        action_sequences = self._extract_action_sequences(full_text)
        pain_indicators = self._extract_pain_indicators(full_text)
        outcome_indicators = self._extract_outcome_indicators(full_text)
        
        # Score each intent type based on signal strength
        intent_scores = {}
        for intent_type, signals in user_signals.items():
            # Base score from number of signals
            signal_count = len(signals)
            
            # Boost score based on signal quality and context
            quality_boost = 0
            if intent_type in ['learn_and_understand'] and any('tutorial' in s or 'guide' in s for s in signals):
                quality_boost += 0.3
            if intent_type in ['solve_problem'] and pain_indicators:
                quality_boost += 0.2
            if intent_type in ['evaluate_and_purchase'] and any('price' in s or 'cost' in s for s in signals):
                quality_boost += 0.2
            
            intent_scores[intent_type] = (signal_count / 10.0) + quality_boost
        
        return {
            'user_signals': user_signals,
            'action_sequences': action_sequences,
            'pain_indicators': pain_indicators,
            'outcome_indicators': outcome_indicators,
            'intent_scores': intent_scores
        }
    
    def _cluster_user_intents(self, page_analyses: Dict[str, Dict]) -> List[UserIntent]:
        """Cluster pages by user intent rather than content category."""
        user_intents = []
        
        # Group pages by dominant intent type
        intent_groups = defaultdict(list)
        
        for url, analysis in page_analyses.items():
            intent_scores = analysis['intent_scores']
            if intent_scores:
                # Find the dominant intent
                dominant_intent = max(intent_scores.items(), key=lambda x: x[1])
                if dominant_intent[1] > 0.1:  # Minimum confidence threshold
                    intent_groups[dominant_intent[0]].append((url, analysis))
        
        # Create UserIntent objects for each group
        for intent_type, pages_data in intent_groups.items():
            if len(pages_data) < 2:  # Skip groups with too few pages
                continue
            
            urls = [url for url, _ in pages_data]
            analyses = [analysis for _, analysis in pages_data]
            
            # Aggregate signals from all pages in group
            all_signals = []
            all_actions = []
            all_pain_points = []
            
            for analysis in analyses:
                all_signals.extend(analysis['user_signals'].get(intent_type, []))
                all_actions.extend(analysis['action_sequences'])
                all_pain_points.extend(analysis['pain_indicators'])
            
            # Generate user goal description
            user_goal = self._generate_user_goal(intent_type, all_signals, all_actions)
            
            # Calculate confidence based on signal consistency
            confidence = self._calculate_intent_confidence(analyses, intent_type)
            
            user_intent = UserIntent(
                id=f"intent_{len(user_intents)}",
                intent_type=intent_type,
                user_goal=user_goal,
                confidence=confidence,
                signal_phrases=list(set(all_signals))[:10],
                action_verbs=self._extract_action_verbs_from_sequences(all_actions),
                pain_points=list(set(all_pain_points))[:5],
                pages=urls,
                page_count=len(urls),
                evidence={
                    'signal_frequency': len(all_signals),
                    'action_count': len(all_actions),
                    'pain_point_count': len(all_pain_points)
                }
            )
            
            user_intents.append(user_intent)
        
        return user_intents
    
    def _generate_user_goal(self, intent_type: str, signals: List[str], actions: List[str]) -> str:
        """Generate a description of what users are trying to accomplish."""
        intent_info = self.intent_patterns.get(intent_type, {})
        base_goals = intent_info.get('user_goals', ['accomplish task'])
        
        # Try to be more specific based on signals
        if 'api' in ' '.join(signals):
            return f"{base_goals[0]} with API integration"
        elif 'price' in ' '.join(signals) or 'cost' in ' '.join(signals):
            return f"{base_goals[0]} while understanding costs"
        elif 'tutorial' in ' '.join(signals) or 'guide' in ' '.join(signals):
            return f"{base_goals[0]} through step-by-step guidance"
        elif actions:
            # Use the most common action
            action_words = []
            for action in actions:
                action_words.extend(action.split()[:3])  # First 3 words
            if action_words:
                return f"{base_goals[0]}: {' '.join(action_words[:5])}"
        
        return base_goals[0] if base_goals else "accomplish their goal"
    
    def _calculate_intent_confidence(self, analyses: List[Dict], intent_type: str) -> float:
        """Calculate confidence score based on signal consistency across pages."""
        if not analyses:
            return 0.0
        
        # Check how many pages have this intent type with significant score
        strong_signals = sum(1 for analysis in analyses 
                           if analysis['intent_scores'].get(intent_type, 0) > 0.2)
        
        consistency_ratio = strong_signals / len(analyses)
        
        # Average signal strength
        avg_signal_strength = np.mean([
            analysis['intent_scores'].get(intent_type, 0) 
            for analysis in analyses
        ])
        
        return min(consistency_ratio * avg_signal_strength, 1.0)
    
    def _extract_action_verbs_from_sequences(self, action_sequences: List[str]) -> List[str]:
        """Extract action verbs from action sequences."""
        if not self.nlp:
            return []
        
        verbs = []
        for sequence in action_sequences:
            if len(sequence) > 100:  # Skip very long sequences
                continue
            doc = self.nlp(sequence)
            for token in doc:
                if token.pos_ == "VERB" and len(token.text) > 2:
                    verbs.append(token.lemma_)
        
        # Return most common verbs
        verb_counts = Counter(verbs)
        return [verb for verb, _ in verb_counts.most_common(10)]
    
    def extract_intents(self, processed_contents: Dict[str, ProcessedContent]) -> Dict:
        """Main method to extract user intents."""
        self.logger.info(f"Extracting user intents from {len(processed_contents)} pages")
        
        # Analyze each page for user intent indicators
        page_analyses = {}
        for url, content in processed_contents.items():
            page_analyses[url] = self._analyze_page_intent(content)
        
        # Cluster pages by user intent
        user_intents = self._cluster_user_intents(page_analyses)
        
        # Sort by confidence and page count
        user_intents.sort(key=lambda x: (x.confidence, x.page_count), reverse=True)
        
        return self._format_output(user_intents, processed_contents)
    
    def _format_output(self, user_intents: List[UserIntent], 
                      processed_contents: Dict[str, ProcessedContent]) -> Dict:
        """Format user intents for output."""
        discovered_intents = []
        for intent in user_intents:
            discovered_intents.append({
                'primary_intent': intent.intent_type,
                'user_goal': intent.user_goal,
                'confidence': intent.confidence,
                'keywords': intent.signal_phrases,
                'action_verbs': intent.action_verbs,
                'pain_points': intent.pain_points,
                'page_count': intent.page_count,
                'extraction_method': 'user_intent_analysis',
                'pages': intent.pages,
                'evidence': intent.evidence
            })
        
        # Group by sections
        by_section = defaultdict(list)
        for intent in user_intents:
            for page_url in intent.pages:
                if page_url in processed_contents:
                    section = self._get_section_from_url(page_url)
                    content = processed_contents[page_url]
                    by_section[section].append({
                        'intent': intent.intent_type,
                        'user_goal': intent.user_goal,
                        'confidence': intent.confidence,
                        'keywords': intent.signal_phrases[:5],
                        'page_url': page_url,
                        'page_title': content.title
                    })
        
        return {
            'discovered_intents': discovered_intents,
            'by_section': dict(by_section),
            'total_intents_discovered': len(discovered_intents),
            'extraction_methods_used': ['user_intent_analysis']
        }
    
    def _get_section_from_url(self, url: str) -> str:
        """Extract section name from URL."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split('/') if p]
        
        if not path_parts:
            return 'home'
        
        section = path_parts[0].lower()
        section = re.sub(r'\.(html?|php|aspx?)$', '', section)
        section = section.replace('-', ' ').replace('_', ' ').title()
        
        return section