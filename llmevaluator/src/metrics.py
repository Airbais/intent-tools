"""
Metrics Calculator
Calculates aggregate metrics from response analyses
"""

import logging
from typing import Dict, List, Any
from dataclasses import dataclass, field
from collections import defaultdict
import statistics

from .analyzer import ResponseAnalysis
from .prompt_executor import PromptResult

@dataclass
class CategoryMetrics:
    prompts: int = 0
    total_mentions: int = 0
    total_website_mentions: int = 0
    average_sentiment: float = 0.0
    sentiment_distribution: Dict[str, int] = field(default_factory=dict)
    mention_rate: float = 0.0
    context_distribution: Dict[str, int] = field(default_factory=dict)

@dataclass
class AggregateMetrics:
    total_prompts: int = 0
    total_brand_mentions: int = 0
    total_website_mentions: int = 0
    average_sentiment: float = 0.0
    mention_rate: float = 0.0
    website_mention_rate: float = 0.0
    categories: Dict[str, CategoryMetrics] = field(default_factory=dict)
    sentiment_distribution: Dict[str, int] = field(default_factory=dict)
    position_distribution: Dict[str, int] = field(default_factory=dict)
    context_distribution: Dict[str, int] = field(default_factory=dict)
    competitor_comparison: Dict[str, int] = field(default_factory=dict)
    prompts_with_mentions: int = 0
    prompts_with_website: int = 0

