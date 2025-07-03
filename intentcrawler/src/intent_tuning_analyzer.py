import json
import pandas as pd
from collections import Counter, defaultdict
from typing import Dict, List
import matplotlib.pyplot as plt
import seaborn as sns

class IntentTuningAnalyzer:
    """Analyze intent extraction results to identify tuning opportunities."""
    
    def __init__(self, results_file: str):
        with open(results_file, 'r') as f:
            self.data = json.load(f)
    
    def analyze_intent_distribution(self):
        """Analyze how intents are distributed across the site."""
        intents = self.data.get('discovered_intents', [])
        
        # Intent frequency analysis
        intent_counts = Counter([intent['primary_intent'] for intent in intents])
        confidence_scores = [intent['confidence'] for intent in intents]
        
        print("🎯 Intent Distribution Analysis")
        print("=" * 50)
        for intent, count in intent_counts.most_common():
            avg_confidence = sum(i['confidence'] for i in intents 
                               if i['primary_intent'] == intent) / count
            print(f"{intent:25} | {count:3d} pages | {avg_confidence:.2f} confidence")
        
        return {
            'intent_counts': intent_counts,
            'avg_confidence': sum(confidence_scores) / len(confidence_scores),
            'low_confidence_intents': [i for i in intents if i['confidence'] < 0.3]
        }
    
    def identify_signal_gaps(self):
        """Find pages that might have missed intents (low signal detection)."""
        intents = self.data.get('discovered_intents', [])
        
        # Pages with weak signals
        weak_signal_pages = []
        for intent in intents:
            if intent['confidence'] < 0.2 or len(intent.get('keywords', [])) < 3:
                weak_signal_pages.extend(intent['pages'])
        
        print("\n🔍 Signal Gap Analysis")
        print("=" * 50)
        print(f"Pages with weak signals: {len(set(weak_signal_pages))}")
        
        # Suggest pattern improvements
        all_keywords = []
        for intent in intents:
            all_keywords.extend(intent.get('keywords', []))
        
        rare_keywords = [k for k, count in Counter(all_keywords).items() if count == 1]
        print(f"Unique keywords (potential new patterns): {len(rare_keywords)}")
        print("Top unique keywords:", rare_keywords[:10])
        
        return {
            'weak_signal_pages': list(set(weak_signal_pages)),
            'rare_keywords': rare_keywords[:20],
            'improvement_suggestions': self._generate_improvement_suggestions(rare_keywords)
        }
    
    def _generate_improvement_suggestions(self, rare_keywords: List[str]) -> List[str]:
        """Generate suggestions for pattern improvements."""
        suggestions = []
        
        # Look for common themes in rare keywords
        if any('onboard' in k for k in rare_keywords):
            suggestions.append("Add 'onboarding' patterns to learn_and_understand intent")
        
        if any('migrat' in k for k in rare_keywords):
            suggestions.append("Add 'migration' patterns to implement_and_integrate intent")
        
        if any('scale' in k or 'grow' in k for k in rare_keywords):
            suggestions.append("Consider adding 'scale_and_grow' as new intent type")
        
        return suggestions
    
    def analyze_section_coverage(self):
        """Analyze intent coverage across site sections."""
        by_section = self.data.get('by_section', {})
        
        print("\n📊 Section Coverage Analysis")
        print("=" * 50)
        
        section_stats = {}
        for section, pages in by_section.items():
            intent_types = set(page['intent'] for page in pages)
            section_stats[section] = {
                'page_count': len(pages),
                'intent_diversity': len(intent_types),
                'dominant_intent': Counter(page['intent'] for page in pages).most_common(1)[0]
            }
            
            print(f"{section:20} | {len(pages):3d} pages | {len(intent_types)} intents | Main: {section_stats[section]['dominant_intent'][0]}")
        
        return section_stats
    
    def suggest_new_intent_types(self):
        """Suggest new intent types based on unclassified patterns."""
        intents = self.data.get('discovered_intents', [])
        
        # Look for keywords that don't fit well into existing intents
        all_keywords = []
        for intent in intents:
            if intent['confidence'] < 0.4:  # Low confidence might indicate misfit
                all_keywords.extend(intent.get('keywords', []))
        
        keyword_themes = self._cluster_keywords_by_theme(all_keywords)
        
        print("\n💡 New Intent Type Suggestions")
        print("=" * 50)
        for theme, keywords in keyword_themes.items():
            if len(keywords) >= 3:
                print(f"Potential intent: '{theme}' - Keywords: {keywords[:5]}")
        
        return keyword_themes
    
    def _cluster_keywords_by_theme(self, keywords: List[str]) -> Dict[str, List[str]]:
        """Group keywords by semantic themes."""
        themes = defaultdict(list)
        
        for keyword in keywords:
            if any(term in keyword for term in ['scale', 'grow', 'expand']):
                themes['scale_and_grow'].append(keyword)
            elif any(term in keyword for term in ['security', 'secure', 'compliance']):
                themes['ensure_security_compliance'].append(keyword)
            elif any(term in keyword for term in ['team', 'collaborate', 'share']):
                themes['collaborate_and_share'].append(keyword)
            elif any(term in keyword for term in ['automate', 'automation', 'workflow']):
                themes['automate_processes'].append(keyword)
            elif any(term in keyword for term in ['mobile', 'app', 'device']):
                themes['mobile_access'].append(keyword)
            else:
                themes['unclassified'].append(keyword)
        
        return dict(themes)
    
    def export_tuning_report(self, output_file: str = 'intent_tuning_report.json'):
        """Export comprehensive tuning analysis."""
        report = {
            'distribution_analysis': self.analyze_intent_distribution(),
            'signal_gaps': self.identify_signal_gaps(),
            'section_coverage': self.analyze_section_coverage(),
            'new_intent_suggestions': self.suggest_new_intent_types(),
            'tuning_recommendations': self._generate_tuning_recommendations()
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📋 Tuning report exported to: {output_file}")
        return report
    
    def _generate_tuning_recommendations(self) -> List[str]:
        """Generate specific tuning recommendations."""
        recommendations = []
        
        # Analyze current data for recommendations
        intents = self.data.get('discovered_intents', [])
        avg_confidence = sum(i['confidence'] for i in intents) / len(intents)
        
        if avg_confidence < 0.4:
            recommendations.append("Overall confidence is low - consider reducing min_confidence_threshold")
        
        if len(intents) < 5:
            recommendations.append("Few intents detected - consider lowering similarity_threshold")
        
        if len(intents) > 15:
            recommendations.append("Many intents detected - consider raising similarity_threshold or min_cluster_size")
        
        return recommendations

if __name__ == "__main__":
    # Example usage
    analyzer = IntentTuningAnalyzer('results/2024-06-26/intent-report.json')
    analyzer.export_tuning_report()