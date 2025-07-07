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

@dataclass
class ComparativeMetrics:
    """Metrics comparing performance across multiple LLMs"""
    enabled: bool = True
    mention_rate_variance: float = 0.0
    sentiment_alignment: float = 0.0
    consensus_score: float = 0.0
    response_consistency: Dict[str, float] = field(default_factory=dict)
    llm_agreement_matrix: Dict[str, Dict[str, float]] = field(default_factory=dict)

@dataclass
class MultiLLMMetrics:
    """Container for multi-LLM evaluation metrics"""
    llm_metrics: Dict[str, AggregateMetrics] = field(default_factory=dict)
    comparative_metrics: ComparativeMetrics = field(default_factory=ComparativeMetrics)
    aggregate_metrics: AggregateMetrics = field(default_factory=AggregateMetrics)

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
            
            # Collect sentiment data (only for responses with brand mentions)
            if analysis.sentiment_label != "not_mentioned":
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
    
    def calculate_multi_llm_metrics(self, results: List['MultiLLMPromptResult'], 
                                   analyses: Dict[str, Dict[str, ResponseAnalysis]]) -> 'MultiLLMMetrics':
        """Calculate metrics for multi-LLM evaluation"""
        multi_metrics = MultiLLMMetrics()
        
        # Get list of LLM names
        llm_names = set()
        for result in results:
            llm_names.update(result.llm_results.keys())
        llm_names = sorted(llm_names)
        
        # Calculate per-LLM metrics
        for llm_name in llm_names:
            llm_results = []
            llm_analyses = {}
            
            # Extract results for this LLM
            for prompt_result in results:
                if llm_name in prompt_result.llm_results:
                    llm_result = prompt_result.llm_results[llm_name]
                    llm_results.append(llm_result)
                    
                    # Get corresponding analysis
                    if prompt_result.prompt_id in analyses and llm_name in analyses[prompt_result.prompt_id]:
                        llm_analyses[llm_result.prompt_id] = analyses[prompt_result.prompt_id][llm_name]
            
            # Calculate metrics for this LLM
            multi_metrics.llm_metrics[llm_name] = self.calculate_metrics(llm_results, llm_analyses)
        
        # Calculate comparative metrics if more than one LLM
        if len(llm_names) > 1:
            multi_metrics.comparative_metrics = self._calculate_comparative_metrics(results, analyses)
        else:
            multi_metrics.comparative_metrics.enabled = False
        
        # Calculate aggregate metrics across all LLMs
        multi_metrics.aggregate_metrics = self._calculate_aggregate_multi_metrics(multi_metrics.llm_metrics)
        
        self.logger.info(f"Calculated multi-LLM metrics for {len(llm_names)} LLMs")
        return multi_metrics
    
    def _calculate_category_metrics(self, category_items: List[tuple]) -> CategoryMetrics:
        """Calculate metrics for a specific category"""
        cat_metrics = CategoryMetrics()
        sentiments = []
        
        for result, analysis in category_items:
            cat_metrics.prompts += 1
            cat_metrics.total_mentions += analysis.brand_mentions
            cat_metrics.total_website_mentions += analysis.website_mentions
            
            # Sentiment tracking (only for responses with brand mentions)
            if analysis.sentiment_label != "not_mentioned":
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
    
    def _calculate_comparative_metrics(self, results: List['MultiLLMPromptResult'], 
                                     analyses: Dict[str, Dict[str, ResponseAnalysis]]) -> 'ComparativeMetrics':
        """Calculate metrics comparing LLM performance"""
        comp_metrics = ComparativeMetrics()
        
        # Get LLM names
        llm_names = set()
        for result in results:
            llm_names.update(result.llm_results.keys())
        
        # Calculate mention rate variance
        mention_rates = []
        for llm_name in llm_names:
            mentions = 0
            total = 0
            for prompt_result in results:
                if llm_name in prompt_result.llm_results and prompt_result.prompt_id in analyses:
                    if llm_name in analyses[prompt_result.prompt_id]:
                        analysis = analyses[prompt_result.prompt_id][llm_name]
                        mentions += 1 if analysis.brand_mentions > 0 else 0
                        total += 1
            if total > 0:
                mention_rates.append(mentions / total)
        
        if len(mention_rates) > 1:
            comp_metrics.mention_rate_variance = statistics.stdev(mention_rates)
        
        # Calculate sentiment alignment
        sentiment_scores = defaultdict(list)
        for prompt_result in results:
            prompt_id = prompt_result.prompt_id
            if prompt_id in analyses:
                for llm_name, analysis in analyses[prompt_id].items():
                    if analysis.sentiment_label != "not_mentioned":
                        sentiment_scores[prompt_id].append((llm_name, analysis.sentiment_score))
        
        # Calculate pairwise sentiment correlation
        if len(sentiment_scores) > 0:
            total_alignment = 0
            count = 0
            for prompt_sentiments in sentiment_scores.values():
                if len(prompt_sentiments) > 1:
                    # Calculate variance for this prompt
                    scores = [s[1] for s in prompt_sentiments]
                    if len(scores) > 1:
                        alignment = 1 - min(statistics.stdev(scores), 1.0)  # Normalize to 0-1
                        total_alignment += alignment
                        count += 1
            
            comp_metrics.sentiment_alignment = total_alignment / count if count > 0 else 0.0
        
        # Calculate consensus score (how often LLMs agree on mentioning the brand)
        mention_agreement = 0
        total_prompts = 0
        
        for prompt_result in results:
            prompt_id = prompt_result.prompt_id
            if prompt_id in analyses:
                mentions = []
                for llm_name in llm_names:
                    if llm_name in analyses[prompt_id]:
                        analysis = analyses[prompt_id][llm_name]
                        mentions.append(1 if analysis.brand_mentions > 0 else 0)
                
                if len(mentions) == len(llm_names):
                    # All agree (either all mention or all don't mention)
                    if all(m == mentions[0] for m in mentions):
                        mention_agreement += 1
                    total_prompts += 1
        
        comp_metrics.consensus_score = mention_agreement / total_prompts if total_prompts > 0 else 0.0
        
        return comp_metrics
    
    def _calculate_aggregate_multi_metrics(self, llm_metrics: Dict[str, AggregateMetrics]) -> AggregateMetrics:
        """Calculate aggregate metrics across all LLMs"""
        agg = AggregateMetrics()
        
        if not llm_metrics:
            return agg
        
        # Get the first LLM metrics as reference for structure
        first_metrics = next(iter(llm_metrics.values()))
        agg.total_prompts = first_metrics.total_prompts
        
        # Calculate averages across all LLMs
        all_mention_rates = []
        all_sentiments = []
        
        for metrics in llm_metrics.values():
            all_mention_rates.append(metrics.mention_rate)
            if metrics.average_sentiment != 0.0:
                all_sentiments.append(metrics.average_sentiment)
            
            # Aggregate counts
            agg.total_brand_mentions += metrics.total_brand_mentions
            agg.total_website_mentions += metrics.total_website_mentions
            agg.prompts_with_mentions += metrics.prompts_with_mentions
            agg.prompts_with_website += metrics.prompts_with_website
        
        # Calculate averages
        num_llms = len(llm_metrics)
        if num_llms > 0:
            agg.mention_rate = statistics.mean(all_mention_rates)
            agg.website_mention_rate = agg.total_website_mentions / (agg.total_prompts * num_llms)
            agg.prompts_with_mentions = agg.prompts_with_mentions / num_llms
            agg.prompts_with_website = agg.prompts_with_website / num_llms
        
        if all_sentiments:
            agg.average_sentiment = statistics.mean(all_sentiments)
        
        return agg
    
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
        
        # Sentiment insight - only for responses with brand mentions
        not_mentioned_count = metrics.sentiment_distribution.get("not_mentioned", 0)
        brand_mentioned_count = metrics.total_prompts - not_mentioned_count
        
        if brand_mentioned_count > 0:
            if metrics.average_sentiment > 0.3:
                insights.append(f"Brand sentiment is positive when mentioned (score: {metrics.average_sentiment:.2f}, {brand_mentioned_count} mentions)")
            elif metrics.average_sentiment < -0.3:
                insights.append(f"Brand sentiment is negative when mentioned (score: {metrics.average_sentiment:.2f}, {brand_mentioned_count} mentions)")
            else:
                insights.append(f"Brand sentiment is neutral when mentioned (score: {metrics.average_sentiment:.2f}, {brand_mentioned_count} mentions)")
        else:
            insights.append("No brand-specific sentiment available (brand not mentioned in any responses)")
        
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