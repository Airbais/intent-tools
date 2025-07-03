import json
import os
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import asdict
import logging

class ReportGenerator:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.logger = logging.getLogger(__name__)
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_structured_report(self, 
                                 intent_data: Dict,
                                 site_structure: Dict,
                                 llmstxt_content: str,
                                 website_url: str) -> str:
        report = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'website_url': website_url,
                'analysis_version': '1.0',
                'total_pages_analyzed': intent_data.get('total_pages_analyzed', 0),
                'total_intents_discovered': intent_data.get('total_intents', 0)
            },
            'site_structure': site_structure,
            'intent_analysis': intent_data,
            'llmstxt_content': llmstxt_content,
            'recommendations': self._generate_recommendations(intent_data, site_structure)
        }
        
        report_file = os.path.join(self.output_dir, 'intent-report.json')
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Structured report saved to {report_file}")
        return report_file
    
    def generate_llm_export(self, intent_data: Dict, site_structure: Dict, website_url: str) -> str:
        llm_export = {
            'website': website_url,
            'analysis_date': datetime.now().isoformat(),
            'intent_summary': {
                'primary_intents': [
                    {
                        'intent': intent['primary_intent'],
                        'confidence': intent['confidence'],
                        'page_count': intent['page_count'],
                        'keywords': intent['keywords'][:5]
                    }
                    for intent in intent_data.get('discovered_intents', [])
                ],
                'section_breakdown': intent_data.get('by_section', {}),
                'intent_patterns': intent_data.get('intent_patterns', {})
            },
            'site_organization': {
                'sections': site_structure.get('sections', {}),
                'navigation_structure': site_structure.get('navigation', {}),
                'total_pages': site_structure.get('total_pages', 0)
            },
            'actionable_insights': self._generate_actionable_insights(intent_data, site_structure)
        }
        
        export_file = os.path.join(self.output_dir, 'llm-export.json')
        with open(export_file, 'w', encoding='utf-8') as f:
            json.dump(llm_export, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"LLM export saved to {export_file}")
        return export_file
    
    def generate_dashboard_data(self, intent_data: Dict, site_structure: Dict) -> str:
        dashboard_data = {
            'discovered_intents': intent_data.get('discovered_intents', []),
            'by_section': intent_data.get('by_section', {}),
            'total_pages_analyzed': intent_data.get('total_pages_analyzed', 0),
            'total_intents': len(intent_data.get('discovered_intents', [])),
            'site_metrics': {
                'sections': site_structure.get('sections', {}),
                'navigation': site_structure.get('navigation', {}),
                'graph_metrics': site_structure.get('graph_metrics', {})
            }
        }
        
        dashboard_file = os.path.join(self.output_dir, 'dashboard-data.json')
        with open(dashboard_file, 'w', encoding='utf-8') as f:
            json.dump(dashboard_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Dashboard data saved to {dashboard_file}")
        return dashboard_file
    
    def _generate_recommendations(self, intent_data: Dict, site_structure: Dict) -> List[Dict]:
        recommendations = []
        
        intents = intent_data.get('discovered_intents', [])
        sections = intent_data.get('by_section', {})
        
        if len(intents) < 3:
            recommendations.append({
                'type': 'content_expansion',
                'priority': 'high',
                'title': 'Limited Intent Diversity',
                'description': 'Your website shows limited intent variety. Consider adding more content types.',
                'suggested_actions': [
                    'Add FAQ or help section for informational intents',
                    'Include product comparison pages',
                    'Create getting started guides',
                    'Add pricing or service information'
                ]
            })
        
        weak_intents = [intent for intent in intents if intent.get('confidence', 0) < 0.3]
        if len(weak_intents) > len(intents) * 0.5:
            recommendations.append({
                'type': 'content_clarity',
                'priority': 'medium',
                'title': 'Unclear Intent Signals',
                'description': 'Many pages have weak intent signals. Content clarity could be improved.',
                'suggested_actions': [
                    'Use clearer action-oriented language',
                    'Add specific calls-to-action',
                    'Include more descriptive headings',
                    'Structure content with clear user goals'
                ]
            })
        
        if 'home' not in sections or len(sections.get('home', [])) == 0:
            recommendations.append({
                'type': 'navigation',
                'priority': 'high',
                'title': 'Missing Home Page Intent',
                'description': 'No clear home page intent detected.',
                'suggested_actions': [
                    'Ensure home page clearly communicates primary value proposition',
                    'Add clear navigation to key sections',
                    'Include overview of main site purposes'
                ]
            })
        
        transactional_intents = [
            intent for intent in intents 
            if any(keyword in intent.get('keywords', []) for keyword in ['buy', 'purchase', 'order', 'pricing'])
        ]
        if not transactional_intents and len(intents) > 2:
            recommendations.append({
                'type': 'conversion',
                'priority': 'medium',
                'title': 'Missing Conversion Intents',
                'description': 'No clear transactional or conversion intents detected.',
                'suggested_actions': [
                    'Add clear pricing information',
                    'Include contact or consultation options',
                    'Create product/service purchase flows',
                    'Add trial or demo opportunities'
                ]
            })
        
        return recommendations
    
    def _generate_actionable_insights(self, intent_data: Dict, site_structure: Dict) -> List[Dict]:
        insights = []
        
        sections = intent_data.get('by_section', {})
        intents = intent_data.get('discovered_intents', [])
        
        high_confidence_intents = [i for i in intents if i.get('confidence', 0) > 0.7]
        insights.append({
            'category': 'strengths',
            'insight': f"Strong intent clarity in {len(high_confidence_intents)} areas",
            'details': [intent['primary_intent'] for intent in high_confidence_intents[:5]]
        })
        
        largest_section = max(sections.items(), key=lambda x: len(x[1])) if sections else None
        if largest_section:
            insights.append({
                'category': 'content_focus',
                'insight': f"Primary content focus on {largest_section[0]}",
                'details': f"{len(largest_section[1])} intents in this section"
            })
        
        intent_distribution = {}
        for intent in intents:
            primary = intent.get('primary_intent', 'unknown')
            intent_distribution[primary] = intent_distribution.get(primary, 0) + 1
        
        if intent_distribution:
            most_common = max(intent_distribution.items(), key=lambda x: x[1])
            insights.append({
                'category': 'intent_patterns',
                'insight': f"Most common intent type: {most_common[0]}",
                'details': f"Appears in {most_common[1]} different contexts"
            })
        
        return insights
    
    def generate_summary_report(self, intent_data: Dict, site_structure: Dict, website_url: str) -> str:
        summary = []
        summary.append(f"# Website Intent Analysis Summary")
        summary.append(f"**Website:** {website_url}")
        summary.append(f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        summary.append("")
        
        summary.append("## Overview")
        total_pages = intent_data.get('total_pages_analyzed', 0)
        total_intents = len(intent_data.get('discovered_intents', []))
        total_sections = len(intent_data.get('by_section', {}))
        
        summary.append(f"- **Total Pages Analyzed:** {total_pages}")
        summary.append(f"- **Discovered Intents:** {total_intents}")
        summary.append(f"- **Site Sections:** {total_sections}")
        summary.append("")
        
        summary.append("## Discovered Intents")
        for intent in intent_data.get('discovered_intents', [])[:10]:
            confidence = intent.get('confidence', 0)
            pages = intent.get('page_count', 0)
            keywords = ', '.join(intent.get('keywords', [])[:3])
            summary.append(f"- **{intent.get('primary_intent', 'Unknown')}** "
                          f"(confidence: {confidence:.2f}, pages: {pages})")
            if keywords:
                summary.append(f"  - Keywords: {keywords}")
        summary.append("")
        
        summary.append("## Intents by Section")
        for section, section_intents in intent_data.get('by_section', {}).items():
            summary.append(f"### {section.title()}")
            intent_counts = {}
            for item in section_intents:
                intent_name = item.get('intent', 'unknown')
                intent_counts[intent_name] = intent_counts.get(intent_name, 0) + 1
            
            for intent, count in sorted(intent_counts.items(), key=lambda x: x[1], reverse=True):
                summary.append(f"- {intent}: {count} pages")
            summary.append("")
        
        summary_text = '\n'.join(summary)
        summary_file = os.path.join(self.output_dir, 'intent-summary.md')
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(summary_text)
        
        self.logger.info(f"Summary report saved to {summary_file}")
        return summary_file