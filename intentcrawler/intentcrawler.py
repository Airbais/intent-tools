#!/usr/bin/env python3

import os
import sys
import yaml
import logging
import argparse
import shutil
from datetime import datetime, timedelta
from typing import Dict, Any

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.crawler import WebCrawler
from src.content_processor import ContentProcessor
from src.llmstxt_formatter import LLMSTXTFormatter
from src.site_analyzer import SiteStructureAnalyzer
from src.intent_extractor import IntentExtractor
from src.enhanced_intent_extractor import EnhancedIntentExtractor
from src.user_intent_extractor import UserIntentExtractor
from src.report_generator import ReportGenerator
from src.dashboard import IntentDashboard

def setup_logging(log_level: str = 'INFO'):
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('intentcrawler.log')
        ]
    )

def load_config(config_file: str = 'config.yaml') -> Dict[str, Any]:
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logging.warning(f"Config file {config_file} not found. Using defaults.")
        return {
            'crawler': {'max_pages': 100, 'rate_limit': 2, 'respect_robots': True, 'timeout': 30},
            'content': {'min_content_length': 100, 'max_summary_length': 500},
            'intents': {'min_cluster_size': 3, 'similarity_threshold': 0.7, 'baseline_categories': ['informational', 'navigational', 'transactional']},
            'dashboard': {'port': 8050, 'auto_open_browser': True},
            'output': {'base_directory': 'results', 'date_format': '%Y-%m-%d', 'keep_past_results': 7, 'overwrite_today': True}
        }

def manage_results_directory(config: Dict[str, Any]) -> str:
    """Create and manage results directory structure based on configuration."""
    output_config = config.get('output', {})
    base_dir = output_config.get('base_directory', 'results')
    date_format = output_config.get('date_format', '%Y-%m-%d')
    keep_past_results = output_config.get('keep_past_results', 7)
    
    logger = logging.getLogger(__name__)
    
    # Create base results directory if it doesn't exist
    os.makedirs(base_dir, exist_ok=True)
    
    # Get today's date folder
    today = datetime.now().strftime(date_format)
    today_dir = os.path.join(base_dir, today)
    
    # Create today's directory
    os.makedirs(today_dir, exist_ok=True)
    
    # Clean up old results if configured
    if keep_past_results >= 0:
        logger.info(f"Cleaning up old results, keeping last {keep_past_results} days")
        cleanup_old_results(base_dir, keep_past_results, date_format)
    
    return today_dir

def cleanup_old_results(base_dir: str, keep_days: int, date_format: str):
    """Remove result directories older than keep_days."""
    logger = logging.getLogger(__name__)
    
    try:
        # Get all directories in base_dir
        dirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
        
        # Parse dates and sort
        date_dirs = []
        for d in dirs:
            try:
                dir_date = datetime.strptime(d, date_format)
                date_dirs.append((dir_date, d))
            except ValueError:
                logger.warning(f"Skipping non-date directory: {d}")
        
        # Sort by date (newest first)
        date_dirs.sort(reverse=True)
        
        # Remove directories beyond keep_days
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        for dir_date, dir_name in date_dirs:
            if dir_date < cutoff_date:
                dir_path = os.path.join(base_dir, dir_name)
                logger.info(f"Removing old results directory: {dir_path}")
                shutil.rmtree(dir_path)
    
    except Exception as e:
        logger.error(f"Error cleaning up old results: {e}")

def get_latest_results_directory(base_dir: str = 'results') -> str:
    """Get the path to the most recent results directory."""
    if not os.path.exists(base_dir):
        return None
    
    dirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    if not dirs:
        return None
    
    # Sort directories by name (which should be dates)
    dirs.sort(reverse=True)
    return os.path.join(base_dir, dirs[0])

