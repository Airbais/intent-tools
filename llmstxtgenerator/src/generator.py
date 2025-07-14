import os
import json
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class LLMSTextGenerator:
    def __init__(self, config_manager, analysis: Dict, pages: Dict[str, Dict]):
        self.config = config_manager
        self.analysis = analysis
        self.pages = pages
        self.output_dir = None
    
    def generate(self) -> Dict[str, str]:
        logger.info("Generating LLMS.txt files...")
        
        # Create output directory
        self._create_output_directory()
        
        # Generate content
        content = self._generate_content()
        
        # Save in different formats
        results = {}
        for format in self.config.output_formats:
            if format == 'txt':
                results['txt'] = self._save_txt(content)
            elif format == 'markdown':
                results['markdown'] = self._save_markdown(content)
            elif format == 'json':
                results['json'] = self._save_json()
        
        # Generate report if configured
        if self.config.get('output.generate_report', True):
            results['report'] = self._generate_report()
        
        # Generate dashboard data
        results['dashboard'] = self._generate_dashboard_data()
        
        return results
    
    def _create_output_directory(self):
        base_dir = self.config.output_directory
        date_str = datetime.now().strftime('%Y-%m-%d')
        self.output_dir = os.path.join(base_dir, date_str)
        
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Clean old results if configured
        if not self.config.get('output.keep_past_results', True):
            self._clean_old_results(base_dir, date_str)
    
    def _clean_old_results(self, base_dir: str, current_date: str):
        for item in os.listdir(base_dir):
            item_path = os.path.join(base_dir, item)
            if os.path.isdir(item_path) and item != current_date:
                import shutil
                shutil.rmtree(item_path)
    
    def _generate_content(self) -> str:
        lines = []
        
        # H1 header with project name (mandatory)
        site_name = self.analysis.get('site_name', 'Website')
        lines.append(f"# {site_name}")
        lines.append("")
        
        # Optional blockquote with description
        site_description = self.analysis.get('site_description', '')
        if site_description:
            lines.append(f"> {site_description}")
            lines.append("")
        
        # Optional detailed explanation
        if self.analysis.get('key_pages'):
            homepage = next((p for p in self.analysis['key_pages'] if p['url'] == self.config.website_url), None)
            if homepage and homepage.get('description') and len(homepage['description']) > len(site_description):
                lines.append(homepage['description'])
                lines.append("")
        
        # Add sections (dynamically discovered)
        sections = self.analysis.get('sections', {})
        
        # Add all discovered sections (sorted by name for consistency)
        for section_name in sorted(sections.keys()):
            if sections[section_name]:  # Only add sections with content
                lines.append(f"## {section_name.capitalize()}")
                
                for link in sections[section_name]:
                    title = link.get('title', 'Untitled')
                    url = link.get('url', '')
                    description = link.get('description', '')
                    
                    # Format according to spec: [name](url): optional description
                    if description:
                        lines.append(f"- [{title}]({url}): {description}")
                    else:
                        lines.append(f"- [{title}]({url})")
                
                lines.append("")
        
        # Add Optional section for additional resources
        additional_pages = self._get_additional_pages(sections)
        if additional_pages:
            lines.append("## Optional")
            for page in additional_pages[:10]:  # Limit to 10 additional links
                title = page.get('title', 'Untitled')
                url = page.get('url', '')
                lines.append(f"- [{title}]({url})")
            lines.append("")
        
        return "\n".join(lines).strip()
    
    def _get_additional_pages(self, sections: Dict[str, List]) -> List[Dict]:
        # Get pages that aren't in main sections but might be useful
        section_urls = set()
        for pages in sections.values():
            for page in pages:
                section_urls.add(page['url'])
        
        additional = []
        for page in self.analysis.get('key_pages', []):
            if page['url'] not in section_urls and page['section'] == 'general':
                additional.append(page)
        
        return additional
    
    def _save_txt(self, content: str) -> str:
        filepath = os.path.join(self.output_dir, 'llms.txt')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Saved llms.txt to {filepath}")
        return filepath
    
    def _save_markdown(self, content: str) -> str:
        filepath = os.path.join(self.output_dir, 'llms.md')
        
        # Add markdown-specific formatting
        md_content = f"""---
title: {self.analysis.get('site_name', 'Website')} - LLMS.txt
generated: {datetime.now().isoformat()}
generator: LLMS.txt Generator by Airbais
---

{content}

---

*This file was automatically generated to help LLMs understand the structure and content of {self.config.website_url}*
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)
        logger.info(f"Saved llms.md to {filepath}")
        return filepath
    
    def _save_json(self) -> str:
        filepath = os.path.join(self.output_dir, 'llms.json')
        
        json_data = {
            'metadata': {
                'site_name': self.analysis.get('site_name', ''),
                'site_url': self.config.website_url,
                'site_description': self.analysis.get('site_description', ''),
                'generated': datetime.now().isoformat(),
                'generator': 'LLMS.txt Generator by Airbais'
            },
            'sections': self.analysis.get('sections', {}),
            'navigation': self.analysis.get('navigation_structure', {}),
            'statistics': {
                'total_pages_crawled': len(self.pages),
                'total_sections': len(self.analysis.get('sections', {})),
                'content_categories': self.analysis.get('content_categories', {})
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2)
        logger.info(f"Saved llms.json to {filepath}")
        return filepath
    
    def _generate_report(self) -> str:
        filepath = os.path.join(self.output_dir, 'generation_report.md')
        
        report = f"""# LLMS.txt Generation Report

