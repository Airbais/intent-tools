"""
Readable metric evaluator - Reading level assessment
"""

import textstat
from typing import Dict, List


class ReadableEvaluator:
    """Evaluate content readability for target audience"""
    
    def __init__(self, config):
        self.config = config
        
        # Define target level mappings
        self.target_levels = {
            'elementary': (3, 6),      # Grades 3-6
            'high_school': (7, 12),    # Grades 7-12
            'college': (13, 16),       # Grades 13-16
            'graduate': (17, 20),      # Grades 17+
            'general_public': (6, 8)   # General public (Grade 6-8)
        }
    
    def evaluate(self, content: str, target_level: str = 'general_public') -> bool:
        """
        Evaluate if content matches target reading level
        
        Args:
            content: Text content to evaluate
            target_level: Target audience level
            
        Returns:
            bool: True if content is appropriate for target level
        """
        if not content or not content.strip():
            return False
        
        try:
            # Calculate multiple readability scores
            flesch_kincaid = textstat.flesch_kincaid_grade(content)
            gunning_fog = textstat.gunning_fog(content)
            coleman_liau = textstat.coleman_liau_index(content)
            
            # Calculate average grade level
            scores = [flesch_kincaid, gunning_fog, coleman_liau]
            # Filter out invalid scores (negative or extremely high)
            valid_scores = [score for score in scores if 0 <= score <= 25]
            
            if not valid_scores:
                return False
            
            avg_grade_level = sum(valid_scores) / len(valid_scores)
            
            # Get target range
            target_range = self.target_levels.get(target_level, (6, 8))
            
            # Check if average score is within acceptable range
            # Allow some tolerance (±1 grade level)
            min_grade = target_range[0] - 1
            max_grade = target_range[1] + 1
            
            return min_grade <= avg_grade_level <= max_grade
            
        except Exception as e:
            # If readability calculation fails, return False
            return False
    
    def get_detailed_scores(self, content: str) -> Dict:
        """Get detailed readability scores and analysis"""
        if not content or not content.strip():
            return {
                'flesch_kincaid': 0,
                'gunning_fog': 0,
                'coleman_liau': 0,
                'average_grade_level': 0,
                'flesch_reading_ease': 0,
                'word_count': 0,
                'sentence_count': 0,
                'analysis': 'No content to analyze'
            }
        
        try:
            # Calculate various readability metrics
            flesch_kincaid = textstat.flesch_kincaid_grade(content)
            gunning_fog = textstat.gunning_fog(content)
            coleman_liau = textstat.coleman_liau_index(content)
            flesch_reading_ease = textstat.flesch_reading_ease(content)
            
            # Basic text statistics
            word_count = textstat.lexicon_count(content)
            sentence_count = textstat.sentence_count(content)
            
            # Calculate average grade level
            grade_scores = [flesch_kincaid, gunning_fog, coleman_liau]
            valid_scores = [score for score in grade_scores if 0 <= score <= 25]
            avg_grade_level = sum(valid_scores) / len(valid_scores) if valid_scores else 0
            
            # Generate analysis
            analysis = self._generate_analysis(avg_grade_level, flesch_reading_ease)
            
            return {
                'flesch_kincaid': round(flesch_kincaid, 1),
                'gunning_fog': round(gunning_fog, 1),
                'coleman_liau': round(coleman_liau, 1),
                'average_grade_level': round(avg_grade_level, 1),
                'flesch_reading_ease': round(flesch_reading_ease, 1),
                'word_count': word_count,
                'sentence_count': sentence_count,
                'analysis': analysis
            }
            
        except Exception as e:
            return {
                'error': f"Error calculating readability: {str(e)}",
                'flesch_kincaid': 0,
                'gunning_fog': 0,
                'coleman_liau': 0,
                'average_grade_level': 0,
                'flesch_reading_ease': 0,
                'word_count': 0,
                'sentence_count': 0,
                'analysis': 'Error in analysis'
            }
    
    def _generate_analysis(self, grade_level: float, reading_ease: float) -> str:
        """Generate human-readable analysis of readability"""
        # Grade level analysis
        if grade_level <= 6:
            grade_desc = "Elementary school level"
        elif grade_level <= 8:
            grade_desc = "Middle school level"
        elif grade_level <= 12:
            grade_desc = "High school level"
        elif grade_level <= 16:
            grade_desc = "College level"
        else:
            grade_desc = "Graduate level"
        
        # Reading ease analysis
        if reading_ease >= 90:
            ease_desc = "Very easy to read"
        elif reading_ease >= 80:
            ease_desc = "Easy to read"
        elif reading_ease >= 70:
            ease_desc = "Fairly easy to read"
        elif reading_ease >= 60:
            ease_desc = "Standard reading level"
        elif reading_ease >= 50:
            ease_desc = "Fairly difficult to read"
        elif reading_ease >= 30:
            ease_desc = "Difficult to read"
        else:
            ease_desc = "Very difficult to read"
        
        return f"{grade_desc}. {ease_desc}."
    
    def check_target_alignment(self, content: str, target_level: str) -> Dict:
        """Check how well content aligns with target reading level"""
        scores = self.get_detailed_scores(content)
        is_appropriate = self.evaluate(content, target_level)
        
        target_range = self.target_levels.get(target_level, (6, 8))
        current_level = scores.get('average_grade_level', 0)
        
        # Calculate how far off the target we are
        if current_level < target_range[0]:
            deviation = target_range[0] - current_level
            recommendation = "Content is too simple. Consider using more sophisticated vocabulary and complex sentences."
        elif current_level > target_range[1]:
            deviation = current_level - target_range[1]
            recommendation = "Content is too complex. Consider simplifying vocabulary and sentence structure."
        else:
            deviation = 0
            recommendation = "Content reading level is appropriate for target audience."
        
        return {
            'is_appropriate': is_appropriate,
            'current_level': current_level,
            'target_range': target_range,
            'deviation': round(deviation, 1),
            'recommendation': recommendation,
            'detailed_scores': scores
        }
    
    async def generate_enhanced_recommendations(self, content: str, target_level: str, is_appropriate: bool) -> List[Dict]:
        """Generate detailed, actionable recommendations for readability improvements"""
        recommendations = []
        
        scores = self.get_detailed_scores(content)
        current_level = scores.get('average_grade_level', 0)
        target_range = self.target_levels.get(target_level, (6, 8))
        
        if not is_appropriate:
            if current_level > target_range[1]:
                # Content is too complex
                deviation = current_level - target_range[1]
                severity = "critical" if deviation > 3 else "high" if deviation > 1.5 else "medium"
                
                recommendations.append({
                    "priority": severity,
                    "category": "complexity_reduction",
                    "issue": f"Content reading level ({current_level:.1f}) exceeds target ({target_level}: {target_range[0]}-{target_range[1]})",
                    "impact": "10% weight metric - readers may struggle to understand content",
                    "action": "Simplify content to match target audience reading level",
                    "specifics": {
                        "current_grade_level": current_level,
                        "target_range": f"{target_range[0]}-{target_range[1]}",
                        "deviation": f"+{deviation:.1f} grade levels",
                        "flesch_reading_ease": scores.get('flesch_reading_ease', 0),
                        "word_count": scores.get('word_count', 0),
                        "sentence_count": scores.get('sentence_count', 0)
                    },
                    "implementation": {
                        "effort": "medium",
                        "timeline": "2-3 days",
                        "steps": [
                            "Replace complex words with simpler alternatives",
                            "Break long sentences into shorter ones (target 15-20 words)",
                            "Use active voice instead of passive voice",
                            "Add transition words to improve flow",
                            "Remove unnecessary jargon and technical terms"
                        ],
                        "specific_targets": [
                            f"Reduce average sentence length to 15-20 words",
                            f"Target Flesch Reading Ease score of 60-70",
                            f"Aim for grade level {target_range[1]:.0f} or lower"
                        ]
                    }
                })
                
                # Additional recommendations based on specific metrics
                if scores.get('flesch_reading_ease', 0) < 50:
                    recommendations.append({
                        "priority": "medium",
                        "category": "sentence_structure",
                        "issue": f"Low reading ease score ({scores.get('flesch_reading_ease', 0):.1f}) indicates difficult sentence structure",
                        "impact": "Readers may abandon content due to complexity",
                        "action": "Improve sentence structure and flow",
                        "implementation": {
                            "effort": "low",
                            "timeline": "1-2 days",
                            "specific_actions": [
                                "Use bullet points for complex information",
                                "Add subheadings to break up dense text",
                                "Use parallel sentence structures",
                                "Include examples and analogies"
                            ]
                        }
                    })
            
            elif current_level < target_range[0]:
                # Content is too simple
                deviation = target_range[0] - current_level
                
                recommendations.append({
                    "priority": "medium",
                    "category": "sophistication_increase",
                    "issue": f"Content reading level ({current_level:.1f}) is below target ({target_level}: {target_range[0]}-{target_range[1]})",
                    "impact": "May appear unprofessional or lack depth for target audience",
                    "action": "Increase content sophistication appropriately",
                    "specifics": {
                        "current_grade_level": current_level,
                        "target_range": f"{target_range[0]}-{target_range[1]}",
                        "deviation": f"-{deviation:.1f} grade levels"
                    },
                    "implementation": {
                        "effort": "medium",
                        "timeline": "2-3 days",
                        "steps": [
                            "Use more sophisticated vocabulary where appropriate",
                            "Include more detailed explanations",
                            "Add industry-specific terminology with context",
                            "Incorporate complex sentence structures occasionally"
                        ]
                    }
                })
        
        else:
            # Content is appropriate but could be optimized
            recommendations.append({
                "priority": "low",
                "category": "readability_optimization",
                "issue": "Content reading level is appropriate but can be optimized",
                "impact": "Opportunity to improve user experience",
                "action": "Fine-tune readability for optimal user engagement",
                "implementation": {
                    "effort": "low",
                    "timeline": "1 day",
                    "steps": [
                        "Review sentence variety (mix of short and medium sentences)",
                        "Ensure consistent terminology throughout",
                        "Add formatting (bold, italics) for emphasis",
                        "Include visual breaks with lists or subheadings"
                    ]
                }
            })
        
        # Content-specific recommendations based on detailed scores
        if scores.get('sentence_count', 0) > 0:
            avg_words_per_sentence = scores.get('word_count', 0) / scores.get('sentence_count', 1)
            if avg_words_per_sentence > 25:
                recommendations.append({
                    "priority": "medium",
                    "category": "sentence_length",
                    "issue": f"Average sentence length is {avg_words_per_sentence:.1f} words (ideal: 15-20)",
                    "impact": "Long sentences reduce comprehension",
                    "action": "Break down long sentences",
                    "implementation": {
                        "effort": "low",
                        "timeline": "1 day",
                        "target": "Reduce average sentence length to 15-20 words"
                    }
                })
        
        return recommendations