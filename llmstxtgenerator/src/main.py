import logging
import sys
from typing import Dict, Optional
import os

from .config_manager import ConfigManager
from .crawler import WebsiteCrawler
from .analyzer import ContentAnalyzer
from .generator import LLMSTextGenerator

# Configure logging
def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def run_generator(config_path: str = "config.yaml", **kwargs) -> Dict:
    # Load configuration
    config = ConfigManager(config_path)
    
    # Override config with command line arguments
    if kwargs.get('url'):
        config.update('website.url', kwargs['url'])
    if kwargs.get('name'):
        config.update('website.name', kwargs['name'])
    if kwargs.get('description'):
        config.update('website.description', kwargs['description'])
    if kwargs.get('max_pages'):
        config.update('generation.max_pages', kwargs['max_pages'])
    if kwargs.get('max_depth'):
        config.update('generation.max_depth', kwargs['max_depth'])
    if kwargs.get('output_dir'):
        config.update('output.directory', kwargs['output_dir'])
    if kwargs.get('no_ai'):
        config.update('analysis.use_ai_descriptions', False)
    
    # Setup logging
    setup_logging(kwargs.get('verbose', False))
    logger = logging.getLogger(__name__)
    
    logger.info(f"Starting LLMS.txt generation for {config.website_url}")
    
    try:
        # Step 1: Crawl website
        logger.info("Step 1/4: Crawling website...")
        crawler = WebsiteCrawler(config)
        pages = crawler.crawl()
        
        if not pages:
            logger.error("No pages found during crawling")
            return {'status': 'error', 'message': 'No pages found during crawling'}
        
        # Step 2: Analyze content
        logger.info("Step 2/4: Analyzing content structure...")
        analyzer = ContentAnalyzer(config)
        analysis = analyzer.analyze_site_structure(pages)
        
        # Step 3: Enhance link descriptions if needed
        logger.info("Step 3/4: Enhancing content descriptions...")
        for section_name, links in analysis['sections'].items():
            analysis['sections'][section_name] = analyzer.generate_link_descriptions(links, pages)
        
        # Step 4: Generate LLMS.txt files
        logger.info("Step 4/4: Generating LLMS.txt files...")
        generator = LLMSTextGenerator(config, analysis, pages)
        results = generator.generate()
        
        # Report results
        logger.info("Generation complete!")
        logger.info(f"Files generated: {len(results)}")
        for format, filepath in results.items():
            if filepath and os.path.exists(filepath):
                logger.info(f"  - {format}: {filepath}")
        
        # Launch dashboard if requested
        if kwargs.get('dashboard'):
            launch_dashboard(results.get('dashboard'))
        
        return {
            'status': 'success',
            'files_generated': len(results),
            'results': results,
            'metrics': {
                'pages_crawled': len(pages),
                'sections_found': len(analysis['sections']),
                'site_name': analysis.get('site_name', ''),
                'site_description': analysis.get('site_description', '')
            }
        }
        
    except Exception as e:
        logger.error(f"Error during generation: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'message': str(e)
        }

def launch_dashboard(dashboard_file: Optional[str]):
    if not dashboard_file or not os.path.exists(dashboard_file):
        logging.warning("Dashboard file not found")
        return
    
    dashboard_path = os.path.abspath("../dashboard/index.html")
    if os.path.exists(dashboard_path):
        import webbrowser
        webbrowser.open(f"file://{dashboard_path}")
        logging.info(f"Dashboard launched: {dashboard_path}")
    else:
        logging.warning("Dashboard not found. Please ensure the dashboard is set up in ../dashboard/")