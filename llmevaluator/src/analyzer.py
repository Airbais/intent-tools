"""
Response Analyzer
Analyzes LLM responses for brand mentions, sentiment, and context
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from textblob import TextBlob
import json

from .config import BrandInfo
from .prompt_executor import PromptResult
from .llm_interface import LLMInterface

@dataclass
class MentionContext:
    text: str
    position: str  # first_paragraph, middle, conclusion
    context_type: str  # recommendation, comparison, example, explanation

@dataclass
class ResponseAnalysis:
    brand_mentions: int = 0
    website_mentions: int = 0
    sentiment_score: float = 0.0
    sentiment_label: str = "neutral"
    mention_positions: List[str] = field(default_factory=list)
    mention_contexts: List[MentionContext] = field(default_factory=list)
    competitor_mentions: Dict[str, int] = field(default_factory=dict)
    response_excerpt: str = ""

class ResponseAnalyzer:
    def __init__(self, brand_info: BrandInfo, llm_interface: Optional[LLMInterface] = None):
        self.brand_info = brand_info
        self.llm_interface = llm_interface
        self.logger = logging.getLogger(__name__)
        
        # Prepare search patterns
        self._prepare_search_patterns()
    
    def _prepare_search_patterns(self) -> None:
        """Prepare regex patterns for brand and website detection"""
        # Brand name patterns (case-insensitive)
        brand_names = [self.brand_info.name] + self.brand_info.aliases
        brand_pattern = '|'.join(re.escape(name) for name in brand_names)
        self.brand_pattern = re.compile(rf'\b({brand_pattern})\b', re.IGNORECASE)
        
        # Website patterns
        website = self.brand_info.website
        # Extract domain from URL
        domain_match = re.search(r'https?://(?:www\.)?([^/]+)', website)
        if domain_match:
            domain = domain_match.group(1)
            # Match full URL or just domain
            self.website_pattern = re.compile(
                rf'({re.escape(website)}|{re.escape(domain)})', 
                re.IGNORECASE
            )
        else:
            self.website_pattern = re.compile(re.escape(website), re.IGNORECASE)
        
        # Competitor patterns
        self.competitor_patterns = {}
        for competitor in self.brand_info.competitors:
            pattern = re.compile(rf'\b{re.escape(competitor)}\b', re.IGNORECASE)
            self.competitor_patterns[competitor] = pattern
    
    def analyze_response(self, result: PromptResult, use_llm_sentiment: bool = True) -> ResponseAnalysis:
        """Analyze a single response for brand mentions and sentiment"""
        analysis = ResponseAnalysis()
        response_text = result.response
        
        if not response_text or result.error:
            return analysis
        
        # Count brand mentions
        brand_matches = list(self.brand_pattern.finditer(response_text))
        analysis.brand_mentions = len(brand_matches)
        
        # Count website mentions
        website_matches = list(self.website_pattern.finditer(response_text))
        analysis.website_mentions = len(website_matches)
        
        # Analyze mention positions and contexts
        if brand_matches or website_matches:
            analysis.mention_positions = self._analyze_positions(
                response_text, brand_matches + website_matches
            )
            analysis.mention_contexts = self._analyze_contexts(
                response_text, brand_matches + website_matches
            )
        
        # Count competitor mentions
        for competitor, pattern in self.competitor_patterns.items():
            matches = pattern.findall(response_text)
            if matches:
                analysis.competitor_mentions[competitor] = len(matches)
        
        # Analyze sentiment
        if use_llm_sentiment and self.llm_interface:
            analysis.sentiment_score, analysis.sentiment_label = self._analyze_sentiment_llm(
                response_text, result.prompt_text
            )
        else:
            analysis.sentiment_score, analysis.sentiment_label = self._analyze_sentiment_textblob(
                response_text
            )
        
        # Extract excerpt around first brand mention
        if brand_matches:
            analysis.response_excerpt = self._extract_excerpt(
                response_text, brand_matches[0].start()
            )
        else:
            # Use first 200 characters if no brand mention
            analysis.response_excerpt = response_text[:200] + "..." if len(response_text) > 200 else response_text
        
        return analysis
    
    def _analyze_positions(self, text: str, matches: List[re.Match]) -> List[str]:
        """Determine where in the response mentions appear"""
        positions = []
        text_length = len(text)
        
        # Define position thresholds
        first_third = text_length // 3
        second_third = 2 * text_length // 3
        
        for match in matches:
            position = match.start()
            if position < first_third:
                positions.append("first_paragraph")
            elif position < second_third:
                positions.append("middle")
            else:
                positions.append("conclusion")
        
        # Return unique positions in order
        seen = set()
        return [p for p in positions if not (p in seen or seen.add(p))]
    
    def _analyze_contexts(self, text: str, matches: List[re.Match]) -> List[MentionContext]:
        """Analyze the context of each mention"""
        contexts = []
        
        for match in matches:
            # Extract surrounding context (100 chars before and after)
            start = max(0, match.start() - 100)
            end = min(len(text), match.end() + 100)
            context_text = text[start:end]
            
            # Determine position
            position = self._get_position(text, match.start())
            
            # Determine context type
            context_type = self._classify_context(context_text.lower())
            
            contexts.append(MentionContext(
                text=context_text,
                position=position,
                context_type=context_type
            ))
        
        return contexts
    
    def _get_position(self, text: str, position: int) -> str:
        """Get position classification for a specific character position"""
        text_length = len(text)
        first_third = text_length // 3
        second_third = 2 * text_length // 3
        
        if position < first_third:
            return "first_paragraph"
        elif position < second_third:
            return "middle"
        else:
            return "conclusion"
    
    def _classify_context(self, context_text: str) -> str:
        """Classify the type of context a mention appears in"""
        # Keywords for different context types
        recommendation_keywords = ['recommend', 'suggest', 'best', 'should use', 'try', 'consider']
        comparison_keywords = ['compared to', 'versus', 'vs', 'better than', 'alternative', 'instead of']
        example_keywords = ['example', 'for instance', 'such as', 'like', 'e.g.']
        
        for keyword in recommendation_keywords:
            if keyword in context_text:
                return "recommendation"
        
        for keyword in comparison_keywords:
            if keyword in context_text:
                return "comparison"
        
        for keyword in example_keywords:
            if keyword in context_text:
                return "example"
        
        return "explanation"
    
    def _analyze_sentiment_textblob(self, text: str) -> Tuple[float, str]:
        """Analyze sentiment using TextBlob"""
        try:
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity  # -1 to 1
            
            # Classify sentiment
            if polarity > 0.1:
                label = "positive"
            elif polarity < -0.1:
                label = "negative"
            else:
                label = "neutral"
            
            return polarity, label
        
        except Exception as e:
            self.logger.error(f"Error in TextBlob sentiment analysis: {e}")
            return 0.0, "neutral"
    
    def _analyze_sentiment_llm(self, response_text: str, prompt_text: str) -> Tuple[float, str]:
        """Analyze sentiment using LLM"""
        if not self.llm_interface:
            return self._analyze_sentiment_textblob(response_text)
        
        sentiment_prompt = f"""Analyze the sentiment of the following LLM response about {self.brand_info.name} brand.

