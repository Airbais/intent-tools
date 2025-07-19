"""
Main GRASP evaluation engine
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

from config_manager import ConfigManager
from metrics.grounded import GroundedEvaluator
from metrics.readable import ReadableEvaluator
from metrics.accurate import AccurateEvaluator
from metrics.structured import StructuredEvaluator
from metrics.polished import PolishedEvaluator
from utils.content_extractor import ContentExtractor
from utils.scoring import ScoringEngine


class GRASPEvaluator:
    """Main GRASP evaluation orchestrator"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = ConfigManager(config_path)
        self.logger = logging.getLogger(__name__)
        
        # Initialize evaluators
        self.grounded_evaluator = GroundedEvaluator(self.config)
        self.readable_evaluator = ReadableEvaluator(self.config)
        self.accurate_evaluator = AccurateEvaluator(self.config)
        self.structured_evaluator = StructuredEvaluator(self.config)
        self.polished_evaluator = PolishedEvaluator(self.config)
        
        # Initialize utilities
        self.content_extractor = ContentExtractor()
        self.scoring_engine = ScoringEngine()
        
    async def evaluate_website(self, url: str) -> Dict:
        """Evaluate a website using GRASP metrics"""
        self.logger.info(f"Starting GRASP evaluation for: {url}")
        
        try:
            # Fetch and extract content
            html_content, text_content = await self._fetch_content(url)
            
            # Run all evaluations concurrently
            tasks = [
                self._evaluate_grounded(text_content),
                self._evaluate_readable(text_content),
                self._evaluate_accurate(html_content, url),
                self._evaluate_structured(html_content),
                self._evaluate_polished(text_content)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            grounded_score, readable_result, accurate_result, structured_result, polished_result = results
            
            # Handle any exceptions
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"Error in evaluation {i}: {result}")
                    results[i] = self._get_default_result(i)
            
            # Calculate overall GRASP score
            metrics = {
                'grounded': grounded_score,
                'readable': readable_result,
                'accurate': accurate_result,
                'structured': structured_result,
                'polished': polished_result
            }
            
            overall_score = self.scoring_engine.calculate_grasp_score(metrics)
            
            # Generate enhanced recommendations
            enhanced_recommendations = await self._generate_enhanced_recommendations(metrics, text_content, html_content, url)
            
            # Prepare results
            evaluation_result = {
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'overall_score': overall_score,
                'metrics': metrics,
                'breakdown': self._create_breakdown(metrics),
                'recommendations': self._generate_recommendations(metrics),  # Legacy format
                'enhanced_recommendations': enhanced_recommendations  # New detailed format
            }
            
            self.logger.info(f"GRASP evaluation completed. Overall score: {overall_score}")
            return evaluation_result
            
        except Exception as e:
            self.logger.error(f"Error evaluating website {url}: {e}")
            raise
    
    async def _fetch_content(self, url: str) -> Tuple[str, str]:
        """Fetch and extract content from URL"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            html_content = response.text
            
            # Extract clean text content
            text_content = self.content_extractor.extract_text(html_content)
            
            return html_content, text_content
            
        except Exception as e:
            self.logger.error(f"Error fetching content from {url}: {e}")
            raise
    
    async def _evaluate_grounded(self, content: str) -> float:
        """Evaluate grounded metric"""
        try:
            intents = self.config.get_intents()
            return await self.grounded_evaluator.evaluate(content, intents)
        except Exception as e:
            self.logger.error(f"Error in grounded evaluation: {e}")
            return 0.0
    
    async def _evaluate_readable(self, content: str) -> bool:
        """Evaluate readable metric"""
        try:
            target_level = self.config.get_target_audience()
            return self.readable_evaluator.evaluate(content, target_level)
        except Exception as e:
            self.logger.error(f"Error in readable evaluation: {e}")
            return False
    
    async def _evaluate_accurate(self, html: str, url: str) -> str:
        """Evaluate accurate metric"""
        try:
            return self.accurate_evaluator.evaluate(html, url)
        except Exception as e:
            self.logger.error(f"Error in accurate evaluation: {e}")
            return "Low"
    
    async def _evaluate_structured(self, html: str) -> str:
        """Evaluate structured metric"""
        try:
            return self.structured_evaluator.evaluate(html)
        except Exception as e:
            self.logger.error(f"Error in structured evaluation: {e}")
            return "Poor"
    
    async def _evaluate_polished(self, content: str) -> str:
        """Evaluate polished metric"""
        try:
            return await self.polished_evaluator.evaluate(content)
        except Exception as e:
            self.logger.error(f"Error in polished evaluation: {e}")
            return "Poor"
    
    def _get_default_result(self, evaluation_index: int):
        """Get default result for failed evaluations"""
        defaults = [0.0, False, "Low", "Poor", "Poor"]
        return defaults[evaluation_index]
    
    def _create_breakdown(self, metrics: Dict) -> Dict:
        """Create detailed breakdown of scores"""
        weights = {
            'grounded': 0.40,
            'readable': 0.10,
            'accurate': 0.30,
            'structured': 0.10,
            'polished': 0.10
        }
        
        breakdown = {}
        for metric, weight in weights.items():
            normalized_score = self.scoring_engine.normalize_metric(metrics[metric], metric)
            breakdown[metric] = {
                'score': metrics[metric],
                'normalized': normalized_score,
                'weight': weight,
                'weighted_contribution': normalized_score * weight
            }
        
        return breakdown
    
    def _generate_recommendations(self, metrics: Dict) -> List[str]:
        """Generate improvement recommendations based on metrics"""
        recommendations = []
        
        # Grounded recommendations
        if metrics['grounded'] < 7.0:
            recommendations.append("Improve content alignment with customer intents. Consider adding more specific information that directly addresses user questions.")
        
        # Readable recommendations
        if not metrics['readable']:
            recommendations.append("Adjust content reading level to match your target audience. Consider simplifying complex sentences or adding explanations for technical terms.")
        
        # Accurate recommendations
        if metrics['accurate'] == 'Low':
            recommendations.append("Update content with recent information. Add last-modified dates or timestamps to improve content freshness signals.")
        
        # Structured recommendations
        if metrics['structured'] in ['Poor', 'Very Poor']:
            recommendations.append("Improve HTML structure with semantic elements, proper heading hierarchy, and schema markup for better LLM understanding.")
        
        # Polished recommendations
        if metrics['polished'] in ['Poor', 'Very Poor']:
            recommendations.append("Review and improve grammar, spelling, and writing quality throughout the content.")
        
        return recommendations
    
    async def _generate_enhanced_recommendations(self, metrics: Dict, text_content: str, html_content: str = "", url: str = "") -> List[Dict]:
        """Generate enhanced recommendations across all metrics"""
        all_recommendations = []
        
        # Collect enhanced recommendations from each metric evaluator
        try:
            # Grounded recommendations
            grounded_detailed = await self.grounded_evaluator.get_detailed_analysis(text_content, self.config.get_intents())
            grounded_recs = await self.grounded_evaluator._generate_enhanced_recommendations(
                grounded_detailed.get('intent_scores', []),
                metrics['grounded'],
                text_content
            )
            all_recommendations.extend(grounded_recs)
        except Exception as e:
            self.logger.error(f"Error generating grounded recommendations: {e}")
        
        try:
            # Readable recommendations
            target_level = self.config.get_target_audience()
            readable_recs = await self.readable_evaluator.generate_enhanced_recommendations(
                text_content, target_level, metrics['readable']
            )
            all_recommendations.extend(readable_recs)
        except Exception as e:
            self.logger.error(f"Error generating readable recommendations: {e}")
        
        try:
            # Accurate recommendations
            accurate_recs = await self.accurate_evaluator.generate_enhanced_recommendations(
                html_content, url, metrics['accurate']
            )
            all_recommendations.extend(accurate_recs)
        except Exception as e:
            self.logger.error(f"Error generating accurate recommendations: {e}")
        
        try:
            # Structured recommendations
            structured_recs = await self.structured_evaluator.generate_enhanced_recommendations(
                html_content, metrics['structured']
            )
            all_recommendations.extend(structured_recs)
        except Exception as e:
            self.logger.error(f"Error generating structured recommendations: {e}")
        
        try:
            # Polished recommendations
            polished_recs = await self.polished_evaluator.generate_enhanced_recommendations(
                text_content, metrics['polished']
            )
            all_recommendations.extend(polished_recs)
        except Exception as e:
            self.logger.error(f"Error generating polished recommendations: {e}")
        
        # Sort recommendations by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        all_recommendations.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 3))
        
        return all_recommendations
    
    def save_results(self, results: Dict, output_dir: Optional[str] = None) -> str:
        """Save evaluation results to files"""
        if output_dir is None:
            timestamp = datetime.now().strftime("%Y-%m-%d")
            output_dir = Path(__file__).parent.parent / "results" / timestamp
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save detailed results
        results_file = output_dir / "grasp_evaluation_results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Save dashboard data
        dashboard_data = self._prepare_dashboard_data(results)
        dashboard_file = output_dir / "dashboard-data.json"
        with open(dashboard_file, 'w') as f:
            json.dump(dashboard_data, f, indent=2)
        
        self.logger.info(f"Results saved to {output_dir}")
        return str(output_dir)
    
    def _prepare_dashboard_data(self, results: Dict) -> Dict:
        """Prepare data for dashboard display"""
        return {
            "tool": "graspevaluator",
            "version": "1.0.0",
            "timestamp": results['timestamp'],
            "url": results['url'],
            "overall_score": results['overall_score'],
            "metrics": {
                "grounded": {
                    "score": results['metrics']['grounded'],
                    "normalized_score": results['metrics']['grounded'] * 10,
                    "weight": 40,
                    "description": "Content alignment with customer intents"
                },
                "readable": {
                    "score": results['metrics']['readable'],
                    "normalized_score": 100 if results['metrics']['readable'] else 0,
                    "weight": 10,
                    "description": "Appropriate reading level for target audience"
                },
                "accurate": {
                    "score": results['metrics']['accurate'],
                    "normalized_score": {"High": 100, "Medium": 50, "Low": 0}.get(results['metrics']['accurate'], 0),
                    "weight": 30,
                    "description": "Content freshness as accuracy proxy"
                },
                "structured": {
                    "score": results['metrics']['structured'],
                    "normalized_score": self.scoring_engine.rating_to_score(results['metrics']['structured']),
                    "weight": 10,
                    "description": "Semantic HTML structure for LLM consumption"
                },
                "polished": {
                    "score": results['metrics']['polished'],
                    "normalized_score": self.scoring_engine.rating_to_score(results['metrics']['polished']),
                    "weight": 10,
                    "description": "Grammar and language quality"
                }
            },
            "recommendations": results['recommendations'],
            "enhanced_recommendations": results.get('enhanced_recommendations', []),
            "breakdown": results['breakdown']
        }