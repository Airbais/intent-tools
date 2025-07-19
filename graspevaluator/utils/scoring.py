"""
Scoring calculation utilities for GRASP evaluator
"""

from typing import Dict, Union


class ScoringEngine:
    """Calculate and normalize GRASP scores"""
    
    def __init__(self):
        self.weights = {
            'grounded': 0.40,
            'readable': 0.10,
            'accurate': 0.30,
            'structured': 0.10,
            'polished': 0.10
        }
        
        self.rating_scores = {
            'Excellent': 100,
            'Very Good': 90,
            'Good': 80,
            'Fair': 60,
            'Poor': 40,
            'Very Poor': 20
        }
    
    def calculate_grasp_score(self, metrics: Dict) -> float:
        """Calculate overall GRASP score"""
        # Normalize all metrics to 0-100 scale
        normalized = {
            'grounded': self.normalize_metric(metrics['grounded'], 'grounded'),
            'readable': self.normalize_metric(metrics['readable'], 'readable'),
            'accurate': self.normalize_metric(metrics['accurate'], 'accurate'),
            'structured': self.normalize_metric(metrics['structured'], 'structured'),
            'polished': self.normalize_metric(metrics['polished'], 'polished')
        }
        
        # Calculate weighted score
        total = sum(normalized[k] * self.weights[k] for k in self.weights)
        return round(total, 1)
    
    def normalize_metric(self, value: Union[float, bool, str], metric_type: str) -> float:
        """Normalize metric value to 0-100 scale"""
        if metric_type == 'grounded':
            # Already on 1-10 scale, convert to 0-100
            return min(100, max(0, value * 10))
        
        elif metric_type == 'readable':
            # Boolean: Pass/Fail
            return 100.0 if value else 0.0
        
        elif metric_type == 'accurate':
            # String rating: High/Medium/Low
            accuracy_scores = {
                'High': 100,
                'Medium': 50,
                'Low': 0
            }
            return accuracy_scores.get(value, 0)
        
        elif metric_type in ['structured', 'polished']:
            # String rating: Excellent/Good/Fair/Poor/Very Poor
            return self.rating_scores.get(value, 0)
        
        else:
            return 0.0
    
    def rating_to_score(self, rating: str) -> float:
        """Convert rating string to numerical score"""
        return self.rating_scores.get(rating, 0)
    
    def score_to_rating(self, score: float) -> str:
        """Convert numerical score to rating string"""
        if score >= 95:
            return "Excellent"
        elif score >= 85:
            return "Very Good"
        elif score >= 75:
            return "Good"
        elif score >= 55:
            return "Fair"
        elif score >= 35:
            return "Poor"
        else:
            return "Very Poor"
    
    def get_metric_breakdown(self, metrics: Dict) -> Dict:
        """Get detailed breakdown of metric contributions"""
        breakdown = {}
        
        for metric, value in metrics.items():
            normalized_score = self.normalize_metric(value, metric)
            weight = self.weights.get(metric, 0)
            
            breakdown[metric] = {
                'raw_value': value,
                'normalized_score': normalized_score,
                'weight_percentage': weight * 100,
                'weighted_contribution': normalized_score * weight,
                'rating': self.score_to_rating(normalized_score) if metric in ['structured', 'polished'] else None
            }
        
        return breakdown
    
    def calculate_improvement_potential(self, metrics: Dict) -> Dict:
        """Calculate potential score improvement for each metric"""
        current_total = self.calculate_grasp_score(metrics)
        improvements = {}
        
        for metric in metrics:
            # Calculate score if this metric was perfect (100)
            improved_metrics = metrics.copy()
            
            if metric == 'grounded':
                improved_metrics[metric] = 10.0  # Max grounded score
            elif metric == 'readable':
                improved_metrics[metric] = True  # Pass
            elif metric == 'accurate':
                improved_metrics[metric] = 'High'  # Best accuracy
            elif metric in ['structured', 'polished']:
                improved_metrics[metric] = 'Excellent'  # Best rating
            
            improved_total = self.calculate_grasp_score(improved_metrics)
            potential_gain = improved_total - current_total
            
            improvements[metric] = {
                'current_contribution': self.normalize_metric(metrics[metric], metric) * self.weights[metric],
                'max_contribution': 100 * self.weights[metric],
                'potential_gain': potential_gain,
                'priority': 'High' if potential_gain > 5 else 'Medium' if potential_gain > 2 else 'Low'
            }
        
        return improvements
    
    def get_grade(self, score: float) -> str:
        """Get letter grade for GRASP score"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    def format_score_display(self, score: float, max_score: float = 100) -> str:
        """Format score for display"""
        return f"{score:.1f}/{max_score}"
    
    def create_progress_bar(self, score: float, max_score: float = 100, width: int = 10) -> str:
        """Create ASCII progress bar for score"""
        percentage = min(1.0, score / max_score)
        filled = int(percentage * width)
        empty = width - filled
        
        return "█" * filled + "░" * empty