## Summary
- **Website**: {self.config.website_url}
- **Site Name**: {self.analysis.get('site_name', 'Unknown')}
- **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Total Pages Crawled**: {len(self.pages)}
- **Total Sections Found**: {len(self.analysis.get('sections', {}))}

## Site Structure
- **Maximum Depth Reached**: {self.analysis.get('navigation_structure', {}).get('max_depth_reached', 0)}
- **Average Links per Page**: {self.analysis.get('navigation_structure', {}).get('average_links_per_page', 0):.1f}

## Content Categories
"""
        
        categories = self.analysis.get('content_categories', {})
        for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            report += f"- **{category.capitalize()}**: {count} pages\n"
        
        report += f"""
## Sections Included
"""
        
        sections = self.analysis.get('sections', {})
        for section, pages in sections.items():
            report += f"- **{section.capitalize()}**: {len(pages)} links\n"
        
        report += f"""
## Configuration Used
- **Max Pages**: {self.config.max_pages}
- **Max Depth**: {self.config.max_depth}
- **AI Descriptions**: {'Enabled' if self.config.use_ai_descriptions else 'Disabled'}
- **Output Formats**: {', '.join(self.config.output_formats)}

## Files Generated
- llms.txt - Standard LLMS.txt file
"""
        
        if 'markdown' in self.config.output_formats:
            report += "- llms.md - Markdown version with metadata\n"
        if 'json' in self.config.output_formats:
            report += "- llms.json - JSON structured data\n"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"Saved generation report to {filepath}")
        return filepath
    
    def _generate_dashboard_data(self) -> str:
        filepath = os.path.join(self.output_dir, 'dashboard-data.json')
        
        # Calculate success metrics
        sections_data = self.analysis.get('sections', {})
        total_links = sum(len(links) for links in sections_data.values())
        
        # Calculate success rate based on how many pages were organized into meaningful sections
        total_pages = len(self.pages)
        pages_in_sections = sum(len(links) for section, links in sections_data.items() if section != 'general')
        
        # If we have non-general sections, calculate based on those
        # Otherwise, consider it successful if we have any links in general section
        if any(section != 'general' for section in sections_data.keys()):
            success_rate = (pages_in_sections / max(total_pages, 1)) * 100
        else:
            # For sites with no clear sections, success is having organized any content
            success_rate = (total_links / max(total_pages, 1)) * 100
        
        # Format data to match dashboard expectations
        dashboard_data = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'tool_name': 'llmstxtgenerator',
                'tool_version': '1.0.0',
                'website_url': self.config.website_url,
                'website_name': self.analysis.get('site_name', ''),
                'configuration': {
                    'max_pages': self.config.max_pages,
                    'max_depth': self.config.max_depth,
                    'ai_descriptions': self.config.use_ai_descriptions,
                    'output_formats': self.config.output_formats
                }
            },
            'generation_summary': {
                'pages_crawled': len(self.pages),
                'sections_detected': len(sections_data),
                'total_links_generated': total_links,
                'files_generated': len(self.config.output_formats) + 2,
                'max_depth_reached': self.analysis.get('navigation_structure', {}).get('max_depth_reached', 0),
                'success_rate': min(100, success_rate)
            },
            'site_analysis': {
                'sections': sections_data,
                'section_counts': {
                    section: len(links) for section, links in sections_data.items()
                },
                'content_categories': self.analysis.get('content_categories', {}),
                'navigation_structure': self.analysis.get('navigation_structure', {}),
                'key_pages': self.analysis.get('key_pages', [])[:10]  # Limit to top 10
            },
            'files_generated': {
                'llms_txt': True,
                'llms_md': 'markdown' in self.config.output_formats,
                'llms_json': 'json' in self.config.output_formats,
                'generation_report': self.config.get('output.generate_report', True)
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(dashboard_data, f, indent=2)
        logger.info(f"Saved dashboard data to {filepath}")
        return filepath