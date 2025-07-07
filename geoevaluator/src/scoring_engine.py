"""
Scoring engine for the GEO Evaluator
Implements weighted scoring algorithm and grade calculation
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class AnalysisResult:
    """Result from a single analyzer."""
    category: str
    score: float  # 0.0 to 1.0
    max_score: float = 1.0
    details: Dict[str, Any] = None
    recommendations: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}
        if self.recommendations is None:
            self.recommendations = []


@dataclass
class CategoryScore:
    """Score for a single category."""
    category: str
    score: float  # 0.0 to 100.0
    weight: float
    weighted_score: float
    grade: str
    details: Dict[str, Any] = None
    recommendations: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}
        if self.recommendations is None:
            self.recommendations = []


@dataclass
class OverallScore:
    """Overall GEO optimization score."""
    total_score: float  # 0.0 to 100.0
    grade: str
    category_scores: Dict[str, CategoryScore]
    page_count: int
    recommendations: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.recommendations is None:
            self.recommendations = []


class BaseAnalyzer(ABC):
    """Base class for all content analyzers."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.analysis_config = config.get('analysis', {})
        self.thresholds = self.analysis_config.get('thresholds', {})
    
    @abstractmethod
    def analyze(self, pages: List[Dict[str, Any]]) -> AnalysisResult:
        """Analyze pages and return result."""
        pass
    
    @abstractmethod
    def get_category_name(self) -> str:
        """Get the category name for this analyzer."""
        pass
    
    def _calculate_percentage_score(self, value: float, excellent_threshold: float, 
                                  good_threshold: float, fair_threshold: float = None) -> float:
        """
        Calculate a percentage score based on thresholds.
        
        Args:
            value: The value to score (0.0 to 1.0)
            excellent_threshold: Threshold for excellent score (e.g., 0.80)
            good_threshold: Threshold for good score (e.g., 0.60)
            fair_threshold: Threshold for fair score (e.g., 0.40)
        
        Returns:
            Score from 0.0 to 1.0
        """
        if fair_threshold is None:
            fair_threshold = good_threshold * 0.67
        
        if value >= excellent_threshold:
            # Scale from excellent_threshold to 1.0 -> 0.8 to 1.0
            normalized = (value - excellent_threshold) / (1.0 - excellent_threshold)
            return 0.8 + (normalized * 0.2)
        elif value >= good_threshold:
            # Scale from good_threshold to excellent_threshold -> 0.6 to 0.8
            normalized = (value - good_threshold) / (excellent_threshold - good_threshold)
            return 0.6 + (normalized * 0.2)
        elif value >= fair_threshold:
            # Scale from fair_threshold to good_threshold -> 0.4 to 0.6
            normalized = (value - fair_threshold) / (good_threshold - fair_threshold)
            return 0.4 + (normalized * 0.2)
        else:
            # Scale from 0 to fair_threshold -> 0.0 to 0.4
            normalized = value / fair_threshold
            return normalized * 0.4
    
    def _create_recommendation(self, title: str, description: str, priority: str = "medium",
                             category: str = None, pages_affected: int = 0,
                             estimated_impact: str = "medium") -> Dict[str, Any]:
        """Create a recommendation dictionary."""
        return {
            'title': title,
            'description': description,
            'priority': priority,  # high, medium, low
            'category': category or self.get_category_name(),
            'pages_affected': pages_affected,
            'estimated_impact': estimated_impact  # high, medium, low
        }