def analyze_website(website_url: str, config: Dict[str, Any], output_dir: str = None) -> str:
    logger = logging.getLogger(__name__)
    logger.info(f"Starting analysis of {website_url}")
    
    # Use provided output_dir or get from config
    if output_dir is None:
        output_dir = manage_results_directory(config)
    
    logger.info(f"Results will be saved to: {output_dir}")
    
    crawler_config = config.get('crawler', {})
    crawler = WebCrawler(
        base_url=website_url,
        max_pages=crawler_config.get('max_pages', 100),
        rate_limit=crawler_config.get('rate_limit', 2),
        respect_robots=crawler_config.get('respect_robots', True),
        timeout=crawler_config.get('timeout', 30)
    )
    
    logger.info("Starting web crawl...")
    use_sitemap = crawler_config.get('use_sitemap', True)
    pages = crawler.crawl(use_sitemap=use_sitemap)
    logger.info(f"Crawled {len(pages)} pages")
    
    if not pages:
        logger.error("No pages were successfully crawled")
        return ""
    
    content_config = config.get('content', {})
    processor = ContentProcessor(
        max_summary_length=content_config.get('max_summary_length', 500),
        min_content_length=content_config.get('min_content_length', 100)
    )
    
    logger.info("Processing page content...")
    processed_contents = {}
    for page in pages:
        try:
            # Use raw_html if available, otherwise try processing the content
            html_to_process = page.raw_html if page.raw_html else page.content
            processed = processor.process_content(html_to_process, page.url)
            if processed:
                processed_contents[page.url] = processed
        except Exception as e:
            logger.warning(f"Failed to process {page.url}: {e}")
    
    logger.info(f"Successfully processed {len(processed_contents)} pages")
    
    site_analyzer = SiteStructureAnalyzer()
    logger.info("Analyzing site structure...")
    site_structure = site_analyzer.analyze_site_structure(pages)
    structure_data = site_analyzer.export_structure_data()
    
    intent_config = config.get('intents', {})
    extraction_method = intent_config.get('extraction_method', 'user_intent')
    
    # Use user intent extractor by default
    if extraction_method == 'user_intent':
        logger.info("Using user intent extraction (focuses on customer goals)")
        intent_extractor = UserIntentExtractor(config=intent_config)
        intent_data = intent_extractor.extract_intents(processed_contents)
    elif extraction_method == 'dynamic':
        logger.info("Using enhanced dynamic intent extraction")
        intent_extractor = EnhancedIntentExtractor(config=intent_config)
        intent_data = intent_extractor.extract_intents(processed_contents)
    else:
        # Fall back to original extractor
        logger.info("Using original intent extraction")
        intent_extractor = IntentExtractor(
            baseline_categories=intent_config.get('baseline_categories', ['informational', 'navigational', 'transactional'])
        )
        intent_data = intent_extractor.extract_intents(
            processed_contents,
            min_cluster_size=intent_config.get('min_cluster_size', 3),
            similarity_threshold=intent_config.get('similarity_threshold', 0.7)
        )
    
    logger.info(f"Discovered {len(intent_data.get('discovered_intents', []))} intent clusters")
    
    from urllib.parse import urlparse
    site_name = urlparse(website_url).netloc.replace('www.', '').replace('.com', '').title()
    
    formatter = LLMSTXTFormatter(site_name=site_name)
    llmstxt_content = formatter.format_as_llmstxt(pages, processed_contents)
    
    llmstxt_dir = os.path.join(output_dir, 'llmstxt')
    llmstxt_file = formatter.save_llmstxt(llmstxt_content, llmstxt_dir)
    formatter.create_section_files(pages, processed_contents, llmstxt_dir)
    
    logger.info(f"Generated llmstxt files in {llmstxt_dir}")
    
    report_generator = ReportGenerator(output_dir)
    
    structured_report = report_generator.generate_structured_report(
        intent_data, structure_data, llmstxt_content, website_url
    )
    
    llm_export = report_generator.generate_llm_export(
        intent_data, structure_data, website_url
    )
    
    dashboard_data = report_generator.generate_dashboard_data(
        intent_data, structure_data
    )
    
    summary_report = report_generator.generate_summary_report(
        intent_data, structure_data, website_url
    )
    
    logger.info("Analysis complete!")
    logger.info(f"Results saved to: {output_dir}")
    logger.info(f"- Structured report: {structured_report}")
    logger.info(f"- LLM export: {llm_export}")
    logger.info(f"- Dashboard data: {dashboard_data}")
    logger.info(f"- Summary: {summary_report}")
    
    return dashboard_data

def main():
    parser = argparse.ArgumentParser(description='Website Intent Analysis Tool')
    parser.add_argument('url', nargs='?', help='Website URL to analyze')
    parser.add_argument('--config', default='config.yaml', help='Configuration file path')
    parser.add_argument('--output', help='Output directory (overrides config)')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    parser.add_argument('--dashboard', action='store_true', help='Launch interactive dashboard after analysis')
    parser.add_argument('--dashboard-only', action='store_true', help='Launch dashboard with latest results')
    parser.add_argument('--dashboard-date', help='Launch dashboard with results from specific date (YYYY-MM-DD)')
    parser.add_argument('--list-results', action='store_true', help='List available result dates')
    
    args = parser.parse_args()
    
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    config = load_config(args.config)
    
    # Handle listing results
    if args.list_results:
        base_dir = config.get('output', {}).get('base_directory', 'results')
        if os.path.exists(base_dir):
            dirs = sorted([d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))], reverse=True)
            if dirs:
                logger.info("Available result dates:")
                for d in dirs:
                    logger.info(f"  - {d}")
            else:
                logger.info("No results found")
        else:
            logger.info("Results directory does not exist")
        return
    
    # Handle dashboard-only mode
    if args.dashboard_only or args.dashboard_date:
        base_dir = config.get('output', {}).get('base_directory', 'results')
        
        if args.dashboard_date:
            results_dir = os.path.join(base_dir, args.dashboard_date)
        else:
            results_dir = get_latest_results_directory(base_dir)
        
        if not results_dir or not os.path.exists(results_dir):
            logger.error("No results found to display")
            return
        
        dashboard_file = os.path.join(results_dir, 'dashboard-data.json')
        if not os.path.exists(dashboard_file):
            logger.error(f"Dashboard data not found at {dashboard_file}")
            return
        
        logger.info(f"Launching dashboard with data from {results_dir}")
        dashboard = IntentDashboard(data_file=dashboard_file)
        dashboard.run(debug=False)
        return
    
    if not args.url:
        parser.error("URL is required unless using --dashboard-only or --list-results")
        return
    
    try:
        # Use custom output directory if specified, otherwise use config
        output_dir = args.output if args.output else None
        dashboard_data_file = analyze_website(args.url, config, output_dir)
        
        if args.dashboard and dashboard_data_file:
            logger.info("Launching interactive dashboard...")
            dashboard = IntentDashboard(data_file=dashboard_data_file)
            dashboard.run(debug=False)
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()