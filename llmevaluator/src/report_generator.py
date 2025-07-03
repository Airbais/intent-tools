"""
Report Generator
Generates dashboard-compatible reports and exports
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from .config import ConfigurationManager
from .prompt_executor import PromptResult
from .analyzer import ResponseAnalysis
from .metrics import AggregateMetrics, MetricsCalculator

class ReportGenerator:
    def __init__(self, output_dir: str = "./results"):
        self.output_dir = Path(output_dir)
        self.logger = logging.getLogger(__name__)
    
    def generate_dashboard_data(self, 
                              config: ConfigurationManager,
                              results: List[PromptResult],
                              analyses: Dict[str, ResponseAnalysis],
                              metrics: AggregateMetrics,
                              insights: List[str]) -> Dict[str, Any]:
        """Generate dashboard-compatible data structure"""
        
        # Build evaluation results
        evaluation_results = []
        for result in results:
            if result.prompt_id not in analyses:
                continue
            
            analysis = analyses[result.prompt_id]
            
            eval_result = {
                'prompt': result.prompt_text,
                'category': result.category,
                'response_analysis': {
                    'brand_mentions': analysis.brand_mentions,
                    'website_mentions': analysis.website_mentions,
                    'sentiment_score': round(analysis.sentiment_score, 3),
                    'sentiment_label': analysis.sentiment_label,
                    'mention_positions': analysis.mention_positions,
                    'competitor_mentions': analysis.competitor_mentions,
                    'mention_contexts': [
                        {
                            'type': ctx.context_type,
                            'position': ctx.position
                        } for ctx in analysis.mention_contexts
                    ]
                },
                'response_excerpt': analysis.response_excerpt,
                'timestamp': result.timestamp,
                'cached': result.cached,
                'error': result.error
            }
            
            evaluation_results.append(eval_result)
        
        # Build aggregate metrics
        metrics_dict = MetricsCalculator().to_dict(metrics)
        
        # Build complete dashboard data
        dashboard_data = {
            'evaluation_results': evaluation_results,
            'aggregate_metrics': metrics_dict,
            'insights': insights,
            'brand_info': {
                'name': config.brand_info.name,
                'website': config.brand_info.website,
                'aliases': config.brand_info.aliases,
                'competitors': config.brand_info.competitors,
                'evaluation_date': datetime.now().isoformat(),
                'llm_provider': config.settings.llm_provider,
                'llm_model': config.settings.model
            },
            'evaluation_summary': {
                'total_prompts_evaluated': len(results),
                'successful_evaluations': sum(1 for r in results if not r.error),
                'failed_evaluations': sum(1 for r in results if r.error),
                'cached_responses': sum(1 for r in results if r.cached),
                'categories_evaluated': list(set(r.category for r in results))
            }
        }
        
        return dashboard_data
    
    def save_report(self, dashboard_data: Dict[str, Any], 
                   timestamp: Optional[datetime] = None) -> Path:
        """Save report to results directory with timestamp"""
        if timestamp is None:
            timestamp = datetime.now()
        
        # Create timestamped directory
        date_str = timestamp.strftime('%Y-%m-%d')
        results_dir = self.output_dir / date_str
        results_dir.mkdir(parents=True, exist_ok=True)
        
        # Save dashboard data
        dashboard_file = results_dir / 'dashboard-data.json'
        with open(dashboard_file, 'w', encoding='utf-8') as f:
            json.dump(dashboard_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Saved dashboard data to {dashboard_file}")
        
        # Save detailed results
        self._save_detailed_results(dashboard_data, results_dir)
        
        return results_dir
    
    def _save_detailed_results(self, dashboard_data: Dict[str, Any], 
                             results_dir: Path) -> None:
        """Save additional detailed results files"""
        
        # Save raw evaluation results
        raw_results_file = results_dir / 'raw_results.json'
        with open(raw_results_file, 'w', encoding='utf-8') as f:
            json.dump(dashboard_data['evaluation_results'], f, indent=2, ensure_ascii=False)
        
        # Generate and save text report
        text_report = self._generate_text_report(dashboard_data)
        report_file = results_dir / 'evaluation_report.txt'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(text_report)
        
        # Save metrics summary
        metrics_file = results_dir / 'metrics_summary.json'
        with open(metrics_file, 'w', encoding='utf-8') as f:
            json.dump(dashboard_data['aggregate_metrics'], f, indent=2)
        
        self.logger.info(f"Saved additional reports to {results_dir}")
    
    def _generate_text_report(self, dashboard_data: Dict[str, Any]) -> str:
        """Generate human-readable text report"""
        brand_info = dashboard_data['brand_info']
        metrics = dashboard_data['aggregate_metrics']
        summary = dashboard_data['evaluation_summary']
        insights = dashboard_data.get('insights', [])
        
        report = []
        report.append("=" * 60)
        report.append(f"LLM Brand Evaluation Report for {brand_info['name']}")
        report.append("=" * 60)
        report.append(f"\nEvaluation Date: {brand_info['evaluation_date']}")
        report.append(f"Website: {brand_info['website']}")
        report.append(f"LLM Provider: {brand_info['llm_provider']} ({brand_info['llm_model']})")
        report.append(f"\nTotal Prompts Evaluated: {summary['total_prompts_evaluated']}")
        report.append(f"Successful: {summary['successful_evaluations']}")
        report.append(f"Failed: {summary['failed_evaluations']}")
        report.append(f"Cached: {summary['cached_responses']}")
        
        report.append("\n" + "-" * 60)
        report.append("OVERALL METRICS")
        report.append("-" * 60)
        report.append(f"Total Brand Mentions: {metrics['total_brand_mentions']}")
        report.append(f"Total Website Mentions: {metrics['total_website_mentions']}")
        report.append(f"Average Mentions per Prompt: {metrics['mention_rate']:.2f}")
        report.append(f"Average Sentiment Score: {metrics['average_sentiment']:.3f}")
        report.append(f"Prompts with Brand Mentions: {metrics['prompts_with_mentions']}/{metrics['total_prompts']}")
        
        if metrics['sentiment_distribution']:
            report.append("\nSentiment Distribution:")
            for sentiment, count in metrics['sentiment_distribution'].items():
                percentage = (count / metrics['total_prompts']) * 100
                report.append(f"  - {sentiment.capitalize()}: {count} ({percentage:.1f}%)")
        
        if metrics['position_distribution']:
            report.append("\nMention Position Distribution:")
            for position, count in metrics['position_distribution'].items():
                report.append(f"  - {position}: {count}")
        
        if metrics['context_distribution']:
            report.append("\nMention Context Distribution:")
            for context, count in metrics['context_distribution'].items():
                report.append(f"  - {context}: {count}")
        
        if metrics['competitor_comparison']:
            report.append("\nCompetitor Mentions:")
            for competitor, count in metrics['competitor_comparison'].items():
                report.append(f"  - {competitor}: {count}")
        
        report.append("\n" + "-" * 60)
        report.append("CATEGORY BREAKDOWN")
        report.append("-" * 60)
        for category, cat_metrics in metrics['categories'].items():
            report.append(f"\n{category}:")
            report.append(f"  - Prompts: {cat_metrics['prompts']}")
            report.append(f"  - Total Mentions: {cat_metrics['mentions']}")
            report.append(f"  - Mention Rate: {cat_metrics['mention_rate']:.2f}")
            report.append(f"  - Average Sentiment: {cat_metrics['sentiment']:.3f}")
        
        if insights:
            report.append("\n" + "-" * 60)
            report.append("KEY INSIGHTS")
            report.append("-" * 60)
            for i, insight in enumerate(insights, 1):
                report.append(f"{i}. {insight}")
        
        report.append("\n" + "=" * 60)
        report.append("END OF REPORT")
        report.append("=" * 60)
        
        return "\n".join(report)