class ScoringEngine:
    """
    Main scoring engine that aggregates analyzer results into final scores.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Get scoring weights
        weights_config = config.get('analysis', {}).get('weights', {})
        self.weights = {
            'structural_html': weights_config.get('structural_html', 0.25),
            'content_organization': weights_config.get('content_organization', 0.30),
            'token_efficiency': weights_config.get('token_efficiency', 0.20),
            'llm_technical': weights_config.get('llm_technical', 0.15),
            'accessibility': weights_config.get('accessibility', 0.10)
        }
        
        # Validate weights sum to 1.0
        total_weight = sum(self.weights.values())
        if abs(total_weight - 1.0) > 0.01:
            self.logger.warning(f"Weights sum to {total_weight:.3f}, normalizing to 1.0")
            for key in self.weights:
                self.weights[key] = self.weights[key] / total_weight
    
    def calculate_scores(self, analysis_results: Dict[str, AnalysisResult], 
                        page_count: int) -> OverallScore:
        """
        Calculate final scores from analyzer results.
        
        Args:
            analysis_results: Dict mapping category name to AnalysisResult
            page_count: Number of pages analyzed
        
        Returns:
            OverallScore with all calculations
        """
        
        category_scores = {}
        total_weighted_score = 0.0
        all_recommendations = []
        
        # Calculate category scores
        for category_name, weight in self.weights.items():
            if category_name in analysis_results:
                result = analysis_results[category_name]
                
                # Convert 0-1 score to 0-100
                score_100 = result.score * 100.0
                weighted_score = score_100 * weight
                total_weighted_score += weighted_score
                
                # Determine grade
                grade = self._score_to_grade(score_100)
                
                category_score = CategoryScore(
                    category=category_name,
                    score=score_100,
                    weight=weight,
                    weighted_score=weighted_score,
                    grade=grade,
                    details=result.details,
                    recommendations=result.recommendations
                )
                
                category_scores[category_name] = category_score
                all_recommendations.extend(result.recommendations)
                
            else:
                self.logger.warning(f"Missing analysis result for category: {category_name}")
                # Create empty result with 0 score
                category_score = CategoryScore(
                    category=category_name,
                    score=0.0,
                    weight=weight,
                    weighted_score=0.0,
                    grade="Very Poor",
                    details={'error': 'Analysis not completed'},
                    recommendations=[self._create_missing_analysis_recommendation(category_name)]
                )
                category_scores[category_name] = category_score
                all_recommendations.extend(category_score.recommendations)
        
        # Calculate overall grade
        overall_grade = self._score_to_grade(total_weighted_score)
        
        # Sort recommendations by priority
        sorted_recommendations = self._sort_recommendations(all_recommendations)
        
        overall_score = OverallScore(
            total_score=round(total_weighted_score, 1),
            grade=overall_grade,
            category_scores=category_scores,
            page_count=page_count,
            recommendations=sorted_recommendations
        )
        
        self.logger.info(f"Calculated overall score: {overall_score.total_score:.1f}/100 ({overall_grade})")
        
        return overall_score
    
    def _score_to_grade(self, score: float) -> str:
        """Convert numeric score to letter grade."""
        if score >= 90:
            return "Excellent"
        elif score >= 80:
            return "Good"
        elif score >= 70:
            return "Fair"
        elif score >= 60:
            return "Poor"
        else:
            return "Very Poor"
    
    def _create_missing_analysis_recommendation(self, category: str) -> Dict[str, Any]:
        """Create recommendation for missing analysis."""
        return {
            'title': f'Complete {category.replace("_", " ").title()} Analysis',
            'description': f'Analysis for {category} category was not completed',
            'priority': 'high',
            'category': category,
            'pages_affected': 0,
            'estimated_impact': 'high'
        }
    
    def _sort_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort recommendations by priority and impact."""
        
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        impact_order = {'high': 0, 'medium': 1, 'low': 2}
        
        def sort_key(rec):
            priority = priority_order.get(rec.get('priority', 'medium'), 1)
            impact = impact_order.get(rec.get('estimated_impact', 'medium'), 1)
            pages_affected = rec.get('pages_affected', 0)
            
            # Sort by: priority, impact, pages affected (descending)
            return (priority, impact, -pages_affected)
        
        return sorted(recommendations, key=sort_key)
    
    def get_score_breakdown(self, overall_score: OverallScore) -> Dict[str, Any]:
        """Get detailed score breakdown for reporting."""
        
        breakdown = {
            'overall': {
                'score': overall_score.total_score,
                'grade': overall_score.grade,
                'pages_analyzed': overall_score.page_count
            },
            'categories': {},
            'weights': self.weights.copy(),
            'recommendations': {
                'total': len(overall_score.recommendations),
                'by_priority': {
                    'high': len([r for r in overall_score.recommendations if r.get('priority') == 'high']),
                    'medium': len([r for r in overall_score.recommendations if r.get('priority') == 'medium']),
                    'low': len([r for r in overall_score.recommendations if r.get('priority') == 'low'])
                }
            }
        }
        
        # Add category details
        for category_name, category_score in overall_score.category_scores.items():
            breakdown['categories'][category_name] = {
                'score': category_score.score,
                'grade': category_score.grade,
                'weight': category_score.weight,
                'weighted_contribution': category_score.weighted_score,
                'recommendations_count': len(category_score.recommendations)
            }
        
        return breakdown
    
    def get_benchmarks(self, overall_score: OverallScore) -> Dict[str, Any]:
        """Calculate benchmark comparisons."""
        
        # Industry benchmark estimates (would be updated with real data)
        industry_benchmarks = {
            'industry_average': 65.0,
            'top_quartile': 80.0,
            'top_decile': 90.0,
            'leader_threshold': 95.0
        }
        
        score = overall_score.total_score
        
        # Calculate percentile (estimated)
        if score >= industry_benchmarks['leader_threshold']:
            percentile = 99
        elif score >= industry_benchmarks['top_decile']:
            percentile = 90 + ((score - industry_benchmarks['top_decile']) / 
                             (industry_benchmarks['leader_threshold'] - industry_benchmarks['top_decile']) * 9)
        elif score >= industry_benchmarks['top_quartile']:
            percentile = 75 + ((score - industry_benchmarks['top_quartile']) / 
                             (industry_benchmarks['top_decile'] - industry_benchmarks['top_quartile']) * 15)
        elif score >= industry_benchmarks['industry_average']:
            percentile = 50 + ((score - industry_benchmarks['industry_average']) / 
                             (industry_benchmarks['top_quartile'] - industry_benchmarks['industry_average']) * 25)
        else:
            percentile = (score / industry_benchmarks['industry_average']) * 50
        
        return {
            'score': score,
            'industry_average': industry_benchmarks['industry_average'],
            'percentile_rank': round(percentile),
            'top_quartile_threshold': industry_benchmarks['top_quartile'],
            'top_decile_threshold': industry_benchmarks['top_decile'],
            'leader_threshold': industry_benchmarks['leader_threshold'],
            'vs_industry_average': round(score - industry_benchmarks['industry_average'], 1),
            'performance_tier': self._get_performance_tier(score, industry_benchmarks)
        }
    
    def _get_performance_tier(self, score: float, benchmarks: Dict[str, float]) -> str:
        """Determine performance tier based on score."""
        if score >= benchmarks['leader_threshold']:
            return "Industry Leader"
        elif score >= benchmarks['top_decile']:
            return "Top Performer"
        elif score >= benchmarks['top_quartile']:
            return "Above Average"
        elif score >= benchmarks['industry_average']:
            return "Average"
        else:
            return "Below Average"