Original question: {prompt_text}

Response: {response_text[:1000]}...

Please analyze the sentiment and provide a JSON response with:
1. sentiment_score: A number between -1 (very negative) and 1 (very positive)
2. sentiment_label: One of "positive", "negative", or "neutral"
3. reasoning: Brief explanation of the sentiment

Respond only with valid JSON."""
        
        try:
            llm_response = self.llm_interface.generate(
                sentiment_prompt, 
                temperature=0.3,  # Lower temperature for more consistent analysis
                max_tokens=200
            )
            
            # Parse JSON response
            sentiment_data = json.loads(llm_response)
            score = float(sentiment_data.get('sentiment_score', 0))
            label = sentiment_data.get('sentiment_label', 'neutral')
            
            # Validate score range
            score = max(-1, min(1, score))
            
            return score, label
        
        except Exception as e:
            self.logger.warning(f"LLM sentiment analysis failed, falling back to TextBlob: {e}")
            return self._analyze_sentiment_textblob(response_text)
    
    def _extract_excerpt(self, text: str, position: int, context_length: int = 150) -> str:
        """Extract an excerpt around a specific position"""
        start = max(0, position - context_length)
        end = min(len(text), position + context_length)
        
        excerpt = text[start:end]
        
        # Add ellipsis if truncated
        if start > 0:
            excerpt = "..." + excerpt
        if end < len(text):
            excerpt = excerpt + "..."
        
        return excerpt
    
    def batch_analyze(self, results: List[PromptResult], use_llm_sentiment: bool = True) -> Dict[str, ResponseAnalysis]:
        """Analyze a batch of responses"""
        analyses = {}
        
        for result in results:
            self.logger.info(f"Analyzing response for prompt: {result.prompt_id}")
            analysis = self.analyze_response(result, use_llm_sentiment)
            analyses[result.prompt_id] = analysis
        
        return analyses