class MetricsCalculator:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def calculate_metrics(self, results: List[PromptResult], 
                         analyses: Dict[str, ResponseAnalysis]) -> AggregateMetrics:
        """Calculate aggregate metrics from results and analyses"""
        metrics = AggregateMetrics()
        
        # Group results by category
        category_data = defaultdict(list)
        for result in results:
            if result.prompt_id in analyses:
                category_data[result.category].append((result, analyses[result.prompt_id]))
        
        # Calculate overall metrics
        all_sentiments = []
        
        for result in results:
            if result.prompt_id not in analyses:
                continue
            
            analysis = analyses[result.prompt_id]
            
            # Count totals
            metrics.total_prompts += 1
            metrics.total_brand_mentions += analysis.brand_mentions
            metrics.total_website_mentions += analysis.website_mentions
            
            # Track prompts with mentions
            if analysis.brand_mentions > 0:
                metrics.prompts_with_mentions += 1
            if analysis.website_mentions > 0:
                metrics.prompts_with_website += 1
            
            # Collect sentiment data
            all_sentiments.append(analysis.sentiment_score)
            metrics.sentiment_distribution[analysis.sentiment_label] = \
                metrics.sentiment_distribution.get(analysis.sentiment_label, 0) + 1
            
            # Position distribution
            for position in analysis.mention_positions:
                metrics.position_distribution[position] = \
                    metrics.position_distribution.get(position, 0) + 1
            
            # Context distribution
            for context in analysis.mention_contexts:
                metrics.context_distribution[context.context_type] = \
                    metrics.context_distribution.get(context.context_type, 0) + 1
            
            # Competitor mentions
            for competitor, count in analysis.competitor_mentions.items():
                metrics.competitor_comparison[competitor] = \
                    metrics.competitor_comparison.get(competitor, 0) + count
        
        # Calculate averages
        if metrics.total_prompts > 0:
            metrics.mention_rate = metrics.total_brand_mentions / metrics.total_prompts
            metrics.website_mention_rate = metrics.total_website_mentions / metrics.total_prompts
        
        if all_sentiments:
            metrics.average_sentiment = statistics.mean(all_sentiments)
        
        # Calculate category-specific metrics
        for category, category_items in category_data.items():
            cat_metrics = self._calculate_category_metrics(category_items)
            metrics.categories[category] = cat_metrics
        
        self.logger.info(f"Calculated metrics for {metrics.total_prompts} prompts")
        return metrics
    
    def _calculate_category_metrics(self, category_items: List[tuple]) -> CategoryMetrics:
        """Calculate metrics for a specific category"""
        cat_metrics = CategoryMetrics()
        sentiments = []
        
        for result, analysis in category_items:
            cat_metrics.prompts += 1
            cat_metrics.total_mentions += analysis.brand_mentions
            cat_metrics.total_website_mentions += analysis.website_mentions
            
            # Sentiment tracking
            sentiments.append(analysis.sentiment_score)
            cat_metrics.sentiment_distribution[analysis.sentiment_label] = \
                cat_metrics.sentiment_distribution.get(analysis.sentiment_label, 0) + 1
            
            # Context tracking
            for context in analysis.mention_contexts:
                cat_metrics.context_distribution[context.context_type] = \
                    cat_metrics.context_distribution.get(context.context_type, 0) + 1
        
        # Calculate averages
        if cat_metrics.prompts > 0:
            cat_metrics.mention_rate = cat_metrics.total_mentions / cat_metrics.prompts
        
        if sentiments:
            cat_metrics.average_sentiment = statistics.mean(sentiments)
        
        return cat_metrics
    
    def generate_insights(self, metrics: AggregateMetrics) -> List[str]:
        """Generate human-readable insights from metrics"""
        insights = []
        
        # Brand presence insight
        if metrics.total_prompts > 0:
            mention_percentage = (metrics.prompts_with_mentions / metrics.total_prompts) * 100
            insights.append(
                f"Brand mentioned in {mention_percentage:.1f}% of responses "
                f"({metrics.prompts_with_mentions}/{metrics.total_prompts} prompts)"
            )
        
        # Sentiment insight
        if metrics.average_sentiment > 0.3:
            insights.append(f"Overall sentiment is positive (score: {metrics.average_sentiment:.2f})")
        elif metrics.average_sentiment < -0.3:
            insights.append(f"Overall sentiment is negative (score: {metrics.average_sentiment:.2f})")
        else:
            insights.append(f"Overall sentiment is neutral (score: {metrics.average_sentiment:.2f})")
        
        # Position insight
        if metrics.position_distribution:
            most_common_position = max(metrics.position_distribution.items(), key=lambda x: x[1])
            insights.append(f"Brand most frequently mentioned in {most_common_position[0]} of responses")
        
        # Context insight
        if metrics.context_distribution:
            most_common_context = max(metrics.context_distribution.items(), key=lambda x: x[1])
            insights.append(f"Brand most often mentioned in {most_common_context[0]} context")
        
        # Category performance
        if metrics.categories:
            best_category = max(
                metrics.categories.items(), 
                key=lambda x: x[1].mention_rate
            )
            insights.append(
                f"Highest brand mention rate in '{best_category[0]}' category "
                f"({best_category[1].mention_rate:.1f} mentions per prompt)"
            )
        
        # Competitor comparison
        if metrics.competitor_comparison:
            total_competitor_mentions = sum(metrics.competitor_comparison.values())
            if total_competitor_mentions > 0:
                insights.append(
                    f"Competitors mentioned {total_competitor_mentions} times "
                    f"vs brand's {metrics.total_brand_mentions} mentions"
                )
        
        return insights
    
    def to_dict(self, metrics: AggregateMetrics) -> Dict[str, Any]:
        """Convert metrics to dictionary format"""
        return {
            'total_prompts': metrics.total_prompts,
            'total_brand_mentions': metrics.total_brand_mentions,
            'total_website_mentions': metrics.total_website_mentions,
            'average_sentiment': round(metrics.average_sentiment, 3),
            'mention_rate': round(metrics.mention_rate, 2),
            'website_mention_rate': round(metrics.website_mention_rate, 2),
            'prompts_with_mentions': metrics.prompts_with_mentions,
            'prompts_with_website': metrics.prompts_with_website,
            'sentiment_distribution': metrics.sentiment_distribution,
            'position_distribution': metrics.position_distribution,
            'context_distribution': metrics.context_distribution,
            'competitor_comparison': metrics.competitor_comparison,
            'categories': {
                name: {
                    'prompts': cat.prompts,
                    'mentions': cat.total_mentions,
                    'website_mentions': cat.total_website_mentions,
                    'sentiment': round(cat.average_sentiment, 3),
                    'mention_rate': round(cat.mention_rate, 2),
                    'sentiment_distribution': cat.sentiment_distribution,
                    'context_distribution': cat.context_distribution
                }
                for name, cat in metrics.categories.items()
            }
        }