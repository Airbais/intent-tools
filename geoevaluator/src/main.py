"""
Main analysis pipeline for the GEO Evaluator
Orchestrates crawling, analysis, and reporting
"""

import logging
import json
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from crawler import WebCrawler
from scoring_engine import ScoringEngine, AnalysisResult
from utils import create_timestamped_directory, format_duration


class GEOAnalysisPipeline:
    """
    Main pipeline that orchestrates the GEO analysis process.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.crawler = WebCrawler(config)
        self.scoring_engine = ScoringEngine(config)
        
        # Will be initialized as analyzers are implemented
        self.analyzers = {}
        
        # Results storage
        self.crawled_pages: List[Dict[str, Any]] = []
        self.analysis_results: Dict[str, AnalysisResult] = {}
        self.final_scores = None
        
        # Timing
        self.start_time = None
        self.end_time = None
    
    def run(self) -> Optional[Dict[str, Any]]:
        """
        Run the complete GEO analysis pipeline.
        
        Returns:
            Analysis results dictionary or None if failed
        """
        
        self.logger.info("Starting GEO analysis pipeline")
        self.start_time = datetime.now()
        
        try:
            # Step 1: Crawl website
            self.logger.info("Step 1: Crawling website...")
            self.crawled_pages = self.crawler.crawl()
            
            if not self.crawled_pages:
                self.logger.error("No pages crawled successfully")
                return None
            
            self.logger.info(f"Successfully crawled {len(self.crawled_pages)} pages")
            
            # Step 2: Run analysis (placeholder for now)
            self.logger.info("Step 2: Running content analysis...")
            self._run_analysis()
            
            # Step 3: Calculate scores
            self.logger.info("Step 3: Calculating scores...")
            self.final_scores = self.scoring_engine.calculate_scores(
                self.analysis_results, len(self.crawled_pages)
            )
            
            # Step 4: Generate outputs
            self.logger.info("Step 4: Generating outputs...")
            results = self._generate_outputs()
            
            self.end_time = datetime.now()
            duration = (self.end_time - self.start_time).total_seconds()
            
            self.logger.info(f"Analysis completed successfully in {format_duration(duration)}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Analysis pipeline failed: {e}")
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.exception("Full error details:")
            return None
    
    def _run_analysis(self) -> None:
        """Run all content analyzers."""
        
        # For now, create placeholder results for each category
        # These will be replaced with actual analyzer implementations
        
        categories = [
            'structural_html',
            'content_organization', 
            'token_efficiency',
            'llm_technical',
            'accessibility'
        ]
        
        for category in categories:
            self.logger.info(f"Analyzing {category}...")
            
            # Placeholder analysis that gives reasonable scores based on basic checks
            result = self._placeholder_analysis(category)
            self.analysis_results[category] = result
            
            self.logger.info(f"{category} analysis completed: {result.score:.2f}")
    
    def _placeholder_analysis(self, category: str) -> AnalysisResult:
        """
        Placeholder analysis that provides basic scoring.
        Will be replaced with actual analyzer implementations.
        """
        
        if not self.crawled_pages:
            return AnalysisResult(
                category=category,
                score=0.0,
                details={'error': 'No pages to analyze'},
                recommendations=[{
                    'title': 'No Content Available',
                    'description': 'No pages were successfully crawled for analysis',
                    'priority': 'high',
                    'category': category,
                    'pages_affected': 0,
                    'estimated_impact': 'high'
                }]
            )
        
        # Basic scoring based on simple checks
        total_score = 0.0
        details = {}
        recommendations = []
        
        if category == 'structural_html':
            # Check for basic HTML structure
            semantic_pages = 0
            total_headings = 0
            
            for page in self.crawled_pages:
                html = page.get('raw_html', '')
                
                # Check for semantic elements
                semantic_elements = ['<main', '<article', '<section', '<header', '<footer', '<nav']
                if any(elem in html.lower() for elem in semantic_elements):
                    semantic_pages += 1
                
                # Count headings
                headings = page.get('headings', [])
                total_headings += len(headings)
            
            semantic_ratio = semantic_pages / len(self.crawled_pages)
            avg_headings = total_headings / len(self.crawled_pages)
            
            # Score based on semantic usage and heading structure
            total_score = (semantic_ratio * 0.7) + (min(avg_headings / 5, 1.0) * 0.3)
            
            details = {
                'semantic_html_ratio': semantic_ratio,
                'pages_with_semantic_elements': semantic_pages,
                'average_headings_per_page': avg_headings,
                'total_pages_analyzed': len(self.crawled_pages)
            }
            
            if semantic_ratio < 0.8:
                recommendations.append({
                    'title': 'Improve Semantic HTML Usage',
                    'description': f'Only {semantic_pages}/{len(self.crawled_pages)} pages use semantic HTML elements',
                    'priority': 'high' if semantic_ratio < 0.5 else 'medium',
                    'category': category,
                    'pages_affected': len(self.crawled_pages) - semantic_pages,
                    'estimated_impact': 'high'
                })
        
        elif category == 'content_organization':
            # Check content length and structure
            total_content_score = 0.0
            short_content_pages = 0
            short_content_urls = []
            
            for page in self.crawled_pages:
                content = page.get('content', '')
                word_count = len(content.split())
                
                # Score based on content length (sweet spot around 300-2000 words)
                if 300 <= word_count <= 2000:
                    content_score = 1.0
                elif 100 <= word_count < 300 or 2000 < word_count <= 5000:
                    content_score = 0.7
                elif word_count < 100:
                    content_score = 0.3
                    short_content_pages += 1
                    short_content_urls.append({
                        'url': page.get('url', ''),
                        'title': page.get('title', '')[:50] + ('...' if len(page.get('title', '')) > 50 else ''),
                        'word_count': word_count
                    })
                else:
                    content_score = 0.5
                
                total_content_score += content_score
            
            total_score = total_content_score / len(self.crawled_pages)
            
            details = {
                'average_content_score': total_score,
                'pages_with_short_content': short_content_pages,
                'total_pages_analyzed': len(self.crawled_pages)
            }
            
            if short_content_pages > 0:
                recommendations.append({
                    'title': 'Expand Short Content',
                    'description': f'{short_content_pages} pages have very short content (<100 words)',
                    'priority': 'medium',
                    'category': category,
                    'pages_affected': short_content_pages,
                    'estimated_impact': 'medium',
                    'affected_pages': short_content_urls
                })
        
        elif category == 'token_efficiency':
            # Check content-to-markup ratio
            total_ratio = 0.0
            low_ratio_pages = []
            
            for page in self.crawled_pages:
                html_size = page.get('html_size', 1)
                content_size = page.get('content_size', 0)
                ratio = content_size / html_size if html_size > 0 else 0
                total_ratio += ratio
                
                if ratio < 0.3:  # Less than 30% content
                    low_ratio_pages.append({
                        'url': page.get('url', ''),
                        'title': page.get('title', '')[:50] + ('...' if len(page.get('title', '')) > 50 else ''),
                        'content_ratio': f"{ratio:.1%}"
                    })
            
            avg_ratio = total_ratio / len(self.crawled_pages)
            total_score = min(avg_ratio / 0.5, 1.0)  # Target 50% content ratio
            
            details = {
                'average_content_markup_ratio': avg_ratio,
                'total_pages_analyzed': len(self.crawled_pages)
            }
            
            if avg_ratio < 0.3:
                recommendations.append({
                    'title': 'Improve Content-to-Markup Ratio',
                    'description': f'Average content-to-markup ratio is {avg_ratio:.1%}, target >30%',
                    'priority': 'medium',
                    'category': category,
                    'pages_affected': len(low_ratio_pages),
                    'estimated_impact': 'medium',
                    'affected_pages': low_ratio_pages
                })
        
        elif category == 'llm_technical':
            # Check for llms.txt and structured data
            has_llms_txt = False
            structured_data_pages = 0
            
            # Check if llms.txt exists at the root of the website
            base_url = self.config.get('website', {}).get('url', '')
            if base_url:
                llms_txt_url = base_url.rstrip('/') + '/llms.txt'
                try:
                    response = requests.head(llms_txt_url, timeout=5, allow_redirects=True)
                    has_llms_txt = response.status_code == 200
                    self.logger.info(f"Checked llms.txt at {llms_txt_url}: status={response.status_code}, exists={has_llms_txt}")
                except Exception as e:
                    self.logger.warning(f"Error checking llms.txt at {llms_txt_url}: {e}")
                    has_llms_txt = False
            
            # Check if any page might be llms.txt (fallback check)
            for page in self.crawled_pages:
                if 'llms.txt' in page.get('url', ''):
                    has_llms_txt = True
                
                structured_data = page.get('structured_data', [])
                if structured_data:
                    structured_data_pages += 1
            
            # Score based on presence of LLM-specific features
            llms_score = 1.0 if has_llms_txt else 0.0
            structured_ratio = structured_data_pages / len(self.crawled_pages)
            
            total_score = (llms_score * 0.5) + (structured_ratio * 0.5)
            
            details = {
                'has_llms_txt': has_llms_txt,
                'structured_data_ratio': structured_ratio,
                'pages_with_structured_data': structured_data_pages,
                'total_pages_analyzed': len(self.crawled_pages)
            }
            
            if not has_llms_txt:
                recommendations.append({
                    'title': 'Implement llms.txt File',
                    'description': 'No llms.txt file detected. This is crucial for LLM optimization.',
                    'priority': 'high',
                    'category': category,
                    'pages_affected': 1,
                    'estimated_impact': 'high'
                })
            
            if structured_ratio < 0.5:
                recommendations.append({
                    'title': 'Add Structured Data Markup',
                    'description': f'Only {structured_data_pages}/{len(self.crawled_pages)} pages have structured data',
                    'priority': 'medium',
                    'category': category,
                    'pages_affected': len(self.crawled_pages) - structured_data_pages,
                    'estimated_impact': 'medium'
                })
        
        elif category == 'accessibility':
            # Check images with alt text
            total_images = 0
            images_with_alt = 0
            
            for page in self.crawled_pages:
                images = page.get('images', [])
                for image in images:
                    total_images += 1
                    if image.get('alt', '').strip():
                        images_with_alt += 1
            
            if total_images > 0:
                alt_ratio = images_with_alt / total_images
                total_score = alt_ratio
            else:
                total_score = 1.0  # No images to check
            
            details = {
                'total_images': total_images,
                'images_with_alt_text': images_with_alt,
                'alt_text_ratio': images_with_alt / total_images if total_images > 0 else 1.0,
                'total_pages_analyzed': len(self.crawled_pages)
            }
            
            if total_images > 0 and alt_ratio < 0.9:
                missing_alt = total_images - images_with_alt
                recommendations.append({
                    'title': 'Add Missing Alt Text',
                    'description': f'{missing_alt} images are missing descriptive alt text',
                    'priority': 'medium',
                    'category': category,
                    'pages_affected': len([p for p in self.crawled_pages if any(not img.get('alt', '').strip() for img in p.get('images', []))]),
                    'estimated_impact': 'medium'
                })
        
        return AnalysisResult(
            category=category,
            score=total_score,
            details=details,
            recommendations=recommendations
        )
    
    def _generate_outputs(self) -> Dict[str, Any]:
        """Generate all configured output formats."""
        
        # Create output directory
        output_dir = create_timestamped_directory(self.config['output']['export_path'])
        
        # Prepare complete results
        results = {
            'metadata': self._generate_metadata(output_dir),
            'overall_score': self._format_overall_score(),
            'analysis_summary': self._generate_analysis_summary(),
            'recommendations': self.final_scores.recommendations,
            'page_scores': self._generate_page_scores(),
            'benchmarks': self.scoring_engine.get_benchmarks(self.final_scores),
            'crawl_stats': self.crawler.get_crawl_stats()
        }
        
        output_formats = self.config['output']['formats']
        
        # Generate JSON output
        if 'json' in output_formats:
            self._save_json_results(results, output_dir)
        
        # Generate dashboard data
        if 'dashboard' in output_formats:
            self._save_dashboard_data(results, output_dir)
        
        # Generate HTML report (if configured)
        if 'html' in output_formats or self.config['output'].get('generate_html_report', False):
            self._save_html_report(results, output_dir)
        
        # Update results with output information
        results['metadata']['output_directory'] = str(output_dir)
        results['metadata']['generated_files'] = self._get_generated_files(output_dir)
        
        return results
    
    def _generate_metadata(self, output_dir: Path) -> Dict[str, Any]:
        """Generate analysis metadata."""
        
        duration = 0
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'tool_name': 'geoevaluator',
            'tool_version': '1.0.0',
            'website_url': self.config['website']['url'],
            'website_name': self.config['website']['name'],
            'pages_analyzed': len(self.crawled_pages),
            'analysis_duration_seconds': round(duration, 2),
            'configuration': {
                'max_pages': self.config['website']['max_pages'],
                'crawl_depth': self.config['website']['crawl_depth'],
                'analysis_weights': self.config['analysis']['weights']
            }
        }
    
    def _format_overall_score(self) -> Dict[str, Any]:
        """Format overall score for output."""
        
        category_scores = {}
        for name, score_obj in self.final_scores.category_scores.items():
            category_scores[name] = round(score_obj.score, 1)
        
        return {
            'total_score': self.final_scores.total_score,
            'grade': self.final_scores.grade,
            'category_scores': category_scores
        }
    
    def _generate_analysis_summary(self) -> Dict[str, Any]:
        """Generate high-level analysis summary."""
        
        # Calculate averages and stats from analysis results
        summary = {
            'pages_analyzed': len(self.crawled_pages),
        }
        
        # Add category-specific summaries
        for category, result in self.analysis_results.items():
            details = result.details
            if category == 'structural_html':
                summary['avg_semantic_html_usage'] = details.get('semantic_html_ratio', 0)
            elif category == 'token_efficiency':
                summary['avg_content_to_markup_ratio'] = details.get('average_content_markup_ratio', 0)
            elif category == 'llm_technical':
                summary['llms_txt_present'] = details.get('has_llms_txt', False)
                summary['structured_data_coverage'] = details.get('structured_data_ratio', 0)
            elif category == 'accessibility':
                summary['alt_text_coverage'] = details.get('alt_text_ratio', 0)
        
        return summary
    
    def _generate_page_scores(self) -> List[Dict[str, Any]]:
        """Generate individual page scores."""
        
        page_scores = []
        weights = self.config['analysis']['weights']
        
        for page in self.crawled_pages:
            # Calculate individual page scores
            category_scores = {}
            
            # Structural HTML score
            category_scores['structural_html'] = 100.0 if page.get('semantic_html', False) else 50.0
            
            # Content organization score
            content_length = len(page.get('content', '').split())
            if content_length >= 300:
                content_score = 100.0
            elif content_length >= 100:
                content_score = 70.0 + (content_length - 100) * 0.15  # Scale from 70-100
            else:
                content_score = max(20.0, content_length * 0.5)  # Scale from 0-70
            category_scores['content_organization'] = min(content_score, 100.0)
            
            # Token efficiency score (content-to-markup ratio)
            html_size = page.get('html_size', 1)
            content_size = page.get('content_size', 0)
            ratio = content_size / html_size if html_size > 0 else 0
            category_scores['token_efficiency'] = min(ratio / 0.3 * 100, 100.0)  # Target 30% ratio
            
            # LLM technical score (structured data + llms.txt)
            structured_data_score = 50.0 if page.get('structured_data') else 0.0
            llms_txt_score = 50.0 if self.analysis_results.get('llm_technical', {}).details.get('has_llms_txt', False) else 0.0
            category_scores['llm_technical'] = structured_data_score + llms_txt_score
            
            # Accessibility score
            category_scores['accessibility'] = 100.0 if page.get('alt_text_coverage', 0) >= 0.8 else page.get('alt_text_coverage', 0) * 100
            
            # Calculate overall score
            overall_score = sum(
                category_scores[category] * weight 
                for category, weight in weights.items()
            )
            
            page_score = {
                'url': page['url'],
                'title': page.get('title', ''),
                'overall_score': round(overall_score, 1),
                'category_scores': {k: round(v, 1) for k, v in category_scores.items()}
            }
            
            page_scores.append(page_score)
        
        return page_scores
    
    def _save_json_results(self, results: Dict[str, Any], output_dir: Path) -> None:
        """Save complete results as JSON."""
        
        output_file = output_dir / 'detailed_scores.json'
        
        # Clean results for JSON serialization
        clean_results = self._clean_for_json(results)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(clean_results, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Detailed results saved to {output_file}")
    
    def _save_dashboard_data(self, results: Dict[str, Any], output_dir: Path) -> None:
        """Save dashboard-compatible data."""
        
        # Format data for dashboard integration
        dashboard_data = {
            'metadata': results['metadata'],
            'overall_score': results['overall_score'],
            'analysis_summary': results['analysis_summary'],
            'recommendations': results['recommendations'][:10],  # Top 10 recommendations
            'page_scores': results['page_scores'],
            'benchmarks': results['benchmarks']
        }
        
        output_file = output_dir / 'dashboard-data.json'
        
        # Clean data for JSON serialization
        clean_dashboard_data = self._clean_for_json(dashboard_data)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(clean_dashboard_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Dashboard data saved to {output_file}")
    
    def _save_html_report(self, results: Dict[str, Any], output_dir: Path) -> None:
        """Save human-readable HTML report."""
        
        # For now, create a simple HTML report
        # In a full implementation, this would use Jinja2 templates
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>GEO Analysis Report - {results['metadata']['website_name']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ border-bottom: 2px solid #ccc; padding-bottom: 20px; }}
        .score {{ font-size: 24px; font-weight: bold; color: #2c5aa0; }}
        .category {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; }}
        .recommendation {{ margin: 10px 0; padding: 10px; background: #f9f9f9; }}
        .high {{ border-left: 4px solid #d32f2f; }}
        .medium {{ border-left: 4px solid #f57c00; }}
        .low {{ border-left: 4px solid #388e3c; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>GEO Analysis Report</h1>
        <h2>{results['metadata']['website_name']}</h2>
        <p><strong>URL:</strong> {results['metadata']['website_url']}</p>
        <p><strong>Analysis Date:</strong> {results['metadata']['timestamp'][:10]}</p>
        <p><strong>Pages Analyzed:</strong> {results['metadata']['pages_analyzed']}</p>
    </div>
    
    <div class="score">
        Overall Score: {results['overall_score']['total_score']}/100 ({results['overall_score']['grade']})
    </div>
    
    <h3>Category Scores</h3>
    """
        
        for category, score in results['overall_score']['category_scores'].items():
            category_name = category.replace('_', ' ').title()
            html_content += f'<div class="category"><strong>{category_name}:</strong> {score}/100</div>'
        
        html_content += '<h3>Top Recommendations</h3>'
        
        for rec in results['recommendations'][:10]:
            priority_class = rec.get('priority', 'medium')
            html_content += f"""
            <div class="recommendation {priority_class}">
                <strong>{rec['title']}</strong><br>
                {rec['description']}<br>
                <small>Priority: {rec['priority'].title()} | Impact: {rec['estimated_impact'].title()}</small>
            </div>
            """
        
        html_content += '</body></html>'
        
        output_file = output_dir / 'geo_analysis_report.html'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"HTML report saved to {output_file}")
    
    def _clean_for_json(self, obj: Any) -> Any:
        """Clean object for JSON serialization by converting datetime objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {key: self._clean_for_json(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._clean_for_json(item) for item in obj]
        else:
            return obj
    
    def _get_generated_files(self, output_dir: Path) -> List[str]:
        """Get list of generated output files."""
        
        files = []
        for file in output_dir.glob('*'):
            if file.is_file():
                files.append(file.name)
        
        return sorted(files)